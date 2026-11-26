extends RefCounted
## Runs in the real Godot scene, including the exported Windows release binary.
var failed=false
var played:Array[String]=[]

func check(condition:bool,message:String):
    if not condition:
        failed=true
        push_error("FAIL: "+message)

func run(r):
    r.set_process(false)
    r.feedback.enabled=true
    var heard_callback=func(cue):played.append(cue)
    r.feedback.cue_played.connect(heard_callback)
    for cue in ["grab","excited","release","close","open","grumpy","laugh","sad"]:
        var sound:AudioStreamWAV=r.feedback.sounds[cue]
        check(sound.get_length()>0.05 and sound.get_length()<(0.5 if cue in ["laugh","sad"] else 0.25),cue+" must be short")
        var pcm=sound.data
        var peak=0
        for i in range(0,pcm.size(),2):peak=maxi(peak,absi(pcm.decode_s16(i)))
        check(peak>1000 and peak<16000,cue+" audible PCM without clipping")
        check(pcm.decode_s16(0)==0 and pcm.decode_s16(pcm.size()-2)==0,cue+" smooth boundaries")
    check(r.feedback.sounds["open"].data!=r.feedback.sounds["close"].data,"distinct open/close cues")

    r._begin_hold(Vector2i(100,100))
    check(r.dragging and r.emotion=="surprised","press shows surprise")
    check(played==["grab"],"one immediate grab cue")
    r._update_emotion(0.3)
    check(r.emotion=="happy" and r.smile.visible,"holding shows a smile")
    check(not r.feedback.play_cue("grab"),"rapid repeat is debounced")
    r.feedback.next_touch_ms=0
    r._move_hold(Vector2i(140,110),Vector2(40,10))
    check(r.emotion=="excited" and r.hold_excited,"fast drag shows delight")
    check(played==["grab","excited"],"single delighted chirp")
    for i in range(20):r._move_hold(Vector2i(180+i,120),Vector2(30,10))
    check(played.size()==2,"motion does not flood sounds")
    r.feedback.next_touch_ms=0
    r._finish_hold(Vector2i(200,120))
    check(not r.dragging and r.emotion=="happy","release settles into smile")
    check(played.back()=="release","release cue")
    r._update_emotion(1.0)
    check(r.emotion=="idle" and not r.smile.visible,"expression returns to idle")

    # Commands bypass touch debounce and interrupt any current chirp, no queue.
    r._hide()
    check(r.hidden and not r.robot.visible and r.small_eye.visible,"close shows cream orb")
    check(played.back()=="close","close interrupts touch sound immediately")
    var count=played.size()
    r._hide()
    check(played.size()==count,"duplicate close is silent")
    r._show()
    check(not r.hidden and r.robot.visible and not r.small_eye.visible,"open restores 3D")
    check(played.back()=="open","open immediately replaces close sound")
    r._begin_hold(Vector2i(100,100))
    check(played.back()=="open","touch does not cut off command cue")
    r._cancel_hold()
    check(not r.dragging and r.emotion=="idle","focus loss cancels hold")

    r._hide()
    r._begin_hold(Vector2i(100,100))
    r._move_hold(Vector2i(180,130),Vector2(80,30))
    r._move_hold(Vector2i(100,100),Vector2(-80,-30))
    r._finish_hold(Vector2i(100,100))
    check(r.hidden,"orb drag returning to origin never becomes a click")
    r._begin_hold(Vector2i(100,100))
    r._finish_hold(Vector2i(102,101))
    check(not r.hidden,"orb click still opens robot")

    # Use the actual file bridge to check both recognition directions.
    r.signal_file=OS.get_user_data_dir()+"/interaction_test.cmd"
    var file=FileAccess.open(r.signal_file,FileAccess.WRITE)
    file.store_string("hide")
    file.close()
    r._listen_to_python_voice(0.03)
    check(r.hidden and played.back()=="close","voice close reaches scene in one poll")
    file=FileAccess.open(r.signal_file,FileAccess.WRITE)
    file.store_string("show")
    file.close()
    r._listen_to_python_voice(0.03)
    check(not r.hidden and played.back()=="open","voice open reaches scene in one poll")
    r.signal_file=""

    # Real GUI propagation: menu and belly must not trigger the new grab effect.
    r.menu.visible=true
    await r.get_tree().process_frame
    var press=InputEventMouseButton.new()
    press.button_index=MOUSE_BUTTON_LEFT
    press.pressed=true
    press.position=Vector2(40,20)
    Input.parse_input_event(press)
    await r.get_tree().process_frame
    check(not r.dragging,"menu press is consumed before grab handler")
    r._cancel_hold()
    r.menu.visible=false
    press=InputEventMouseButton.new()
    press.button_index=MOUSE_BUTTON_LEFT
    press.pressed=true
    press.position=Vector2(85,140)
    Input.parse_input_event(press)
    await r.get_tree().process_frame
    check(not r.dragging,"belly button press is not a grab")

    # Both right-click and belly request the same host menu without changing mode.
    r.bridge_file=OS.get_user_data_dir()+"/shared_menu_test.cmd"
    r.menu.visible=false
    r._toggle_menu()
    check(FileAccess.get_file_as_string(r.bridge_file)=="menu","belly requests shared host menu")
    check(not r.menu.visible and not r.hidden,"shared menu keeps 3D visible")
    DirAccess.remove_absolute(r.bridge_file)
    r._hide()
    var right_click=InputEventMouseButton.new()
    right_click.button_index=MOUSE_BUTTON_RIGHT
    right_click.pressed=true
    r._input(right_click)
    check(FileAccess.get_file_as_string(r.bridge_file)=="menu","orb right-click uses shared menu")
    check(r.hidden,"opening orb context menu does not expand the avatar")
    DirAccess.remove_absolute(r.bridge_file)
    var middle_click=InputEventMouseButton.new()
    middle_click.button_index=MOUSE_BUTTON_MIDDLE
    middle_click.pressed=true
    r._input(middle_click)
    check(FileAccess.get_file_as_string(r.bridge_file)=="menu","middle-click uses the same host menu")
    DirAccess.remove_absolute(r.bridge_file)
    r.bridge_file=""
    check(r.small_eye.size==Vector2(64,64),"fluffy orb has room for its fur")
    check(r.orb_left_eye.size.x==14.0 and r.orb_right_eye.size.x==14.0,"both black eyes are larger")
    r._show()
    r.menu.visible=true
    r._on_focus_exited()
    check(not r.menu.visible,"standalone menu dismisses on focus loss")
    r.menu.visible=true
    var outside_click=InputEventMouseButton.new()
    outside_click.button_index=MOUSE_BUTTON_LEFT
    outside_click.pressed=true
    outside_click.position=Vector2(-10,-10)
    r._input(outside_click)
    check(not r.menu.visible and not r.dragging,"standalone outside click closes without dragging")

    r._begin_hold(Vector2i(100,100))
    r._update_emotion(1.3)
    check(r.emotion=="love" and r.heart_eyes[0].visible,"gentle long hold shows heart eyes")
    r._cancel_hold()
    r._set_emotion("wink",1.0)
    r._update_emotion(0.2)
    check(r.pupils[0].scale.y<0.3 and r.pupils[1].scale.y>0.8,"wink closes only one eye")
    r._set_emotion("curious",1.0)
    r._update_emotion(0.2)
    check(r.pupils[0].scale.y>r.pupils[1].scale.y,"curiosity has asymmetric eyes")
    r._set_emotion("sleepy",1.0)
    r._update_emotion(0.2)
    check(r.pupils[0].scale.y<0.3 and r.pupils[1].scale.y<0.3,"sleepy eyes relax together")

    r._begin_hold(Vector2i(100,100))
    r._move_hold(Vector2i(160,140),Vector2(60,40))
    for i in range(30):r._advance_soft_body(1.0/30.0)
    check(r.robot.scale.y<0.83 and r.robot.scale.x>1.10,"plush compresses more softly than v2.2.19: "+str(r.robot.scale))
    check(absf(r.robot.scale.x*r.robot.scale.y*r.robot.scale.z-1.0)<0.001,"squash preserves body volume")
    r._finish_hold(Vector2i(160,140))
    var stretched=false
    for i in range(150):
        r._advance_soft_body(1.0/30.0)
        if r.robot.scale.y>1.01:stretched=true
    check(stretched,"release springs through a gentle stretch")
    check(absf(r.squish)<0.003 and r.head_lag.length()<0.003,"body and head settle after release")
    for i in range(20):r._advance_soft_body(0.5)
    check(r.robot.scale.is_finite(),"slow frames cannot destabilize the spring")

    # Hover strokes must reach the actual deformed 3D body, with no held button.
    r._cancel_hold()
    r._update_emotion(0.1)
    r.menu.visible=false
    r.feedback.command_until_ms=0
    r.feedback.next_touch_ms=0
    var camera=r.get_viewport().get_camera_3d()
    var cheek=camera.unproject_position(r.head.global_position)
    check(r._pointer_on_plush(cheek),"pet hit test finds the actual head")
    check(not r._pointer_on_plush(Vector2(1,190)),"transparent corners are not pettable")
    var before_position=r.get_window().position
    count=played.size()
    for i in range(10):r._pet_motion(cheek,Vector2(8,0))
    check(r.emotion!="laugh","one-way pointer movement is not rubbing")
    r._reset_pet()
    for i in range(16):r._pet_motion(cheek,Vector2(0.4 if i%2==0 else -0.4,0))
    check(r.emotion!="laugh","stationary mouse jitter is ignored")
    for i in range(3):
        r._pet_motion(cheek,Vector2(18,0))
        r._advance_pet(0.4)
        r._pet_motion(cheek,Vector2(-18,0))
        r._advance_pet(0.4)
    check(r.emotion!="laugh","separate passes do not accumulate into rubbing")
    r._reset_pet()
    # Dispatch through the real viewport so GUI filtering and mouse-up behavior apply.
    for i in range(12):
        var motion=InputEventMouseMotion.new()
        var direction=1.0 if (i/3)%2==0 else -1.0
        motion.position=cheek+Vector2(float(i%3-1)*8.0,0)
        motion.relative=Vector2(10.0*direction,0)
        motion.button_mask=0
        Input.parse_input_event(motion)
        await r.get_tree().process_frame
    r._update_emotion(0.05)
    check(r.emotion=="laugh" and r.laugh_mouth.visible and r.laugh_eyes[0].visible,"real hover rubbing makes laughing eyes and mouth")
    check(not r.dragging and r.get_window().position==before_position,"rubbing never moves the desktop robot")
    check(played.size()==count+1 and played.back()=="laugh","rubbing plays one short giggle")
    check(not r.feedback.play_cue("grab"),"incidental cues cannot chop a giggle")
    for i in range(60):r._pet_motion(cheek,Vector2(20.0 if (i/2)%2==0 else -20.0,0))
    check(played.size()==count+1,"continued rubbing does not flood giggles")
    r._hide()
    check(played.back()=="close","close interrupts the giggle without a queue")
    for i in range(12):r._pet_motion(cheek,Vector2(20.0 if i%2==0 else -20.0,0))
    check(r.emotion!="laugh","closed orb does not start an invisible laugh")
    r._show()
    r._cancel_hold()
    r.menu.visible=true
    for i in range(12):r._pet_motion(cheek,Vector2(20.0 if i%2==0 else -20.0,0))
    check(r.emotion!="laugh","an open menu prevents pet gestures")
    r.menu.visible=false
    r._begin_hold(Vector2i(100,100))
    for i in range(12):r._pet_motion(cheek,Vector2(20.0 if i%2==0 else -20.0,0))
    check(r.emotion=="surprised","dragging cannot become hover rubbing")
    r._cancel_hold()

    for i in range(3):
        r._begin_hold(Vector2i(100,100))
        r._finish_hold(Vector2i(100,100))
    r._update_emotion(0.1)
    check(r.emotion=="angry" and r.angry_face.visible,"three quick taps show playful grumpiness")
    check(r.pupils[0].rotation.z<0.0 and r.pupils[1].rotation.z>0.0,"grumpy eyes slant inwards")
    check(not r.smile.visible and not r.laugh_mouth.visible,"grumpy face clears happy mouths")
    r._update_emotion(2.0)
    check(r.emotion=="idle" and not r.angry_face.visible,"anger settles by itself")
    r.emotion_cycle=0
    r._show_next_emotion()
    check(r.emotion=="laugh","shared emotion menu includes laughter")
    r._show_next_emotion()
    check(r.emotion=="angry","shared emotion menu includes anger")
    r.antenna_glow.update_glow(1.0,"laugh",1.0)
    check(r.antenna_glow.halo.texture.get_width()==96,"antenna uses a cached soft radial texture")
    check(r.antenna_glow.tint.r>0.95 and r.antenna_glow.light.light_energy>0.3,"laughter warms the real antenna light")
    r.antenna_glow.update_glow(2.0,"angry",1.0)
    check(r.antenna_glow.tint.r>r.antenna_glow.tint.b,"anger softly warms the antenna rays")
    r._cancel_hold()

    r._begin_hold(Vector2i(100,100))
    for x in [125,150,175,200]:
        r._move_hold(Vector2i(x,100),Vector2(25,0))
        r._advance_shake(0.06)
    check(r.emotion!="dizzy","ordinary one-way dragging is not shaking")
    r._cancel_hold()
    r._begin_hold(Vector2i(100,100))
    for x in [160,100,160,100]:
        r._move_hold(Vector2i(x,100),Vector2(60,0))
        r._advance_shake(0.4)
    check(r.emotion!="dizzy","slow direction changes do not cause dizziness")
    r._cancel_hold()
    r._begin_hold(Vector2i(100,100))
    for x in [160,100,160,100]:
        r._move_hold(Vector2i(x,100),Vector2(60,0))
        r._advance_shake(0.06)
    r._update_emotion(0.01)
    check(r.emotion=="dizzy" and r.dizzy_eyes[0].visible and r.dizzy_mouth.visible,"deliberate shaking shows two spiral eyes and a wobbly mouth")
    check(not r.pupils[0].visible and not r.laugh_eyes[0].visible,"spirals replace the normal pupils")
    var angle=r.dizzy_eyes[0].rotation.z
    r.t+=0.2
    r._update_emotion(0.01)
    check(absf(r.dizzy_eyes[0].rotation.z-angle)>0.5,"spiral eyes really rotate over time")
    r._finish_hold(Vector2i(100,100))
    check(r.emotion=="dizzy" and not r.dragging,"dizzy effect continues briefly after release")
    r._update_emotion(2.5)
    check(r.emotion=="idle" and not r.dizzy_eyes[0].visible,"dizziness settles automatically")
    r._hide()
    r._begin_hold(Vector2i(100,100))
    for x in [160,100,160,100]:r._move_hold(Vector2i(x,100),Vector2(60,0))
    check(r.emotion!="dizzy","closed orb dragging does not animate hidden spirals")
    r._cancel_hold()
    r._show()
    r._cancel_hold()

    r.feedback.enabled=false
    count=played.size()
    r.laugh_cooldown=0.0
    for i in range(12):r._pet_motion(cheek,Vector2(20.0 if (i/2)%2==0 else -20.0,0))
    check(r.emotion=="laugh" and played.size()==count,"muted petting stays expressive and silent")
    r._hide()
    r._show()
    check(played.size()==count and not r.hidden,"mute keeps open/close working")
    await _coat_checks(r)
    _cry_checks(r)
    await motion_checks(r)
    r.feedback.cue_played.disconnect(heard_callback)
    r.feedback.player.stop()
    await r.get_tree().create_timer(0.35).timeout
    print("PASS: real scene emotions, deliberate shake and rotating dizzy eyes, hover rubbing and giggle debounce, playful anger, antenna glow, sound PCM, shared menu, softer spring stability, fluffy orb, voice bridge and mute" if not failed else "FAIL: interaction regressions")

func _coat_checks(r):
    r._cancel_hold()
    r.feedback.enabled=true
    r.feedback.command_until_ms=0
    r.feedback.next_touch_ms=0
    r.feedback.next_sad_ms=0
    for i in 60:r._process(1.0/30.0)
    var camera=r.get_viewport().get_camera_3d()
    var cheek=camera.unproject_position(r.head.to_global(Vector3(-0.65,0.12,0.06)))
    var face=camera.unproject_position(r.head.to_global(Vector3(0.0,0.0,0.64)))
    var clothes=r.fur_pull
    for point in [face,Vector2(1.0,1.0)]:
        clothes.arm(camera,point,point)
        check(not clothes.armed,"visor and transparent corners cannot grab the fur")
    var belly_edge=camera.unproject_position(r.robot.to_global(Vector3(0.49,-0.59,0.17)))
    clothes.arm(camera,belly_edge,belly_edge)
    check(clothes.armed and clothes.selected.skin.name=="RoundedBody","torso has a pickable coat")
    clothes.reset()
    # Start through the viewport's actual press handler; do not hardcode a tuft.
    var press=InputEventMouseButton.new()
    press.button_index=MOUSE_BUTTON_LEFT
    press.pressed=true
    press.position=cheek
    r.get_viewport().push_input(press,true)
    await r.get_tree().process_frame
    var start=r.drag_from
    var window=r.get_window().position
    check(clothes.armed and not clothes.pulling,"a real press on the head catches a visible tuft")
    r._move_hold(start+Vector2i(-3,0),Vector2(-3,0))
    check(not clothes.pulling and r.emotion!="sad","tiny motion does not upset the robot")
    var sad_count=played.count("sad")
    r._move_hold(start+Vector2i(-31,2),Vector2(-28,2))
    for i in 18:r._process(1.0/30.0)
    check(clothes.pulling and r.emotion=="sad" and r.sad_face.visible,"outward tug shows a sad face")
    check(r.get_window().position==window and r.sad_weight>0.85 and r.left_hand.position.x>-0.54,
        "the window stays in place while the head and limbs fold in")
    check(played.count("sad")==sad_count+1,"a single quiet sigh per pull")
    if clothes.selected!=null:
        var selected=clothes.selected
        var extension:Vector3=selected.fur_mat.get_shader_parameter("extension")
        check(extension.x < -0.25 and extension.length()<=clothes.MAX_EXTENSION+0.001,
            "the actual coat material follows the pointer by a bounded amount")
        check(extension==selected.skin_mat.get_shader_parameter("extension"),"skin and fur roots remain attached")
        for patch in clothes.patches:
            if patch!=selected:
                var other=patch.fur_mat.get_shader_parameter("extension")
                check(other==null or other==Vector3.ZERO,"the other coat patch stays at rest")
    for i in 35:r._move_hold(start+Vector2i(-70-i,2),Vector2(-1,0))
    check(played.count("sad")==sad_count+1,"continuing a tug does not repeat the sigh")
    r._finish_hold(start+Vector2i(-100,2))
    check(not r.dragging and r.emotion=="sad","releasing a tuft does not switch to a happy chirp")
    for i in 120:r._process(1.0/30.0)
    check(clothes.selected==null and clothes.displacement==Vector3.ZERO and r.emotion=="idle",
        "coat and mood settle after release")
    r._begin_hold(start,face)
    r._move_hold(start+Vector2i(28,0),Vector2(28,0))
    check(r.orb_moved and not clothes.pulling and r.emotion!="sad","center drag still moves the robot")
    r._cancel_hold()
    r.feedback.enabled=false
    sad_count=played.count("sad")
    cheek=camera.unproject_position(r.head.to_global(Vector3(-0.65,0.12,0.06)))
    r._begin_hold(start,cheek)
    r._move_hold(start+Vector2i(-28,0),Vector2(-28,0))
    check(clothes.pulling and r.emotion=="sad" and played.count("sad")==sad_count,"muted tugs remain expressive")
    r._hide()
    check(not clothes.armed and clothes.selected==null and r.hidden,"close during a pull releases it")
    r._show()
    r._set_emotion("laugh",1.4)
    var low=INF
    var high=-INF
    for i in 30:
        r._process(1.0/30.0)
        low=minf(low,r.robot.position.y)
        high=maxf(high,r.robot.position.y)
    check(r.laugh_weight>0.95 and high-low>0.09 and r.left_hand.position.y>-0.23,
        "laughter bounces the body and lifts the arms")
    check(r.feedback.sounds["sad"].data!=r.feedback.sounds["laugh"].data,"sigh and giggle have distinct audio")
    if not failed:print("PASS: local fur stretch, 3D-only gestures, quiet sad/laugh poses, mute and recovery")

func _cry_checks(r):
    var enabled: bool = r.feedback.enabled
    r._cancel_hold()
    r.feedback.enabled = true
    var count := played.count("cry")
    r._handle_host_command("cry")
    for i in 9:r._process(1.0/30)
    var first_y: float = r.cry_tears[0].position.y
    var elapsed: float = r.cry_elapsed
    r._handle_host_command("cry")
    check(played.count("cry")==count+1 and r.cry_elapsed==elapsed,"repeat Cry preserves the current sob")
    for i in 12:r._process(1.0/30)
    check(r.sad_face.visible and not r.sad_tear.visible and r.sad_weight>0.9,"cry lowers the plush and shows a frown")
    check(r.cry_tears[0].visible and r.cry_tears[1].visible and r.cry_tears[0].position.y<first_y-0.14
        and r.cry_tears[1].position.y>r.cry_tears[0].position.y+0.05,"tears roll separately down both cheeks")
    var voice: AudioStreamWAV = r.feedback.sounds["cry"]
    var pcm := voice.data
    var peak := 0
    var pulses := 0
    var previous_loud := false
    var block := voice.mix_rate/25
    for start in range(0,pcm.size()/2,block):
        var local_peak := 0
        for frame in range(start,mini(start+block,pcm.size()/2)):
            local_peak=maxi(local_peak,absi(pcm.decode_s16(frame*2)))
        peak=maxi(peak,local_peak)
        if local_peak>1500 and not previous_loud:pulses+=1
        previous_loud=local_peak>1500
    check(pulses==3 and peak>2000 and peak<12000 and pcm.decode_s16(0)==0 and pcm.decode_s16(pcm.size()-2)==0,
        "cry has three quiet voiced sobs with clean boundaries")
    r._handle_host_command("stop")
    r._process(0.03)
    check(r.emotion=="idle" and not r.cry_tears[0].visible and not r.feedback.player.playing,"Stop ends cry and its sound")
    r.feedback.enabled=false
    r._handle_host_command("fly")
    r._handle_host_command("cry")
    for i in 20:r._process(1.0/30)
    check(r.motion.flying and r.cry_tears[1].visible and played.count("cry")==count+1,"muted cry works during flight")
    for i in 80:r._process(1.0/30)
    check(r.emotion=="idle" and not r.cry_tears[1].visible and r.motion.flying,"cry settles without stopping flight")
    r._hide()
    r._handle_host_command("cry")
    r._process(0.03)
    check(r.hidden and r.emotion!="cry","the closed orb ignores Cry")
    r._show()
    r.feedback.enabled=enabled
    if not failed:print("PASS: voice Cry animates two falling tears and three gentle sobs, respects mute, Stop and the closed orb")

func motion_checks(r):
    r.set_process(false)
    var sound_enabled = r.feedback.enabled
    r.feedback.enabled = false
    _flight_pose_checks(r)
    # The model also handles a monitor to the left of the primary display.
    var path = r.DesktopMotion.new()
    var bounds := Rect2i(-1440,50,1264,590)
    var origin := Vector2i(-780,390)
    path.fly(origin,bounds)
    check(path.location==Vector2(origin),"flight starts where the robot is")
    var far := 0.0
    for i in 500:
        path.advance(1.0/30.0)
        check(path.location==path.location.clamp(Vector2(bounds.position),Vector2(bounds.end)),"flight stays on its monitor")
        far=maxf(far,path.location.distance_to(Vector2(origin)))
    check(far>390.0,"flight crosses the desktop")
    var airborne=path.location
    path.fly(origin,bounds)
    check(path.location==airborne,"repeating Fly does not restart the path")
    path.jump(Vector2i(airborne),bounds)
    for i in 10:path.advance(1.0/30.0)
    check(path.flying and path.jump_height>0.3,"an airborne hop preserves the flight path")
    path.stop()
    var stopped=path.location
    for i in 30:path.advance(1.0/30.0)
    check(path.location==stopped and not path.flying and not path.jumping,"Stop holds the exact current position")
    path.jump(origin,bounds)
    var peak := 0.0
    for i in 40:
        path.advance(1.0/30.0)
        peak=maxf(peak,origin.y-path.location.y)
    check(peak>95.0 and path.location==Vector2(origin) and not path.jumping,"one hop rises and lands at its starting point")
    path.jump(bounds.position,bounds)
    path.advance(0.10)
    path.advance(0.10)
    check(path.jump_height>0.0 and path.location.y==bounds.position.y,"a hop at the top keeps the robot on screen")

    await _wave_checks(r)
    var native := DisplayServer.get_name()!="headless"
    var window:Window=r.get_window()
    if native:
        window.position=r._motion_limits().get_center()
        await r.get_tree().process_frame
    var start=window.position
    r._handle_host_command("fly")
    for i in 48:r._process(1.0/30.0)
    check(r.motion.flying,"Fly starts continuous motion")
    if native:
        await RenderingServer.frame_post_draw
        var layer:Window=r.flight_trail
        check(window.position.distance_to(start)>85.0 and window.size==r.DESK_SIZE,"real avatar window travels at its original size")
        check(layer!=null and layer.visible and layer.mouse_passthrough and layer.unfocusable,"trail is visible and click-through")
        var wake=layer.get_texture().get_image()
        wake.convert(Image.FORMAT_RGBA8)
        var pixels=0
        var jade=0
        var gold=0
        var reach=0.0
        var avatar=Rect2i(window.position,window.size)
        for y in wake.get_height():
            for x in wake.get_width():
                var desktop_pixel=layer.position+Vector2i(x,y)
                if avatar.has_point(desktop_pixel):continue
                var ink=wake.get_pixel(x,y)
                if ink.a>0.15:pixels+=1
                if ink.g-ink.r>0.10 and ink.g>ink.b:jade+=1
                if ink.r-ink.b>0.09 and ink.r>ink.g:gold+=1
                if ink.a>0.08:reach=maxf(reach,desktop_pixel.distance_to(avatar.get_center()))
        check(pixels>350 and jade>35 and gold>15 and reach>160.0,"jade and gold ribbons extend behind the avatar: "+str([pixels,jade,gold,reach]))
        var folder=OS.get_environment("ROBOT_REVIEW_DIR")
        if not folder.is_empty():
            var both=Rect2i(layer.position,layer.size).merge(avatar)
            var picture=Image.create_empty(both.size.x,both.size.y,false,Image.FORMAT_RGBA8)
            picture.fill(Color("263447"))
            _composite_viewport(picture,wake,layer.position-both.position)
            var robot_image=window.get_texture().get_image()
            robot_image.convert(Image.FORMAT_RGBA8)
            _composite_viewport(picture,robot_image,window.position-both.position)
            picture.save_png(folder+"/flight.png")
    r._handle_host_command("stop")
    var freeze=window.position
    for i in 18:r._process(1.0/30.0)
    check(not r.motion.flying and window.position==freeze,"Stop freezes the desktop position immediately")
    if native:
        check(r.flight_trail.visible,"the existing trail lingers after Stop")
        for i in 60:r._process(1.0/30.0)
        check(window.position==freeze and not r.flight_trail.visible,"afterglow expires without moving the robot")
        window.position=Vector2i(freeze.x,r._motion_limits().get_center().y)
        freeze=window.position
    r._handle_host_command("jump")
    for i in 12:r._process(1.0/30.0)
    check(r.motion.jump_height>0.85 and r.left_foot.position.y>-0.73,"Jump tucks both feet")
    if native:
        await RenderingServer.frame_post_draw
        check(window.position.y<freeze.y-40,"the real window rises on Jump")
        _review_frame(r,"jump")
    for i in 25:r._process(1.0/30.0)
    check(window.position==freeze and not r.motion.jumping,"the real jump lands once")
    r._handle_host_command("fly")
    r._begin_hold(Vector2i(100,100))
    check(r.dragging and not r.motion.flying,"mouse hold takes control during flight")
    r._cancel_hold()
    r._handle_host_command("fly")
    r._hide()
    for command in ["wave","fly","jump","stop"]:r._handle_host_command(command)
    check(r.hidden and not r.motion.flying and not r.motion.jumping and not r.motion.waving,"closed orb ignores movement commands")
    r._show()
    check(not r.hidden and not r.motion.flying,"Open restores the stationary plush")
    check(r.motion.lean==Vector2.ZERO and r.motion.follow_through==Vector2.ZERO,"the restored plush starts with no flight deformation")
    if native:
        await _ribbon_checks(r)
        if not failed:print("PASS: articulated wave, layered light ribbons and lingering afterglow on the native desktop")
        await _render_cry(r)
    r.feedback.enabled = sound_enabled
    if not failed:print("PASS: Hello hand wave, bounded desktop flight, trail, immediate stop, single jump and manual control")

func _wave_checks(r):
    r._cancel_hold()
    r._handle_host_command("wave")
    var smooth := true
    var narrowest_x := INF
    var widest_x := -INF
    var previous:Vector3
    var raised_elbow:Vector3
    var review := {5:"hello_lift",12:"hello",16:"hello_in",24:"hello_out",45:"hello_lower"}
    for i in range(1,57):
        if i==20:r._handle_host_command("wave")
        r._process(1.0/30.0)
        var palm:Vector3 = r.right_hand.position
        if i>1:smooth = smooth and previous.distance_to(palm)<0.115
        previous = palm
        if r.wave_upper_arm.visible:
            var elbow:Vector3 = 2.0*r.wave_upper_arm.position-r.WAVE_SHOULDER
            smooth = smooth and absf(elbow.distance_to(r.WAVE_SHOULDER)-r.UPPER_ARM_LENGTH)<0.001
            smooth = smooth and absf(elbow.distance_to(palm)-r.ELBOW_TO_PALM)<0.001
            if i>=12 and i<=38:
                if i==12:raised_elbow=elbow
                smooth = smooth and elbow.distance_to(raised_elbow)<0.003
                smooth = smooth and palm.y>0.22 and palm.x>0.71 and r.right_hand.basis.y.normalized().y>0.69
                smooth = smooth and r.left_hand.position.y<0.0
                narrowest_x=minf(narrowest_x,palm.x)
                widest_x=maxf(widest_x,palm.x)
        if review.has(i) and DisplayServer.get_name()!="headless" and not OS.get_environment("ROBOT_REVIEW_DIR").is_empty():
            await RenderingServer.frame_post_draw
            _review_frame(r,review[i])
    check(smooth and widest_x-narrowest_x>0.11,"a fixed-length bent arm waves from a planted elbow with an upright mitten")
    check(not r.motion.waving and not r.wave_upper_arm.visible and r.right_hand.position.y<0.0 and r.right_hand.scale.is_equal_approx(r.REST_HAND_SIZE),"the greeting settles back into its ordinary hand pose")

func _flight_pose_checks(r):
    var path = r.motion
    var bounds := Rect2i(-1440,50,1264,590)
    path.fly(bounds.get_center(),bounds)
    var directions := [false,false,false,false]
    var longest := 1.0
    var most_lag := 0.0
    var valid := true
    for i in 660:
        var previous:Vector2 = path.location
        path.advance(1.0/30.0)
        var actual:Vector2 = (path.location-previous)*30.0
        if i==0:check(actual.length()<52.0,"takeoff starts gently")
        if i==105:path.jump(Vector2i(path.location),bounds)
        r._advance_soft_body(1.0/30.0)
        r._apply_motion_pose()
        var pose:Basis = r.flight_pose.basis
        valid = valid and actual.distance_to(path.velocity)<0.03 and absf(pose.determinant()-1.0)<0.002
        most_lag = maxf(most_lag,path.lean.distance_to(path.follow_through))
        if actual.length()<140.0:continue
        var heading := Vector3(actual.x,-actual.y,0.0).normalized()
        longest=maxf(longest,(pose.transposed()*heading).length())
        if actual.x>160.0 and pose.y.x>0.12:directions[0]=true
        if actual.x< -160.0 and pose.y.x< -0.12:directions[1]=true
        if actual.y>125.0 and pose.z.y< -0.075:directions[2]=true
        if actual.y< -125.0 and pose.z.y>0.075:directions[3]=true
    check(valid and not directions.has(false),"real pose leans left, right, up and down along screen travel, even during a hop")
    check(longest>1.11 and most_lag>0.18,"body stretches along travel while feet and antenna catch up")
    path.stop()
    var freeze:Vector2 = path.location
    for i in 48:path.advance(1.0/15.0)
    check(freeze==path.location and path.lean.length()<0.001 and path.follow_through.length()<0.001,"stopping fixes the window while the elastic pose settles")
    path.reset_flight_pose()

func _ribbon_checks(r):
    var layer = r.flight_trail
    var base := Vector2(r._work_area().get_center())-Vector2(120,0)
    var counts := []
    for fps in [15,60]:
        layer.clear_trail()
        for i in range(fps+1):
            var point := base+Vector2(220.0*i/fps,0.0)
            layer.advance(1.0/fps,true,point,base+Vector2(140,0),base+Vector2(140,22))
        counts.append(layer.ribbons.knots.size())
    check(counts[0]==counts[1] and counts[0]>=40,"ribbons sample equal distances across frame rates")
    await RenderingServer.frame_post_draw
    var image=layer.get_texture().get_image()
    var face:=Vector2i(base+Vector2(140,0))-Vector2i(layer.position)
    check(image.get_pixelv(face).a<0.01 and image.get_pixelv(face+Vector2i(65,0)).a>0.13,"ribbons stay behind the face during a crossing")
    # Measure actual opacity across the wake, in desktop pixels, off the avatar.
    var width := 0
    var streamers := 0
    for offset in [74, 86, 192]:
        var column := Vector2i(base+Vector2(offset,0))-Vector2i(layer.position)
        var lo := 80
        var hi := -80
        var bands := 0
        var inside := false
        for y in range(-74,75):
            var alpha: float = image.get_pixelv(column+Vector2i(0,y)).a
            if alpha > 0.16:
                lo = mini(lo,y)
                hi = maxi(hi,y)
            if alpha > 0.46 and not inside:
                bands += 1
            inside = alpha > 0.46
        width = maxi(width,hi-lo+1)
        streamers = maxi(streamers,bands)
    check(width>=72 and streamers>=4,"flight fans across the robot's back with separate bright streamers: "+str([width,streamers]))
    if not failed:print("PASS: rendered flight fan spans ",width," desktop pixels with ",streamers," bright streamers")
    var probe := base+Vector2(195,0)
    var brightness := []
    for frames in [24,36,57]:
        for i in frames:layer.advance(1.0/60.0,false,base,base,base)
        await RenderingServer.frame_post_draw
        image=layer.get_texture().get_image()
        var local := Vector2i(probe)-Vector2i(layer.position)
        var energy := 0.0
        for y in range(-72,73):energy+=image.get_pixelv(local+Vector2i(0,y)).a
        brightness.append(energy)
    check(brightness[0]>brightness[1] and brightness[1]>brightness[2] and brightness[2]>0.01,"a fixed patch of afterglow dims gradually for nearly two seconds")
    for i in 45:layer.advance(1.0/60.0,false,base,base,base)
    check(layer.ribbons.knots.is_empty() and not layer.visible,"the last light disappears on its own")
    var away := base+Vector2(0,120)
    for i in 21:layer.advance(1.0/30.0,true,base+Vector2(i*5,0),away,away)
    layer.end_emission()
    for i in 21:layer.advance(1.0/30.0,true,base+Vector2(180+i*5,0),away,away)
    await RenderingServer.frame_post_draw
    image=layer.get_texture().get_image()
    var gap:=Vector2i(base+Vector2(140,0))-Vector2i(layer.position)
    var empty_gap:=true
    for y in range(-72,73):
        if image.get_pixelv(gap+Vector2i(0,y)).a>0.02:empty_gap=false
    check(empty_gap,"restarting flight leaves separate strokes without a line across the gap")
    layer.clear_trail()

func _render_cry(r):
    r._handle_host_command("cry")
    for i in 19:r._process(1.0/30.0)
    await RenderingServer.frame_post_draw
    _review_frame(r,"cry")
    var wet: Image = r.get_viewport().get_texture().get_image()
    var camera: Camera3D = r.get_viewport().get_camera_3d()
    var cheeks: Array[Vector2i] = []
    for drop in r.cry_tears:
        cheeks.append(Vector2i(camera.unproject_position(drop.global_position)))
        drop.hide()
    await RenderingServer.frame_post_draw
    var dry: Image = r.get_viewport().get_texture().get_image()
    for point in cheeks:
        var pixels := 0
        for y in range(-5,6):
            for x in range(-5,6):
                var at := point + Vector2i(x,y)
                var water := wet.get_pixelv(at)
                var skin := dry.get_pixelv(at)
                if water.b > water.r+0.15 and absf(water.r-skin.r)+absf(water.b-skin.b)>0.20:
                    pixels+=1
        check(pixels>=3,"each cheek has a rendered blue tear: "+str(pixels))
    r._handle_host_command("stop")
    if not failed:print("PASS: both blue tears are visible on the rendered desktop robot")

func _composite_viewport(picture: Image, source: Image, origin: Vector2i):
    # Viewport textures contain premultiplied color as sent to the desktop compositor.
    for y in source.get_height():
        for x in source.get_width():
            var pixel := source.get_pixel(x,y)
            if pixel.a==0.0:continue
            var at := origin+Vector2i(x,y)
            var color := pixel+picture.get_pixelv(at)*(1.0-pixel.a)
            color.a=1.0
            picture.set_pixelv(at,color)

func _review_frame(r,label:String):
    var folder=OS.get_environment("ROBOT_REVIEW_DIR")
    if not folder.is_empty() and DisplayServer.get_name()!="headless":
        var frame=r.get_viewport().get_texture().get_image()
        frame.convert(Image.FORMAT_RGBA8)
        frame.save_png(folder+"/"+label+".png")
