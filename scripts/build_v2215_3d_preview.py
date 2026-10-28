#!/usr/bin/env python3
"""Muhammad Robot v2.2.15: auto-install an OPTIONAL Windows real-3D preview.

v2.2.14 remains the functional primary assistant. Published Godot 3D prototype
is packed under app/visual3d/, exposed via a 'Try 3D robot (beta)' menu item.
NO automatic launch, no microphone/editor/code changes. 3D preview Run/Studio
controls are not bridged yet. Explicitly warn user before opening.
Existing 100-file / 80MB ZIP / 120MB unpack security limits MUST all pass.
"""
from pathlib import Path
import hashlib,json,re,sys,zipfile,ast

BASE_SHA='2bcef2406fb22b93d84f8ff21ff63bfcda8b4df4f8881eaf5893888c82547a1a'
PREVIEW_SHA='645c65b6ae9c01955477e5f531efcdd414d69ebea7470fe0518800c6c6bae365'
INSERT_BEFORE="    def _hover_button(self, idx, entering):"
MENU_ANCHOR="self.menu.add_command(label='Appearance: Living / Classic',command=self.switch_robot_look)"
NEW_METHOD="""
    def open_real3d_preview(self):
        import subprocess
        exe=HERE/'visual3d'/'MuhammadRobot3D.exe'
        pack=HERE/'visual3d'/'MuhammadRobot3D.pck'
        if not exe.is_file() or not pack.is_file():
            messagebox.showerror('3D Robot', '3D preview files are missing. Please run Check GitHub updates.', parent=self.root)
            return
        if getattr(self,'preview_3d_process',None) is not None:
            if self.preview_3d_process.poll() is None:
                messagebox.showinfo('3D Robot', '3D preview is already running.', parent=self.root)
                return
        if not messagebox.askyesno('Muhammad Robot 3D (BETA)',
            'Open the experimental REAL 3D cream robot?\\n\\n'
            'Your current Python robot stays working.\\n'
            'The 3D preview has live eyes and antenna, but its Run/Studio buttons are NOT yet connected.\\n\\n'
            'Click yes to try the visual prototype.', parent=self.root):
            return
        try:
            self.preview_3d_process=subprocess.Popen([str(exe)],cwd=str(exe.parent),
                close_fds=True)
        except Exception as exc:
            messagebox.showerror('3D Robot', 'Windows could not start the preview:\\n'+str(exc), parent=self.root)

"""
def prepare_app(source):
    if source.count(INSERT_BEFORE)!=1:raise ValueError('Missing known GUI method')
    if source.count(MENU_ANCHOR)!=1:raise ValueError('Missing current menu anchor')
    source=source.replace(INSERT_BEFORE,NEW_METHOD+INSERT_BEFORE)
    source=source.replace(MENU_ANCHOR, MENU_ANCHOR+
      "\n        self.menu.add_command(label='Try 3D robot (beta)',command=self.open_real3d_preview)")
    compile(source,'robot_app.py','exec')
    return source

def build(baseline,preview,out):
    baseline=Path(baseline);preview=Path(preview);out=Path(out)
    if hashlib.sha256(baseline.read_bytes()).hexdigest()!=BASE_SHA:
        raise ValueError('Baseline v2.2.14 SHA mismatch')
    if hashlib.sha256(preview.read_bytes()).hexdigest()!=PREVIEW_SHA:
        raise ValueError('3D preview SHA mismatch')
    out.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(baseline) as z,zipfile.ZipFile(preview) as p,zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=7) as archive:
        if z.testzip() or p.testzip():raise ValueError('Source ZIP corrupted')
        names=z.namelist()
        if len(set(names))!=len(names) or len(names)>98:raise ValueError('Invalid baseline')
        for info in z.infolist():
            data=z.read(info.filename)
            if info.filename=='app/robot_app.py':
                data=prepare_app(data.decode('utf8')).encode('utf8')
            elif info.filename=='app/robot_core.py':
                code=data.decode('utf8')
                old="APP_VERSION = '2.2.14'"
                if code.count(old)!=1:raise ValueError('Incorrect base version')
                code=code.replace(old,"APP_VERSION = '2.2.15'")
                compile(code,'robot_core.py','exec')
                data=code.encode('utf8')
            archive.writestr(info,data)
        for name in ('MuhammadRobot3D.exe','MuhammadRobot3D.pck'):
            if name not in p.namelist():raise ValueError('3D preview missing '+name)
            data=p.read(name)
            if name.endswith('.exe') and data[:2]!=b'MZ':raise ValueError('Not a Windows executable')
            archive.writestr('app/visual3d/'+name,data)
    with zipfile.ZipFile(out) as z:
        entries=z.infolist()
        unpacked=sum(x.file_size for x in entries)
        if z.testzip() or len(entries)>100 or unpacked>120_000_000 or out.stat().st_size>80_000_000:
            raise ValueError('Existing updater safety limits exceeded: '+str((len(entries),unpacked,out.stat().st_size)))
        assert z.namelist()==names+['app/visual3d/MuhammadRobot3D.exe','app/visual3d/MuhammadRobot3D.pck']
        assert b'2.2.15' in z.read('app/robot_core.py')
        assert b'Try 3D robot (beta)' in z.read('app/robot_app.py')
    manifest={'version':'2.2.15','zip':out.name,'sha256':hashlib.sha256(out.read_bytes()).hexdigest()}
    (out.parent/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8')
    print('PASS v2.2.15:',len(entries),'entries',unpacked,'unpacked bytes',out.stat().st_size,'ZIP bytes; old app preserved')
if __name__=='__main__':
    if len(sys.argv)!=4:raise SystemExit('Usage: build_v2215_3d_preview.py base.zip preview.zip output.zip')
    build(sys.argv[1],sys.argv[2],sys.argv[3])
