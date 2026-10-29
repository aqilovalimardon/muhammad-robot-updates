"""Opt-in, offline English voice commands for Muhammad Robot.

Speech is processed on the user's computer, never sent to a remote AI service.
Vosk and sounddevice are user-installed in a separate local Voice directory.
"""
from __future__ import annotations
import hashlib
import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
import zipfile
from pathlib import Path

MODEL_URL = 'https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip'
MODEL_SHA256 = '30f26242c4eb449f948e42cb302dd7a686cb29a3423a8367f99ff41780942498'
MODEL_FOLDER = 'vosk-model-small-en-us-0.15'


def voice_home(root:Path) -> Path:
    return root/'Voice'


def installed(root:Path) -> bool:
    home=voice_home(root)
    libs=home/'libs'
    if libs.exists() and str(libs) not in sys.path:sys.path.insert(0,str(libs))
    try:
        import vosk, sounddevice
        return (home/'model'/'am'/'final.mdl').is_file()
    except (ImportError,OSError):return False


def setup(root:Path, inform=lambda text:None) -> None:
    """Call only after the user explicitly approves microphone support and downloads."""
    home=voice_home(root)
    home.mkdir(parents=True,exist_ok=True)
    libs=home/'libs'
    inform('Installing offline voice libraries for the current Windows user...')
    # Python 3.11 on Muhammad's school-managed machine; installs only under LOCALAPPDATA.
    command=[sys.executable,'-m','pip','install','--disable-pip-version-check','--prefer-binary',
             '--target',str(libs),'vosk==0.3.45','sounddevice==0.5.3','srt==3.5.3']
    flags=0x08000000 if sys.platform=='win32' else 0
    result=subprocess.run(command,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT,text=True,timeout=360,creationflags=flags)
    if result.returncode:
        raise RuntimeError('Voice package installation failed. Please share this error with ChatGPT.\n'+result.stdout[-1200:])
    model=home/'model'
    if (model/'am'/'final.mdl').is_file():
        inform('Voice model is already installed.')
        return
    archive=home/'model_download.zip'
    inform('Downloading the English voice recognition model (approximately 40 MB)...')
    if archive.is_file():archive.unlink()
    h=hashlib.sha256()
    request=urllib.request.Request(MODEL_URL,headers={'User-Agent':'MuhammadRobot/2.1'})
    try:
        with urllib.request.urlopen(request,timeout=60) as response, archive.open('wb') as file:
            total=0
            while True:
                data=response.read(128*1024)
                if not data:break
                total+=len(data)
                if total>60_000_000:raise ValueError('Model download too large')
                file.write(data);h.update(data)
                if total//5_000_000 != (total-len(data))//5_000_000:
                    inform(f'Downloaded {total//1_000_000} MB...')
        if h.hexdigest()!=MODEL_SHA256:
            raise ValueError('English model verification failed. Please try again.')
        stage=home/'model_stage'
        if stage.exists():shutil.rmtree(stage)
        stage.mkdir()
        inform('Extracting the verified voice model...')
        with zipfile.ZipFile(archive) as z:
            infos=z.infolist()
            if len(infos)>250 or sum(info.file_size for info in infos)>240_000_000:
                raise ValueError('Unexpected model archive')
            for info in infos:
                n=info.filename.replace('\\','/')
                parts=Path(n).parts
                if not parts or parts[0]!=MODEL_FOLDER or '..' in parts or n.startswith('/') or ':' in n:
                    raise ValueError('Unsafe model archive')
                if (info.external_attr>>16)&0o170000 == 0o120000:
                    raise ValueError('Unexpected symlink in voice model')
                if info.is_dir():continue
                destination=stage.joinpath(*parts[1:])
                destination.parent.mkdir(parents=True,exist_ok=True)
                with z.open(info) as src, destination.open('wb') as dst:shutil.copyfileobj(src,dst)
        if not (stage/'am'/'final.mdl').exists():raise ValueError('Downloaded model is incomplete')
        if model.exists():shutil.rmtree(model)
        os.replace(stage,model)
    finally:
        archive.unlink(missing_ok=True)
    inform('Offline speech recognition is ready!')


def normalize_command(text:str) -> str | None:
    """Small grammar: only explicit voice commands are accepted."""
    cleaned=' '.join(''.join(c if c.isalnum() or c.isspace() else ' ' for c in text.lower()).split())
    if cleaned in {'close robot','close the robot','hide robot','hide the robot','robot close','hey robot close','please close robot'}:return 'close'
    if cleaned in {'open robot','open the robot','show robot','show the robot','robot open','hey robot open','please open robot'}:return 'open'
    if cleaned in {'hello robot','helo robot','hallo robot','hey robot','hi robot','hello robo','hello the robot'}:return 'hello'
    return None


GRAMMAR = json.dumps(['open robot','close robot','hello robot','open the robot',
    'close the robot','hide robot','hide the robot','robot close','show robot',
    'show the robot','robot open','hey robot open','hey robot close',
    'please open robot','please close robot','hello the robot','hey robot','hi robot','[unk]'])


class CommandGate:
    """Fast stable Open/Close partials; one event per utterance, no prefix greeting."""
    def __init__(self):
        self.partial=None
        self.since=0.0
        self.sent=None

    def accept(self, text, final, now):
        command=normalize_command(text)
        if final:
            result=command if command != self.sent else None
            self.partial=self.sent=None
            self.since=0.0
            return result
        if command not in ('open','close'):
            self.partial=None
            return None
        if command != self.partial:
            self.partial=command
            self.since=now
        elif now-self.since>=0.18 and self.sent!=command:
            self.sent=command
            return command
        return None


def recognize_audio(rec, gate, data, events, now):
    """Same recognition/dispatch path for the microphone and recorded-audio tests."""
    final=bool(rec.AcceptWaveform(data))
    result=json.loads(rec.Result() if final else rec.PartialResult())
    heard=result.get('text' if final else 'partial','')
    if final and heard:events.put(('mic_heard',heard))
    command=gate.accept(heard,final,now)
    if command:
        if not final:events.put(('mic_heard',heard))
        events.put(('command',command))


class PCMResampler:
    """Streaming mono int16 conversion; works without the removed audioop module."""
    def __init__(self, rate):
        from array import array
        self.samples=array('h')
        self.position=0.0
        self.step=float(rate)/16000.0

    def convert(self, data):
        from array import array
        if self.step==1.0:return data
        self.samples.frombytes(data)
        output=array('h')
        while self.position+1<len(self.samples):
            index=int(self.position)
            fraction=self.position-index
            output.append(round(self.samples[index]*(1.0-fraction)+self.samples[index+1]*fraction))
            self.position+=self.step
        consumed=min(int(self.position),len(self.samples))
        self.samples=self.samples[consumed:]
        self.position-=consumed
        return output.tobytes()


def microphone_candidates(sd):
    """Return usable recording devices, preferring modern Windows WASAPI over MME.

    Devices are enumerated at each microphone start so plugging in a headset
    or changing Windows defaults does not leave stale device indices.
    """
    devices=sd.query_devices()
    apis=sd.query_hostapis()
    options=[]
    for n,dev in enumerate(devices):
        if int(dev.get('max_input_channels',0))<1:continue
        api=apis[dev['hostapi']]
        api_name=api.get('name','')
        name=dev.get('name','')
        if 'WASAPI' in api_name:priority=0
        elif 'DirectSound' in api_name:priority=1
        elif 'MME' in api_name:priority=2
        else:priority=3
        default=api.get('default_input_device',-1)==n
        # Prefer real microphones over software mixers and loopback devices.
        low=name.lower()
        virtual=('stereo mix' in low or 'wave out' in low or 'loopback' in low)
        rate=round(float(dev.get('default_samplerate') or 0))
        if rate<16000 or rate>192000:continue
        options.append((virtual, not default, priority, n, rate, name, api_name))
    options.sort()
    return options


class OfflineListener:
    """Never touches tkinter from the worker thread; emits commands via a queue."""
    def __init__(self,root:Path,command_queue:queue.Queue, speaking:threading.Event|None=None):
        self.root=root
        self.events=command_queue
        self.speaking=speaking
        self.stop_flag=threading.Event()
        self.thread=None
        self.last_error=None

    def start(self):
        if self.thread and self.thread.is_alive():return
        if not installed(self.root):raise RuntimeError('Voice commands are not installed.')
        self.stop_flag.clear()
        self.thread=threading.Thread(target=self._run,daemon=True)
        self.thread.start()

    def stop(self):self.stop_flag.set()

    def _run(self):
        try:
            import vosk, sounddevice as sd
            vosk.SetLogLevel(-1)
            model=vosk.Model(str(voice_home(self.root)/'model'))
            candidates=microphone_candidates(sd)
            if not candidates:
                raise RuntimeError('No usable microphone input device was detected.')
            problems=[]
            for _,_,_,device_index,rate,name,api in candidates:
                if self.stop_flag.is_set():return
                audios=queue.Queue(maxsize=30)
                resampler=PCMResampler(rate)
                rec=vosk.KaldiRecognizer(model,16000,GRAMMAR)
                gate=CommandGate()
                last_audio=time.monotonic()
                def callback(indata,frames,time_data,status):
                    # Mark self-speech at CAPTURE time, so queued audio cannot echo later.
                    packet=(bytes(indata), bool(self.speaking and self.speaking.is_set()), time.monotonic())
                    try:audios.put_nowait(packet)
                    except queue.Full:
                        try:audios.get_nowait()
                        except queue.Empty:pass
                        try:audios.put_nowait(packet)
                        except queue.Full:pass
                try:
                    # blocksize=0 lets PortAudio negotiate; high latency is less
                    # demanding on school-managed Windows laptops.
                    settings=(sd.WasapiSettings(exclusive=False,auto_convert=True)
                              if 'WASAPI' in api else None)
                    with sd.RawInputStream(device=device_index,samplerate=rate,
                                           blocksize=0,dtype='int16',channels=1,
                                           latency='high',extra_settings=settings,
                                           callback=callback) as stream:
                        self.events.put(('mic_device',f'{name} ({api}), {rate} Hz'))
                        self.events.put(('mic_status','Listening (offline)'))
                        while not self.stop_flag.is_set():
                            try:data,own_voice,captured=audios.get(timeout=.25)
                            except queue.Empty:
                                if not stream.active or time.monotonic()-last_audio>4.0:
                                    raise RuntimeError('Microphone stopped delivering audio; reconnecting')
                                continue
                            last_audio=time.monotonic()
                            if own_voice or (self.speaking and self.speaking.is_set()) or last_audio-captured>1.0:
                                rec.Reset()
                                gate=CommandGate()
                                resampler=PCMResampler(rate)
                                continue
                            data=resampler.convert(data)
                            recognize_audio(rec,gate,data,self.events,last_audio)
                    return  # successful stream, or user turned microphone off
                except (sd.PortAudioError,ValueError,RuntimeError,OSError) as e:
                    # Failure can be per-device/per-backend, so try other Windows
                    # APIs before telling the parent the microphone is broken.
                    problems.append(f'{name} ({api}): {str(e)[:150]}')
            # No device opened. Short, actionable error with useful diagnostics.
            summary='\n'.join(problems[:4])
            raise RuntimeError(
                'Could not open any microphone.\n'
                'Close other voice apps and check Windows > Sound > Input.\n'
                'Tried: ' + summary)
        except Exception as e:
            self.last_error=str(e)
            if not self.stop_flag.is_set():self.events.put(('mic_error',str(e)))
        finally:
            self.events.put(('mic_status','Microphone off'))
            if not self.stop_flag.is_set():self.events.put(('mic_ended','The audio stream stopped'))
