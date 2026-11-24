extends RefCounted
## Coordinates are desktop pixels, including negative monitor origins.
const HOP_SECONDS := 0.86
const WAVE_SECONDS := 1.34
const FLIGHT_SPEED := 255.0
const TAKEOFF_TIME := 0.16

var flying := false
var jumping := false
var waving := false
var location := Vector2.ZERO
var velocity := Vector2.ZERO
var lean := Vector2.ZERO
var follow_through := Vector2.ZERO
var _lean_rate := Vector2.ZERO
var _follow_rate := Vector2.ZERO
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
    _angular_speed = minf(1.1, FLIGHT_SPEED / maxf(1.0, maxf(radius.x, 1.45*radius.y)))
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

func reset_flight_pose() -> void:
    lean = Vector2.ZERO
    follow_through = Vector2.ZERO
    _lean_rate = Vector2.ZERO
    _follow_rate = Vector2.ZERO

func advance(delta: float) -> void:
    var dt := clampf(delta, 0.0, 0.10)
    if waving:
        _wave_time += dt
        hand_raise = smoothstep(0.0, 0.24, _wave_time) * (1.0-smoothstep(1.04, WAVE_SECONDS, _wave_time))
        hand_swing = hand_raise * sin((_wave_time-0.24)*TAU*2.5)
        waving = _wave_time < WAVE_SECONDS
    if flying or jumping:
        _advance_travel(dt)
    if flying or lean != Vector2.ZERO or follow_through != Vector2.ZERO:
        _advance_flight_pose(dt)

func _advance_travel(dt: float) -> void:
    var previous := location
    if flying:
        _flight_time += dt
        # Ease into the original path from rest. Its speed and extent then match cruising flight.
        var phase_time := (_flight_time-TAKEOFF_TIME*(1.0-exp(-_flight_time/TAKEOFF_TIME))) * _angular_speed
        var angles := _phase + Vector2(phase_time, phase_time*1.45)
        _base = _bounds.get_center() + _bounds.size*0.5*Vector2(cos(angles.x), cos(angles.y))
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
    if flying and dt > 0.0:
        # Include an in-flight hop in the direction seen by the player.
        velocity = (location-previous)/dt

func _advance_flight_pose(dt: float) -> void:
    var target := (velocity / FLIGHT_SPEED).limit_length(1.0)
    var remaining := dt
    while remaining > 0.0:
        var step := minf(remaining, 1.0/120.0)
        remaining -= step
        _lean_rate += ((target-lean)*130.0 - _lean_rate*15.0)*step
        lean += _lean_rate*step
        _follow_rate += ((lean-follow_through)*60.0 - _follow_rate*8.8)*step
        follow_through += _follow_rate*step
    if not flying and lean.length_squared()+follow_through.length_squared()+_lean_rate.length_squared()+_follow_rate.length_squared() < 0.000001:
        reset_flight_pose()
