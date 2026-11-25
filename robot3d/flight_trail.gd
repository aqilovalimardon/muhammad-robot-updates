extends Window
## A click-through desktop window for the light ribbons that follow the avatar.
const LIFETIME := 2.40
const SPACING := 5.0
const MAX_KNOTS := 224
const WINDOW_STEP := 64
const TRAIL_MASK := preload("res://flight_trail_mask.gdshader")

class Knot:
    var point: Vector2
    var born: float
    var arc: float
    var first: bool

    func _init(at: Vector2, time: float, length_along: float, starts_stroke: bool):
        point = at
        born = time
        arc = length_along
        first = starts_stroke

class Ribbons extends Node2D:
    const PROFILE := [-1.0, -0.59, -0.17, 0.0, 0.17, 0.59, 1.0]
    const JADE := Color("34d9c4")
    const ICE := Color("e9fffa")
    const BLUE := Color("4d9beb")
    const PEARL := Color("cdefff")
    const AMBER := Color("dfa85f")
    const GOLD := Color("fff2c5")

    var knots: Array[Knot] = []
    var clock := 0.0
    var vertices := PackedVector2Array()
    var colors := PackedColorArray()
    var indices := PackedInt32Array()

    func add_band(center: Vector2, normal: Vector2, radius: float, edge: Color,
            core: Color, opacity: float, previous: int) -> int:
        var base := vertices.size()
        for j in PROFILE.size():
            var across: float = PROFILE[j]
            var color := edge
            color.a = 0.0
            if absf(across) < 0.99:
                color = edge.lerp(core, 1.0-smoothstep(0.0, 0.60, absf(across)))
                color.a = opacity * (1.0-0.55*absf(across))
            vertices.append(center+normal*radius*across)
            colors.append(color)
            if previous >= 0 and j > 0:
                indices.append(previous+j-1)
                indices.append(base+j-1)
                indices.append(base+j)
                indices.append(previous+j-1)
                indices.append(base+j)
                indices.append(previous+j)
        return base

    func add_glint(center: Vector2, tangent: Vector2, alpha: float) -> void:
        var base := vertices.size()
        var side := tangent.orthogonal()
        for offset in [tangent*3.8, side*1.25, -tangent*3.8, -side*1.25]:
            vertices.append(center+offset)
            colors.append(Color(GOLD,alpha))
        indices.append_array(PackedInt32Array([base,base+1,base+2,base,base+2,base+3]))

    func _draw() -> void:
        vertices.clear()
        colors.clear()
        indices.clear()
        var origin := Vector2(get_window().position)
        var last_jade := -1
        var last_blue := -1
        var last_gold := -1
        for i in knots.size():
            var knot := knots[i]
            var left := knot.point
            var right := knot.point
            if i>0 and not knot.first:
                left = knots[i-1].point
            else:
                last_jade = -1
                last_blue = -1
                last_gold = -1
            if i+1 < knots.size() and not knots[i+1].first:
                right = knots[i+1].point
            var tangent := (right-left).normalized()
            if tangent == Vector2.ZERO:
                tangent = (knot.point-left).normalized()
                if tangent == Vector2.ZERO:
                    continue
            var normal := tangent.orthogonal()
            var life := clampf((clock-knot.born)/LIFETIME, 0.0, 1.0)
            var fade := (1.0-smoothstep(0.05, 1.0, life))*smoothstep(0.0, 28.0, knot.arc)
            var spread := smoothstep(0.0, 0.20, life)
            var phase := knot.arc*0.024 - life*2.1
            var center := knot.point-origin + normal*(3.0*spread*sin(phase))
            var twist := sin(phase*0.72+0.8)
            var taper := sqrt(fade)
            var width := (4.2+1.1*cos(phase))*taper
            last_jade = add_band(center, normal, width, JADE, ICE, fade, last_jade)
            var blue_offset := spread*(4.5+6.2*twist)
            last_blue = add_band(center+normal*blue_offset, normal, 2.1*taper, BLUE, PEARL, 0.85*fade, last_blue)
            var gold_offset := -spread*(6.0+6.7*sin(phase*0.74+0.25))
            last_gold = add_band(center+normal*gold_offset, normal, 1.35*taper, AMBER, GOLD, 0.83*fade, last_gold)
            if i>0 and not knot.first and floori(knot.arc/108.0)!=floori(knots[i-1].arc/108.0):
                add_glint(center+normal*(gold_offset-3.5),tangent,0.83*fade)
        if not indices.is_empty():
            RenderingServer.canvas_item_add_triangle_array(get_canvas_item(), indices, vertices, colors)

var ribbons := Ribbons.new()
var mask := ShaderMaterial.new()
var _emitting := false
var _last_point := Vector2.ZERO
var _remainder := 0.0
var _arc := 0.0

func _init():
    visible = false
    force_native = true
    transparent = true
    transparent_bg = true
    borderless = true
    unfocusable = true
    mouse_passthrough = true
    transient = true
    unresizable = true
    disable_3d = true
    size = Vector2i(192, 128)
    title = "Muhammad Robot flight trail"
    mask.shader = TRAIL_MASK
    ribbons.material = mask
    add_child(ribbons)

func advance(delta: float, flying: bool, point: Vector2, face: Vector2, chest: Vector2) -> void:
    if not flying and ribbons.knots.is_empty():
        return
    ribbons.clock += maxf(delta, 0.0)
    while not ribbons.knots.is_empty() and ribbons.clock-ribbons.knots.front().born >= LIFETIME:
        ribbons.knots.pop_front()
    if flying:
        if delta>0.35 or (not ribbons.knots.is_empty() and _last_point.distance_to(point)>240.0):
            clear_trail()
        _sample(point, delta)
    else:
        end_emission()
    if ribbons.knots.size() < 2:
        if visible:hide()
        return
    var bounds := Rect2(ribbons.knots[0].point, Vector2.ZERO)
    for knot in ribbons.knots:
        bounds = bounds.expand(knot.point)
    bounds = bounds.grow(23.0)
    if not visible or not Rect2(Vector2(position), Vector2(size)).encloses(bounds):
        var blocks := Vector2i(((bounds.size+Vector2(40,40))/float(WINDOW_STEP)).ceil())
        size = size.max(blocks*WINDOW_STEP)
        position = Vector2i((bounds.get_center()-Vector2(size)*0.5).floor())
    if not visible:show()
    mask.set_shader_parameter("face_center", face-Vector2(position))
    mask.set_shader_parameter("chest_center", chest-Vector2(position))
    ribbons.queue_redraw()

func _sample(point: Vector2, delta: float) -> void:
    if not _emitting:
        _emitting = true
        _last_point = point
        _arc = 0.0
        _remainder = 0.0
        _add_knot(point,ribbons.clock,0.0,true)
        return
    var distance := _last_point.distance_to(point)
    if distance <= 0.001:
        return
    var direction := (point-_last_point)/distance
    var offset := SPACING-_remainder
    while offset <= distance:
        var born := ribbons.clock-delta*(1.0-offset/distance)
        _add_knot(_last_point+direction*offset,born,_arc+offset,false)
        offset += SPACING
    _remainder = fposmod(_remainder+distance,SPACING)
    _arc += distance
    _last_point = point

func _add_knot(point: Vector2, born: float, arc: float, first: bool) -> void:
    if ribbons.knots.size() >= MAX_KNOTS:
        ribbons.knots.pop_front()
    ribbons.knots.append(Knot.new(point,born,arc,first))

func end_emission() -> void:
    _emitting = false

func clear_trail() -> void:
    end_emission()
    hide()
    ribbons.knots.clear()
    ribbons.clock = 0.0
