extends Window
## A small transparent, click-through desktop surface for the wake beyond the avatar.
const LIFETIME := 0.62
const FRAME_SIZE := Vector2i(384, 320)

class Ribbon extends Node2D:
    var points := PackedVector2Array()
    var times := PackedFloat64Array()
    var now := 0.0

    func _draw() -> void:
        var origin := Vector2(get_window().position)
        for i in range(1, points.size()):
            var fresh := clampf(1.0-(now-times[i])/LIFETIME, 0.0, 1.0)
            var start := points[i-1]-origin
            var end := points[i]-origin
            if start.distance_squared_to(end)<0.25:
                continue
            draw_line(start,end,Color(0.24,0.70,0.90,0.47*fresh),2.0+6.0*fresh,true)
            draw_line(start,end,Color(0.72,0.94,1.0,0.90*fresh),1.1+2.5*fresh,true)
            # Stationary accents remain in the wake as it fades.
            if int(times[i]*14.0) != int(times[i-1]*14.0):
                var normal := (end-start).normalized().orthogonal()
                var side := 1.0 if int(times[i]*14.0)%2==0 else -1.0
                draw_circle(end+normal*side*(4.0+5.0*(1.0-fresh)),0.7+1.4*fresh,Color(1.0,0.88,0.65,0.82*fresh),true,-1.0,true)

var ribbon := Ribbon.new()

func _init():
    visible = false
    force_native = true
    transparent = true
    transparent_bg = true
    borderless = true
    unfocusable = true
    mouse_passthrough = true
    # Owned by the always-on-top avatar, with no second taskbar entry.
    transient = true
    unresizable = true
    disable_3d = true
    size = FRAME_SIZE
    title = "Muhammad Robot flight trail"
    add_child(ribbon)

func sample(point: Vector2, delta: float) -> void:
    ribbon.now += delta
    while not ribbon.times.is_empty() and ribbon.now-ribbon.times[0] > LIFETIME:
        ribbon.times.remove_at(0)
        ribbon.points.remove_at(0)
    ribbon.points.append(point)
    ribbon.times.append(ribbon.now)
    var box := Rect2(point,Vector2.ZERO)
    for p in ribbon.points:
        box = box.expand(p)
    if not visible or not Rect2(Vector2(position),Vector2(FRAME_SIZE)).encloses(box.grow(12.0)):
        position = Vector2i((box.get_center()-Vector2(FRAME_SIZE)*0.5).round())
    if not visible:
        show()
    ribbon.queue_redraw()

func clear_trail() -> void:
    hide()
    ribbon.points.clear()
    ribbon.times.clear()
    ribbon.now = 0.0
