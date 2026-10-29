extends Node3D
## A cached soft halo and real nearby light, including on GL Compatibility.
var halo:Sprite3D
var light:OmniLight3D
var tint=Color("a8ddff")

func _ready():
    var picture=Image.create(96,96,false,Image.FORMAT_RGBA8)
    for y in range(96):
        for x in range(96):
            var p=(Vector2(x,y)-Vector2(47.5,47.5))/47.5
            var radius=p.length()
            if radius>=1.0:continue
            var haze=exp(-radius*radius*5.5)*pow(1.0-radius,0.7)*0.52
            var rays=pow(absf(cos(p.angle()*3.0)),24.0)*0.20
            rays*=smoothstep(0.20,0.38,radius)*pow(1.0-radius,1.6)
            picture.set_pixel(x,y,Color(1,1,1,haze+rays))
    halo=Sprite3D.new()
    halo.name="SoftAntennaRays"
    halo.texture=ImageTexture.create_from_image(picture)
    halo.pixel_size=0.007
    halo.billboard=BaseMaterial3D.BILLBOARD_ENABLED
    halo.shaded=false
    halo.position.z=0.15
    halo.cast_shadow=GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
    add_child(halo)
    light=OmniLight3D.new()
    light.name="GentleAntennaLight"
    light.omni_range=0.85
    light.light_energy=0.35
    light.shadow_enabled=false
    add_child(light)
    update_glow(0.0,"idle",0.0)

func update_glow(time:float,mood:String,delta:float):
    var target=Color("a8ddff")
    if mood=="laugh":target=Color("ffe2a2")
    elif mood=="angry":target=Color("ffb59a")
    elif mood=="love":target=Color("ffc5df")
    tint=tint.lerp(target,minf(1.0,delta*5.0))
    var pulse=1.0+0.055*sin(time*2.4)
    var joy=0.12 if mood=="laugh" else 0.0
    halo.modulate=Color(tint.r,tint.g,tint.b,0.82+joy)
    halo.scale=Vector3.ONE*(pulse+joy)
    light.light_color=tint
    light.light_energy=0.32+0.06*sin(time*2.4)+joy
