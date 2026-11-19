"""Muhammad Robot — 3D desktop companion and Python Studio.
The editor never executes arbitrary Python; it interprets beginner lessons safely.
"""
import os
import sys
import time
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from pathlib import Path
from robot_core import (APP_VERSION, LESSONS, DataStore, ScriptError, parse_actions,
                        check_drive_update, check_github_update, local_root)
from voice_commands import OfflineListener, installed as offline_installed, setup as setup_offline_voice

HERE=Path(__file__).resolve().parent
BG='#0c1428'; PANEL='#15223b'; PRIMARY='#59e0ff'; TXT='#e8f5ff'; MUTED='#9db5ce'
BUTTON='#183960'

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
            # Keep audio cached locally for instant replay; never sync voice cache to Drive.

class Editor:
    def __init__(self,robot):
        self.robot=robot; self.store=robot.store
        self.window=tk.Toplevel(robot.root)
        self.window.title("Muhammad's Robot — Python Studio")
        self.window.configure(bg=BG)
        self.window.geometry('1010x670')
        self.window.minsize(740,480)
        self.window.protocol('WM_DELETE_WINDOW',self.hide)
        self.window.bind('<Control-s>',self.save_shortcut)
        self.window.bind('<Control-Return>',self.run_shortcut)
        self.window.bind('<F5>',self.run_shortcut)
        self.current=self.store.settings.get('last_script','robot_main')
        if self.current not in self.store.list_scripts():self.current='robot_main'
        self.pending=None; self.dirty=False
        self._draw()
        self.refresh_scripts()
        self.load_script(self.current)

    def _btn(self,parent,label,fn,color=BUTTON):
        return tk.Button(parent,text=label,command=fn,bg=color,fg='white',activebackground='#285a87',
                         activeforeground='white',relief='flat',bd=0,padx=10,pady=8,cursor='hand2',
                         font=('Segoe UI',10,'bold'))

    def _draw(self):
        header=tk.Frame(self.window,bg=BG,height=56)
        header.pack(fill='x',padx=16,pady=(12,4))
        tk.Label(header,text='PYTHON STUDIO',bg=BG,fg=PRIMARY,font=('Segoe UI',18,'bold')).pack(side='left')
        tk.Label(header,text='  LEARN  •  CODE  •  CREATE',bg=BG,fg=MUTED,font=('Segoe UI',9)).pack(side='left')
        self.status=tk.StringVar(value='Ready')
        tk.Label(header,textvariable=self.status,bg=BG,fg='#8deabb',font=('Segoe UI',10)).pack(side='right')

        toolbar=tk.Frame(self.window,bg=BG)
        toolbar.pack(fill='x',padx=16,pady=(0,8))
        for label,command,color in [
            ('SAVE  Ctrl+S',self.save,'#087d8c'),('RUN  F5',self.run,'#245ba4'),
            ('+ NEW SCRIPT',self.new_script,BUTTON),('OPEN IN IDLE',self.open_idle,BUTTON),
            ('BACKUPS',self.open_backups,BUTTON)]:
            self._btn(toolbar,label,command,color).pack(side='left',padx=(0,8))
        tk.Label(toolbar,text='Autosave ON',bg=BG,fg=MUTED,font=('Segoe UI',9)).pack(side='right')

        body=tk.PanedWindow(self.window,orient='horizontal',bg=BG,sashwidth=5,relief='flat',bd=0)
        body.pack(expand=True,fill='both',padx=15)
        side=tk.Frame(body,bg=PANEL,width=220)
        side.pack_propagate(False)
        body.add(side,minsize=175)
        work=tk.Frame(body,bg=BG)
        body.add(work,minsize=380)
        tk.Label(side,text='MY PYTHON FILES',bg=PANEL,fg=PRIMARY,font=('Segoe UI',10,'bold')).pack(anchor='w',padx=12,pady=(12,5))
        self.scripts=tk.Listbox(side,bg='#0b1a30',fg=TXT,selectbackground='#2478a4',
                                font=('Consolas',10),relief='flat',height=8,highlightthickness=0,activestyle='none')
        self.scripts.pack(fill='x',padx=10,pady=(0,12))
        self.scripts.bind('<<ListboxSelect>>',self.pick_script)
        tk.Label(side,text='DAILY LESSONS',bg=PANEL,fg=PRIMARY,font=('Segoe UI',10,'bold')).pack(anchor='w',padx=12,pady=(6,6))
        self.lesson_list=tk.Listbox(side,bg='#0b1a30',fg=TXT,selectbackground='#2478a4',
                                font=('Segoe UI',10),relief='flat',height=9,highlightthickness=0,activestyle='none')
        self.lesson_list.pack(fill='x',padx=10)
        for l in LESSONS:self.lesson_list.insert('end',l[0])
        self.lesson_list.bind('<<ListboxSelect>>',self.pick_lesson)
        self.lesson_info=tk.Label(side,text='Choose a lesson, then add its code.',bg=PANEL,fg=MUTED,
                                  font=('Segoe UI',9),justify='left',anchor='nw',wraplength=185)
        self.lesson_info.pack(fill='x',padx=12,pady=12)
        self._btn(side,'ADD LESSON CODE',self.insert_lesson).pack(fill='x',padx=10,pady=(2,10))
        top=tk.Frame(work,bg=BG)
        top.pack(fill='x')
        self.file_title=tk.StringVar()
        tk.Label(top,textvariable=self.file_title,bg=BG,fg=TXT,font=('Consolas',11,'bold')).pack(anchor='w',padx=9,pady=6)
        editor_box=tk.Frame(work,bg='#071021',highlightbackground='#234b68',highlightthickness=1)
        editor_box.pack(fill='both',expand=True,padx=8)
        self.lines=tk.Text(editor_box,width=4,bg='#0b1830',fg='#63829e',font=('Consolas',12),bd=0,
                           padx=6,pady=12,takefocus=0,state='disabled',wrap='none',highlightthickness=0)
        self.lines.pack(side='left',fill='y')
        scrolly=tk.Scrollbar(editor_box)
        scrolly.pack(side='right',fill='y')
        self.code=tk.Text(editor_box,undo=True,maxundo=500,wrap='none',bg='#071021',fg='#d7f8ff',
                          insertbackground='white',selectbackground='#12567a',font=('Consolas',12),
                          padx=10,pady=12,bd=0,highlightthickness=0,yscrollcommand=scrolly.set,
                          tabs=('32',))
        self.code.pack(side='left',expand=True,fill='both')
        scrolly.config(command=self._scroll)
        self.code.tag_config('str',foreground='#90eeb0')
        self.code.tag_config('kw',foreground='#82c5ff')
        self.code.tag_config('comment',foreground='#778aa4')
        self.code.bind('<<Modified>>',self.on_change)
        self.code.bind('<KeyRelease>',lambda e:self.window.after_idle(self._highlight))
        self.code.bind('<Tab>',self.tab_spaces)
        bottom=tk.Frame(work,bg=BG)
        bottom.pack(fill='x',padx=8,pady=8)
        tk.Label(bottom,text='Tip: Ctrl+S = save · F5 = run · # = comment',bg=BG,fg=MUTED,
                 font=('Segoe UI',9)).pack(side='left')
        self.cloudstatus=tk.StringVar(value='')
        tk.Label(bottom,textvariable=self.cloudstatus,bg=BG,fg='#75cbe1',font=('Segoe UI',9)).pack(side='right')

    def _scroll(self,*args):
        self.code.yview(*args);self.lines.yview(*args)
    def save_shortcut(self,e): self.save();return 'break'
    def run_shortcut(self,e): self.run();return 'break'
    def tab_spaces(self,e):self.code.insert('insert','    ');return 'break'
    def refresh_scripts(self):
        self.scripts.delete(0,'end')
        for x in self.store.list_scripts():self.scripts.insert('end',x+'.py')
    def pick_script(self,event):
        sel=self.scripts.curselection()
        if sel:
            name=self.scripts.get(sel[0]).removesuffix('.py')
            if name!=self.current:
                self.save()
                self.load_script(name)
    def pick_lesson(self,event):
        sel=self.lesson_list.curselection()
        if sel:
            self.lesson_info.config(text=LESSONS[sel[0]][2])
    def insert_lesson(self):
        sel=self.lesson_list.curselection()
        if not sel:
            messagebox.showinfo('Lesson','Choose a lesson first.',parent=self.window);return
        snippet=LESSONS[sel[0]][1]
        self.code.insert('end','\n'+snippet+'\n')
        self.code.see('end')
        self.code.focus_set()
    def new_script(self):
        self.save()
        name=simpledialog.askstring('New Python file','Name (English letters):',parent=self.window)
        if not name:return
        try:
            name=self.store.safe_script_name(name)
            if name in self.store.list_scripts():raise ValueError('That script already exists.')
            self.store.save_script(name,'# '+name+' — my robot code\n')
            self.refresh_scripts();self.load_script(name)
        except Exception as e:messagebox.showerror('File name',str(e),parent=self.window)
    def load_script(self,name):
        self.current=name;self.store.setting('last_script',name)
        self.code.delete('1.0','end')
        self.code.insert('1.0',self.store.read_script(name))
        self.code.edit_modified(False)
        self.dirty=False
        self.file_title.set(name+'.py')
        self.status.set('Saved')
        self._highlight()
    def on_change(self,e=None):
        if not self.code.edit_modified():return
        self.code.edit_modified(False)
        self.dirty=True
        self.status.set('Unsaved changes • autosave soon')
        self._line_numbers()
        if self.pending:self.window.after_cancel(self.pending)
        self.pending=self.window.after(1800,self.save)
    def _line_numbers(self):
        count=int(self.code.index('end-1c').split('.')[0])
        self.lines.config(state='normal')
        self.lines.delete('1.0','end')
        self.lines.insert('1.0','\n'.join(map(str,range(1,count+1))))
        self.lines.config(state='disabled')
    def _highlight(self):
        import tokenize, io
        content=self.code.get('1.0','end-1c')
        for t in ('str','kw','comment'):self.code.tag_remove(t,'1.0','end')
        try:
            for tok in tokenize.generate_tokens(io.StringIO(content).readline):
                a='%d.%d'%(tok.start[0],tok.start[1]);b='%d.%d'%(tok.end[0],tok.end[1])
                if tok.type==tokenize.STRING:self.code.tag_add('str',a,b)
                elif tok.type==tokenize.COMMENT:self.code.tag_add('comment',a,b)
                elif tok.string in ('for','in','range','print','if','else','def','return'):
                    self.code.tag_add('kw',a,b)
        except Exception:pass
        self._line_numbers()
    def save(self):
        if self.pending:
            try:self.window.after_cancel(self.pending)
            except Exception:pass
            self.pending=None
        text=self.code.get('1.0','end-1c')
        try:
            synced=self.store.save_script(self.current,text)
            self.dirty=False
            self.status.set('✓ SAVED  '+time.strftime('%H:%M:%S'))
            self.cloudstatus.set('Google Drive ✓' if synced else 'Local ✓  ·  Drive not synced')
            return True
        except Exception as e:
            self.status.set('Save failed!')
            messagebox.showerror('Save error',str(e),parent=self.window)
            return False
    def run(self):
        if not self.save():return
        source=self.code.get('1.0','end-1c')
        try: actions=parse_actions(source)
        except ScriptError as e:
            self.status.set('Python lesson error: '+str(e))
            messagebox.showerror('Python lesson error',str(e),parent=self.window)
            return
        self.status.set('RUN ✓  '+str(len(actions))+' actions')
        self.robot.perform_actions(actions)
    def open_idle(self):
        import subprocess
        self.save()
        try:subprocess.Popen([sys.executable,'-m','idlelib',str(self.store.path(self.current))],close_fds=True)
        except Exception as e:messagebox.showerror('Python IDLE',str(e),parent=self.window)
    def open_backups(self):
        try:
            if sys.platform=='win32':os.startfile(str(self.store.backups))
            else:messagebox.showinfo('Backups',str(self.store.backups),parent=self.window)
        except Exception as e:messagebox.showerror('Backups',str(e),parent=self.window)
    def hide(self):
        self.save()
        self.window.withdraw()
    def show(self):
        self.window.deiconify();self.window.lift();self.code.focus_set()

class RobotApp:
    def __init__(self):
        self.root=tk.Tk()
        self.root.title('Muhammad Robot')
        self.root.withdraw()
        self.store=DataStore()
        self.voice=Voice()
        self.mic_events=queue.Queue()
        self.listener=None
        self.mic_active=False
        self.mic_installing=False
        self.mic_last_heard='No speech recognized yet'
        self.mic_last_command='No command recognized yet'
        self.mic_device='Not connected'
        self.mic_state='OFF'
        self.mic_debug_window=None
        self._mic_requested=False
        self._mic_generation=0
        self._mic_retry_at=0.0
        self._mic_retry_count=0
        self.editor = None
        self._three_d_active = False
        self.preview_3d_process = None
        self._three_d_bridge = None
        self._three_d_signal = None
        self._build_menu()
        self.action_queue=[]
        self.updates=queue.Queue()
        self.root.after(400,self._poll_updates)
        self.root.after(50,self._poll_mic_events)
        self.root.after(2800,self._enable_existing_mic)
        self.root.after(1500,self.start_greeting)
        self.root.after(2400,self.background_update_check)
        self.root.after(100,self._start_3d)
        self.root.protocol('WM_DELETE_WINDOW',self.exit)

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

    def _start_3d(self):
        import secrets
        import subprocess
        if self._three_d_active:
            return
        folder = HERE / 'visual3d'
        try:
            exe = folder / 'MuhammadRobot3D.exe'
            if not exe.is_file() or not (folder / 'MuhammadRobot3D.pck').is_file():
                raise FileNotFoundError('The 3D program or resource pack is missing.')
            data = local_root() / 'Data'
            data.mkdir(parents=True, exist_ok=True)
            session = secrets.token_hex(12)
            bridge = data / ('3d_switch_' + session + '.cmd')
            signal = data / ('3d_voice_' + session + '.cmd')
            child = subprocess.Popen([str(exe), '--', '--robot-bridge', str(bridge),
                                      '--robot-signal', str(signal)], cwd=folder, close_fds=True)
        except OSError as exc:
            self._offer_3d_retry(str(exc))
            return
        self._three_d_bridge = bridge
        self._three_d_signal = signal
        self.preview_3d_process = child
        self._three_d_active = True
        self.root.after(180, self._poll_real3d_mode)
        self.root.after(1000, self._mark_launch_ok)

    def _offer_3d_retry(self, reason):
        self._dismiss_shared_menu()
        if messagebox.askretrycancel('Muhammad Robot', 'Could not run the 3D robot.\n\n' + reason,
                                     parent=self.root):
            self.root.after_idle(self._start_3d)
        else:
            self.exit()

    def _poll_real3d_mode(self):
        if not getattr(self,'_three_d_active',False):return
        process=getattr(self,'preview_3d_process',None)
        bridge=getattr(self,'_three_d_bridge',None)
        command=''
        if bridge is not None and bridge.is_file():
            claimed=bridge.with_suffix('.reading')
            try:
                bridge.replace(claimed)
                command=claimed.read_text(encoding='utf-8').strip()
            except (OSError,UnicodeError):pass
            finally:
                try:claimed.unlink(missing_ok=True)
                except OSError:pass
        if command=='menu':
            self.root.after(0,self._show_shared_menu)
        elif command=='editor':
            self.open_editor()
        elif command=='run':
            self.quick_run()
        elif command == 'exit':
            self.exit()
            return
        exit_code = process.poll()
        if exit_code is None:
            self.root.after(40, self._poll_real3d_mode)
        elif exit_code == 0:
            self.exit()
        else:
            self._stop_real3d()
            self._offer_3d_retry('The 3D window closed unexpectedly (code %d).' % exit_code)

    def _build_menu(self):
        self.menu=tk.Menu(self.root,tearoff=0)
        self.menu.add_command(label='Edit Python code',command=self.open_editor)
        self.menu.add_command(label='Run Python code',command=self.quick_run)
        self.menu.add_command(label='Learn Python',command=self.learn)
        self.menu.add_command(label='Speak: Hello Muhammad',command=lambda:self.say('Hello, Muhammad!'))
        self.menu.add_command(label='Open / show robot',command=self.restore)
        self.menu.add_command(label='Hide / minimize',command=self.minimize)
        self.menu.add_command(label='Show next 3D emotion',command=self._cycle_3d_emotion)
        self.menu.add_command(label='3D effect sounds: On / Off',command=self._toggle_3d_effects)
        self.menu.add_command(label='Enable / Disable offline voice commands',command=self.toggle_microphone)
        self.menu.add_command(label='Voice status / restart microphone',command=self.show_mic_status)
        self.menu.add_command(label='Drive folder settings',command=self.drive_settings)
        self.menu.add_command(label='About robot / version',command=self.show_version)
        self.menu.add_command(label='Check GitHub updates',command=self.check_updates_now)
        self.menu.add_command(label='Natural voice setup (optional)',command=self.natural_voice_setup)
        self.menu.add_separator()
        self.menu.add_command(label='Exit Robot',command=self.exit)
    def popup(self,event):
        self._show_shared_menu(event)
    def say(self,text):
        if getattr(self,'_three_d_active',False):self._signal_real3d('happy')
        self.voice.speak(text)
    def start_greeting(self):self.say('Hello, Muhammad! Let us learn Python!')
    def open_editor(self):
        if self.editor is None or not self.editor.window.winfo_exists():self.editor=Editor(self)
        else:self.editor.show()
    def learn(self):
        self.open_editor()
        self.editor.lesson_list.selection_clear(0,'end')
        self.editor.lesson_list.selection_set(0)
        self.editor.pick_lesson(None)
        self.say('Today, we will learn one Python command!')
    def quick_run(self):
        if self.editor and self.editor.window.winfo_exists():self.editor.run();return
        try:
            name=self.store.settings.get('last_script','robot_main')
            actions=parse_actions(self.store.read_script(name))
            self.perform_actions(actions)
        except Exception as e:messagebox.showerror('Python lesson',str(e))
    def perform_actions(self,actions):
        self.action_queue=list(actions)
        self._next_action()
    def _next_action(self):
        if not self.action_queue:return
        action,val=self.action_queue.pop(0)
        if action=='say':self.say(val);delay=max(1100,min(4000,len(val)*65))
        elif action=='wave':
            delay=1000
        elif action=='fly':
            delay=1100
        elif action=='dance':
            delay=1100
        elif action=='glow':
            c={'cyan':'#87efff','blue':'#80b5ff','purple':'#bc96ff','gold':'#ffe28a','green':'#95f4be'}[val]
            delay=600
        else:
            delay=600
        if self.action_queue:self.root.after(delay,self._next_action)
    def minimize(self):
        self._dismiss_shared_menu()
        self._signal_real3d('hide')

    def restore(self):
        self._dismiss_shared_menu()
        self._signal_real3d('show')

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

    def _offer_voice_setup(self):
        if not self.root.winfo_exists():return
        if messagebox.askyesno('English voice commands',
            'Would you like to enable OFFLINE English voice commands?\n\n'
            'Muhammad can say: Open robot, Close robot, Hello robot.\n'
            'The microphone audio stays on this computer.\n\n'
            'One-time setup downloads about 40 MB for the voice model plus Python libraries.\n'
            'Use only with permission on a school-managed laptop.', parent=self.root):
            self.toggle_microphone()

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
        elif offline_installed(local_root()):
            self.restart_microphone()
        else:self._offer_offline_install()

    def show_mic_status(self):
        """Explain what is actually working without opening a terminal."""
        if self.mic_debug_window and self.mic_debug_window.winfo_exists():
            self.mic_debug_window.deiconify()
            self.mic_debug_window.lift()
            self._refresh_mic_status()
            return
        win=tk.Toplevel(self.root)
        self.mic_debug_window=win
        win.title('Muhammad Robot — Voice status')
        win.geometry('590x360')
        win.configure(bg=BG)
        tk.Label(win,text='VOICE COMMAND STATUS',font=('Segoe UI',16,'bold'),bg=BG,fg=PRIMARY).pack(pady=(18,8))
        self.mic_debug_text=tk.StringVar()
        tk.Label(win,textvariable=self.mic_debug_text,bg=BG,fg=TXT,font=('Consolas',10),
                 justify='left',anchor='nw',wraplength=545).pack(expand=True,fill='both',padx=22,pady=8)
        bar=tk.Frame(win,bg=BG);bar.pack(pady=(0,18))
        tk.Button(bar,text='REFRESH',command=self._refresh_mic_status,
                  bg='#126682',fg='white',relief='flat',padx=12,pady=8).pack(side='left',padx=6)
        tk.Button(bar,text='RESTART MICROPHONE',command=self.restart_microphone,
                  bg='#087c8b',fg='white',relief='flat',padx=12,pady=8).pack(side='left',padx=6)
        tk.Button(bar,text='CLOSE',command=win.destroy,
                  bg='#304262',fg='white',relief='flat',padx=12,pady=8).pack(side='left',padx=6)
        self._refresh_mic_status()

    def _refresh_mic_status(self):
        if not self.mic_debug_window or not self.mic_debug_window.winfo_exists():return
        alive=bool(self.listener and self.listener.thread and self.listener.thread.is_alive())
        self.mic_debug_text.set(
            f'Microphone setting: {"ON" if self.store.settings.get("microphone_enabled") else "OFF"}\n'
            f'Listening process: {"ACTIVE" if alive else "NOT RUNNING"}\n'
            f'Listening status: {self.mic_state}\n'
            f'Input device: {self.mic_device}\n'
            f'Last speech heard: {self.mic_last_heard}\n'
            f'Last command: {self.mic_last_command}\n'
            f'Robot speaking now: {"YES" if self.voice.speaking.is_set() else "NO"}\n\n'
            'Say clearly: HELLO ROBOT, CLOSE ROBOT, OPEN ROBOT.\n'
            'If the last speech is blank, check microphone input / permissions.\n'
            'The voice model runs locally; speech is not sent to a server.')

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

    def _offer_offline_install(self):
        if not messagebox.askyesno('Set up offline voice commands',
            'Install offline microphone recognition now?\n\n'
            'Vosk English model: about 40 MB; dependencies: approx 16 MB.\n'
            'The audio is processed locally and is NOT sent online.\n'
            'Some speech packages are installed from Python source distribution.\n'
            'Libraries are installed only to your own Windows profile.\n'
            'If school restrictions block this, ask the school IT administrator.',parent=self.root):
            return
        dialog=tk.Toplevel(self.root)
        dialog.title('Offline Microphone Setup')
        dialog.geometry('530x160')
        dialog.configure(bg=BG)
        tk.Label(dialog,text='Installing English voice commands',font=('Segoe UI',13,'bold'),fg=PRIMARY,bg=BG).pack(pady=(15,5))
        status=tk.StringVar(value='Preparing...')
        tk.Label(dialog,textvariable=status,wraplength=485,fg='white',bg=BG,font=('Segoe UI',10)).pack(padx=10,pady=10)
        tk.Label(dialog,text='Do not close the robot during installation.',fg=MUTED,bg=BG).pack()
        dialog.protocol('WM_DELETE_WINDOW',lambda:None)
        self.voice_dialog=(dialog,status)
        self.mic_installing=True
        def worker():
            try:
                setup_offline_voice(local_root(),lambda txt:self.mic_events.put(('setup_progress',txt)))
                self.mic_events.put(('setup_done','Installed successfully.'))
            except Exception as e:
                self.mic_events.put(('setup_failed',str(e)))
        threading.Thread(target=worker,daemon=True).start()

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
        except Exception as exc:self._mic_failed(str(exc))

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

    def drive_settings(self):
        path=filedialog.askdirectory(title='Choose MuhammadRobot folder inside Google Drive',parent=self.root)
        if path:
            self.store.set_cloud(path)
            c=self.store.sync_all()
            messagebox.showinfo('Google Drive',f'Saved folder:\n{path}\n\nFiles synchronized: {c}',parent=self.root)
    def _mark_launch_ok(self):
        if not self._three_d_active or self.preview_3d_process.poll() is not None:
            return
        try:(local_root()/'launch_pending.json').unlink(missing_ok=True)
        except Exception:pass
    def show_version(self):
        messagebox.showinfo('Muhammad Robot · Version',
            f'Muhammad Robot v{APP_VERSION}\n\n'
            'Pull a tuft outward to stretch it. Stroke the fur back and forth to make the robot giggle.\n'
            'Hold the middle of the face to move the robot.',
            parent=self.root)

    def check_updates_now(self):
        """Manual check always reports a status, even if Drive is unavailable."""
        self.background_update_check(manual=True)

    def background_update_check(self, manual=False):
        if getattr(self,'update_inflight',False):
            return
        self.update_inflight=True
        def worker():
            try:
                result,new=check_github_update(local_root(), APP_VERSION)
                if not new:
                    drive_result,drive_new=check_drive_update(self.store,local_root(),APP_VERSION)
                    if drive_new:result,new=drive_result,True
                    elif not result.startswith('Already up to date') and drive_result not in ('No Google Drive connected','No published updates'):
                        result=result+'\nDrive: '+drive_result
                if new:self.updates.put(('update',result))
                elif manual:self.updates.put(('status',result))
            except Exception as exc:
                if manual:self.updates.put(('status','Update check error: '+str(exc)))
            finally:
                self.update_inflight=False
        threading.Thread(target=worker,daemon=True).start()
        if not manual:
            self.root.after(12*60*1000,self.background_update_check)

    def _poll_updates(self):
        try:
            while True:
                kind,text=self.updates.get_nowait()
                if kind=='update':self.notify_update(text)
                elif kind=='status':messagebox.showinfo('Muhammad Robot · Update status',text,parent=self.root)
                elif kind=='voice':messagebox.showinfo('Natural voice setup',text,parent=self.root)
        except queue.Empty:
            pass
        self.root.after(400,self._poll_updates)

    def natural_voice_setup(self):
        # Optional neural cloud TTS. User must explicitly opt in.
        if self.voice.engine.startswith('Neural'):
            messagebox.showinfo('Natural voice','Neural voice is already available.',parent=self.root)
            return
        if not messagebox.askyesno('Optional online natural voice',
            'Install the optional edge-tts Python package for a more natural English voice?\n\n'
            'This uses an unofficial online Microsoft voice service. It sends spoken TEXT over the internet, '
            'not microphone recordings. Availability can change. Your school may restrict installations.\n\n'
            'You can continue without it. Install now?',parent=self.root):
            return
        import subprocess
        def worker():
            try:
                cmd=[sys.executable,'-m','pip','install','--user','edge-tts']
                p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                                 text=True,timeout=120,creationflags=0x08000000 if sys.platform=='win32' else 0)
                result='Installed. Restart the robot to enable natural voice.' if p.returncode==0 else                        'Installation failed or was blocked by school policy.\n'+p.stdout[-1600:]
            except Exception as e:result='Installation unavailable: '+str(e)
            self.updates.put(('voice',result))
        threading.Thread(target=worker,daemon=True).start()
    def notify_update(self,message):
        # Silent self-restart only once active editing and audio actions are done.
        # The separate stable Launcher is retained, so it can load the new version.
        self.update_ready=message
        self._restart_when_safe()

    def _restart_when_safe(self):
        # Complete self-update even with 3D as default; never stall forever.
        if getattr(self,'_three_d_active',False):
            editing=self.editor and self.editor.window.winfo_exists() and self.editor.window.state()!='withdrawn'
            if editing or bool(self.action_queue) or self.voice.speaking.is_set():
                self.root.after(5000,self._restart_when_safe)
                return
            process=getattr(self,'preview_3d_process',None)
            if process is not None and process.poll() is None:
                try:process.terminate()
                except OSError:pass
            self._three_d_active=False
        if not getattr(self,'update_ready',None):return
        editing=self.editor and self.editor.window.winfo_exists() and self.editor.window.state()!='withdrawn'
        busy=bool(self.action_queue) or self.voice.speaking.is_set()
        if editing or busy:
            self.root.after(5000,self._restart_when_safe)
            return
        try:
            if self.editor and self.editor.window.winfo_exists():self.editor.save()
            self.restart()
        except Exception as exc:
            messagebox.showwarning('Update ready', 'The update is installed but automatic restart failed: '+str(exc),parent=self.root)

    def restart(self):
        self._dismiss_shared_menu()
        self._mic_requested=False
        self._mic_generation=getattr(self,"_mic_generation",0)+1
        self._stop_real3d()
        import subprocess
        if self.listener:
            self.listener.stop()
            if self.listener.thread and self.listener.thread.is_alive():
                self.listener.thread.join(timeout=1.5)
        if self.editor and self.editor.window.winfo_exists():self.editor.save()
        launcher=local_root()/'Launcher.pyw'
        if launcher.is_file():
            subprocess.Popen([sys.executable,str(launcher)],close_fds=True)
        self.root.destroy()
    def exit(self):
        self._dismiss_shared_menu()
        self._mic_requested=False
        self._mic_generation=getattr(self,"_mic_generation",0)+1
        self._stop_real3d()
        if self.listener:self.listener.stop()
        if self.editor and self.editor.window.winfo_exists():self.editor.save()
        self.root.destroy()

    def _show_shared_menu(self,event=None):
        if getattr(self,'_shared_popup',None) is not None:
            self._dismiss_shared_menu()
            return
        x=event.x_root if event is not None else self.root.winfo_pointerx()
        y=event.y_root if event is not None else self.root.winfo_pointery()
        win=tk.Toplevel(self.root)
        win.withdraw()
        win.overrideredirect(True)
        win.attributes('-topmost',True)
        win.configure(bg='#4dc8ed')
        self._shared_popup=win
        self._shared_popup_job=None
        panel=tk.Frame(win,bg='#082943')
        panel.pack(fill='both',expand=True,padx=1,pady=1)
        tk.Label(panel,text='Muhammad Robot',anchor='w',bg='#082943',fg='#d8faff',
                 font=('Segoe UI',10,'bold')).pack(fill='x',padx=10,pady=(7,0))
        self._shared_voice_text=tk.StringVar(value=self._popup_voice_status())
        tk.Label(panel,textvariable=self._shared_voice_text,anchor='w',bg='#082943',fg='#9bc8dc',
                 font=('Segoe UI',8),wraplength=300).pack(fill='x',padx=10,pady=(1,5))
        canvas=tk.Canvas(panel,bg='#082943',bd=0,highlightthickness=0,width=320)
        scrollbar=tk.Scrollbar(panel,orient='vertical',command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side='left',fill='both',expand=True)
        rows=tk.Frame(canvas,bg='#082943')
        item=canvas.create_window(0,0,window=rows,anchor='nw')
        canvas.bind('<Configure>',lambda e:canvas.itemconfigure(item,width=e.width))
        self._shared_popup_buttons={}
        for index in range((self.menu.index('end') or 0)+1):
            if self.menu.type(index)=='separator':
                tk.Frame(rows,bg='#346078',height=1).pack(fill='x',padx=9,pady=4)
                continue
            label=self.menu.entrycget(index,'label')
            button=tk.Button(rows,text=label,anchor='w',relief='flat',bd=0,
                bg='#082943',fg='#e1f4fb',activebackground='#245473',activeforeground='white',
                disabledforeground='#688393',font=('Segoe UI',9),padx=10,pady=3,
                state=self.menu.entrycget(index,'state'),
                command=lambda n=index:self._invoke_shared_action(n))
            button.pack(fill='x',padx=3)
            self._shared_popup_buttons[label]=button
        rows.update_idletasks()
        canvas.configure(scrollregion=canvas.bbox('all'))
        height=rows.winfo_reqheight()
        available=max(120,self.root.winfo_screenheight()-95)
        canvas.configure(height=min(height,available))
        if height>available:scrollbar.pack(side='right',fill='y')
        def scroll(event):
            canvas.yview_scroll(-1 if event.delta>0 else 1,'units')
            return 'break'
        win.bind('<MouseWheel>',scroll)
        win.bind('<Escape>',lambda e:self._dismiss_shared_menu())
        win.bind('<FocusOut>',lambda e:win.after_idle(lambda:self._popup_check_focus(win)))
        win.update_idletasks()
        width=win.winfo_reqwidth()
        height=win.winfo_reqheight()
        x=max(0,min(int(x),max(0,self.root.winfo_screenwidth()-width-8)))
        y=max(0,min(int(y),max(0,self.root.winfo_screenheight()-height-8)))
        win.geometry(f'{width}x{height}+{x}+{y}')
        self._shared_popup_mouse=self._popup_pointer()[0]
        win.deiconify()
        win.lift()
        win.focus_force()
        # No tk_popup, grab or wait_window: microphone polling keeps running.
        self._shared_popup_job=self.root.after(30,self._poll_shared_popup)

    def _toggle_3d_effects(self):
        if getattr(self,'_three_d_active',False):self._signal_real3d('sound')

    def _cycle_3d_emotion(self):
        if getattr(self,'_three_d_active',False):self._signal_real3d('emotion')

    def _stop_real3d(self):
        self._three_d_active=False
        process=getattr(self,'preview_3d_process',None)
        if process is not None and process.poll() is None:
            try:process.terminate()
            except OSError:pass
        self.preview_3d_process=None
        for name in ('_three_d_bridge','_three_d_signal'):
            path=getattr(self,name,None)
            if path is not None:
                for item in (path,path.with_suffix('.tmp'),path.with_suffix('.reading'),
                             path.with_name(path.name+'.tmp'),path.with_name(path.name+'.reading')):
                    try:item.unlink(missing_ok=True)
                    except OSError:pass
            setattr(self,name,None)

    def _mic_failed(self,message):
        self.mic_active=False
        self.mic_state='RECONNECTING: '+str(message)[:130]
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

    def _popup_voice_status(self):
        if not getattr(self,'_mic_requested',False):return 'Voice: off'
        return 'Voice: '+str(getattr(self,'mic_state','Starting'))[:85]

    def _popup_pointer(self):
        # Poll only while this menu exists. No global hook or background recorder.
        import sys
        if sys.platform=='win32':
            import ctypes
            from ctypes import wintypes
            api=getattr(self,'_popup_user32',None)
            if api is None:
                api=ctypes.WinDLL('user32',use_last_error=True)
                api.GetAsyncKeyState.argtypes=[ctypes.c_int]
                api.GetAsyncKeyState.restype=ctypes.c_short
                api.GetCursorPos.argtypes=[ctypes.POINTER(wintypes.POINT)]
                api.GetCursorPos.restype=wintypes.BOOL
                self._popup_user32=api
            point=wintypes.POINT()
            if api.GetCursorPos(ctypes.byref(point)):
                buttons=sum((1<<n) for n,key in enumerate((1,2,4)) if api.GetAsyncKeyState(key)&0x8000)
                return buttons,point.x,point.y
        x,y=self.root.winfo_pointerxy()
        return 0,x,y

    def _popup_check_focus(self,expected=None):
        win=getattr(self,'_shared_popup',None)
        if win is None or (expected is not None and win is not expected):return
        try:
            focus=win.focus_get()
            if focus is None or focus.winfo_toplevel()!=win:self._dismiss_shared_menu()
        except (tk.TclError,KeyError):self._dismiss_shared_menu()

    def _poll_shared_popup(self):
        win=getattr(self,'_shared_popup',None)
        self._shared_popup_job=None
        if win is None:return
        try:
            buttons,x,y=self._popup_pointer()
            pressed=buttons & ~self._shared_popup_mouse
            self._shared_popup_mouse=buttons
            inside=(win.winfo_rootx()<=x<win.winfo_rootx()+win.winfo_width() and
                    win.winfo_rooty()<=y<win.winfo_rooty()+win.winfo_height())
            if pressed and not inside:
                self._dismiss_shared_menu()
                return
            text=self._popup_voice_status()
            if self._shared_voice_text.get()!=text:self._shared_voice_text.set(text)
            self._shared_popup_job=self.root.after(30,self._poll_shared_popup)
        except tk.TclError:self._dismiss_shared_menu()

    def _dismiss_shared_menu(self):
        win=getattr(self,'_shared_popup',None)
        self._shared_popup=None
        job=getattr(self,'_shared_popup_job',None)
        self._shared_popup_job=None
        if job is not None:
            try:self.root.after_cancel(job)
            except tk.TclError:pass
        if win is not None:
            try:win.destroy()
            except tk.TclError:pass

    def _invoke_shared_action(self,index):
        self._dismiss_shared_menu()
        self.menu.invoke(index)

if __name__=='__main__':
    app=RobotApp()
    app.root.mainloop()
