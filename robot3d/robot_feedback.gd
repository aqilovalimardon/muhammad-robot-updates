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
    # Three rounded "hee-hee" syllables, separated by breath-sized silent gaps.
    sounds["laugh"] = _make_sound([[640.0, 850.0, 0.095, 0.34], [1.0, 1.0, 0.045, 0.0],
        [790.0, 1030.0, 0.10, 0.32], [1.0, 1.0, 0.05, 0.0], [920.0, 720.0, 0.13, 0.28]])
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

func play_cue(cue: String) -> bool:
    if not enabled or not sounds.has(cue):return false
    var now = Time.get_ticks_msec()
    var command = cue == "close" or cue == "open"
    if cue=="grumpy" and now<next_grumpy_ms:return false
    if not command and (now < command_until_ms or (now < next_touch_ms and cue!="grumpy")):
        return false
    if cue=="grumpy":next_grumpy_ms=now+1000
    player.stop()
    player.stream = sounds[cue]
    player.play()
    if command:
        command_until_ms = now + int(player.stream.get_length() * 1000.0)
    else:
        # A laugh must finish before another incidental touch cue can interrupt it.
        next_touch_ms = now + (int(player.stream.get_length()*1000.0)+100 if cue=="laugh" else 130)
    cue_played.emit(cue)
    return true

func toggle_enabled() -> bool:
    enabled = not enabled
    if not enabled:player.stop()
    var config = ConfigFile.new()
    config.set_value("sounds", "enabled", enabled)
    config.save(PREFERENCES)
    return enabled
