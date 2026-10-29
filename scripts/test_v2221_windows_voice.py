#!/usr/bin/env python3
"""Recognize actual Windows-generated voice audio and drive the shipped 3D EXE."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from urllib.request import urlretrieve
import wave
import zipfile
from test_v2221_voice import load_commands, make_host


def wait_for(path,word,process):
    deadline=time.monotonic()+12
    while time.monotonic()<deadline:
        if path.is_file() and word in path.read_text().splitlines():return
        if process.poll() is not None:break
        time.sleep(0.04)
    raise AssertionError('Godot did not acknowledge '+word)


def main(archive, fixtures):
    archive,fixtures=Path(archive).resolve(),Path(fixtures).resolve()
    commands=load_commands(archive)
    import vosk
    vosk.SetLogLevel(-1)
    with tempfile.TemporaryDirectory() as td:
        folder=Path(td)
        model_zip=folder/'model.zip'
        urlretrieve(commands.MODEL_URL,model_zip)
        assert hashlib.sha256(model_zip.read_bytes()).hexdigest()==commands.MODEL_SHA256
        with zipfile.ZipFile(model_zip) as z:
            for name in z.namelist():
                assert name.startswith(commands.MODEL_FOLDER+'/') and '..' not in Path(name).parts
            z.extractall(folder)
        model=vosk.Model(str(folder/commands.MODEL_FOLDER))
        with zipfile.ZipFile(archive) as z:
            z.extractall(folder/'installed')
            source=z.read('app/robot_app.py').decode('utf-8')
            native_source=z.read('app/windows_speech.py')
        # Validate the real SAPI COM signatures and bounded asynchronous wait on Windows.
        scope={}
        exec(compile(native_source,'windows_speech.py','exec'),scope)
        native=scope['NativeWindowsSpeech']()
        try:native.speak('')
        finally:native.close()
        host=make_host(source,folder)
        host._enable_existing_mic()
        spoken=[]
        host.voice.speak=spoken.append
        ack=folder/'ack.txt'
        exe=folder/'installed/app/visual3d/MuhammadRobot3D.exe'
        log=Path('windows-voice-integration.log').resolve()
        with log.open('w',encoding='utf-8') as output:
            process=subprocess.Popen([str(exe),'--headless','--','--robot-signal',str(host._three_d_signal),
                '--voice-integration-test','--voice-ack',str(ack)],cwd=exe.parent,stdout=output,stderr=subprocess.STDOUT)
            try:
                wait_for(ack,'ready',process)
                for command in ('hello','close','open'):
                    with wave.open(str(fixtures/(command+'.wav')),'rb') as sound:
                        assert sound.getsampwidth()==2 and sound.getnchannels()==1
                        rate=sound.getframerate()
                        pcm=sound.readframes(sound.getnframes())+bytes(rate*2)
                    pcm=commands.PCMResampler(rate).convert(pcm)
                    rec=vosk.KaldiRecognizer(model,16000,commands.GRAMMAR)
                    gate=commands.CommandGate()
                    for offset in range(0,len(pcm),4000):
                        commands.recognize_audio(rec,gate,pcm[offset:offset+4000],host.listener.events,offset/32000.0)
                        host._poll_mic_events()
                    final=json.loads(rec.FinalResult()).get('text','')
                    pending=gate.accept(final,True,len(pcm)/32000.0)
                    if pending:host.listener.events.put(('command',pending))
                    host._poll_mic_events()
                    assert host.mic_last_command==command,(command,host.mic_last_heard)
                    wait_for(ack,command,process)
                assert process.wait(timeout=10)==0
                assert spoken==['Hello, Muhammad! Let us code together!']
            finally:
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=5)
        print(log.read_text(encoding='utf-8'))
        assert 'PASS: recorded Hello/Close/Open' in log.read_text(encoding='utf-8')
    print('PASS: real Windows SAPI + Vosk audio recognition + host event dispatch + exported 3D Hello/Close/Open')


if __name__=='__main__':main(*sys.argv[1:])
