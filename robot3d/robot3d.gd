extends Node3D
# Muhammad Robot: actual Godot 3D meshes, light, fur, 3D eye & antenna movement.
# v2.2.21: recovered voice bridge and dizzy spiral eyes after deliberate shaking.
const Feedback = preload("res://robot_feedback.gd")
const PlushOrb = preload("res://plush_orb.gd")
const AntennaGlow = preload("res://antenna_glow.gd")
const DESK_SIZE=Vector2i(176,200)
const ORB_SIZE=Vector2i(64,64)
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
var small_eye:Control
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
var hold_love=false
var heart_eyes:Array[MeshInstance3D]=[]
var emotion_cycle=0
var idle_elapsed=0.0
var soft_offset=Vector2.ZERO
var soft_velocity=Vector2.ZERO
var head_lag=Vector2.ZERO
var head_lag_velocity=Vector2.ZERO
var drag_force=Vector2.ZERO
var left_foot:MeshInstance3D
var right_foot:MeshInstance3D
var pet_surfaces:Array[MeshInstance3D]=[]
var laugh_eyes:Array[Node3D]=[]
var laugh_mouth:Node3D
var angry_face:Node3D
var antenna_glow
var pet_distance=0.0
var pet_reversals=0
var pet_axis=Vector2.ZERO
var pet_stroke=0.0
var pet_gap=0.0
var laugh_cooldown=0.0
var tap_count=0
var last_tap_ms=-1000
var dizzy_eyes:Array[Node3D]=[]
var dizzy_mouth:Node3D
var shake_last=Vector2i.ZERO
var shake_axis=Vector2.ZERO
var shake_distance=0.0
var shake_stroke=0.0
var shake_reversals=0
var shake_elapsed=0.0
var shake_gap=0.0

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
    elif "--voice-integration-test" in cmd:
        call_deferred("_run_voice_bridge_test")
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

func _run_voice_bridge_test():
    var test=load("res://tests/voice_bridge_test.gd").new()
    await test.run(self)

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
    cam.size=3.2
    cam.position=Vector3(0.0,0.26,5.1)
    add_child(cam)
    cam.look_at(Vector3(0,0.26,0),Vector3.UP)
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
    pet_surfaces.append(_sphere(robot,"RoundedBody",Vector3(0,-0.32,0.02),Vector3(0.59,0.61,0.45),cream))
    left_hand=_sphere(robot,"LeftHand",Vector3(-0.63,-0.24,0),Vector3(0.21,0.32,0.22),soft)
    left_hand.rotation_degrees.z=-15
    right_hand=_sphere(robot,"RightHand",Vector3(0.63,-0.24,0),Vector3(0.21,0.32,0.22),soft)
    right_hand.rotation_degrees.z=15
    pet_surfaces.append(left_hand)
    pet_surfaces.append(right_hand)
    left_foot=_sphere(robot,"FootLeft",Vector3(-0.30,-0.80,0.18),Vector3(0.29,0.22,0.30),soft)
    right_foot=_sphere(robot,"FootRight",Vector3(0.30,-0.80,0.18),Vector3(0.29,0.22,0.30),soft)
    head=Node3D.new()
    head.name="Head"
    head.position=Vector3(0,0.34,0)
    robot.add_child(head)
    pet_surfaces.append(_sphere(head,"SoftFurryHead",Vector3.ZERO,Vector3(0.67,0.67,0.52),cream))
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
        heart_eyes.append(_heart_eye(x))
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
    _expressive_face(mouth_mat)
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
    antenna_glow=AntennaGlow.new()
    antenna_glow.position=Vector3(0.16,0.41,0)
    antenna.add_child(antenna_glow)

func _expressive_face(mouth_mat:Material):
    for center in [-0.22,0.22]:
        var eye=Node3D.new()
        head.add_child(eye)
        for i in range(10):
            var a=-0.12+float(i)*0.024
            var b=a+0.024
            _rod(eye,"LaughEye"+str(i),Vector3(center+a,0.07-4.0*a*a,0.72),
                Vector3(center+b,0.07-4.0*b*b,0.72),0.022,mouth_mat)
        eye.visible=false
        laugh_eyes.append(eye)
    laugh_mouth=Node3D.new()
    head.add_child(laugh_mouth)
    for i in range(16):
        var a=PI*float(i)/16.0
        var b=PI*float(i+1)/16.0
        _rod(laugh_mouth,"LaughMouth"+str(i),Vector3(cos(a)*0.13,-0.17-sin(a)*0.10,0.69),
            Vector3(cos(b)*0.13,-0.17-sin(b)*0.10,0.69),0.015,mouth_mat)
    _rod(laugh_mouth,"MouthTop",Vector3(-0.13,-0.17,0.69),Vector3(0.13,-0.17,0.69),0.012,mouth_mat)
    laugh_mouth.visible=false
    angry_face=Node3D.new()
    head.add_child(angry_face)
    var warm=_mat(Color("ffc2a0"),0.8,0.35)
    _rod(angry_face,"LeftBrow",Vector3(-0.36,0.17,0.73),Vector3(-0.09,0.07,0.73),0.024,warm)
    _rod(angry_face,"RightBrow",Vector3(0.09,0.07,0.73),Vector3(0.36,0.17,0.73),0.024,warm)
    for i in range(10):
        var a=-0.10+float(i)*0.02
        var b=a+0.02
        _rod(angry_face,"Frown"+str(i),Vector3(a,-0.20-3.0*a*a,0.68),
            Vector3(b,-0.20-3.0*b*b,0.68),0.014,warm)
    angry_face.visible=false
    for x in [-0.22,0.22]:
        var eye=Node3D.new()
        eye.position=Vector3(x,-0.01,0.73)
        head.add_child(eye)
        var ribbon=SurfaceTool.new()
        ribbon.begin(Mesh.PRIMITIVE_TRIANGLES)
        for i in range(64):
            var points:PackedVector3Array=[]
            for j in [i,i+1]:
                var angle=float(j)/64.0*TAU*2.15
                var radius=0.012+float(j)/64.0*0.13
                var outward=Vector3(cos(angle),sin(angle),0)
                points.append(outward*(radius-0.009))
                points.append(outward*(radius+0.009))
            for k in [0,1,2,1,3,2]:
                ribbon.set_normal(Vector3(0,0,1))
                ribbon.add_vertex(points[k])
        var mesh=MeshInstance3D.new()
        mesh.mesh=ribbon.commit()
        var mat=_mat(Color("c4ddff"),0.8,0.4)
        mat.cull_mode=BaseMaterial3D.CULL_DISABLED
        mesh.material_override=mat
        eye.add_child(mesh)
        eye.visible=false
        dizzy_eyes.append(eye)
    dizzy_mouth=Node3D.new()
    head.add_child(dizzy_mouth)
    for i in range(12):
        var a=-0.12+float(i)*0.02
        var b=a+0.02
        _rod(dizzy_mouth,"WobblyMouth"+str(i),Vector3(a,-0.23+sin(a*55.0)*0.019,0.70),
            Vector3(b,-0.23+sin(b*55.0)*0.019,0.70),0.012,mouth_mat)
    dizzy_mouth.visible=false

func _heart_eye(x:float)->MeshInstance3D:
    var st=SurfaceTool.new()
    st.begin(Mesh.PRIMITIVE_TRIANGLES)
    var outline:PackedVector3Array=[]
    for i in range(40):
        var a=TAU*i/40.0
        outline.append(Vector3(16.0*pow(sin(a),3.0),
            13.0*cos(a)-5.0*cos(2*a)-2.0*cos(3*a)-cos(4*a),0.0)*0.009)
    for i in range(outline.size()):
        for point in [Vector3.ZERO,outline[i],outline[(i+1)%outline.size()]]:
            st.set_normal(Vector3(0,0,1))
            st.add_vertex(point)
    var mesh=MeshInstance3D.new()
    mesh.mesh=st.commit()
    var mat=_mat(Color("ff9db3"),0.8,0.35)
    mat.cull_mode=BaseMaterial3D.CULL_DISABLED
    mesh.material_override=mat
    mesh.position=Vector3(x,0.015,0.72)
    mesh.visible=false
    head.add_child(mesh)
    return mesh

func _controls():
    var layer=CanvasLayer.new()
    add_child(layer)
    get_window().mouse_exited.connect(_reset_pet)
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
    small_eye=PlushOrb.new()
    small_eye.name="CreamEyeOrb"
    small_eye.visible=false
    small_eye.position=Vector2.ZERO
    small_eye.size=Vector2(64,64)
    small_eye.mouse_filter=Control.MOUSE_FILTER_IGNORE
    layer.add_child(small_eye)
    orb_left_eye=Panel.new()
    orb_right_eye=Panel.new()
    var black_eye_style=StyleBoxFlat.new()
    black_eye_style.bg_color=Color(0.015,0.013,0.025,1.0)
    black_eye_style.set_corner_radius_all(7)
    for eye in [orb_left_eye,orb_right_eye]:
        eye.size=Vector2(14,16)
        eye.mouse_filter=Control.MOUSE_FILTER_IGNORE
        eye.add_theme_stylebox_override("panel",black_eye_style)
        small_eye.add_child(eye)
    orb_left_eye.position=Vector2(15,24)
    orb_right_eye.position=Vector2(35,24)

func _toggle_menu():
    _cancel_hold()
    if not bridge_file.is_empty():
        menu.visible=false
        _bridge("menu")
    else:
        if hidden:_show()
        menu.visible=not menu.visible

func _bridge(command:String):
    if bridge_file.is_empty():
        print("Standalone 3D preview: no Python robot bridge for ",command)
        return
    if command not in ["classic","editor","run","menu"]:
        return
    var pending=bridge_file+".tmp"
    var file=FileAccess.open(pending,FileAccess.WRITE)
    if file!=null:
        file.store_string(command)
        file.flush()
        file.close()
        DirAccess.rename_absolute(pending,bridge_file)

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
    elif data=="sound":
        var on=feedback.toggle_enabled()
        sound_button.text="♪ Sounds: On" if on else "♪ Sounds: Off"
    elif data=="emotion":
        _show_next_emotion()
    elif data=="happy":
        _set_emotion("excited",1.2)

func _process(delta:float):
    t+=minf(delta,0.05)
    _listen_to_python_voice(delta)
    _advance_pet(delta)
    _advance_shake(delta)
    _update_emotion(delta)
    if hidden:
        # The larger black dots track the pointer on the fluffy cream pom-pom.
        var mouse=DisplayServer.mouse_get_position()-get_window().position
        var aim=(Vector2(mouse)-Vector2(32,32)).limit_length(100.0)*0.016
        orb_left_eye.position=Vector2(15,24)+aim
        orb_right_eye.position=Vector2(35,24)+aim
        return
    _advance_soft_body(delta)
    antenna_glow.update_glow(t,emotion,delta)
    var camera=get_viewport().get_camera_3d()
    belly.position=camera.unproject_position(robot.to_global(Vector3(0,-0.37,0.57)))-belly.size*0.5
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
    drag_v=lerpf(drag_v,0.0,minf(1,delta*8))
    blinking+=delta
    if blinking>3.1:
        var p=blinking-3.1
        var h=1.0-0.8*sin(clampf(p/0.18,0,1)*PI)
        for eye in pupils:eye.scale.y*=h
        if p>0.18:blinking=0.0

func _advance_soft_body(delta:float):
    # Substeps keep the spring response stable even after a slow frame.
    var remaining=minf(delta,0.12)
    while remaining>0.0:
        var step=minf(remaining,1.0/120.0)
        remaining-=step
        var target=clampf(0.22+absf(drag_force.x)*0.09+drag_force.y*0.10,0.06,0.34) if dragging else 0.0
        if emotion=="laugh" and not dragging:target=0.04+0.055*sin(t*18.0)
        squish_velocity+=((target-squish)*48.0-squish_velocity*5.8)*step
        squish=clampf(squish+squish_velocity*step,-0.20,0.36)
        var offset_target=-drag_force*0.14 if dragging else Vector2.ZERO
        soft_velocity+=((offset_target-soft_offset)*46.0-soft_velocity*6.8)*step
        soft_offset+=soft_velocity*step
        head_lag_velocity+=((soft_offset*1.7-head_lag)*32.0-head_lag_velocity*5.4)*step
        head_lag+=head_lag_velocity*step
        drag_force=drag_force.move_toward(Vector2.ZERO,step*2.3)
    var height=1.0-squish
    var width=1.0/sqrt(height)
    robot.scale=Vector3(width,height,width)
    var giggle_bounce=0.018*sin(t*18.0) if emotion=="laugh" else 0.0
    robot.position=Vector3(soft_offset.x,0.026*sin(t*2.2)-soft_offset.y+giggle_bounce,0.0)
    robot.rotation.z=clampf(-soft_offset.x*1.8,-0.22,0.22)
    var tilt=-0.15 if emotion=="curious" else (0.10 if emotion=="sleepy" else 0.0)
    if emotion=="laugh":tilt=0.045*sin(t*13.0)
    elif emotion=="angry":tilt=0.055*sin(t*7.0)
    elif emotion=="dizzy":tilt=0.15*sin(t*5.0)
    head.position=Vector3(head_lag.x,0.34-head_lag.y+squish*0.18,0.0)
    head.rotation.z=clampf(-head_lag.x*2.3+tilt,-0.30,0.30)
    # Face, torso and limbs lag differently, then gently wobble back into place.
    head.scale=Vector3(1.0-squish*0.15,1.0+squish*0.18,1.0)
    var arms=0.25 if emotion=="angry" else (0.16*sin(t*13.0) if emotion=="laugh" else 0.0)
    left_hand.rotation.z=-0.26-squish*2.1+head_lag.x*2.0-arms
    right_hand.rotation.z=0.26+squish*2.1+head_lag.x*2.0+arms
    left_hand.position.y=-0.24+head_lag.y*0.8
    right_hand.position.y=-0.24-head_lag.y*0.8
    left_foot.rotation.z=-squish*0.6-soft_offset.x
    right_foot.rotation.z=squish*0.6-soft_offset.x
    antenna.rotation.z=0.28*sin(t*3.4)+0.035*sin(t*5.7)-head_lag.x*2.5
    antenna.rotation.x=0.10*sin(t*2.7)+head_lag.y*1.8

func _set_emotion(value:String,duration:float):
    emotion=value
    emotion_left=duration
    blinking=0.0
    idle_elapsed=0.0

func _show_next_emotion():
    var choices=["laugh","angry","dizzy","wink","love","curious","sleepy","happy"]
    _set_emotion(choices[emotion_cycle%choices.size()],1.8)
    if emotion=="laugh":feedback.play_cue("laugh")
    elif emotion=="angry":feedback.play_cue("grumpy")
    emotion_cycle+=1

func _update_emotion(delta:float):
    emotion_left=maxf(0.0,emotion_left-delta)
    if dragging:
        hold_elapsed+=delta
        if not hidden and hold_elapsed>1.2 and not orb_moved and not hold_love:
            hold_love=true
            _set_emotion("love",1.5)
        if emotion_left<=0.0:emotion="happy"
    elif emotion_left<=0.0:
        emotion="idle"
        if not hidden:
            idle_elapsed+=delta
            if idle_elapsed>9.0:
                _set_emotion(["curious","wink","sleepy"][emotion_cycle%3],1.4)
                emotion_cycle+=1
    var eye_scale=Vector3.ONE
    if emotion=="surprised":eye_scale=Vector3(1.12,1.12,1.0)
    elif emotion=="happy":eye_scale=Vector3(1.07,0.64,1.0)
    elif emotion=="excited":eye_scale=Vector3(1.12,0.80,1.0)
    elif emotion=="sleepy":eye_scale=Vector3(1.04,0.22,1.0)
    elif emotion=="angry":eye_scale=Vector3(1.04,0.52,1.0)
    for i in range(pupils.size()):
        var target_scale=eye_scale
        if emotion=="wink":target_scale=Vector3(1.06,0.13 if i==0 else 1.02,1.0)
        elif emotion=="curious":target_scale=Vector3(1.03,1.10 if i==0 else 0.65,1.0)
        pupils[i].visible=emotion not in ["love","laugh","dizzy"]
        heart_eyes[i].visible=emotion=="love"
        laugh_eyes[i].visible=emotion=="laugh"
        dizzy_eyes[i].visible=emotion=="dizzy"
        dizzy_eyes[i].rotation.z=t*7.0*(1.0 if i==0 else -1.0)
        heart_eyes[i].scale=Vector3.ONE*(1.0+0.05*sin(t*5.0))
        pupils[i].scale=pupils[i].scale.lerp(target_scale,minf(1.0,delta*16.0))
        var tilt=0.10 if i==0 else -0.10
        if emotion=="angry":tilt=-0.20 if i==0 else 0.20
        pupils[i].rotation.z=lerpf(pupils[i].rotation.z,
            tilt if emotion in ["happy","excited","angry"] else 0.0,minf(1.0,delta*12.0))
    smile.visible=emotion in ["happy","excited","wink","love"]
    surprised_mouth.visible=emotion=="surprised"
    laugh_mouth.visible=emotion=="laugh"
    laugh_mouth.scale.y=1.0+0.10*sin(t*18.0) if emotion=="laugh" else 1.0
    angry_face.visible=emotion=="angry"
    dizzy_mouth.visible=emotion=="dizzy"
    # The two black eyes on the small cream orb react to touch as well.
    var eye_height=11.0 if dragging else 16.0
    for eye in [orb_left_eye,orb_right_eye]:
        eye.size.y=lerpf(eye.size.y,eye_height,minf(1.0,delta*16.0))

func _begin_hold(pointer:Vector2i):
    _reset_pet()
    _reset_shake()
    shake_last=pointer
    dragging=true
    orb_moved=false
    hold_elapsed=0.0
    hold_excited=false
    hold_love=false
    drag_from=pointer
    window_from=get_window().position
    _set_emotion("surprised",0.25)
    squish_velocity=1.2
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
        drag_force=relative.limit_length(70.0)*0.018
        _shake_motion(pointer)
    if relative.length()>14.0 and hold_elapsed>0.15 and not hold_excited and emotion!="dizzy":
        hold_excited=true
        _set_emotion("excited",0.45)
        feedback.play_cue("excited")

func _finish_hold(pointer:Vector2i):
    if not dragging:return
    dragging=false
    if hidden and not orb_moved and (pointer-drag_from).length()<7.0:
        _show()
    elif emotion=="dizzy" and not hidden:
        _set_emotion("dizzy",2.4)
        squish_velocity=-1.0
    else:
        var quick_tap=not hidden and not orb_moved and hold_elapsed<0.25
        var now=Time.get_ticks_msec()
        if quick_tap:
            tap_count=tap_count+1 if now-last_tap_ms<650 else 1
            last_tap_ms=now
        else:tap_count=0
        if tap_count>=3:
            tap_count=0
            _set_emotion("angry",1.8)
            feedback.play_cue("grumpy")
        else:
            _set_emotion("wink" if quick_tap else "happy",0.85)
            feedback.play_cue("release")
        squish_velocity=-1.25

func _cancel_hold():
    _reset_pet()
    _reset_shake()
    tap_count=0
    dragging=false
    drag_v=0.0
    drag_force=Vector2.ZERO
    _set_emotion("idle",0.0)

func _reset_shake():
    shake_axis=Vector2.ZERO
    shake_distance=0.0
    shake_stroke=0.0
    shake_reversals=0
    shake_elapsed=0.0
    shake_gap=0.0

func _advance_shake(delta:float):
    if not dragging:return
    shake_elapsed+=delta
    shake_gap+=delta
    if shake_gap>0.30 or shake_elapsed>1.2:_reset_shake()

func _shake_motion(pointer:Vector2i):
    # Screen coordinates avoid counting synthetic local motion from window dragging.
    var movement=Vector2(pointer-shake_last)
    shake_last=pointer
    var distance=movement.length()
    if distance<4.0:return
    if distance>240.0:
        _reset_shake()
        return
    var direction=movement.normalized()
    shake_gap=0.0
    if shake_axis==Vector2.ZERO:shake_axis=direction
    elif direction.dot(shake_axis)<-0.5:
        if shake_stroke>=18.0:shake_reversals+=1
        shake_axis=direction
        shake_stroke=0.0
    shake_stroke+=distance
    shake_distance+=minf(distance,80.0)
    if shake_reversals>=3 and shake_distance>=160.0:
        _set_emotion("dizzy",2.4)
        _reset_shake()

func _input(e:InputEvent):
    # Right click directly on the 3D robot opens the SAME mode switch menu.
    if e is InputEventMouseButton and e.button_index==MOUSE_BUTTON_RIGHT and e.pressed:
        _toggle_menu()
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
    elif e is InputEventMouseMotion and e.button_mask==0:
        _pet_motion(e.position,e.relative)

func _pointer_on_plush(point:Vector2)->bool:
    # Intersect the actual moving ellipsoids, not the transparent window rectangle.
    var camera=get_viewport().get_camera_3d()
    var origin=camera.project_ray_origin(point)
    var direction=camera.project_ray_normal(point)
    for surface in pet_surfaces:
        var inverse=surface.global_transform.affine_inverse()
        var o=inverse*origin
        var d=inverse.basis*direction
        var a=d.dot(d)
        var b=2.0*o.dot(d)
        var c=o.dot(o)-1.0
        var discriminant=b*b-4.0*a*c
        if discriminant>=0.0 and (-b+sqrt(discriminant))/(2.0*a)>=0.0:return true
    return false

func _reset_pet():
    pet_distance=0.0
    pet_reversals=0
    pet_axis=Vector2.ZERO
    pet_stroke=0.0
    pet_gap=0.0

func _advance_pet(delta:float):
    laugh_cooldown=maxf(0.0,laugh_cooldown-delta)
    pet_gap+=delta
    if pet_gap>0.32:_reset_pet()

func _pet_motion(point:Vector2,relative:Vector2):
    if hidden or dragging or menu.visible or belly.get_global_rect().has_point(point):
        _reset_pet()
        return
    if not _pointer_on_plush(point) or relative.length()>70.0:
        _reset_pet()
        return
    var distance=relative.length()
    if distance<1.5:return # Ignore mouse jitter.
    pet_gap=0.0
    var direction=relative.normalized()
    if pet_axis==Vector2.ZERO:pet_axis=direction
    elif direction.dot(pet_axis)<-0.35:
        if pet_stroke>=9.0:pet_reversals+=1
        pet_axis=direction
        pet_stroke=0.0
    pet_stroke+=distance
    pet_distance+=minf(distance,30.0)
    if pet_reversals>=2 and pet_distance>=80.0:
        _set_emotion("laugh",1.4)
        if laugh_cooldown<=0.0:
            feedback.play_cue("laugh")
            laugh_cooldown=2.4
        # Keep the happy pose during continued rubbing, but rate-limit the audio.
        pet_distance=0.0
        pet_reversals=0
        squish_velocity+=0.3

func _save_and_quit():
    var im=get_viewport().get_texture().get_image()
    im.save_png("user://render.png")
    print("Render test saved")
    get_tree().quit()
