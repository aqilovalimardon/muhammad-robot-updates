"""RobotApp method replacements; Tk work remains on its GUI thread."""
import queue
import time


class HostChanges:
    def _enable_existing_mic(self):
        ready=offline_installed(local_root())
        # This repair restores an already-installed listener disabled by old errors.
        # Explicit Off from this version is recorded separately and always respected.
        if ready and not self.store.settings.get('voice_recovery_v2221'):
            if not self.store.settings.get('microphone_user_disabled'):
                self.store.setting('microphone_enabled',True)
            self.store.setting('voice_recovery_v2221',True)
        self._mic_requested=bool(self.store.settings.get('microphone_enabled'))
        if self._mic_requested:self.start_microphone()
        elif not self.store.settings.get('voice_intro_seen'):
            self.store.setting('voice_intro_seen',True)
            self.root.after(1000,self._offer_voice_setup)

    def toggle_microphone(self):
        if self.mic_installing:return
        if self._mic_requested or self.mic_active:
            self._mic_requested=False
            self._mic_retry_at=0.0
            self._mic_generation+=1
            if self.listener:self.listener.stop()
            self.mic_active=False
            self.mic_state='OFF'
            self.store.setting('microphone_enabled',False)
            self.store.setting('microphone_user_disabled',True)
            self.main.itemconfigure(self.mic_label,text='MIC OFF · right-click to enable')
        elif offline_installed(local_root()):
            self.restart_microphone()
        else:self._offer_offline_install()

    def restart_microphone(self):
        self._mic_requested=True
        self._mic_retry_at=0.0
        self._mic_retry_count=0
        self._mic_generation+=1
        self.store.setting('microphone_enabled',True)
        self.store.setting('microphone_user_disabled',False)
        self.mic_state='RESTARTING'
        if self.listener:self.listener.stop()
        self.mic_active=False
        self.root.after(250,lambda:self._restart_mic_when_released(0))
        self._refresh_mic_status()

    def _restart_mic_when_released(self,tries):
        if not self._mic_requested or not self.root.winfo_exists():return
        if self.listener and self.listener.thread and self.listener.thread.is_alive():
            if tries<40:self.root.after(250,lambda:self._restart_mic_when_released(tries+1))
            else:self._mic_failed('Waiting for the old microphone stream to release')
            return
        self.start_microphone()
        self._refresh_mic_status()

    def start_microphone(self):
        if self.listener and self.listener.thread and self.listener.thread.is_alive():return
        self._mic_requested=True
        if not self.store.settings.get('microphone_enabled'):
            self.store.setting('microphone_enabled',True)
        if self.store.settings.get('microphone_user_disabled'):
            self.store.setting('microphone_user_disabled',False)
        self._mic_retry_at=0.0
        self._mic_generation+=1
        generation=self._mic_generation
        events=self.mic_events
        class SessionQueue:
            def put(self,item):events.put(('mic_session',(generation,item)))
        try:
            self.listener=OfflineListener(local_root(),SessionQueue(),self.voice.speaking)
            self.listener.start()
            self.mic_active=True
            self.mic_state='STARTING · waiting for device'
            self.main.itemconfigure(self.mic_label,text='MIC STARTING · wait for device')
        except Exception as exc:self._mic_failed(str(exc))

    def _mic_failed(self,message):
        self.mic_active=False
        self.mic_state='RECONNECTING: '+str(message)[:130]
        self.main.itemconfigure(self.mic_label,text='MIC RECONNECTING')
        # A transient fault must never rewrite the user's ON setting to OFF.
        if self._mic_requested:
            delay=min(30.0,2.0**min(self._mic_retry_count+1,5))
            self._mic_retry_count+=1
            self._mic_retry_at=time.monotonic()+delay

    def _maybe_retry_microphone(self):
        if not self._mic_requested or not self._mic_retry_at or self.mic_installing:return
        if time.monotonic()<self._mic_retry_at:return
        if self.listener and self.listener.thread and self.listener.thread.is_alive():return
        self.start_microphone()

    def _poll_mic_events(self):
        try:
            for _ in range(100):
                event,value=self.mic_events.get_nowait()
                if event=='mic_session':
                    generation,(event,value)=value
                    if generation!=self._mic_generation:continue
                if event=='command':
                    if not self.mic_active or not self._mic_requested:continue
                    self.mic_last_command=value
                    if value=='open':self.restore()
                    elif value=='close':self.minimize()
                    elif value=='hello':self.say('Hello, Muhammad! Let us code together!')
                elif event=='mic_heard':self.mic_last_heard=str(value)[:100] or '(silence)'
                elif event=='mic_device':self.mic_device=str(value)[:150]
                elif event=='mic_error':self._mic_failed(value)
                elif event=='mic_ended':
                    if self.mic_active and self._mic_requested:self._mic_failed(value)
                elif event=='mic_status':
                    if self.mic_active:
                        self.mic_state=str(value)
                        if str(value).startswith('Listening'):
                            self._mic_retry_count=0
                            self._mic_retry_at=0.0
                        self.main.itemconfigure(self.mic_label,text='MIC ON · Listening')
                elif event=='setup_progress':
                    if hasattr(self,'voice_dialog') and self.voice_dialog[0].winfo_exists():self.voice_dialog[1].set(value)
                elif event in ('setup_done','setup_failed'):
                    self.mic_installing=False
                    if hasattr(self,'voice_dialog') and self.voice_dialog[0].winfo_exists():self.voice_dialog[0].destroy()
                    if event=='setup_done':
                        self.start_microphone()
                        messagebox.showinfo('Voice commands','Ready! Say: Hello robot, Close robot, Open robot.',parent=self.root)
                    else:messagebox.showerror('Voice setup',value,parent=self.root)
        except queue.Empty:pass
        finally:
            # Even a dismissed window or failing command cannot kill the event pump.
            try:
                self._maybe_retry_microphone()
                self._refresh_mic_status()
            finally:
                if self.root.winfo_exists():self.root.after(50,self._poll_mic_events)

    def _signal_real3d(self,command):
        signal=getattr(self,'_three_d_signal',None)
        if signal is None or command not in ('hide','show','sound','emotion','happy'):return
        pending=signal.with_suffix('.tmp')
        try:
            # A greeting animation must not overwrite an unread Open/Close command.
            if command=='happy' and signal.is_file() and signal.read_text(encoding='utf-8').strip() in ('hide','show'):
                return
            pending.write_text(command,encoding='utf-8')
            pending.replace(signal)
        except OSError:
            try:pending.unlink(missing_ok=True)
            except OSError:pass
