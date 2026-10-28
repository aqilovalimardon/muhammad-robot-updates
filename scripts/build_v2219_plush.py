#!/usr/bin/env python3
"""v2.2.19: one context menu, primary 3D, soft plush and expressive fluffy orb."""
import ast
import hashlib
import json
from pathlib import Path
import sys
import zipfile

BASE_SHA256 = '05ccedd3800be9357d404033f6ff45d5ccb4a8eb53c5641774c22f42fee5fbb3'


class HostChanges:
    # These methods replace/extend RobotApp inside the verified baseline ZIP.
    def _start_default_3d(self):
        # Classic is a recovery view for this session, not the next launch default.
        self.store.setting('robot_visual_mode','3d')
        self.open_real3d_preview()

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
        self.menu.add_command(label='Appearance: Living / Classic',command=self.switch_robot_look)
        self.menu.add_command(label='Switch to 3D Plush Robot',command=self.open_real3d_preview)
        self.menu.add_command(label='Switch to Classic (backup)',command=self.switch_to_classic)
        self.menu.add_command(label='About robot / version',command=self.show_version)
        self.menu.add_command(label='Check GitHub updates',command=self.check_updates_now)
        self.menu.add_command(label='Natural voice setup (optional)',command=self.natural_voice_setup)
        self.menu.add_separator()
        self.menu.add_command(label='Exit Robot',command=self.exit)

    def _show_shared_menu(self,event=None):
        # Exactly the same native menu is used with either visible avatar.
        active=getattr(self,'_three_d_active',False)
        for label in ('Show next 3D emotion','3D effect sounds: On / Off','Switch to Classic (backup)'):
            self.menu.entryconfigure(label,state='normal' if active else 'disabled')
        self.menu.entryconfigure('Switch to 3D Plush Robot',state='disabled' if active else 'normal')
        x=event.x_root if event is not None else self.root.winfo_pointerx()
        y=event.y_root if event is not None else self.root.winfo_pointery()
        self.root.update_idletasks()
        try:self.menu.tk_popup(x,y)
        finally:self.menu.grab_release()

    def popup(self,event):
        self._show_shared_menu(event)

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

    def switch_to_classic(self):
        self._stop_real3d()
        self.restore()

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
        elif command=='classic':
            self.switch_to_classic()
            return
        if process is not None and process.poll() is None:
            self.root.after(40,self._poll_real3d_mode)
            return
        self._stop_real3d()
        self.restore()


def patch_app(code):
    changes = {
        'self.root.after(1400,self._start_default_3d)': 'self.root.after(100,self._start_default_3d)',
        "command not in ('hide','show')": "command not in ('hide','show','sound','emotion','happy')",
        '    def switch_robot_look(self):\n':
            "    def switch_robot_look(self):\n        if getattr(self,'_three_d_active',False):self.switch_to_classic()\n",
        '    def restart(self):\n': '    def restart(self):\n        self._stop_real3d()\n',
        '    def exit(self):\n': '    def exit(self):\n        self._stop_real3d()\n',
        '    def say(self,text):\n':
            "    def say(self,text):\n        if getattr(self,'_three_d_active',False):self._signal_real3d('happy')\n",
    }
    for before, after in changes.items():
        if code.count(before) != 1:
            raise ValueError('Baseline anchor changed: ' + before)
        code = code.replace(before, after)
    source = Path(__file__).read_text(encoding='utf-8')
    source_lines = source.splitlines(keepends=True)
    overrides = next(n for n in ast.parse(source).body if isinstance(n, ast.ClassDef) and n.name == 'HostChanges')
    target = next(n for n in ast.parse(code).body if isinstance(n, ast.ClassDef) and n.name == 'RobotApp')
    methods = {n.name: n for n in target.body if isinstance(n, ast.FunctionDef)}
    edits, additions = [], []
    for method in overrides.body:
        if not isinstance(method, ast.FunctionDef):continue
        text = ''.join(source_lines[method.lineno-1:method.end_lineno])
        old = methods.get(method.name)
        if old:edits.append((old.lineno-1, old.end_lineno, text))
        else:additions.append('\n' + text)
    edits.append((target.end_lineno, target.end_lineno, ''.join(additions)))
    lines = code.splitlines(keepends=True)
    for start, end, text in sorted(edits, reverse=True):lines[start:end] = [text]
    code = ''.join(lines)
    compile(code, 'robot_app.py', 'exec')
    return code


def build(source, pack, output):
    source, pack, output = map(Path, (source, pack, output))
    if hashlib.sha256(source.read_bytes()).hexdigest() != BASE_SHA256:
        raise ValueError('Expected exact official v2.2.18 ZIP')
    pck = pack.read_bytes()
    if not pck.startswith(b'GDPC') or len(pck) < 1000:raise ValueError('Invalid Godot pack')
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(source) as old, zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=7) as new:
        if old.testzip():raise ValueError('Corrupt baseline')
        names = old.namelist()
        for item in old.infolist():
            data = old.read(item)
            if item.filename == 'app/robot_app.py':data = patch_app(data.decode('utf-8')).encode('utf-8')
            elif item.filename == 'app/robot_core.py':
                text = data.decode('utf-8')
                if text.count("APP_VERSION = '2.2.18'") != 1:raise ValueError('Bad base version')
                data = text.replace("APP_VERSION = '2.2.18'", "APP_VERSION = '2.2.19'").encode('utf-8')
            elif item.filename == 'app/visual3d/MuhammadRobot3D.pck':data = pck
            new.writestr(item, data)
    with zipfile.ZipFile(output) as z:
        if z.testzip() or z.namelist() != names:raise ValueError('Unexpected ZIP layout')
        if len(names)>100 or sum(i.file_size for i in z.infolist())>120_000_000 or output.stat().st_size>80_000_000:
            raise ValueError('Existing updater caps exceeded')
    manifest = {'version':'2.2.19','zip':output.name,'sha256':hashlib.sha256(output.read_bytes()).hexdigest()}
    (output.parent/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('PASS: v2.2.19 package built; only host, version and Godot resources updated')


if __name__ == '__main__':build(*sys.argv[1:])
