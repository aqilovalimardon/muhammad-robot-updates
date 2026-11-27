extends RefCounted
## Windows CI: real recognized WAVs -> host handlers -> this exported Godot scene.
func run(r):
    var args=OS.get_cmdline_user_args()
    var index=args.find("--voice-ack")
    if index<0 or index+1>=args.size():
        r.get_tree().quit(1)
        return
    var output=args[index+1]
    r.feedback.enabled=false
    var file=FileAccess.open(output,FileAccess.WRITE)
    file.store_string("ready\n")
    file.close()
    var motion_test="--voice-motion-test" in args
    var sequence=["hello","fly","stop","jump","close","open"] if motion_test else ["hello","close","open"]
    var cry_test="--voice-cry-test" in args
    if cry_test:sequence=["hello","fly","stop","cry","close","open","jump"]
    var stage=0
    var deadline=Time.get_ticks_msec()+55000
    while Time.get_ticks_msec()<deadline:
        await r.get_tree().process_frame
        var passed=false
        match sequence[stage]:
            "hello":passed=r.wave_upper_arm.visible and r.right_hand.position.y>0.2 if motion_test else r.emotion=="excited"
            "fly":passed=r.motion.flying
            "stop":passed=not r.motion.flying and not r.motion.jumping
            "jump":passed=r.motion.jumping and r.motion.jump_height>0.6
            "cry":passed=r.emotion=="cry" and r.sad_face.visible and r.cry_tears[0].visible and r.sad_weight>0.5
            "close":passed=r.hidden
            "open":passed=not r.hidden
        if not passed:continue
        file=FileAccess.open(output,FileAccess.READ_WRITE)
        file.seek_end()
        file.store_string(sequence[stage]+"\n")
        file.close()
        stage+=1
        if stage==sequence.size():
            print("PASS: recorded Hello/Close/Open reached the actual exported 3D scene")
            if motion_test:print("PASS: six recognized commands raised the hand, flew, stopped, jumped, hid and restored the Windows robot")
            if cry_test:print("PASS: recognized Cry shed tears and Jump triggered a fresh jump in the shipped 3D scene")
            r.get_tree().quit()
            return
    push_error("Voice integration timed out at stage "+str(stage))
    r.get_tree().quit(1)
