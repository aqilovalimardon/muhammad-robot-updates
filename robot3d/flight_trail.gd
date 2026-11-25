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
    var heading: Vector2

    func _init(at: Vector2, time: float, length_along: float, starts_stroke: bool, direction: Vector2):
        point = at
        born = time
        arc = length_along
        first = starts_stroke
        heading = direction

class Ribbons extends Node2D:
    const PROFILE := [-1.0, -0.59, -0.17, 0.0, 0.17, 0.59, 1.0]
    const JADE := Color("34d9c4")
    const ICE := Color("e9fffa")
    const BLUE := Color("2d92c5")
    const PEARL := Color("cbf5ff")
    const AMBER := Color("dfa85f")
    const GOLD := Color("fff2c5")

    # Lateral position, half-width in desktop pixels, tip age, edge and core.
    # Each blade starts at a different point across the robot's back.
    const BLADES := [
        [-0.98, 3.8, 0.66, BLUE, PEARL],
        [-0.73, 7.2, 0.86, JADE, ICE],
        [-0.43, 3.3, 0.71, BLUE, PEARL],
        [-0.16, 14.0, 1.00, JADE, ICE],
        [ 0.13, 2.5, 0.83, AMBER, GOLD],
        [ 0.39, 8.2, 0.93, BLUE, PEARL],
        [ 0.70, 4.8, 0.80, JADE, ICE],
        [ 1.00, 3.2, 0.62, BLUE, PEARL],
    ]

    var knots: Array[Knot] = []
    var clock := 0.0
    var vertices := PackedVector2Array()
    var colors := PackedColorArray()
    var indices := PackedInt32Array()

    func add_band(center: Vector2, normal: Vector2, radius: float, edge: Color,
            core: Color, opacity: float, previous: int, soft := false) -> int:
        var base := vertices.size()
        for j in PROFILE.size():
            var across: float = PROFILE[j]
            var color := edge
            color.a = 0.0
            if absf(across) < 0.99:
                color = edge.lerp(core, 1.0-smoothstep(0.0, 0.60, absf(across)))
                if soft:
                    color.a = opacity * pow(1.0-absf(across), 1.8)
                else:
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
        var last_veil := -1
        var last_blade := PackedInt32Array()
        last_blade.resize(BLADES.size())
        last_blade.fill(-1)
        for i in knots.size():
            var knot := knots[i]
            var left := knot.point
            var right := knot.point
            if i>0 and not knot.first:
                left = knots[i-1].point
            else:
                last_veil = -1
                last_blade.fill(-1)
            if i+1 < knots.size() and not knots[i+1].first:
                right = knots[i+1].point
            var tangent := (right-left).normalized()
            if tangent == Vector2.ZERO:
                tangent = (knot.point-left).normalized()
                if tangent == Vector2.ZERO:
                    continue
            # The emitter moves backwards relative to the desktop on takeoff.
            # Orient its fan using the body's actual travel direction during that sweep.
            if knot.heading != Vector2.ZERO:
                tangent = knot.heading
            var normal := tangent.orthogonal()
            var life := clampf((clock-knot.born)/LIFETIME, 0.0, 1.0)
            var fade := (1.0-smoothstep(0.05, 1.0, life))*smoothstep(0.0, 28.0, knot.arc)
            var spread := smoothstep(0.0, 0.28, life)
            var phase := knot.arc*0.014 - life*2.0
            var center := knot.point-origin + normal*(4.0*spread*sin(phase))
            var taper := sqrt(fade)
            var fan := lerpf(35.0, 56.0, spread) * (0.45+0.55*taper)*smoothstep(0.0, 65.0, knot.arc)
            last_veil = add_band(center,normal,fan*taper,BLUE,JADE,0.36*fade,last_veil,true)
            for b in BLADES.size():
                var blade: Array = BLADES[b]
                var lane: float = blade[0]
                var radius: float = blade[1]
                var end_age: float = blade[2]
                var tip := 1.0-smoothstep(end_age-0.30, end_age, life)
                # The fine outer strokes break into pointed brush marks. The main
                # ribbons stay continuous from the robot to their individual tips.
                if b==0 or b==2 or b==7:
                    var u := fposmod(knot.arc+b*39.0, 166.0+b*8.0)/(166.0+b*8.0)
                    tip *= smoothstep(0.0,0.16,u)*(1.0-smoothstep(0.73,1.0,u))
                if tip*fade <= 0.0001:
                    last_blade[b] = -1
                    continue
                var sweep := sin(phase*1.13+b*0.94)*(2.0+7.5*spread)*taper
                var offset := lane*fan + sweep
                var swell := 0.78+0.22*cos(phase*1.7+b*1.2)
                var strand := center+normal*offset
                last_blade[b] = add_band(strand,normal,radius*swell*taper*sqrt(tip),
                        blade[3],blade[4],fade*tip,last_blade[b])
                if b==4 and i>0 and not knot.first and floori(knot.arc/111.0)!=floori(knots[i-1].arc/111.0):
                    add_glint(strand+normal*3.0,tangent,fade*tip)
        if not indices.is_empty():
            RenderingServer.canvas_item_add_triangle_array(get_canvas_item(), indices, vertices, colors)

var ribbons := Ribbons.new()
var mask := ShaderMaterial.new()
var _emitting := false
var _last_point := Vector2.ZERO
var _last_heading := Vector2.ZERO
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

func advance(delta: float, flying: bool, point: Vector2, face: Vector2, chest: Vector2, heading := Vector2.ZERO) -> void:
    if not flying and ribbons.knots.is_empty():
        return
    ribbons.clock += maxf(delta, 0.0)
    while not ribbons.knots.is_empty() and ribbons.clock-ribbons.knots.front().born >= LIFETIME:
        ribbons.knots.pop_front()
    if flying:
        if delta>0.35 or (not ribbons.knots.is_empty() and _last_point.distance_to(point)>240.0):
            clear_trail()
        _sample(point, delta, heading.normalized())
    else:
        end_emission()
    if ribbons.knots.size() < 2:
        if visible:hide()
        return
    var bounds := Rect2(ribbons.knots[0].point, Vector2.ZERO)
    for knot in ribbons.knots:
        bounds = bounds.expand(knot.point)
    bounds = bounds.grow(78.0)
    if not visible or not Rect2(Vector2(position), Vector2(size)).encloses(bounds):
        var blocks := Vector2i(((bounds.size+Vector2(40,40))/float(WINDOW_STEP)).ceil())
        size = size.max(blocks*WINDOW_STEP)
        position = Vector2i((bounds.get_center()-Vector2(size)*0.5).floor())
    if not visible:show()
    mask.set_shader_parameter("face_center", face-Vector2(position))
    mask.set_shader_parameter("chest_center", chest-Vector2(position))
    ribbons.queue_redraw()

func _sample(point: Vector2, delta: float, heading: Vector2) -> void:
    if not _emitting:
        _emitting = true
        _last_point = point
        _arc = 0.0
        _remainder = 0.0
        _last_heading = heading
        _add_knot(point,ribbons.clock,0.0,true,heading)
        return
    var distance := _last_point.distance_to(point)
    if distance <= 0.001:
        return
    var direction := (point-_last_point)/distance
    var offset := SPACING-_remainder
    while offset <= distance:
        var born := ribbons.clock-delta*(1.0-offset/distance)
        var sample_heading := heading
        if _last_heading != Vector2.ZERO and heading != Vector2.ZERO:
            sample_heading = _last_heading.slerp(heading, offset/distance)
        _add_knot(_last_point+direction*offset,born,_arc+offset,false,sample_heading)
        offset += SPACING
    _remainder = fposmod(_remainder+distance,SPACING)
    _arc += distance
    _last_point = point
    _last_heading = heading

func _add_knot(point: Vector2, born: float, arc: float, first: bool, heading: Vector2) -> void:
    if ribbons.knots.size() >= MAX_KNOTS:
        ribbons.knots.pop_front()
    ribbons.knots.append(Knot.new(point,born,arc,first,heading))

func end_emission() -> void:
    _emitting = false

func clear_trail() -> void:
    end_emission()
    hide()
    ribbons.knots.clear()
    ribbons.clock = 0.0
