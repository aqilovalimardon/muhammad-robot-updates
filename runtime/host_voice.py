"""Voice class copied into the installed host by the versioned build script."""
import queue
import sys
import threading
import time


class Voice:
    NEURAL_TIMEOUT = 5.0

    def __init__(self):
        self.q=queue.Queue()
        self.engine='Windows'
        self.speaking=threading.Event()
        self.last_error=''
        self._neural_retry_at=0.0
        self.cache_dir=local_root()/'Data'/'VoiceCache'
        self.cache_dir.mkdir(parents=True,exist_ok=True)
        try:
            import edge_tts
            self.engine='Neural (Edge TTS, online)'
        except Exception:pass
        threading.Thread(target=self._loop,daemon=True).start()

    def speak(self,msg):
        # Queuing/downloading is not audible speech: keep the microphone listening.
        self.q.put(str(msg)[:300])

    def _loop(self):
        native=None
        while True:
            msg=self.q.get()
            try:native=self._speak_message(msg,native)
            except Exception as exc:self.last_error=str(exc)[:160]
            finally:
                self.speaking.clear()
                self.q.task_done()

    def _speak_message(self,msg,native):
        if self.engine.startswith('Neural') and sys.platform=='win32' and time.monotonic()>=self._neural_retry_at:
            try:
                self._edge(msg)
                self.last_error=''
                return native
            except Exception as exc:
                self.last_error='Online voice unavailable; using Windows: '+str(exc)[:100]
                self._neural_retry_at=time.monotonic()+60.0
        if native is None and sys.platform=='win32':
            from windows_speech import NativeWindowsSpeech
            native=NativeWindowsSpeech()
        if native is not None:
            self.speaking.set()
            try:native.speak(msg)
            finally:self.speaking.clear()
        return native

    def _download_edge(self,msg,file):
        import edge_tts, asyncio
        temporary=file.with_suffix('.pending.mp3')
        async def synth():
            voice=edge_tts.Communicate(msg,'en-US-JennyNeural')
            await asyncio.wait_for(voice.save(str(temporary)),timeout=self.NEURAL_TIMEOUT)
        try:
            asyncio.run(synth())
            if not temporary.is_file() or temporary.stat().st_size<1000:
                raise OSError('No usable online audio received')
            temporary.replace(file)
        finally:temporary.unlink(missing_ok=True)

    def _edge(self,msg):
        import ctypes, hashlib
        cache_id=hashlib.sha256(('en-US-JennyNeural|'+msg).encode('utf-8')).hexdigest()[:28]
        file=self.cache_dir/(cache_id+'.mp3')
        if not file.is_file() or file.stat().st_size<1000:self._download_edge(msg,file)
        api=ctypes.windll.winmm.mciSendStringW
        api.argtypes=[ctypes.c_wchar_p,ctypes.c_wchar_p,ctypes.c_uint,ctypes.c_void_p]
        api.restype=ctypes.c_uint
        def send(command):
            output=ctypes.create_unicode_buffer(256)
            if api(command,output,255,None):raise OSError('Audio device could not play neural voice')
            return output.value
        import os
        alias='muhammad_voice_'+str(os.getpid())
        try:
            send(f'open "{file}" type mpegvideo alias {alias}')
            self.speaking.set()
            send(f'play {alias}')
            deadline=time.monotonic()+min(25.0,max(5.0,len(msg)*0.10))
            while send(f'status {alias} mode')=='playing':
                if time.monotonic()>deadline:raise TimeoutError('Voice playback timed out')
                time.sleep(0.05)
        finally:
            try:send(f'close {alias}')
            except Exception:pass
            self.speaking.clear()
