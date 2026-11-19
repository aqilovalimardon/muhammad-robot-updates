extends RefCounted
## Optional developer visual/audio review; never runs during normal startup.
func run(r):
    r.set_process(false)
    r.feedback.enabled=false
    var output=OS.get_environment("ROBOT_REVIEW_DIR")
    if output.is_empty():output=OS.get_user_data_dir()+"/review"
    DirAccess.make_dir_recursive_absolute(output)
    for state in ["idle","dizzy","laugh","sad","angry","surprised","happy","excited","wink","love","curious","sleepy"]:
        r._set_emotion(state,10.0)
        for i in range(15):r._process(1.0/30.0)
        await RenderingServer.frame_post_draw
        r.get_viewport().get_texture().get_image().save_png(output+"/"+state+".png")
    r._set_emotion("idle",5.0)
    for i in 25:r._process(1.0/30.0)
    var camera=r.get_viewport().get_camera_3d()
    var pinch=camera.unproject_position(r.head.to_global(Vector3(-0.65,0.12,0.06)))
    var start=Vector2i(pinch)
    r._begin_hold(start,pinch)
    r._move_hold(start+Vector2i(-30,6),Vector2(-30,6))
    for i in 18:r._process(1.0/30.0)
    await RenderingServer.frame_post_draw
    r.get_viewport().get_texture().get_image().save_png(output+"/fur_tug.png")
    r._finish_hold(start+Vector2i(-30,6))
    for i in 72:r._process(1.0/30.0)
    r._begin_hold(Vector2i(100,100))
    r._move_hold(Vector2i(125,100),Vector2(25,0))
    for i in range(20):r._process(1.0/30.0)
    await RenderingServer.frame_post_draw
    r.get_viewport().get_texture().get_image().save_png(output+"/soft_hold.png")
    r._finish_hold(Vector2i(125,100))
    for i in range(6):r._process(1.0/30.0)
    await RenderingServer.frame_post_draw
    r.get_viewport().get_texture().get_image().save_png(output+"/soft_release.png")
    r._hide()
    await r.get_tree().process_frame
    await RenderingServer.frame_post_draw
    r.get_viewport().get_texture().get_image().save_png(output+"/orb.png")
    for cue in r.feedback.sounds:
        r.feedback.sounds[cue].save_to_wav(output+"/"+cue+".wav")
    print("PASS: review frames and offline sound samples saved")
