extends Node
## Short, prebuilt, offline earcons. Commands interrupt touch sounds immediately.
signal cue_played(cue: String)

const SAMPLE_RATE = 22050
const PREFERENCES = "user://feedback.cfg"
const SOB_PERIOD := 0.86
const SOB_LENGTH := 0.62
const CRY_AUDIO_SECONDS := 2.0*SOB_PERIOD + SOB_LENGTH
const DANCE_BEAT := 0.46
const DANCE_SECONDS := 12.0*DANCE_BEAT
# Original three-bar whistle. Each entry gives its onset and length in beats, then its MIDI pitch.
const WHISTLE_NOTES := [
    Vector3(0.13,0.43,79), Vector3(0.75,0.19,81), Vector3(1.0,0.72,83),
    Vector3(2.0,0.35,86), Vector3(2.5,0.36,83), Vector3(3.0,0.61,81),
    Vector3(4.0,0.49,79), Vector3(4.75,0.20,83), Vector3(5.0,0.73,86),
    Vector3(6.0,0.49,88), Vector3(6.75,0.18,86), Vector3(7.0,0.59,83),
    Vector3(8.0,0.70,81), Vector3(9.0,0.32,83), Vector3(9.5,0.34,81),
    Vector3(10.0,1.43,79),
]
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
    sounds["cry"] = _cry_sound()
    sounds["dance"] = _whistle_sound()
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
    return _mono_wav(pcm)

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
    return _mono_wav(pcm)

# Three softer breaths, with a pause for air. The shoulders follow the same pulse.
static func sob_strength(seconds: float) -> float:
    if seconds < 0.0 or seconds >= CRY_AUDIO_SECONDS:
        return 0.0
    var u := minf(fposmod(seconds, SOB_PERIOD)/SOB_LENGTH, 1.0)
    var strength := 1.0 - 0.16*floorf(seconds/SOB_PERIOD)
    return strength * pow(maxf(0.0, sin(PI*u)), 1.45)

func _cry_sound() -> AudioStreamWAV:
    var pcm := PackedByteArray()
    var frames := ceili(CRY_AUDIO_SECONDS*SAMPLE_RATE)
    pcm.resize(frames*2)
    var phase := 0.0
    var breath := 0.0
    var rng := RandomNumberGenerator.new()
    rng.seed = 2831
    for i in frames:
        var sec := float(i)/SAMPLE_RATE
        var u := minf(fposmod(sec, SOB_PERIOD)/SOB_LENGTH, 1.0)
        var pitch := 338.0 + 70.0*sin(PI*u) - 84.0*u - 8.0*floorf(sec/SOB_PERIOD)
        phase += TAU*(pitch + 9.0*sin(TAU*6.1*sec))/SAMPLE_RATE
        breath = 0.78*breath + 0.22*rng.randf_range(-1.0,1.0)
        var voice := 0.54*sin(phase) + 0.25*sin(2.0*phase) + 0.13*sin(3.0*phase) + 0.08*sin(5.0*phase)
        pcm.encode_s16(i*2, roundi(32767.0*0.30*sob_strength(sec)*(voice + 0.13*breath)))
    return _mono_wav(pcm)

static func _whistle_breath(seconds: float, length: float) -> float:
    return smoothstep(0.0,0.025,seconds)*smoothstep(0.0,minf(0.065,length*0.35),length-seconds)

static func whistle_strength(seconds: float) -> float:
    for note: Vector3 in WHISTLE_NOTES:
        var local := seconds-note.x*DANCE_BEAT
        if local<0.0:return 0.0
        if local<note.y*DANCE_BEAT:return _whistle_breath(local,note.y*DANCE_BEAT)
    return 0.0

func _whistle_sound() -> AudioStreamWAV:
    var pcm := PackedByteArray()
    pcm.resize(roundi(DANCE_SECONDS*SAMPLE_RATE)*2)
    var rng := RandomNumberGenerator.new()
    rng.seed = 2230
    for note: Vector3 in WHISTLE_NOTES:
        var onset := roundi(note.x*DANCE_BEAT*SAMPLE_RATE)
        var length := note.y*DANCE_BEAT
        var frequency := 440.0*pow(2.0,(note.z-69.0)/12.0)
        var phase := 0.0
        var air := 0.0
        for frame in roundi(length*SAMPLE_RATE):
            var sec := float(frame)/SAMPLE_RATE
            var glide := 1.0-0.050*exp(-sec/0.026)
            var vibrato := 0.006*smoothstep(0.07,0.18,sec)*sin(TAU*5.4*sec)
            phase += TAU*frequency*(glide+vibrato)/SAMPLE_RATE
            air = 0.63*air + 0.37*rng.randf_range(-1.0,1.0)
            var tone := sin(phase)+0.055*sin(2.0*phase)+air*(0.025+0.12*exp(-sec/0.032))
            pcm.encode_s16((onset+frame)*2,roundi(8500.0*_whistle_breath(sec,length)*tone))
    return _mono_wav(pcm)

func _mono_wav(pcm: PackedByteArray) -> AudioStreamWAV:
    var stream := AudioStreamWAV.new()
    stream.format = AudioStreamWAV.FORMAT_16_BITS
    stream.mix_rate = SAMPLE_RATE
    stream.data = pcm
    return stream

func play_cue(cue: String) -> bool:
    if not enabled or not sounds.has(cue):return false
    var now = Time.get_ticks_msec()
    var command = cue in ["close","open","cry","dance"]
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

func stop_cue(cue: String):
    if player.stream == sounds[cue]:
        player.stop()
        command_until_ms = 0

func toggle_enabled() -> bool:
    enabled = not enabled
    if not enabled:player.stop()
    var config = ConfigFile.new()
    config.load(PREFERENCES)
    config.set_value("sounds", "enabled", enabled)
    config.save(PREFERENCES)
    return enabled
