#!/usr/bin/env python3
"""v2.2.16 / real 3D <-> classic exclusive mode with safe Godot IPC.

The working Python robot stays alive but WITHDRAWN when 3D is visible.
3D right-click -> Switch to Classic quits Godot; Python immediately restores
the single original avatar. Godot 'Run Python' bridges to the existing Python
interpreter. Godot 'Python Studio' closes 3D and opens the working Tk editor.
A crash/exit also restores Classic (no stranded user).
"""
from pathlib import Path
import hashlib, json, sys, zipfile

PINNED_BASE='24ec3d750097ff40d1ce2a3a795a761b49980e6ed0b355bc965f2a8b7ab29c04'

START="    def open_real3d_preview(self):\n"
END="    def _hover_button(self, idx, entering):\n"
NEW_METHOD=r'''    def open_real3d_preview(self):
        """Exactly one visible mascot, with Python services still running."""
        import secrets, subprocess
        if getattr(self,'_three_d_active',False):
            return
        exe=HERE/'visual3d'/'MuhammadRobot3D.exe'
        pack=HERE/'visual3d'/'MuhammadRobot3D.pck'
        if not exe.is_file() or not pack.is_file():
            messagebox.showerror('3D Robot','Missing 3D files; check GitHub updates.',parent=self.root)
            return
        data=local_root()/'Data'
        data.mkdir(parents=True,exist_ok=True)
        bridge=data/('3d_switch_'+secrets.token_hex(12)+'.cmd')
        self._three_d_return_editor=False
        try:
            child=subprocess.Popen([str(exe),'--','--robot-bridge',str(bridge)],
                                    cwd=str(exe.parent),close_fds=True)
        except Exception as exc:
            messagebox.showerror('3D Robot',str(exc),parent=self.root)
            return
        self.preview_3d_process=child
        self._three_d_bridge=bridge
        self._three_d_active=True
        try:
            if getattr(self,'aqua_menu',None) is not None:
                self.aqua_menu.destroy()
                self.aqua_menu=None
            if self.editor and self.editor.window.winfo_exists():
                self.editor.hide()
            if getattr(self,'orb',None) is not None and self.orb.winfo_exists():
                self.orb.destroy()
                self.orb=None
            self.minimized=True
            self.root.withdraw()
        except tk.TclError:
            pass
        self.root.after(180,self._poll_real3d_mode)

    def _poll_real3d_mode(self):
        """Tk-thread-only lifecycle guard and three whitelisted bridge commands."""
        if not getattr(self,'_three_d_active',False):
            return
        proc=getattr(self,'preview_3d_process',None)
        bridge=getattr(self,'_three_d_bridge',None)
        cmd=''
        if bridge is not None and bridge.is_file():
            try:
                cmd=bridge.read_text(encoding='utf-8').strip()
            except (OSError,UnicodeError):
                cmd=''
            try:bridge.unlink(missing_ok=True)
            except OSError:pass
        if cmd=='run':
            self.quick_run()
        elif cmd in ('classic','editor'):
            self._three_d_return_editor=(cmd=='editor')
            if proc is not None and proc.poll() is None:
                try:proc.terminate()
                except OSError:pass
        if proc is not None and proc.poll() is None:
            self.root.after(180,self._poll_real3d_mode)
            return
        # The 3D window has ended, including on crash/Windows close.
        self._three_d_active=False
        self.preview_3d_process=None
        if bridge is not None:
            try:bridge.unlink(missing_ok=True)
            except OSError:pass
        self._three_d_bridge=None
        self.restore()
        if getattr(self,'_three_d_return_editor',False):
            self._three_d_return_editor=False
            self.root.after(250,self.open_editor)

'''
def patch_app(s):
    if s.count(START)!=1 or s.count(END)!=1:raise ValueError('Unexpected v2.2.15 methods')
    a=s.index(START);b=s.index(END,a)
    if 'self.preview_3d_process' not in s[a:b] or 'messagebox' not in s[a:b]:
        raise ValueError('Missing expected previous 3D handler')
    s=s[:a]+NEW_METHOD+s[b:]
    old="self.menu.add_command(label='Try 3D robot (beta)',command=self.open_real3d_preview)"
    new="self.menu.add_command(label='Switch to 3D Plush Robot',command=self.open_real3d_preview)"
    if s.count(old)!=1:raise ValueError('Missing classic right-click 3D menu')
    s=s.replace(old,new)
    # Voice OPEN must never make a second Classic avatar appear while 3D is up.
    marker="    def restore(self):"
    if s.count(marker)!=1:raise ValueError('Missing classic restore')
    s=s.replace(marker,marker+"\n        if getattr(self,'_three_d_active',False):return")
    # Installed updates must not restart the hidden Python host while 3D is open.
    guard="    def _restart_when_safe(self):"
    if s.count(guard)!=1:raise ValueError('Missing restart guard anchor')
    s=s.replace(guard,guard+
        "\n        if getattr(self,'_three_d_active',False):\n"
        "            self.root.after(5000,self._restart_when_safe)\n"
        "            return")
    compile(s,'robot_app.py','exec')
    return s

def build(base,preview,out):
    base=Path(base);preview=Path(preview);out=Path(out)
    if hashlib.sha256(base.read_bytes()).hexdigest()!=PINNED_BASE:
        raise ValueError('Must use exact published v2.2.15 source')
    out.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(base) as original,zipfile.ZipFile(preview) as source:
        if original.testzip() or source.testzip():raise ValueError('Bad ZIP')
        names=original.namelist()
        if len(set(names))!=len(names):raise ValueError('Duplicate member')
        exe=source.read('MuhammadRobot3D.exe')
        pck=source.read('MuhammadRobot3D.pck')
        if exe[:2]!=b'MZ' or len(exe)<25_000_000 or len(pck)<100:
            raise ValueError('Invalid Godot Windows binary')
        expected={'app/robot_app.py','app/robot_core.py','app/visual3d/MuhammadRobot3D.exe','app/visual3d/MuhammadRobot3D.pck'}
        if not expected.issubset(set(names)):raise ValueError('Expected installed 3D preview missing')
        with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=7) as z:
            for info in original.infolist():
                path=info.filename
                content=original.read(path)
                if path=='app/robot_app.py':
                    content=patch_app(content.decode('utf8')).encode('utf8')
                elif path=='app/robot_core.py':
                    s=content.decode('utf8')
                    a="APP_VERSION = '2.2.15'"
                    if s.count(a)!=1:raise ValueError('Incorrect old version')
                    s=s.replace(a,"APP_VERSION = '2.2.16'")
                    compile(s,path,'exec')
                    content=s.encode('utf8')
                elif path=='app/visual3d/MuhammadRobot3D.exe':
                    content=exe
                elif path=='app/visual3d/MuhammadRobot3D.pck':
                    content=pck
                z.writestr(info,content)
    with zipfile.ZipFile(out) as z:
        infos=z.infolist()
        total=sum(x.file_size for x in infos)
        if z.testzip() or len(infos)>100 or total>120_000_000 or out.stat().st_size>80_000_000:
            raise ValueError('Existing updater security limits violated: '+str((len(infos),total,out.stat().st_size)))
        if z.namelist()!=names:raise ValueError('Modified package layout')
        assert b'Switch to 3D Plush Robot' in z.read('app/robot_app.py')
        assert b'2.2.16' in z.read('app/robot_core.py')
    mf={'version':'2.2.16','zip':out.name,'sha256':hashlib.sha256(out.read_bytes()).hexdigest()}
    (out.parent/'manifest.json').write_text(json.dumps(mf,indent=2)+'\n','utf8')
    print('PASS safe 3D exclusive update',len(infos),'files',out.stat().st_size,'ZIP bytes,',total,'unpacked')
if __name__=='__main__':
    if len(sys.argv)!=4:raise SystemExit('Usage: build_v2216.py base.zip godot020.zip result.zip')
    build(*sys.argv[1:])
