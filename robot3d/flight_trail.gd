extends Window
## World-space smoke in a click-through window owned by the desktop avatar.
const LIFETIME := 1.80
const SPACING := 6.0
const MAX_PUFFS := 128
const WINDOW_STEP := 64
const SMOKE_MASK := preload("res://flight_smoke.gdshader")

class Puff:
    var origin: Vector2
    var born: float
    var drift: Vector2
    var angle: float
    var spin: float
    var size_factor: float

    func center_at(age: float) -> Vector2:
        return origin + drift*age + Vector2(sin(angle+age*3.0)-sin(angle), 0.0)*age*4.0

    func radius_at(age: float) -> float:
        return size_factor*lerpf(11.0, 35.0, age/LIFETIME)

class Smoke extends Node2D:
    var puffs: Array[Puff] = []
    var clock := 0.0
    var stamp: ImageTexture

    func _ready() -> void:
        texture_filter = CanvasItem.TEXTURE_FILTER_LINEAR
        var noise := FastNoiseLite.new()
        noise.seed = 2351
        noise.frequency = 0.063
        var image := Image.create_empty(80, 80, false, Image.FORMAT_RGBA8)
        for y in 80:
            for x in 80:
                var uv := (Vector2(x, y)-Vector2(39.5, 39.5))/39.5
                var grain := noise.get_noise_2d(x, y)
                var edge := uv.length() + 0.19*grain + 0.055*sin(uv.angle()*3.0)*uv.length()
                var density := (1.0-smoothstep(0.05, 0.94, edge))*(0.74+0.24*grain)
                image.set_pixel(x, y, Color(1.0, 1.0, 1.0, density))
        stamp = ImageTexture.create_from_image(image)

    func _draw() -> void:
        var origin := Vector2(get_window().position)
        for puff in puffs:
            var age := clampf(clock-puff.born, 0.0, LIFETIME)
            var life := age/LIFETIME
            var radius := puff.radius_at(age)
            var center := puff.center_at(age)-origin
            var color := Color(0.80, 0.89, 0.94).lerp(Color(0.57, 0.70, 0.78), life)
            color.a = 0.50*(1.0-smoothstep(0.10, 1.0, life))
            draw_set_transform(center, puff.angle+puff.spin*age, Vector2(1.0, 0.80))
            draw_texture_rect(stamp, Rect2(-Vector2.ONE*radius, Vector2.ONE*2.0*radius), false, color)

var smoke := Smoke.new()
var mask := ShaderMaterial.new()
var _last_point := Vector2.ZERO
var _started := false
var _remainder := 0.0
var _sequence := 0

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
    mask.shader = SMOKE_MASK
    smoke.material = mask
    add_child(smoke)

func sample(point: Vector2, face: Vector2, chest: Vector2, delta: float) -> void:
    var distance := _last_point.distance_to(point)
    # A suspended app or a relocated monitor starts a new plume at the new position.
    if not _started or delta > 0.35 or distance > 240.0:
        clear_trail()
        _started = true
        _last_point = point
        return
    smoke.clock += delta
    while not smoke.puffs.is_empty() and smoke.clock-smoke.puffs.front().born >= LIFETIME:
        smoke.puffs.pop_front()
    if distance > 0.001:
        var direction := (point-_last_point)/distance
        var offset := SPACING-_remainder
        while offset <= distance:
            var born := smoke.clock-delta*(1.0-offset/distance)
            _emit_puff(_last_point+direction*offset, direction, born)
            offset += SPACING
        _remainder = fposmod(_remainder+distance, SPACING)
    _last_point = point
    if smoke.puffs.is_empty():
        hide()
        return
    var bounds := Rect2(point, Vector2.ZERO)
    for puff in smoke.puffs:
        var age := smoke.clock-puff.born
        var radius := puff.radius_at(age)
        var center := puff.center_at(age)
        bounds = bounds.expand(center-Vector2.ONE*radius).expand(center+Vector2.ONE*radius)
    if not visible or not Rect2(Vector2(position), Vector2(size)).encloses(bounds.grow(2.0)):
        # Allocate in blocks with spare room so native windows seldom need resizing.
        var blocks := Vector2i(((bounds.size+Vector2(40, 40))/float(WINDOW_STEP)).ceil())
        size = size.max(blocks*WINDOW_STEP)
        position = Vector2i((bounds.get_center()-Vector2(size)*0.5).floor())
    if not visible:
        show()
    mask.set_shader_parameter("face_center", face-Vector2(position))
    mask.set_shader_parameter("chest_center", chest-Vector2(position))
    smoke.queue_redraw()

func _emit_puff(point: Vector2, direction: Vector2, born: float) -> void:
    if smoke.puffs.size() >= MAX_PUFFS:
        smoke.puffs.pop_front()
    var puff := Puff.new()
    var phase := float(_sequence)*2.39996
    var curl := float(_sequence)*0.19
    _sequence += 1
    puff.origin = point + direction.orthogonal()*(1.8*sin(curl*2.2)+0.7*sin(phase))
    puff.born = born
    puff.drift = direction.orthogonal()*(11.0*sin(curl)+3.0*sin(2.2*curl)) + Vector2.UP*(11.0+4.0*cos(curl))
    puff.angle = phase
    puff.spin = 0.55*cos(phase)
    puff.size_factor = 1.0 + 0.14*sin(phase*1.7)
    smoke.puffs.append(puff)

func clear_trail() -> void:
    hide()
    smoke.puffs.clear()
    smoke.clock = 0.0
    _started = false
    _remainder = 0.0
    _sequence = 0
