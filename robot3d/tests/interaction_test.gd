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
    for cue in ["grab","excited","release","close","open","grumpy","laugh"]:
        var sound:AudioStreamWAV=r.feedback.sounds[cue]
        check(sound.get_length()>0.05 and sound.get_length()<(0.5 if cue=="laugh" else 0.25),cue+" must be short")
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
    r.feedback.cue_played.disconnect(heard_callback)
    r.feedback.player.stop()
    await r.get_tree().create_timer(0.35).timeout
    print("PASS: real scene emotions, deliberate shake and rotating dizzy eyes, hover rubbing and giggle debounce, playful anger, antenna glow, sound PCM, shared menu, softer spring stability, fluffy orb, voice bridge and mute" if not failed else "FAIL: interaction regressions")
