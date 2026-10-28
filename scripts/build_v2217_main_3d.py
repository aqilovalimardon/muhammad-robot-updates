#!/usr/bin/env python3
"""v2.2.17: real 3D by default, voice controls cream orb, editor keeps 3D visible.

Source is verified v2.2.16; preserve all original scripts and user data.
Use exactly the released and Windows-tested Godot v0.3.0 binaries.
"""
from pathlib import Path
import hashlib,json,sys,zipfile

PINNED='b724c7c268dbaf75daca86d03a99675a9c07b1dbea987f323b1c7df9cea23f1d'

def patch_app(code):
    changes=[
        (
            "self.root.after(1000,self._mark_launch_ok)",
            "self.root.after(1000,self._mark_launch_ok)\n"
            "        self.root.after(1400,self._start_default_3d)"
        ),
        (
            "    def open_real3d_preview(self):",
            """    def _start_default_3d(self):
        # 3D is now the primary view. Classic remains a user-selectable fallback.
        if self.store.settings.get('robot_visual_mode','3d')=='3d':
            self.open_real3d_preview()

    def _signal_real3d(self,command):
        signal=getattr(self,'_three_d_signal',None)
        if signal is None or command not in ('hide','show'):return
        try:signal.write_text(command,encoding='utf-8')
        except OSError:pass

    def open_real3d_preview(self):"""
        ),
        (
            "bridge=data/('3d_switch_'+secrets.token_hex(12)+'.cmd')",
            "bridge=data/('3d_switch_'+secrets.token_hex(12)+'.cmd')\n"
            "        signal=data/('3d_voice_'+secrets.token_hex(12)+'.cmd')"
        ),
        (
            "[str(exe),'--','--robot-bridge',str(bridge)]",
            "[str(exe),'--','--robot-bridge',str(bridge),'--robot-signal',str(signal)]"
        ),
        (
            "self._three_d_bridge=bridge\n        self._three_d_active=True",
            "self._three_d_bridge=bridge\n"
            "        self._three_d_signal=signal\n"
            "        self._three_d_active=True\n"
            "        self.store.setting('robot_visual_mode','3d')"
        ),
        (
            """        if cmd=='run':
            self.quick_run()
        elif cmd in ('classic','editor'):
            self._three_d_return_editor=(cmd=='editor')
            if proc is not None and proc.poll() is None:
                try:proc.terminate()
                except OSError:pass""",
            """        if cmd=='run':
            self.quick_run()
        elif cmd=='editor':
            # 3D mascot keeps running. Editor is a standalone Tk Toplevel.
            self.open_editor()
        elif cmd=='classic':
            self.store.setting('robot_visual_mode','classic')
            if proc is not None and proc.poll() is None:
                try:proc.terminate()
                except OSError:pass"""
        ),
        (
            """        self._three_d_bridge=None
        self.restore()""",
            """        self._three_d_bridge=None
        signal=getattr(self,'_three_d_signal',None)
        if signal is not None:
            try:signal.unlink(missing_ok=True)
            except OSError:pass
        self._three_d_signal=None
        self.restore()"""
        ),
        (
            """    def open_editor(self):
        if self.minimized:self.restore()""",
            """    def open_editor(self):
        if self.minimized and not getattr(self,'_three_d_active',False):
            self.restore()"""
        ),
        (
            "    def minimize(self):",
            """    def minimize(self):
        if getattr(self,'_three_d_active',False):
            self._signal_real3d('hide')
            return"""
        ),
        (
            "    def restore(self):",
            """    def restore(self):
        if getattr(self,'_three_d_active',False):
            self._signal_real3d('show')
            return"""
        ),
        (
            "if self.minimized:self._show_restore_orb()",
            "if self.minimized and not getattr(self,'_three_d_active',False):self._show_restore_orb()"
        ),
        (
            """    def _restart_when_safe(self):
        if getattr(self,'_three_d_active',False):
            self.root.after(5000,self._restart_when_safe)
            return""",
            """    def _restart_when_safe(self):
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
            self._three_d_active=False"""
        ),
    ]
    for before,after in changes:
        count=code.count(before)
        if count!=1:raise ValueError(f'Expected one anchor, found {count}: '+before[:115])
        code=code.replace(before,after)
    compile(code,'robot_app.py','exec')
    return code

def build(src,preview,out):
    src=Path(src);preview=Path(preview);out=Path(out)
    if hashlib.sha256(src.read_bytes()).hexdigest()!=PINNED:
        raise ValueError('Must build from exact official v2.2.16 ZIP')
    out.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(src) as old,zipfile.ZipFile(preview) as new:
        if old.testzip() or new.testzip():raise ValueError('Damaged source archive')
        exe=new.read('MuhammadRobot3D.exe');pck=new.read('MuhammadRobot3D.pck')
        if not exe.startswith(b'MZ') or len(exe)<25_000_000 or len(pck)<100:
            raise ValueError('Incorrect Godot Windows binaries')
        names=old.namelist()
        with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=7) as z:
            for item in old.infolist():
                content=old.read(item.filename)
                if item.filename=='app/robot_app.py':
                    content=patch_app(content.decode('utf8')).encode('utf8')
                elif item.filename=='app/robot_core.py':
                    code=content.decode('utf8')
                    k="APP_VERSION = '2.2.16'"
                    if code.count(k)!=1:raise ValueError('Bad base version')
                    code=code.replace(k,"APP_VERSION = '2.2.17'")
                    compile(code,'robot_core.py','exec')
                    content=code.encode('utf8')
                elif item.filename=='app/visual3d/MuhammadRobot3D.exe':
                    content=exe
                elif item.filename=='app/visual3d/MuhammadRobot3D.pck':
                    content=pck
                z.writestr(item,content)
    with zipfile.ZipFile(out) as check:
        files=check.infolist()
        total=sum(x.file_size for x in files)
        if check.testzip() or len(files)>100 or total>120_000_000 or out.stat().st_size>80_000_000:
            raise ValueError('Existing on-device updater caps not met')
        if check.namelist()!=names:raise ValueError('Unintended ZIP layout changes')
    mf={'version':'2.2.17','zip':out.name,'sha256':hashlib.sha256(out.read_bytes()).hexdigest()}
    (out.parent/'manifest.json').write_text(json.dumps(mf,indent=2)+'\n',encoding='utf8')
    print('PASS real 3D primary, voice orb, editor without classic, ZIP limits',len(files),out.stat().st_size,total)
if __name__=='__main__':
    if len(sys.argv)!=4:raise SystemExit('build_v2217_main_3d.py old.zip godot030.zip new.zip')
    build(*sys.argv[1:])
