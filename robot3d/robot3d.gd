extends Node3D
# Muhammad Robot: actual Godot 3D meshes, light, fur, 3D eye & antenna movement.
# v2.2.18: expressive touch reactions and instant, quiet offline feedback sounds.
const Feedback = preload("res://robot_feedback.gd")
const DESK_SIZE=Vector2i(176,200)
const ORB_SIZE=Vector2i(54,54)
const CREAM=Color(0.89,0.78,0.64)
const ICE=Color(0.61,0.88,1.0)
var robot:Node3D
var head:Node3D
var antenna:Node3D
var pupils:Array[Node3D]=[]
var t=0.0
var dragging=false
var drag_from=Vector2i.ZERO
var window_from=Vector2i.ZERO
var drag_v=0.0
var hidden=false
var menu:PanelContainer
var belly:Button
var small_eye:Panel
var orb_left_eye:Panel
var orb_right_eye:Panel
var old_position=Vector2i.ZERO
var signal_file=""
var signal_clock=0.0
var orb_moved=false
var blinking=0.0
var bridge_file=""
var squish=0.0
var squish_velocity=0.0
var spring_head=0.0
var left_hand:MeshInstance3D
var right_hand:MeshInstance3D
var feedback
var sound_button:Button
var smile:Node3D
var surprised_mouth:Node3D
var emotion="idle"
var emotion_left=0.0
var hold_elapsed=0.0
var hold_excited=false

func _ready():
    var w=get_window()
    w.transparent=true
    w.borderless=true
    w.always_on_top=true
    w.unresizable=true
    w.size=DESK_SIZE
    var cmd=OS.get_cmdline_user_args()
    var idx=cmd.find("--robot-bridge")
    if idx>=0 and idx+1<cmd.size():
        bridge_file=cmd[idx+1]
    var sig=cmd.find("--robot-signal")
    if sig>=0 and sig+1<cmd.size():
        signal_file=cmd[sig+1]
    var screen=DisplayServer.screen_get_size()
    w.position=Vector2i(maxi(0,screen.x-220),90)
    old_position=w.position
    get_viewport().transparent_bg=true
    RenderingServer.set_default_clear_color(Color(0,0,0,0))
    Engine.max_fps=30
    _world()
    _character()
    feedback=Feedback.new()
    add_child(feedback)
    _controls()
    w.focus_exited.connect(_cancel_hold)
    if "--render-test" in OS.get_cmdline_user_args():
        get_tree().create_timer(2.0).timeout.connect(_save_and_quit)
    if "--interaction-test" in cmd:
        call_deferred("_run_interaction_tests")
    elif "--capture-review" in cmd:
        call_deferred("_capture_review")

func _capture_review():
    var capture=load("res://tests/capture_review.gd").new()
    await capture.run(self)
    get_tree().quit()

func _run_interaction_tests():
    var test=load("res://tests/interaction_test.gd").new()
    await test.run(self)
    get_tree().quit(1 if test.failed else 0)

func _mat(col:Color,rough:float=0.78,emission:float=0.0)->StandardMaterial3D:
    var m=StandardMaterial3D.new()
    m.albedo_color=col
    m.roughness=rough
    if emission>0.0:
        m.emission_enabled=true
        m.emission=col
        m.emission_energy_multiplier=emission
    return m

func _sphere(parent:Node3D,label:String,p:Vector3,s:Vector3,m:Material)->MeshInstance3D:
    var x=MeshInstance3D.new()
    x.name=label
    var a=SphereMesh.new()
    a.radius=1.0
    a.height=2.0
    a.radial_segments=20
    a.rings=10
    x.mesh=a
    x.material_override=m
    parent.add_child(x)
    x.position=p
    x.scale=s
    return x

func _rod(parent:Node3D,label:String,a:Vector3,b:Vector3,rad:float,mat:Material):
    var n=MeshInstance3D.new()
    n.name=label
    var cyl=CylinderMesh.new()
    cyl.bottom_radius=rad*1.08
    cyl.top_radius=rad
    cyl.height=a.distance_to(b)
    cyl.radial_segments=10
    n.mesh=cyl
    n.material_override=mat
    parent.add_child(n)
    n.position=(a+b)*0.5
    n.quaternion=Quaternion(Vector3.UP,(b-a).normalized())

func _world():
    var env_node=WorldEnvironment.new()
    var e=Environment.new()
    e.background_mode=Environment.BG_CLEAR_COLOR
    e.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR
    e.ambient_light_color=Color(0.79,0.85,1.0)
    e.ambient_light_energy=0.45
    env_node.environment=e
    add_child(env_node)
    var cam=Camera3D.new()
    cam.projection=Camera3D.PROJECTION_ORTHOGONAL
    cam.size=3.0
    cam.position=Vector3(0.0,0.18,5.1)
    add_child(cam)
    cam.look_at(Vector3(0,0.18,0),Vector3.UP)
    cam.current=true
    var key=DirectionalLight3D.new()
    key.light_color=Color(1.0,0.94,0.87)
    key.light_energy=1.15
    key.rotation_degrees=Vector3(-32,-35,0)
    add_child(key)
    var rim=DirectionalLight3D.new()
    rim.light_color=Color(0.48,0.75,1.0)
    rim.light_energy=0.40
    rim.rotation_degrees=Vector3(15,140,0)
    add_child(rim)

func _fur(parent:Node3D,origin:Vector3,axes:Vector3,amount:int,head_fur:bool,cream:Material):
    var rng=RandomNumberGenerator.new()
    rng.seed=12051+amount
    var st=SurfaceTool.new()
    st.begin(Mesh.PRIMITIVE_TRIANGLES)
    for j in range(amount):
        var d=Vector3(rng.randf_range(-1,1),rng.randf_range(-1,1),rng.randf_range(-1,1)).normalized()
        if head_fur and d.z>0.43 and absf(d.y)<0.48:
            continue # black faceplate must stay perfectly clean
        if not head_fur and d.z>0.55 and d.y>-0.47:
            continue # keep chest circle unobstructed
        var origin_point=origin+Vector3(d.x*axes.x,d.y*axes.y,d.z*axes.z)
        var outward=Vector3(d.x/axes.x,d.y/axes.y,d.z/axes.z).normalized()
        var across=outward.cross(Vector3.UP)
        if across.length_squared()<0.05:across=outward.cross(Vector3.RIGHT)
        across=across.normalized()
        var w=rng.randf_range(0.006,0.013)
        var length=rng.randf_range(0.060,0.125)
        st.set_normal(outward)
        st.add_vertex(origin_point-across*w)
        st.set_normal(outward)
        st.add_vertex(origin_point+across*w)
        st.set_normal(outward)
        st.add_vertex(origin_point+outward*length+across*rng.randf_range(-0.02,0.02))
    var mesh=MeshInstance3D.new()
    mesh.name="Micro3DFur"
    mesh.mesh=st.commit()
    mesh.material_override=cream
    parent.add_child(mesh)

func _character():
    var cream=_mat(CREAM,0.94)
    var soft=_mat(Color(0.93,0.84,0.72),0.91)
    var black=_mat(Color(0.014,0.019,0.061),0.13)
    var blue=_mat(Color(0.29,0.61,1.0),0.22,1.8)
    var white=_mat(Color(0.94,0.98,1.0),0.24,0.6)
    var dark=_mat(Color(0.012,0.046,0.22),0.13)
    var fur_mat=_mat(Color(0.94,0.86,0.75),0.99)
    fur_mat.cull_mode=BaseMaterial3D.CULL_DISABLED
    robot=Node3D.new()
    robot.name="MuhammadReal3D"
    add_child(robot)
    _sphere(robot,"RoundedBody",Vector3(0,-0.32,0.02),Vector3(0.59,0.61,0.45),cream)
    left_hand=_sphere(robot,"LeftHand",Vector3(-0.63,-0.24,0),Vector3(0.21,0.32,0.22),soft)
    left_hand.rotation_degrees.z=-15
    right_hand=_sphere(robot,"RightHand",Vector3(0.63,-0.24,0),Vector3(0.21,0.32,0.22),soft)
    right_hand.rotation_degrees.z=15
    _sphere(robot,"FootLeft",Vector3(-0.30,-0.80,0.18),Vector3(0.29,0.22,0.30),soft)
    _sphere(robot,"FootRight",Vector3(0.30,-0.80,0.18),Vector3(0.29,0.22,0.30),soft)
    head=Node3D.new()
    head.name="Head"
    head.position=Vector3(0,0.34,0)
    robot.add_child(head)
    _sphere(head,"SoftFurryHead",Vector3.ZERO,Vector3(0.67,0.67,0.52),cream)
    _sphere(head,"Black3DVisor",Vector3(0,-0.045,0.50),Vector3(0.49,0.32,0.145),black)
    for x in [-0.22,0.22]:
        var eye=Node3D.new()
        eye.name="LeftEye" if x<0.0 else "RightEye"
        head.add_child(eye)
        eye.position=Vector3(x,-0.010,0.63)
        _sphere(eye,"BlueIris",Vector3.ZERO,Vector3(0.148,0.182,0.038),blue)
        _sphere(eye,"DarkPupil",Vector3(0.013,-0.005,0.035),Vector3(0.089,0.132,0.034),dark)
        _sphere(eye,"EyeGlint",Vector3(-0.050,0.070,0.070),Vector3(0.035,0.046,0.012),white)
        pupils.append(eye)
    var mouth_mat=_mat(ICE,0.8,0.25)
    smile=Node3D.new()
    head.add_child(smile)
    for i in range(10):
        var x1=-0.12+0.024*i
        var x2=x1+0.024
        _rod(smile,"Smile"+str(i),Vector3(x1,-0.255+3.1*x1*x1,0.655),
             Vector3(x2,-0.255+3.1*x2*x2,0.655),0.012,mouth_mat)
    surprised_mouth=Node3D.new()
    head.add_child(surprised_mouth)
    for i in range(16):
        var a=TAU*i/16.0
        var b=TAU*(i+1)/16.0
        _rod(surprised_mouth,"Oh"+str(i),Vector3(cos(a)*0.036,-0.235+sin(a)*0.042,0.66),
             Vector3(cos(b)*0.036,-0.235+sin(b)*0.042,0.66),0.009,mouth_mat)
    smile.visible=false
    surprised_mouth.visible=false
    _sphere(robot,"ChestRing",Vector3(0,-0.37,0.51),Vector3(0.169,0.169,0.064),white)
    _sphere(robot,"ChestButton",Vector3(0,-0.37,0.568),Vector3(0.113,0.113,0.022),blue)
    # 2,500 tiny 3D fibers are generated once, with no runtime hair physics.
    _fur(robot,Vector3(0,-0.32,0.02),Vector3(0.59,0.61,0.45),1050,false,fur_mat)
    _fur(head,Vector3.ZERO,Vector3(0.67,0.67,0.52),1450,true,fur_mat)
    antenna=Node3D.new()
    antenna.name="Antenna"
    antenna.position=Vector3(0.04,0.99,0)
    robot.add_child(antenna)
    _rod(antenna,"Lower",Vector3.ZERO,Vector3(0.09,0.22,0),0.044,soft)
    _rod(antenna,"Upper",Vector3(0.09,0.22,0),Vector3(0.16,0.37,0),0.035,soft)
    _sphere(antenna,"GlowingBall",Vector3(0.16,0.41,0),Vector3(0.14,0.14,0.14),white)

func _controls():
    var layer=CanvasLayer.new()
    add_child(layer)
    belly=Button.new()
    belly.name="BellyButton"
    belly.position=Vector2(69,129)
    belly.size=Vector2(38,33)
    belly.flat=true
    belly.tooltip_text="Open robot menu"
    belly.pressed.connect(_toggle_menu)
    layer.add_child(belly)
    menu=PanelContainer.new()
    menu.visible=false
    menu.position=Vector2(2,7)
    var style=StyleBoxFlat.new()
    style.bg_color=Color(0.035,0.125,0.22,0.96)
    style.border_color=Color(0.3,0.75,0.98)
    style.set_border_width_all(1)
    style.set_corner_radius_all(10)
    menu.add_theme_stylebox_override("panel",style)
    var column=VBoxContainer.new()
    menu.add_child(column)
    for action in [["▶ Run Python","run"],["✎ Python Studio","editor"],["↩ Switch to Classic","classic"],["♪ Sounds: On","sound"],["− Hide","hide"],["× Exit 3D","exit"]]:
        var b=Button.new()
        b.text=action[0]
        b.custom_minimum_size=Vector2(170,28)
        b.flat=true
        b.pressed.connect(_action.bind(action[1]))
        column.add_child(b)
        if action[1]=="sound":
            sound_button=b
            sound_button.text="♪ Sounds: On" if feedback.enabled else "♪ Sounds: Off"
    layer.add_child(menu)
    # Real cream-colored movable two-eye minimized orb, not a text glyph.
    small_eye=Panel.new()
    small_eye.name="CreamEyeOrb"
    small_eye.visible=false
    small_eye.position=Vector2(2,2)
    small_eye.size=Vector2(50,50)
    small_eye.mouse_filter=Control.MOUSE_FILTER_IGNORE
    var orb_style=StyleBoxFlat.new()
    orb_style.bg_color=Color(0.88,0.77,0.62,1.0)
    orb_style.border_color=Color(0.97,0.88,0.75,1.0)
    orb_style.set_border_width_all(2)
    orb_style.set_corner_radius_all(25)
    small_eye.add_theme_stylebox_override("panel",orb_style)
    layer.add_child(small_eye)
    orb_left_eye=Panel.new()
    orb_right_eye=Panel.new()
    var black_eye_style=StyleBoxFlat.new()
    black_eye_style.bg_color=Color(0.015,0.013,0.025,1.0)
    black_eye_style.set_corner_radius_all(6)
    for eye in [orb_left_eye,orb_right_eye]:
        eye.size=Vector2(10,12)
        eye.mouse_filter=Control.MOUSE_FILTER_IGNORE
        eye.add_theme_stylebox_override("panel",black_eye_style)
        small_eye.add_child(eye)
    orb_left_eye.position=Vector2(12,19)
    orb_right_eye.position=Vector2(28,19)

func _toggle_menu():
    if not hidden:menu.visible=not menu.visible

func _bridge(command:String):
    if bridge_file.is_empty():
        print("Standalone 3D preview: no Python robot bridge for ",command)
        return
    if command not in ["classic","editor","run"]:
        return
    var file=FileAccess.open(bridge_file,FileAccess.WRITE)
    if file!=null:
        file.store_string(command)
        file.flush()
        file.close()

func _action(command:String):
    menu.visible=false
    if command=="hide":
        _hide()
    elif command=="classic" or command=="exit":
        _bridge("classic")
        get_tree().quit()
    elif command=="editor":
        _bridge("editor")
        # Keep the 3D robot visible while Python Studio is open.
    elif command=="run":
        _bridge("run")
    elif command=="sound":
        var on=feedback.toggle_enabled()
        sound_button.text="♪ Sounds: On" if on else "♪ Sounds: Off"
        menu.visible=true

func _hide():
    if hidden:return
    _cancel_hold()
    feedback.play_cue("close")
    hidden=true
    menu.visible=false
    robot.visible=false
    belly.visible=false
    small_eye.visible=true
    old_position=get_window().position
    get_window().size=ORB_SIZE
    var screen=DisplayServer.screen_get_size()
    get_window().position=Vector2i(16,maxi(8,screen.y-110))
    Engine.max_fps=24

func _show():
    if not hidden:return
    hidden=false
    dragging=false
    feedback.play_cue("open")
    _set_emotion("happy",0.75)
    squish_velocity=-0.8
    robot.visible=true
    belly.visible=true
    small_eye.visible=false
    get_window().size=DESK_SIZE
    var screen=DisplayServer.screen_get_size()
    get_window().position=Vector2i(clampi(old_position.x,0,maxi(0,screen.x-DESK_SIZE.x)),
                                   clampi(old_position.y,0,maxi(0,screen.y-DESK_SIZE.y)))
    Engine.max_fps=30

func _listen_to_python_voice(delta:float):
    if signal_file.is_empty():return
    signal_clock+=delta
    if signal_clock<0.025:return
    signal_clock=0.0
    if not FileAccess.file_exists(signal_file):return
    # Claim this complete message before reading, so a new command is not deleted.
    var claimed=signal_file+".reading"
    if DirAccess.rename_absolute(signal_file,claimed)!=OK:return
    var data=FileAccess.get_file_as_string(claimed).strip_edges()
    DirAccess.remove_absolute(claimed)
    if data=="hide":
        _hide()
    elif data=="show":
        _show()

func _process(delta:float):
    t+=minf(delta,0.05)
    _listen_to_python_voice(delta)
    _update_emotion(delta)
    if hidden:
        # Black eyes follow nearby mouse, even while only the 54px orb exists.
        var mouse=DisplayServer.mouse_get_position()-get_window().position
        var aim=(Vector2(mouse)-Vector2(27,27)).limit_length(130.0)*0.018
        orb_left_eye.position=Vector2(12,19)+aim
        orb_right_eye.position=Vector2(28,19)+aim
        return
    robot.position.y=0.026*sin(t*2.2)
    antenna.rotation.z=0.28*sin(t*3.4)+0.035*sin(t*5.7)-clampf(drag_v*0.003,-0.15,0.15)
    antenna.rotation.x=0.10*sin(t*2.7)
    # Damped spring makes fur and rounded body squeeze as a single soft object.
    var target=clampf(0.04+absf(drag_v)*0.007,0.04,0.145) if dragging else 0.0
    squish_velocity+=(target-squish)*62.0*delta
    squish_velocity*=exp(-9.0*delta)
    squish+=squish_velocity*delta
    squish=clampf(squish,-0.11,0.19)
    robot.scale=Vector3(1.0+squish*0.70,1.0-squish,1.0+squish*0.25)
    spring_head=lerpf(spring_head,clampf(drag_v*-0.012,-0.18,0.18),minf(1,delta*7))
    head.rotation.z=lerpf(head.rotation.z,spring_head,minf(1,delta*9))
    left_hand.rotation.z=lerpf(left_hand.rotation.z,-0.26-squish*0.9,minf(1,delta*8))
    right_hand.rotation.z=lerpf(right_hand.rotation.z,0.26+squish*0.9,minf(1,delta*8))
    var cursor=DisplayServer.mouse_get_position()-get_window().position
    var offset=Vector2(cursor.x-88.0,cursor.y-100.0)
    if offset.length()>160:offset=Vector2.ZERO
    offset.x=clampf(offset.x,-100,100)
    offset.y=clampf(offset.y,-100,100)
    var sx=offset.x/100.0
    var sy=offset.y/100.0
    for i in range(pupils.size()):
        var initial=-0.22 if i==0 else 0.22
        var desired=Vector3(initial+sx*0.055,-0.01-sy*0.043,0.63)
        pupils[i].position=pupils[i].position.lerp(desired,minf(1,delta*12))
    head.rotation.y=lerpf(head.rotation.y,sx*0.09,minf(1,delta*4))
    head.rotation.x=lerpf(head.rotation.x,sy*0.06,minf(1,delta*4))
    robot.rotation.z=lerpf(robot.rotation.z,clampf(drag_v*-0.03,-0.15,0.15) if dragging else 0.0,minf(1,delta*6))
    drag_v=lerpf(drag_v,0.0,minf(1,delta*8))
    blinking+=delta
    if blinking>3.1:
        var p=blinking-3.1
        var h=1.0-0.8*sin(clampf(p/0.18,0,1)*PI)
        for eye in pupils:eye.scale.y*=h
        if p>0.18:blinking=0.0

func _set_emotion(value:String,duration:float):
    emotion=value
    emotion_left=duration
    blinking=0.0

func _update_emotion(delta:float):
    emotion_left=maxf(0.0,emotion_left-delta)
    if dragging:
        hold_elapsed+=delta
        if emotion_left<=0.0:emotion="happy"
    elif emotion_left<=0.0:
        emotion="idle"
    var eye_scale=Vector3.ONE
    if emotion=="surprised":eye_scale=Vector3(1.12,1.12,1.0)
    elif emotion=="happy":eye_scale=Vector3(1.07,0.64,1.0)
    elif emotion=="excited":eye_scale=Vector3(1.12,0.80,1.0)
    for i in range(pupils.size()):
        pupils[i].scale=pupils[i].scale.lerp(eye_scale,minf(1.0,delta*16.0))
        var tilt=0.10 if i==0 else -0.10
        pupils[i].rotation.z=lerpf(pupils[i].rotation.z,
            tilt if emotion in ["happy","excited"] else 0.0,minf(1.0,delta*12.0))
    smile.visible=emotion in ["happy","excited"]
    surprised_mouth.visible=emotion=="surprised"
    # The two black eyes on the small cream orb react to touch as well.
    var eye_height=9.0 if dragging else 12.0
    for eye in [orb_left_eye,orb_right_eye]:
        eye.size.y=lerpf(eye.size.y,eye_height,minf(1.0,delta*16.0))

func _begin_hold(pointer:Vector2i):
    dragging=true
    orb_moved=false
    hold_elapsed=0.0
    hold_excited=false
    drag_from=pointer
    window_from=get_window().position
    _set_emotion("surprised",0.25)
    squish_velocity=0.6
    feedback.play_cue("grab")

func _move_hold(pointer:Vector2i,relative:Vector2):
    if not dragging:return
    var diff=pointer-drag_from
    if diff.length()>6.0:orb_moved=true
    if hidden:
        var screen=DisplayServer.screen_get_size()
        get_window().position=Vector2i(clampi(window_from.x+diff.x,0,maxi(0,screen.x-ORB_SIZE.x)),
            clampi(window_from.y+diff.y,0,maxi(0,screen.y-ORB_SIZE.y)))
    else:
        get_window().position=window_from+diff
        drag_v=clampf(relative.x*0.45,-16.0,16.0)
    if relative.length()>14.0 and hold_elapsed>0.15 and not hold_excited:
        hold_excited=true
        _set_emotion("excited",0.45)
        feedback.play_cue("excited")

func _finish_hold(pointer:Vector2i):
    if not dragging:return
    dragging=false
    if hidden and not orb_moved and (pointer-drag_from).length()<7.0:
        _show()
    else:
        _set_emotion("happy",0.65)
        squish_velocity=-0.65
        feedback.play_cue("release")

func _cancel_hold():
    dragging=false
    drag_v=0.0
    _set_emotion("idle",0.0)

func _input(e:InputEvent):
    # Right click directly on the 3D robot opens the SAME mode switch menu.
    if e is InputEventMouseButton and e.button_index==MOUSE_BUTTON_RIGHT and e.pressed:
        _cancel_hold()
        if hidden:_show()
        menu.visible=not menu.visible
        get_viewport().set_input_as_handled()
        return
    if e is InputEventMouseButton and e.button_index==MOUSE_BUTTON_LEFT and not e.pressed and dragging:
        _finish_hold(DisplayServer.mouse_get_position())
        get_viewport().set_input_as_handled()
    if e is InputEventMouseMotion and dragging:
        _move_hold(DisplayServer.mouse_get_position(),e.relative)
        get_viewport().set_input_as_handled()
    if e is InputEventKey and e.pressed and e.keycode==KEY_ESCAPE:
        if menu.visible:menu.visible=false
        else:_hide()

func _unhandled_input(e:InputEvent):
    # Menu and belly buttons consume presses before any grab sound/reaction.
    if e is InputEventMouseButton and e.button_index==MOUSE_BUTTON_LEFT and e.pressed:
        _begin_hold(DisplayServer.mouse_get_position())
        get_viewport().set_input_as_handled()

func _save_and_quit():
    var im=get_viewport().get_texture().get_image()
    im.save_png("user://render.png")
    print("Render test saved")
    get_tree().quit()
