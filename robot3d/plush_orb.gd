extends Control
## Cached canvas drawing: a softly shaded cream pom-pom with fine fuzzy edges.
func _ready():
    mouse_filter=Control.MOUSE_FILTER_IGNORE

func _draw():
    var rng=RandomNumberGenerator.new()
    rng.seed=2219
    var center=Vector2(32,32)
    # Airy outer fibers stay within the 64px transparent window.
    for i in range(260):
        var angle=TAU*i/260.0+rng.randf_range(-0.018,0.018)
        var normal=Vector2(cos(angle),sin(angle))
        var start=center+normal*rng.randf_range(23.0,25.5)
        var tip=center+normal*rng.randf_range(27.0,30.0)
        var middle=(start+tip)*0.5+normal.orthogonal()*rng.randf_range(-1.2,1.2)
        var cream=Color(0.94,0.83,0.67,rng.randf_range(0.35,0.82))
        draw_polyline(PackedVector2Array([start,middle,tip]),cream,0.75,true)
    draw_circle(center,25.5,Color("c6a77d"),true,-1.0,true)
    # Concentric offset shades give a soft round body instead of a flat button.
    for i in range(24):
        var u=float(i)/23.0
        var shade=Color("d6b98e").lerp(Color("f7e4c4"),u)
        draw_circle(center+Vector2(-2.3,-3.0)*u,25.0-i*0.70,shade,true,-1.0,true)
    for i in range(420):
        var angle=rng.randf()*TAU
        var radius=sqrt(rng.randf())*24.0
        var point=center+Vector2(cos(angle),sin(angle))*radius
        var direction=Vector2(cos(angle-0.35),sin(angle-0.35))
        var shade=Color(1.0,0.94,0.81,rng.randf_range(0.14,0.42))
        draw_line(point,point+direction*rng.randf_range(0.8,2.2),shade,0.6,true)
