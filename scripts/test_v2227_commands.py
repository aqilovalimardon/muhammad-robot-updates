"""Replay quiet, closely spaced and competing speech through the installed recognizer."""
from array import array
import json
import queue
import random
import sys
import threading
import time
from types import SimpleNamespace
from unittest.mock import patch
import wave


def _recording(path):
    with wave.open(str(path), 'rb') as sound:
        assert (sound.getframerate(), sound.getnchannels(), sound.getsampwidth()) == (16000, 1, 2)
        samples = array('h')
        samples.frombytes(sound.readframes(sound.getnframes()))
    threshold = max(map(abs, samples))*0.015
    start = next(i for i, sample in enumerate(samples) if abs(sample)>threshold)
    end = next(i for i, sample in enumerate(reversed(samples)) if abs(sample)>threshold)
    return samples[max(0, start-640):min(len(samples), len(samples)-end+800)]


def _decode(commands, model, samples, rate):
    import vosk
    recognizer = vosk.KaldiRecognizer(model, 16000, commands.GRAMMAR)
    resampler = commands.PCMResampler(rate)
    leveler = commands.SpeechLeveler()
    gate = commands.CommandGate()
    events = queue.Queue()
    stream = array('h', [0])*1920 + samples + array('h', [0])*28000
    if rate != 16000:
        stream = array('h', (stream[i*16000//rate] for i in range(len(stream)*rate//16000)))
    cursor = chunks = 0
    heard = []
    actions = []
    while cursor < len(stream):
        size = (401, 873, 613)[chunks % 3]
        data = resampler.convert(stream[cursor:cursor+size].tobytes())
        cursor += size
        chunks += 1
        if data:
            commands.recognize_audio(recognizer, gate, leveler.process(data), events, cursor/rate)
        while not events.empty():
            kind, value = events.get_nowait()
            if kind == 'command':
                actions.append((value, cursor/rate))
            elif kind == 'mic_heard':
                heard.append(value)
    final = json.loads(recognizer.FinalResult()).get('text', '')
    actions.extend((action, cursor/rate) for action in gate.accept_all(final, True, cursor/rate))
    return actions, heard


def _check_microphone(commands, model, fixtures, quiet_fly):
    """Supply PCM at the hardware callback while exercising the real listener and Vosk."""
    import vosk
    events = queue.Queue()
    speaking = threading.Event()
    listener = commands.OfflineListener(fixtures, events, speaking)
    device = dict(name='Headset input', max_input_channels=1, hostapi=0, default_samplerate=8000)
    class Input:
        active = True

        def __init__(self, callback, samplerate, **settings):
            assert samplerate == 8000
            self.callback = callback

        def __enter__(self):
            self.thread = threading.Thread(target=self.feed, daemon=True)
            self.thread.start()
            return self

        def feed(self):
            for own_voice, audio in [(True, _recording(fixtures/'jump.wav')), (False, quiet_fly)]:
                if own_voice:
                    speaking.set()
                else:
                    speaking.clear()
                samples = array('h', [0])*1200 + audio + array('h', [0])*22000
                narrowband = samples[::2]
                for start in range(0, len(narrowband), 320):
                    block = narrowband[start:start+320]
                    self.callback(block, len(block), None, None)
                    time.sleep(len(block)/8000)
            listener.stop()

        def __exit__(self, *args):
            self.thread.join(6)

    sound = SimpleNamespace(query_devices=lambda: [device],
                            query_hostapis=lambda: [dict(name='MME', default_input_device=0)],
                            RawInputStream=Input, PortAudioError=OSError)
    with patch.dict(sys.modules, {'sounddevice': sound}), patch.object(vosk, 'Model', return_value=model):
        listener._run()
    result = list(events.queue)
    assert not any(kind=='mic_error' for kind, value in result), result
    assert [value for kind, value in result if kind=='command'] == ['fly'], result
    assert any(kind=='mic_level' and -75<value<-18 for kind, value in result), result
    assert any(kind=='mic_device' and '8000 Hz' in value for kind, value in result), result
    print('PASS: quiet headset input passed the real capture callback, 8 kHz resampling and offline decoder; speaker echo was ignored')


def check_recordings(commands, model, fixtures, cry_test=False):
    names = ('fly', 'jump', 'stop', 'open', 'close', 'hello', 'flay', 'robot_fly', 'please_fly',
             'verb', 'wake', 'rope', 'music', 'negative', 'butterfly')
    clips = {name: _recording(fixtures/(name+'.wav')) for name in names}
    rng = random.Random(277)
    quiet = lambda samples: array('h', (round(x*0.026+rng.gauss(0, 3)) for x in samples))
    cases = [(word, clips[word], 16000, [word]) for word in names[:6]]
    cases += [('quiet '+word, quiet(clips[word]), 48000, [word]) for word in names[:6]]
    cases += [(name, clips[name], 44100, ['fly']) for name in ('flay','robot_fly','please_fly')]
    cases += [(name, clips[name], 16000, []) for name in ('verb','wake','rope','music','negative','butterfly')]
    cases += [
        ('two commands', clips['fly']+array('h', [0])*2240+clips['stop'], 44100, ['fly', 'stop']),
        ('two deliberate jumps', clips['jump']+array('h', [0])*3200+clips['jump'], 16000, ['jump', 'jump']),
        ('pause inside command', clips['verb']+array('h', [0])*14400+clips['wake'], 16000, ['fly']),
        ('background alone', quiet(array('h', [0])*32000), 16000, []),
    ]
    if cry_test:
        rump = _recording(fixtures/'rump.wav')
        cry = _recording(fixtures/'cry.wav')
        cases += [
            ('rump jumps', rump, 16000, ['jump']),
            ('quiet rump', quiet(rump), 48000, ['jump']),
            ('cry', cry, 16000, ['cry']),
            ('quiet cry', quiet(cry), 44100, ['cry']),
            ('cry then fly', cry+array('h', [0])*3200+clips['fly'], 16000, ['cry', 'fly']),
            ('rump then cry', rump+array('h', [0])*3000+cry, 16000, ['jump', 'cry']),
            ('unaddressed cry', _recording(fixtures/'cry_alone.wav'), 16000, []),
            ('negated cry', _recording(fixtures/'not_cry.wav'), 16000, []),
        ]
    for name, samples, rate, expected in cases:
        actions, heard = _decode(commands, model, samples, rate)
        assert [action for action, at in actions] == expected, (name, expected, actions, heard)
        if name == 'fly':
            delay = actions[0][1] - (0.12+len(samples)/16000)
            assert delay < 0.58, ('Fly waited for final silence', delay, heard)
    _check_microphone(commands, model, fixtures, quiet(clips['fly']))
    gate = commands.CommandGate()
    assert gate.accept_all('hey robot fly robot', True, 0.0) == ('fly',)
    assert gate.accept_all('fly', True, 1.0) == ()
    assert gate.accept_all('robot', True, 3.2) == (), 'A stale verb cannot arm an unrelated Robot'
    assert gate.accept_all('fly', True, 4.0) == ()
    assert gate.accept_all('[unk]', True, 4.2) == ()
    assert gate.accept_all('robot', True, 4.7) == ()
    leveler = commands.SpeechLeveler()
    soft = array('h', [660, -660])*800
    normalized = array('h')
    normalized.frombytes(leveler.process(soft.tobytes()))
    assert max(normalized) > 3*max(soft) and -35 < leveler.take_level() < -32
    loud = array('h', [32000,-32768])*800
    assert leveler.process(loud.tobytes()) == loud.tobytes()
    print(f'PASS: {len(cases)} recorded-audio cases across 16/44.1/48 kHz, early Fly, quiet gain, short pauses, sequences and rejected background speech')
