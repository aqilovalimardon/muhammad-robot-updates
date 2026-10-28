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
    for cue in ["grab","excited","release","close","open"]:
        var sound:AudioStreamWAV=r.feedback.sounds[cue]
        check(sound.get_length()>0.05 and sound.get_length()<0.25,cue+" must be short")
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

    r.feedback.enabled=false
    count=played.size()
    r._hide()
    r._show()
    check(played.size()==count and not r.hidden,"mute keeps open/close working")
    r.feedback.cue_played.disconnect(heard_callback)
    r.feedback.player.stop()
    await r.get_tree().create_timer(0.35).timeout
    print("PASS: real scene emotions, sound PCM, debounce, command priority, voice bridge, orb drag/click, menu and mute" if not failed else "FAIL: interaction regressions")
