extends RefCounted
## Coordinates are desktop pixels, including negative monitor origins.
const HOP_SECONDS := 0.86
const WAVE_SECONDS := 1.34

var flying := false
var jumping := false
var waving := false
var location := Vector2.ZERO
var velocity := Vector2.ZERO
var jump_height := 0.0
var crouch := 0.0
var hand_raise := 0.0
var hand_swing := 0.0
var _base := Vector2.ZERO
var _bounds := Rect2()
var _phase := Vector2.ZERO
var _angular_speed := 0.0
var _flight_time := 0.0
var _jump_time := 0.0
var _wave_time := 0.0

func _start_position(origin: Vector2i, limits: Rect2i) -> void:
    _bounds = Rect2(limits)
    _base = Vector2(origin).clamp(_bounds.position, _bounds.end)
    location = _base

func _start_phase(value: float, center: float, radius: float) -> float:
    if radius < 0.5:
        return 0.0
    var ratio := clampf((value-center)/radius, -1.0, 1.0)
    return acos(ratio) if ratio >= 0.0 else -acos(ratio)

func fly(origin: Vector2i, limits: Rect2i) -> void:
    if flying:
        return
    if not jumping:
        _start_position(origin, limits)
    var radius := _bounds.size * 0.5
    var center := _bounds.get_center()
    _phase = Vector2(_start_phase(_base.x, center.x, radius.x), _start_phase(_base.y, center.y, radius.y))
    _angular_speed = minf(1.1, 255.0 / maxf(1.0, maxf(radius.x, 1.45*radius.y)))
    _flight_time = 0.0
    flying = true

func jump(origin: Vector2i, limits: Rect2i) -> void:
    if jumping:
        return
    if not flying:
        _start_position(origin, limits)
    _jump_time = 0.0
    jumping = true

func wave() -> void:
    _wave_time = 0.0
    waving = true

func stop() -> void:
    flying = false
    jumping = false
    waving = false
    velocity = Vector2.ZERO
    jump_height = 0.0
    crouch = 0.0
    hand_raise = 0.0
    hand_swing = 0.0

func advance(delta: float) -> void:
    var dt := minf(delta, 0.10)
    if waving:
        _wave_time += dt
        hand_raise = smoothstep(0.0, 0.24, _wave_time) * (1.0-smoothstep(1.04, WAVE_SECONDS, _wave_time))
        hand_swing = hand_raise * sin((_wave_time-0.24)*TAU*2.5)
        waving = _wave_time < WAVE_SECONDS
    if not flying and not jumping:
        return
    if flying:
        _flight_time += dt * _angular_speed
        var angles := _phase + Vector2(_flight_time, _flight_time*1.45)
        _base = _bounds.get_center() + _bounds.size*0.5*Vector2(cos(angles.x), cos(angles.y))
        velocity = -_bounds.size*0.5*_angular_speed*Vector2(sin(angles.x), 1.45*sin(angles.y))
    if jumping:
        _jump_time += dt
        var u := clampf((_jump_time-0.13)/0.58, 0.0, 1.0)
        jump_height = 4.0*u*(1.0-u)
        var bend := clampf(_jump_time/0.13,0.0,1.0) if _jump_time<0.71 else clampf((_jump_time-0.71)/0.15,0.0,1.0)
        crouch = sin(PI*bend) if _jump_time<0.13 or _jump_time>0.71 else 0.0
        if _jump_time >= HOP_SECONDS:
            jumping = false
            jump_height = 0.0
            crouch = 0.0
    var clearance := clampf(_base.y-_bounds.position.y, 0.0, 104.0)
    location = _base - Vector2(0.0, jump_height*clearance)
