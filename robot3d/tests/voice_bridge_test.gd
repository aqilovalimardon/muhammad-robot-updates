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
    var stage=0
    var deadline=Time.get_ticks_msec()+30000
    while Time.get_ticks_msec()<deadline:
        await r.get_tree().process_frame
        var passed=(stage==0 and r.emotion=="excited") or (stage==1 and r.hidden) or (stage==2 and not r.hidden)
        if not passed:continue
        file=FileAccess.open(output,FileAccess.READ_WRITE)
        file.seek_end()
        file.store_string(["hello","close","open"][stage]+"\n")
        file.close()
        stage+=1
        if stage==3:
            print("PASS: recorded Hello/Close/Open reached the actual exported 3D scene")
            r.get_tree().quit()
            return
    push_error("Voice integration timed out at stage "+str(stage))
    r.get_tree().quit(1)
