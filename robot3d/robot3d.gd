extends Node3D
# Muhammad Robot: actual Godot 3D meshes, light, fur, 3D eye & antenna movement.
const Feedback = preload("res://robot_feedback.gd")
const PlushOrb = preload("res://plush_orb.gd")
const AntennaGlow = preload("res://antenna_glow.gd")
const PlushPull = preload("res://plush_pull.gd")
const DesktopMotion = preload("res://desktop_motion.gd")
const FlightTrail = preload("res://flight_trail.gd")
const DESK_SIZE=Vector2i(176,200)
const ORB_SIZE=Vector2i(64,64)
const CREAM=Color(0.89,0.78,0.64)
const ICE=Color(0.61,0.88,1.0)
const WAVE_SHOULDER := Vector3(0.45, -0.095, 0.04)
const UPPER_ARM_LENGTH := 0.38
const ELBOW_TO_PALM := 0.235
const REST_HAND_SIZE := Vector3(0.21, 0.32, 0.22)
const CRY_SECONDS := 3.0
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
var wave_upper_arm:MeshInstance3D
var flight_pose := Node3D.new()
var motion := DesktopMotion.new()
var flight_trail: FlightTrail
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
var sad_face:Node3D
var sad_tear:MeshInstance3D
var cry_tears:Array[MeshInstance3D]=[]
var cry_elapsed := 0.0
var fur_pull = PlushPull.new()
var sad_weight := 0.0
var laugh_weight := 0.0
var laugh_time := 0.0
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
var cried_from_shake := false

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
    w.focus_exited.connect(_on_focus_exited)
    if "--render-test" in OS.get_cmdline_user_args():
        get_tree().create_timer(2.0).timeout.connect(_save_and_quit)
    if "--interaction-test" in cmd or "--motion-test" in cmd:
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
    if "--motion-test" in OS.get_cmdline_user_args():
        await test.motion_checks(self)
    else:
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

func _fur(skin:MeshInstance3D,amount:int,head_fur:bool):
    var origin := skin.position
    var axes := skin.scale
    var roots := PackedVector3Array()
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
        var w=rng.randf_range(0.007,0.015)
        var length=rng.randf_range(0.060,0.125)
        if outward.z >= -0.015:
            roots.append(origin_point + outward * length * 0.40)
        st.set_uv(Vector2.ZERO)
        st.set_normal(outward)
        st.add_vertex(origin_point-across*w)
        st.set_normal(outward)
        st.add_vertex(origin_point+across*w)
        st.set_uv(Vector2.RIGHT)
        st.set_normal(outward)
        st.add_vertex(origin_point+outward*length+across*rng.randf_range(-0.02,0.02))
    var mesh=MeshInstance3D.new()
    mesh.name="Micro3DFur"
    mesh.mesh=st.commit()
    skin.get_parent().add_child(mesh)
    fur_pull.add_patch(skin,mesh,roots,CREAM,Color(0.94,0.86,0.75))

func _character():
    var cream=_mat(CREAM,0.94)
    var soft=_mat(Color(0.93,0.84,0.72),0.91)
    var black=_mat(Color(0.014,0.019,0.061),0.13)
    var blue=_mat(Color(0.29,0.61,1.0),0.22,1.8)
    var white=_mat(Color(0.94,0.98,1.0),0.24,0.6)
    var dark=_mat(Color(0.012,0.046,0.22),0.13)
    robot=Node3D.new()
    robot.name="MuhammadReal3D"
    flight_pose.name="FlightPose"
    add_child(flight_pose)
    flight_pose.add_child(robot)
    var torso = _sphere(robot,"RoundedBody",Vector3(0,-0.32,0.02),Vector3(0.59,0.61,0.45),cream)
    pet_surfaces.append(torso)
    left_hand=_sphere(robot,"LeftHand",Vector3(-0.63,-0.24,0),Vector3(0.21,0.32,0.22),soft)
    left_hand.rotation_degrees.z=-15
    right_hand=_sphere(robot,"RightHand",Vector3(0.63,-0.24,0),REST_HAND_SIZE,soft)
    right_hand.rotation_degrees.z=15
    wave_upper_arm=_sphere(robot,"RightUpperArm",WAVE_SHOULDER,Vector3(0.15,0.24,0.16),soft)
    wave_upper_arm.hide()
    pet_surfaces.append(left_hand)
    pet_surfaces.append(right_hand)
    left_foot=_sphere(robot,"FootLeft",Vector3(-0.30,-0.80,0.18),Vector3(0.29,0.22,0.30),soft)
    right_foot=_sphere(robot,"FootRight",Vector3(0.30,-0.80,0.18),Vector3(0.29,0.22,0.30),soft)
    head=Node3D.new()
    head.name="Head"
    head.position=Vector3(0,0.34,0)
    robot.add_child(head)
    var hood = _sphere(head,"SoftFurryHead",Vector3.ZERO,Vector3(0.67,0.67,0.52),cream)
    pet_surfaces.append(hood)
    var visor = _sphere(head,"Black3DVisor",Vector3(0,-0.045,0.50),Vector3(0.49,0.32,0.145),black)
    fur_pull.occluders.append_array([visor, left_hand, right_hand, left_foot, right_foot])
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
    surprised_mouth.position=Vector3(0,-0.235,0.66)
    head.add_child(surprised_mouth)
    for i in range(16):
        var a=TAU*i/16.0
        var b=TAU*(i+1)/16.0
        _rod(surprised_mouth,"Oh"+str(i),Vector3(cos(a)*0.036,sin(a)*0.042,0),
             Vector3(cos(b)*0.036,sin(b)*0.042,0),0.009,mouth_mat)
    smile.visible=false
    surprised_mouth.visible=false
    _expressive_face(mouth_mat)
    _sphere(robot,"ChestRing",Vector3(0,-0.37,0.51),Vector3(0.169,0.169,0.064),white)
    _sphere(robot,"ChestButton",Vector3(0,-0.37,0.568),Vector3(0.113,0.113,0.022),blue)
    _fur(torso,1050,false)
    _fur(hood,1450,true)
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
    sad_face=Node3D.new()
    head.add_child(sad_face)
    for side in [-1.0,1.0]:
        _rod(sad_face,"RaisedInnerBrow",Vector3(side*0.10,0.17,0.73),
            Vector3(side*0.33,0.09,0.73),0.019,mouth_mat)
    for i in range(12):
        var x1=-0.12+i*0.02
        var x2=x1+0.02
        _rod(sad_face,"DownturnedMouth",Vector3(x1,-0.183-4.0*x1*x1,0.70),
            Vector3(x2,-0.183-4.0*x2*x2,0.70),0.017,mouth_mat)
    sad_tear = _sphere(sad_face,"Tear",Vector3(0.28,-0.13,0.72),Vector3(0.023,0.038,0.014),mouth_mat)
    sad_face.visible=false
    _make_cry_tears()
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

func _make_cry_tears():
    # Pull the top of a round bead to a point. Both cheeks share the same mesh.
    var sphere := SphereMesh.new()
    sphere.radius = 1.0
    sphere.height = 2.0
    sphere.radial_segments = 16
    sphere.rings = 10
    var arrays := sphere.surface_get_arrays(0)
    var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
    for i in vertices.size():
        var point := vertices[i]
        var top := smoothstep(-0.36, 1.0, point.y)
        var radius := 1.0-0.80*top
        vertices[i] = Vector3(point.x*radius, point.y+0.36*top, point.z*radius)
    arrays[Mesh.ARRAY_VERTEX] = vertices
    var shape := ArrayMesh.new()
    shape.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
    var water := _mat(Color("48bce9"),0.24,0.18)
    var glint := _mat(Color("dbf9ff"),0.45,0.35)
    for side in [-1.0,1.0]:
        var drop := MeshInstance3D.new()
        drop.name = "LeftTear" if side < 0.0 else "RightTear"
        drop.mesh = shape
        drop.material_override = water
        drop.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
        head.add_child(drop)
        _sphere(drop,"Glint",Vector3(-0.25,-0.24,0.84),Vector3(0.20,0.31,0.14),glint)
        drop.hide()
        cry_tears.append(drop)

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
    var actions = [["♪ Sounds: On","sound"],["− Hide","hide"],["× Exit Robot","exit"]]
    if not bridge_file.is_empty():
        actions = [["▶ Run Python","run"],["✎ Python Studio","editor"]] + actions
    for action in actions:
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
    _stop_motion()
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
    if command not in ["exit","editor","run","menu"]:
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
    elif command=="exit":
        if not bridge_file.is_empty():_bridge("exit")
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
    _stop_motion()
    if flight_trail != null:
        flight_trail.clear_trail()
    motion.reset_flight_pose()
    _cancel_hold()
    feedback.play_cue("close")
    hidden=true
    menu.visible=false
    robot.visible=false
    belly.visible=false
    small_eye.visible=true
    old_position=get_window().position
    get_window().size=ORB_SIZE
    var area=_work_area()
    get_window().position=area.position+Vector2i(16,maxi(8,area.size.y-110))
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
    var bounds = _motion_limits()
    get_window().position = old_position.clamp(bounds.position, bounds.end)
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
    _handle_host_command(data)

func _handle_host_command(data: String):
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
    elif data=="stop":
        _stop_motion()
        if emotion in ["cry","dance"]:_set_emotion("idle",0.0)
    elif not hidden and not dragging:
        if emotion=="dance" and data in ["fly","jump"]:_set_emotion("idle",0.0)
        match data:
            "wave":
                motion.wave()
                _set_emotion("excited",DesktopMotion.WAVE_SECONDS)
            "fly":
                menu.visible=false
                motion.fly(get_window().position,_motion_limits())
            "jump":
                menu.visible=false
                motion.jump(get_window().position,_motion_limits())
            "cry":
                _start_cry()
            "dance":
                if emotion!="dance":
                    menu.visible=false
                    _stop_motion()
                    _set_emotion("dance",Feedback.DANCE_SECONDS)
                    feedback.play_cue("dance")

func _work_area() -> Rect2i:
    var window := get_window()
    var area := DisplayServer.screen_get_usable_rect(window.current_screen)
    if not area.has_area():
        area = Rect2i(DisplayServer.screen_get_position(window.current_screen),
                      DisplayServer.screen_get_size(window.current_screen))
    return area

func _motion_limits() -> Rect2i:
    var area := _work_area()
    return Rect2i(area.position,(area.size-DESK_SIZE).max(Vector2i.ZERO))

func _stop_motion():
    motion.stop()
    if flight_trail != null:
        flight_trail.end_emission()

func _advance_motion(delta: float):
    var moving := motion.flying or motion.jumping
    motion.advance(delta)
    if moving:
        get_window().position = Vector2i(motion.location.round())

func _update_flight_trail(delta: float, camera: Camera3D):
    if flight_trail == null:
        if not motion.flying or DisplayServer.get_name() == "headless":
            return
        flight_trail = FlightTrail.new()
        add_child(flight_trail)
    if not motion.flying and flight_trail.ribbons.knots.is_empty():
        return
    var origin := Vector2(get_window().position)
    var face := origin + camera.unproject_position(head.to_global(Vector3(0.0, -0.03, 0.46)))
    var chest := origin + camera.unproject_position(robot.to_global(Vector3(0.0, -0.29, 0.14)))
    var heading := (motion.velocity / 110.0).limit_length(1.0)
    flight_trail.advance(delta, motion.flying, face.lerp(chest, 0.58)-heading*54.0, face, chest, heading)

func _apply_flight_pose():
    var lean := motion.lean.limit_length(1.0)
    var follow := motion.follow_through.limit_length(1.0)
    var pull := follow.length()
    var stretch := Basis.IDENTITY
    if pull > 0.001:
        # Stretch along the screen path, including diagonals, and preserve the plush's volume.
        var axis := Vector3(follow.x, -follow.y, 0.0).normalized()
        var axes := Basis(axis, Vector3(-axis.y, axis.x, 0.0), Vector3.BACK)
        var along := 1.0 + pull*(0.15 + 0.035*sin(t*TAU*1.28))
        var across := 1.0/sqrt(along)
        stretch = axes * Basis.from_scale(Vector3(along, across, across)) * axes.transposed()
    flight_pose.basis = stretch * Basis.from_euler(Vector3(0.23*lean.y, 0.24*lean.x, -0.32*lean.x))

    var lag := (lean-follow).limit_length(1.0)
    var head_shift := Vector3(-0.11*lag.x, 0.11*lag.y, 0.0)
    head.position += head_shift
    head.rotation.z += 0.14*lag.x
    antenna.position = Vector3(0.04, 0.99, 0.0) + head_shift
    antenna.rotation.z += 0.35*follow.x + 0.22*lag.x
    antenna.rotation.x += 0.19*follow.y
    var trailing := Vector3(-follow.x, follow.y, 0.0)
    left_hand.position += trailing*0.095 + Vector3.LEFT*0.045*pull
    right_hand.position += trailing*0.095 + Vector3.RIGHT*0.045*pull
    left_hand.rotation.z -= 0.37*pull
    right_hand.rotation.z += 0.37*pull
    left_foot.position += trailing*0.13
    right_foot.position += trailing*0.13

func _apply_motion_pose():
    _apply_flight_pose()
    if motion.jumping:
        robot.scale *= Vector3(1.0+0.065*motion.crouch,1.0-0.14*motion.crouch,1.0+0.065*motion.crouch)
        robot.position.y += 0.10*motion.jump_height-0.08*motion.crouch
        left_hand.position.y += 0.16*motion.jump_height
        right_hand.position.y += 0.16*motion.jump_height
        left_foot.position.y += 0.12*motion.jump_height
        right_foot.position.y += 0.12*motion.jump_height
    _apply_wave()

func _apply_wave():
    var lift := motion.hand_raise
    right_hand.scale = REST_HAND_SIZE.lerp(Vector3(0.174, 0.276, 0.184), lift)
    wave_upper_arm.visible = lift > 0.001
    if not wave_upper_arm.visible:
        return
    # Carry the mitten around the cheek, then wave from the elbow with two fixed-length links.
    var palm := right_hand.position.lerp(Vector3(0.84, 0.305, 0.16), lift)
    palm += Vector3(0.14, -0.028, 0.09)*sin(PI*lift)
    var reach := palm-WAVE_SHOULDER
    var direction := reach.normalized()
    var distance := clampf(reach.length(), UPPER_ARM_LENGTH-ELBOW_TO_PALM+0.001, UPPER_ARM_LENGTH+ELBOW_TO_PALM-0.001)
    var along := (UPPER_ARM_LENGTH*UPPER_ARM_LENGTH-ELBOW_TO_PALM*ELBOW_TO_PALM+distance*distance)/(2.0*distance)
    var bend := sqrt(maxf(0.0, UPPER_ARM_LENGTH*UPPER_ARM_LENGTH-along*along))
    var outward := Vector3(direction.y, -direction.x, 0.0).normalized()
    var upper := direction*along + outward*bend
    var elbow := WAVE_SHOULDER+upper
    var forearm := (direction*distance-upper).rotated(Vector3.BACK, 0.34*motion.hand_swing)
    right_hand.position = elbow+forearm
    right_hand.quaternion = right_hand.quaternion.slerp(Quaternion(Vector3.UP, forearm.normalized()), lift)
    wave_upper_arm.position = WAVE_SHOULDER+upper*0.5
    wave_upper_arm.quaternion = Quaternion(Vector3.UP, upper.normalized())
    var thickness := 0.158*smoothstep(0.0, 0.33, lift)+0.001
    wave_upper_arm.scale = Vector3(thickness, UPPER_ARM_LENGTH*0.5+0.09, thickness*1.05)

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
    _advance_motion(delta)
    fur_pull.advance(delta)
    _advance_soft_body(delta)
    _apply_motion_pose()
    if emotion=="dance":_apply_dance_pose(Feedback.DANCE_SECONDS-emotion_left)
    antenna_glow.update_glow(t,emotion,delta)
    var camera=get_viewport().get_camera_3d()
    _update_flight_trail(delta,camera)
    belly.position=camera.unproject_position(robot.to_global(Vector3(0,-0.37,0.57)))-belly.size*0.5
    var cursor=DisplayServer.mouse_get_position()-get_window().position
    var offset=Vector2(cursor.x-88.0,cursor.y-100.0)
    if offset.length()>160:offset=Vector2.ZERO
    offset.x=clampf(offset.x,-100,100)
    offset.y=clampf(offset.y,-100,100)
    var sx=offset.x/100.0
    var sy=offset.y/100.0
    var heading := motion.lean.limit_length(1.0)
    sx = lerpf(sx,heading.x,heading.length())
    sy = lerpf(sy,heading.y,heading.length())
    for i in range(pupils.size()):
        var initial=-0.22 if i==0 else 0.22
        var desired=Vector3(initial+sx*0.055,-0.01-sy*0.043-sad_weight*0.055,0.63)
        pupils[i].position=pupils[i].position.lerp(desired,minf(1,delta*12))
    head.rotation.y=lerpf(head.rotation.y,sx*0.09,minf(1,delta*4))
    head.rotation.x=lerpf(head.rotation.x,sy*0.06+sad_weight*0.22-laugh_weight*0.12,minf(1,delta*6))
    drag_v=lerpf(drag_v,0.0,minf(1,delta*8))
    blinking+=delta
    if blinking>3.1:
        var p=blinking-3.1
        var h=1.0-0.8*sin(clampf(p/0.18,0,1)*PI)
        for eye in pupils:eye.scale.y*=h
        if p>0.18:blinking=0.0

func _advance_soft_body(delta:float):
    sad_weight = lerpf(sad_weight, float(emotion in ["sad","cry"]), 1.0-exp(-delta*9.0))
    laugh_weight = lerpf(laugh_weight, float(emotion=="laugh"), 1.0-exp(-delta*12.0))
    if emotion=="laugh":laugh_time+=delta
    var jiggle := sin(laugh_time*TAU*4.6)
    var sob := Feedback.sob_strength(cry_elapsed) if emotion=="cry" else 0.0
    # Substeps keep the spring response stable even after a slow frame.
    var remaining=minf(delta,0.12)
    while remaining>0.0:
        var step=minf(remaining,1.0/120.0)
        remaining-=step
        var target=clampf(0.265+absf(drag_force.x)*0.10+drag_force.y*0.12,0.06,0.37) if dragging else 0.0
        if fur_pull.pulling:target=0.095
        target+=sad_weight*0.06+laugh_weight*(0.055+0.09*jiggle)+0.055*sob
        squish_velocity+=((target-squish)*43.0-squish_velocity*5.4)*step
        squish=clampf(squish+squish_velocity*step,-0.22,0.39)
        var offset_target=-drag_force*0.17 if dragging else Vector2.ZERO
        if fur_pull.pulling:offset_target=Vector2(-fur_pull.displacement.x,fur_pull.displacement.y)*0.14
        soft_velocity+=((offset_target-soft_offset)*40.0-soft_velocity*6.0)*step
        soft_offset+=soft_velocity*step
        head_lag_velocity+=((soft_offset*1.7-head_lag)*32.0-head_lag_velocity*5.4)*step
        head_lag+=head_lag_velocity*step
        drag_force=drag_force.move_toward(Vector2.ZERO,step*2.3)
    var height=1.0-squish
    var width=1.0/sqrt(height)
    robot.scale=Vector3(width,height,width)
    var giggle_bounce=laugh_weight*(0.054+0.062*jiggle)
    robot.position=Vector3(soft_offset.x,0.026*sin(t*2.2)-soft_offset.y+giggle_bounce-sad_weight*0.09,0.0)
    robot.rotation.z=clampf(-soft_offset.x*1.8+laugh_weight*0.06*sin(laugh_time*12.0)-sad_weight*0.055,-0.25,0.25)
    var tilt=-0.15 if emotion=="curious" else (0.10 if emotion=="sleepy" else 0.0)
    if emotion=="laugh":tilt=0.045*sin(t*13.0)
    elif emotion=="angry":tilt=0.055*sin(t*7.0)
    elif emotion=="dizzy":tilt=0.15*sin(t*5.0)
    head.position=Vector3(head_lag.x,0.34-head_lag.y+squish*0.18-sad_weight*0.10+laugh_weight*0.035*jiggle,0.0)
    head.rotation.z=clampf(-head_lag.x*2.3+tilt,-0.30,0.30)
    # Face, torso and limbs lag differently, then gently wobble back into place.
    head.scale=Vector3(1.0-squish*0.15,1.0+squish*0.18,1.0)
    var arms=0.25 if emotion=="angry" else (0.16*sin(t*13.0) if emotion=="laugh" else 0.0)
    left_hand.rotation.z=-0.26-squish*2.1+head_lag.x*2.0-arms
    right_hand.rotation=Vector3(0.0,0.0,0.26+squish*2.1+head_lag.x*2.0+arms)
    var tuck=sad_weight*0.13
    var lift=laugh_weight*(0.10+0.07*jiggle)+0.11*sob
    left_hand.position=Vector3(-0.63+tuck,-0.24+head_lag.y*0.8+lift-tuck*0.55,tuck*0.9)
    right_hand.position=Vector3(0.63-tuck,-0.24-head_lag.y*0.8+lift-tuck*0.55,tuck*0.9)
    left_foot.position=Vector3(-0.30,-0.80+laugh_weight*0.045*jiggle+tuck*0.35,0.18)
    right_foot.position=Vector3(0.30,-0.80-laugh_weight*0.045*jiggle+tuck*0.35,0.18)
    left_foot.rotation.y=-sad_weight*0.28
    right_foot.rotation.y=sad_weight*0.28
    left_foot.rotation.z=-squish*0.6-soft_offset.x
    right_foot.rotation.z=squish*0.6-soft_offset.x
    antenna.rotation.z=0.28*sin(t*3.4)+0.035*sin(t*5.7)-head_lag.x*2.5-sad_weight*0.50+laugh_weight*0.16*jiggle
    antenna.rotation.x=0.10*sin(t*2.7)+head_lag.y*1.8

func _apply_dance_pose(seconds: float):
    var beat := seconds/Feedback.DANCE_BEAT
    var weight := smoothstep(0.0,0.45,beat)*(1.0-smoothstep(11.15,12.0,beat))
    var step := sin(PI*beat)
    var left_lift := maxf(0.0,step)*weight
    var right_lift := maxf(0.0,-step)*weight
    var sway := 0.19*step*weight
    var bounce := 0.075*step*step*weight
    var twist := sin(PI*(beat-0.16))*weight
    var accent := smoothstep(3.7,4.4,beat)*(1.0-smoothstep(7.4,8.1,beat))
    var finish := smoothstep(9.6,10.4,beat)
    # Shift onto the planted foot. The free foot taps outward and a little forward.
    robot.position+=Vector3(sway,bounce,0.0)
    robot.rotation.z-=0.17*step*weight
    flight_pose.rotate_object_local(Vector3.UP,(0.18+0.19*accent)*twist)
    head.rotation.z+=0.20*twist
    head.position.y+=0.035*sin(TAU*beat-0.5)*weight
    antenna.rotation.z-=0.28*twist
    left_foot.position+=Vector3(-sway*(1.0-left_lift)-0.13*left_lift,0.25*left_lift-bounce,0.17*left_lift)
    right_foot.position+=Vector3(-sway*(1.0-right_lift)+0.13*right_lift,0.25*right_lift-bounce,0.17*right_lift)
    left_foot.rotation.z+=0.38*left_lift
    right_foot.rotation.z-=0.38*right_lift
    var open := (0.20+0.24*accent+0.53*finish)*weight
    _dance_arm(left_hand,-1.0,open+1.40*right_lift)
    _dance_arm(right_hand,1.0,open+1.40*left_lift)

func _dance_arm(hand: MeshInstance3D, side: float, angle: float):
    var shoulder := Vector3(side*WAVE_SHOULDER.x,WAVE_SHOULDER.y,WAVE_SHOULDER.z)
    hand.position=shoulder+(hand.position-shoulder).rotated(Vector3.BACK,side*angle)
    hand.position.z+=0.085*sin(angle)
    hand.rotation.z+=side*angle

func _start_cry(from_shake := false):
    if emotion=="cry":return
    cried_from_shake=from_shake
    _set_emotion("cry",CRY_SECONDS)
    feedback.play_cue("cry")

func _set_emotion(value:String,duration:float):
    if value=="cry" and emotion!="cry":cry_elapsed=0.0
    if emotion!=value and emotion in ["cry","dance"]:feedback.stop_cue(emotion)
    if value=="laugh" and emotion!="laugh":laugh_time=0.0
    emotion=value
    emotion_left=duration
    blinking=0.0
    idle_elapsed=0.0

func _show_next_emotion():
    var choices=["laugh","angry","sad","dizzy","wink","love","curious","sleepy","happy"]
    _set_emotion(choices[emotion_cycle%choices.size()],1.8)
    if emotion=="laugh":feedback.play_cue("laugh")
    elif emotion=="angry":feedback.play_cue("grumpy")
    elif emotion=="sad":feedback.play_cue("sad")
    emotion_cycle+=1

func _update_emotion(delta:float):
    if emotion=="cry":cry_elapsed+=delta
    emotion_left=maxf(0.0,emotion_left-delta)
    if fur_pull.pulling and emotion!="cry":
        if emotion!="sad":_set_emotion("sad",1.4)
        emotion_left=1.4
    elif dragging:
        hold_elapsed+=delta
        if not hidden and hold_elapsed>1.2 and not orb_moved and not hold_love:
            hold_love=true
            _set_emotion("love",1.5)
        if emotion_left<=0.0:emotion="happy"
    elif emotion_left<=0.0:
        if emotion=="dance":feedback.stop_cue("dance")
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
    elif emotion=="sad":eye_scale=Vector3(0.91,0.82,1.0)
    elif emotion=="cry":eye_scale=Vector3(0.96,0.77-0.34*Feedback.sob_strength(cry_elapsed),1.0)
    elif emotion=="dance":eye_scale=Vector3(1.05,0.82,1.0)
    var show_spirals := emotion=="dizzy" or (emotion=="cry" and cried_from_shake and cry_elapsed<0.8)
    for i in range(pupils.size()):
        var target_scale=eye_scale
        if emotion=="wink":target_scale=Vector3(1.06,0.13 if i==0 else 1.02,1.0)
        elif emotion=="curious":target_scale=Vector3(1.03,1.10 if i==0 else 0.65,1.0)
        pupils[i].visible=not show_spirals and emotion not in ["love","laugh"]
        heart_eyes[i].visible=emotion=="love"
        laugh_eyes[i].visible=emotion=="laugh"
        dizzy_eyes[i].visible=show_spirals
        dizzy_eyes[i].rotation.z=t*7.0*(1.0 if i==0 else -1.0)
        heart_eyes[i].scale=Vector3.ONE*(1.0+0.05*sin(t*5.0))
        pupils[i].scale=pupils[i].scale.lerp(target_scale,minf(1.0,delta*16.0))
        var tilt=0.10 if i==0 else -0.10
        if emotion=="angry":tilt=-0.20 if i==0 else 0.20
        if emotion in ["sad","cry"]:tilt=0.17 if i==0 else -0.17
        pupils[i].rotation.z=lerpf(pupils[i].rotation.z,
            tilt if emotion in ["happy","excited","angry","sad","cry"] else 0.0,minf(1.0,delta*12.0))
    smile.visible=emotion in ["happy","excited","wink","love"]
    surprised_mouth.visible=emotion in ["surprised","dance"]
    if emotion=="dance":
        var breath := Feedback.whistle_strength(Feedback.DANCE_SECONDS-emotion_left)
        surprised_mouth.position.x=0.026
        surprised_mouth.scale=Vector3(1.2+0.42*breath,0.78+0.48*breath,1.0)
    elif surprised_mouth.visible:
        surprised_mouth.position.x=0.0
        surprised_mouth.scale=Vector3.ONE
    laugh_mouth.visible=emotion=="laugh"
    laugh_mouth.scale.y=1.0+0.10*sin(t*18.0) if emotion=="laugh" else 1.0
    angry_face.visible=emotion=="angry"
    sad_face.visible=emotion in ["sad","cry"]
    sad_tear.visible=emotion=="sad"
    if sad_face.visible:sad_face.rotation.z=0.014*sin(t*15.0)
    _update_cry_tears()
    dizzy_mouth.visible=emotion=="dizzy"
    # The two black eyes on the small cream orb react to touch as well.
    var eye_height=11.0 if dragging else 16.0
    for eye in [orb_left_eye,orb_right_eye]:
        eye.size.y=lerpf(eye.size.y,eye_height,minf(1.0,delta*16.0))

func _update_cry_tears():
    for i in cry_tears.size():
        var drop := cry_tears[i]
        var age := cry_elapsed-0.05-0.30*i
        drop.visible = emotion=="cry" and age>=0.0
        if not drop.visible:continue
        var u := fposmod(age,1.08)/1.08
        var size_factor := smoothstep(0.0,0.14,u)*(1.0-smoothstep(0.80,1.0,u))*smoothstep(0.0,0.30,emotion_left)
        var fall := smoothstep(0.16,0.96,u)
        var side := -1.0 if i==0 else 1.0
        drop.position = Vector3(side*(0.235+0.087*fall),-0.14-0.45*fall,0.728-0.045*fall)
        drop.scale = Vector3(0.056,0.071+0.018*fall,0.030)*maxf(0.001,size_factor)

func _begin_hold(pointer:Vector2i,point:=Vector2.INF):
    _stop_motion()
    _reset_pet()
    _reset_shake()
    shake_last=pointer
    cried_from_shake=false
    dragging=true
    orb_moved=false
    hold_elapsed=0.0
    hold_excited=false
    hold_love=false
    drag_from=pointer
    window_from=get_window().position
    if not hidden and point.is_finite():
        fur_pull.arm(get_viewport().get_camera_3d(),point,Vector2(pointer))
    _set_emotion("surprised",0.25)
    squish_velocity=1.2
    feedback.play_cue("grab")

func _move_hold(pointer:Vector2i,relative:Vector2):
    if not dragging:return
    if not hidden and not cried_from_shake:_shake_motion(pointer)
    if fur_pull.armed:
        var already_pulling:bool=fur_pull.pulling
        if fur_pull.move(get_viewport().get_camera_3d(),Vector2(pointer)):
            if fur_pull.pulling and not already_pulling:
                orb_moved=true
                tap_count=0
                _set_emotion("sad",1.4)
                feedback.play_cue("sad")
            return
    var diff=pointer-drag_from
    if diff.length()>6.0:orb_moved=true
    if hidden:
        var area=_work_area()
        get_window().position=(window_from+diff).clamp(area.position,area.position+(area.size-ORB_SIZE).max(Vector2i.ZERO))
    else:
        get_window().position=window_from+diff
        drag_v=clampf(relative.x*0.45,-16.0,16.0)
        drag_force=relative.limit_length(70.0)*0.018
    if relative.length()>14.0 and hold_elapsed>0.15 and not hold_excited and emotion not in ["dizzy","cry"]:
        hold_excited=true
        _set_emotion("excited",0.45)
        feedback.play_cue("excited")

func _finish_hold(pointer:Vector2i):
    if not dragging:return
    dragging=false
    var was_pulling:bool=fur_pull.pulling
    fur_pull.release()
    if emotion=="cry":
        squish_velocity=-1.0
        return
    if was_pulling:
        _set_emotion("sad",1.4)
        squish_velocity=-0.65
        return
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
    fur_pull.reset()
    _reset_pet()
    _reset_shake()
    tap_count=0
    dragging=false
    drag_v=0.0
    drag_force=Vector2.ZERO
    _set_emotion("idle",0.0)

func _on_focus_exited():
    menu.visible=false
    _cancel_hold()

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
    var distance=movement.length()
    if distance<4.0:return
    shake_last=pointer
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
        tap_count=0
        _start_cry(true)

func _input(e:InputEvent):
    if menu.visible and e is InputEventMouseButton and e.pressed and not menu.get_global_rect().has_point(e.position):
        menu.visible=false
        get_viewport().set_input_as_handled()
        return
    # Right/middle click and the belly button use the same non-modal host menu.
    if e is InputEventMouseButton and e.button_index in [MOUSE_BUTTON_RIGHT,MOUSE_BUTTON_MIDDLE] and e.pressed:
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
        _begin_hold(DisplayServer.mouse_get_position(),e.position)
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
