extends Node
## Short, prebuilt, offline earcons. Commands interrupt touch sounds immediately.
signal cue_played(cue: String)

const SAMPLE_RATE = 22050
const PREFERENCES = "user://feedback.cfg"
var enabled = true
var sounds: Dictionary = {}
var player: AudioStreamPlayer
var next_touch_ms = 0
var command_until_ms = 0
var next_grumpy_ms = 0
var next_sad_ms = 0

func _ready():
    player = AudioStreamPlayer.new()
    player.volume_db = -8.0
    player.max_polyphony = 1
    add_child(player)
    # Start/end frequency, duration and amplitude for each tiny note.
    sounds["grab"] = _make_sound([[580.0, 880.0, 0.10, 0.42]])
    sounds["excited"] = _make_sound([[700.0, 1050.0, 0.09, 0.33], [900.0, 1200.0, 0.08, 0.30]])
    sounds["release"] = _make_sound([[880.0, 740.0, 0.07, 0.34], [1050.0, 1050.0, 0.08, 0.28]])
    sounds["close"] = _make_sound([[760.0, 280.0, 0.16, 0.42]])
    sounds["open"] = _make_sound([[460.0, 740.0, 0.075, 0.40], [880.0, 1120.0, 0.10, 0.36]])
    # Soft, voiced syllables with a little breath, generated offline once.
    sounds["laugh"] = _vocal_sound(false)
    sounds["sad"] = _vocal_sound(true)
    sounds["grumpy"] = _make_sound([[330.0, 245.0, 0.16, 0.30], [270.0, 220.0, 0.08, 0.22]])
    var config = ConfigFile.new()
    if config.load(PREFERENCES) == OK:
        enabled = bool(config.get_value("sounds", "enabled", true))

func _make_sound(notes: Array) -> AudioStreamWAV:
    var pcm = PackedByteArray()
    for note in notes:
        var count = int(float(note[2]) * SAMPLE_RATE)
        var offset = pcm.size()
        pcm.resize(offset + count * 2)
        var phase = 0.0
        for i in range(count):
            var u = float(i) / maxf(1.0, count - 1.0)
            var hz = lerpf(float(note[0]), float(note[1]), u)
            phase += TAU * hz / SAMPLE_RATE
            # Smooth zero-valued ends eliminate clicks; no random noise or TTS.
            var envelope = pow(sin(PI * u), 1.4)
            var sample = (sin(phase) + 0.13 * sin(phase * 2.0)) / 1.13
            var value = int(sample * envelope * float(note[3]) * 32767.0)
            pcm.encode_s16(offset + i * 2, value)
    var stream = AudioStreamWAV.new()
    stream.format = AudioStreamWAV.FORMAT_16_BITS
    stream.mix_rate = SAMPLE_RATE
    stream.stereo = false
    stream.data = pcm
    return stream

func _vocal_sound(sigh: bool) -> AudioStreamWAV:
    var length := 0.43 if sigh else 0.47
    var pcm := PackedByteArray()
    var frames := int(length*SAMPLE_RATE)
    pcm.resize(frames*2)
    var phase := 0.0
    var breath := 0.0
    var rng := RandomNumberGenerator.new()
    rng.seed = 2273
    for i in frames:
        var seconds := float(i)/SAMPLE_RATE
        var u := float(i)/float(frames-1)
        var frequency := lerpf(355.0,218.0,smoothstep(0.0,1.0,u))+4.0*sin(TAU*5.5*seconds)
        var envelope := pow(maxf(0.0,sin(PI*u)),1.7)
        var second := smoothstep(0.13,0.23,seconds)
        if not sigh:
            var start := 0.21 if seconds>=0.21 else 0.0
            var beat := clampf((seconds-start)/(length-start if start>0 else 0.17),0.0,1.0)
            envelope = pow(maxf(0.0,sin(PI*beat)),1.35)
            frequency = 345.0+56.0*second+118.0*sin(PI*beat)-44.0*beat
        phase += TAU*frequency/SAMPLE_RATE
        breath = 0.74*breath+0.26*rng.randf_range(-1.0,1.0)
        var voice := 0.66*sin(phase)+0.19*sin(2.0*phase)+0.075*sin(3.0*phase)
        if not sigh:voice+=0.065*sin(5.0*phase)
        var amplitude := 0.25 if sigh else 0.30
        pcm.encode_s16(i*2,roundi(32767.0*amplitude*envelope*(voice+0.085*breath)))
    var stream := AudioStreamWAV.new()
    stream.format = AudioStreamWAV.FORMAT_16_BITS
    stream.mix_rate = SAMPLE_RATE
    stream.data = pcm
    return stream

func play_cue(cue: String) -> bool:
    if not enabled or not sounds.has(cue):return false
    var now = Time.get_ticks_msec()
    var command = cue == "close" or cue == "open"
    if cue=="grumpy" and now<next_grumpy_ms:return false
    if cue=="sad" and now<next_sad_ms:return false
    if not command and (now < command_until_ms or (now < next_touch_ms and cue not in ["grumpy","sad"])):
        return false
    if cue=="grumpy":next_grumpy_ms=now+1000
    if cue=="sad":next_sad_ms=now+1400
    player.stop()
    player.stream = sounds[cue]
    player.play()
    if command:
        command_until_ms = now + int(player.stream.get_length() * 1000.0)
    else:
        # A laugh must finish before another incidental touch cue can interrupt it.
        next_touch_ms = now + (int(player.stream.get_length()*1000.0)+100 if cue in ["laugh","sad"] else 130)
    cue_played.emit(cue)
    return true

func toggle_enabled() -> bool:
    enabled = not enabled
    if not enabled:player.stop()
    var config = ConfigFile.new()
    config.load(PREFERENCES)
    config.set_value("sounds", "enabled", enabled)
    config.save(PREFERENCES)
    return enabled
