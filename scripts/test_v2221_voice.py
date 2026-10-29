#!/usr/bin/env python3
"""Exercise the shipped voice path, recovery, mute state and exact updater package."""
import ast
import asyncio
import importlib.util
import math
from pathlib import Path
import queue
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
from unittest.mock import patch
import zipfile
from test_v2219_plush import main as package_checks, selected_class


def load_commands(archive):
    scope={'__name__':'tested_voice_commands'}
    with zipfile.ZipFile(archive) as z:
        exec(compile(z.read('app/voice_commands.py'),'voice_commands.py','exec'),scope)
    return SimpleNamespace(**scope)


def make_host(source, folder, listener_type=None):
    methods={'_enable_existing_mic','toggle_microphone','restart_microphone',
        '_restart_mic_when_released','start_microphone','_mic_failed','_maybe_retry_microphone',
        '_poll_mic_events','_signal_real3d','minimize','restore','say'}
    if listener_type is None:
        class Listener:
            def __init__(self,root,events,speaking):
                self.events=events
                self.alive=False
                self.thread=SimpleNamespace(is_alive=lambda:self.alive)
            def start(self):self.alive=True
            def stop(self):self.alive=False
        listener_type=Listener
    scope={'queue':queue,'time':time,'OfflineListener':listener_type,
        'local_root':lambda:folder,'offline_installed':lambda root:True,
        'messagebox':SimpleNamespace(showinfo=lambda *a,**k:None,showerror=lambda *a,**k:None),
        'tk':SimpleNamespace(TclError=Exception)}
    Host=selected_class(source,'RobotApp',methods,scope)
    h=Host()
    settings={'microphone_enabled':False,'voice_intro_seen':True}
    h.store=SimpleNamespace(settings=settings,setting=lambda key,value:settings.__setitem__(key,value))
    h.callbacks=[]
    h.root=SimpleNamespace(winfo_exists=lambda:True,after=lambda ms,cb:h.callbacks.append((ms,cb)))
    h.main=SimpleNamespace(itemconfigure=lambda *a,**k:None)
    h.mic_label=0
    h.listener=None
    h.mic_events=queue.Queue()
    h._mic_requested=False
    h._mic_generation=0
    h._mic_retry_at=0.0
    h._mic_retry_count=0
    h.mic_active=False
    h.mic_installing=False
    h._refresh_mic_status=lambda:None
    h._three_d_active=True
    h._three_d_signal=folder/'voice.cmd'
    h.minimized=True
    h.voice=SimpleNamespace(speaking=threading.Event(),speak=lambda text:None)
    return h


def test_recovery(source,folder):
    h=make_host(source,folder)
    h._enable_existing_mic()
    assert h.mic_active and h.store.settings['microphone_enabled'], 'Repair must restore an installed mic disabled by old faults'
    old=h.listener
    old.events.put(('mic_error','USB microphone disconnected'))
    old.alive=False
    h._poll_mic_events()
    assert not h.mic_active and h._mic_retry_at>0
    assert h.store.settings['microphone_enabled'], 'Transient error must preserve ON preference'
    h._mic_retry_at=time.monotonic()-1
    h._maybe_retry_microphone()
    assert h.mic_active and h.listener is not old
    old.events.put(('mic_error','stale error'))
    old.events.put(('mic_ended','stale shutdown'))
    h._poll_mic_events()
    assert h.mic_active, 'Old listener events cannot disable the new listener'
    h.toggle_microphone()
    assert not h._mic_requested and h.store.settings['microphone_user_disabled']
    h._mic_retry_at=time.monotonic()-1
    h._maybe_retry_microphone()
    h._enable_existing_mic()
    assert not h.mic_active, 'Explicit Off must survive retries and startup'
    h.restart_microphone()
    h._restart_mic_when_released(0)
    assert h.mic_active
    spoken=[]
    h.voice.speak=spoken.append
    for command,expected in [('hello','happy'),('close','hide'),('open','show')]:
        h._three_d_signal.unlink(missing_ok=True)
        h.listener.events.put(('command',command))
        h._poll_mic_events()
        assert h._three_d_signal.read_text()==expected
    assert len(spoken)==1 and 'Hello, Muhammad!' in spoken[0]
    h._signal_real3d('hide')
    h.say('Hello, Muhammad!')
    assert h._three_d_signal.read_text()=='hide', 'Greeting cannot swallow Close'
    h._signal_real3d('show')
    h.say('Hello, Muhammad!')
    assert h._three_d_signal.read_text()=='show', 'Greeting cannot swallow Open'
    assert h.callbacks[-1][0]==50, 'Mic polling continues with the Classic window hidden'


def test_recognition_tools(commands):
    for text,expected in [('Hello robot!','hello'),('helo robot','hello'),('hello the robot','hello'),
        ('close the robot','close'),('OPEN ROBOT','open'),('hide the robot','close')]:
        assert commands.normalize_command(text)==expected
    for text in ['robot','close','open the browser','do not close robot','robotics are fun']:
        assert commands.normalize_command(text) is None
    gate=commands.CommandGate()
    assert gate.accept('close robot',False,1.0) is None
    assert gate.accept('close robot',False,1.2)=='close'
    assert gate.accept('close robot',True,1.4) is None, 'No duplicate final command'
    assert gate.accept('close robot',True,2.5)=='close', 'Next utterance still works'
    assert gate.accept('hey robot',False,3.0) is None, 'Do not greet on a command prefix'
    assert gate.accept('hey robot open',True,3.5)=='open'
    from array import array
    for rate in (16000,44100,48000):
        data=array('h',(round(math.sin(i*2*math.pi*440/rate)*10000) for i in range(rate))).tobytes()
        resampler=commands.PCMResampler(rate)
        converted=b''.join(resampler.convert(data[i:i+2048]) for i in range(0,len(data),2048))
        samples=array('h');samples.frombytes(converted)
        assert abs(len(samples)-16000)<=1
        crossings=sum(a<=0<b for a,b in zip(samples,samples[1:]))
        assert abs(crossings-440)<=1, (rate,crossings)


def test_speech(source,folder):
    tree=ast.parse(source)
    node=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Voice')
    scope={'queue':queue,'threading':threading,'time':time,'sys':SimpleNamespace(platform='win32')}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),'Voice','exec'),scope)
    Voice=scope['Voice']
    v=Voice.__new__(Voice)
    v.q=queue.Queue();v.speaking=threading.Event();v.engine='Neural (online)'
    v.cache_dir=folder;v._neural_retry_at=0;v.last_error='';v.NEURAL_TIMEOUT=0.03
    v.speak('Hello, Muhammad!')
    assert not v.speaking.is_set(), 'Queueing/download must not silence recognition'
    received=[]
    def speak(text):
        assert v.speaking.is_set()
        received.append(text)
    class HungOnline:
        def __init__(self,*args):pass
        async def save(self,path):await asyncio.sleep(5)
    with patch.dict(sys.modules,{'edge_tts':SimpleNamespace(Communicate=HungOnline)}):
        before=time.monotonic()
        v._speak_message(v.q.get(),SimpleNamespace(speak=speak))
        assert time.monotonic()-before<1.0
    assert received==['Hello, Muhammad!'] and not v.speaking.is_set()
    assert not list(folder.glob('*.pending.mp3'))
    def broken(text):raise OSError('speaker unplugged')
    v.engine='Windows'
    try:v._speak_message('Test',SimpleNamespace(speak=broken))
    except OSError:pass
    else:raise AssertionError('Expected simulated audio device failure')
    assert not v.speaking.is_set(), 'Failed playback releases the microphone'


def test_audio_stream(commands,folder):
    events=queue.Queue()
    speaking=threading.Event()
    listener=commands.OfflineListener(folder,events,speaking)
    accepted=[]
    resets=[]
    class Recognizer:
        def Reset(self):resets.append(True)
        def AcceptWaveform(self,data):
            accepted.append(data)
            listener.stop_flag.set()
            return True
        def Result(self):return '{"text":"open robot"}'
    class Stream:
        active=True
        def __init__(self,**kwargs):self.callback=kwargs['callback']
        def __enter__(self):
            speaking.set()
            self.callback(b'echo',2,None,None)
            speaking.clear()
            self.callback(b'user',2,None,None)
            return self
        def __exit__(self,*args):pass
    devices=[{'max_input_channels':1,'hostapi':0,'name':'Test microphone','default_samplerate':16000}]
    sd=SimpleNamespace(query_devices=lambda:devices,query_hostapis=lambda:[{'name':'MME','default_input_device':0}],
        RawInputStream=Stream,PortAudioError=OSError)
    vosk=SimpleNamespace(SetLogLevel=lambda n:None,Model=lambda path:object(),KaldiRecognizer=lambda *a:Recognizer())
    with patch.dict(sys.modules,{'vosk':vosk,'sounddevice':sd}):listener._run()
    assert accepted==[b'user'] and resets, 'Queued self-speech must not be recognized after playback'
    emitted=list(events.queue)
    assert ('command','open') in emitted and not any(e=='mic_error' for e,v in emitted)
    class StoppedStream(Stream):
        active=False
        def __enter__(self):return self
    sd.RawInputStream=StoppedStream
    events=queue.Queue()
    listener=commands.OfflineListener(folder,events,speaking)
    with patch.dict(sys.modules,{'vosk':vosk,'sounddevice':sd}):listener._run()
    assert any(e=='mic_error' for e,v in list(events.queue)), 'A stopped callback stream must exit for recovery'


def main(baseline,output):
    package_checks(baseline,output,expected_version='2.2.21',expected_changed={
        'app/robot_app.py','app/robot_core.py','app/voice_commands.py',
        'app/windows_speech.py','app/visual3d/MuhammadRobot3D.pck'})
    with zipfile.ZipFile(output) as z:source=z.read('app/robot_app.py').decode('utf-8')
    commands=load_commands(output)
    test_recognition_tools(commands)
    with tempfile.TemporaryDirectory() as tmp:
        folder=Path(tmp)
        test_recovery(source,folder)
        test_speech(source,folder)
        test_audio_stream(commands,folder)
    print('PASS: Hello/Close/Open dispatch, automatic mic recovery, stale-session isolation, explicit Off, bounded online fallback, echo mute release, 16/44.1/48kHz audio')


if __name__=='__main__':main(*sys.argv[1:])
