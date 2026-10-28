#!/usr/bin/env python3
"""Gate v2.2.16 against duplicate avatars, broken Python features, or unsafe ZIPs."""
import ast, hashlib, json, re, sys, tempfile, zipfile
from pathlib import Path
from types import MethodType, SimpleNamespace
old=Path(sys.argv[1]);new=Path(sys.argv[2])
mf=json.loads((new.parent/'manifest.json').read_text(encoding='utf8'))
with zipfile.ZipFile(old) as z:
    source=z.read('app/robot_core.py').decode('utf8')
    before=z.namelist()
model=ast.parse(source)
fn=[x for x in model.body if isinstance(x,ast.FunctionDef) and x.name in ('inspect_release','version_tuple')]
e=ast.ClassDef(name='UpdateError',bases=[ast.Name(id='Exception',ctx=ast.Load())],keywords=[],body=[ast.Pass()],decorator_list=[])
m=ast.Module(body=[e]+fn,type_ignores=[])
ast.fix_missing_locations(m)
scope={'hashlib':hashlib,'Path':Path,'zipfile':zipfile,'re':re,'VERSION_RE':re.compile(r'^\d+\.\d+\.\d+$')}
exec(compile(m,'device_validator.py','exec'),scope)
assert scope['inspect_release'](mf,new)
print('PASS: device ZIP update safety and checksum accepted')
with zipfile.ZipFile(old) as baseline,zipfile.ZipFile(new) as z:
    assert z.testzip() is None
    assert z.namelist()==before
    assert len(z.namelist())<=100
    edits={'app/robot_app.py','app/robot_core.py','app/visual3d/MuhammadRobot3D.exe','app/visual3d/MuhammadRobot3D.pck'}
    for name in before:
        if name not in edits:assert z.read(name)==baseline.read(name),name
    app=z.read('app/robot_app.py').decode('utf8')
    core=z.read('app/robot_core.py').decode('utf8')
    assert "APP_VERSION = '2.2.16'" in core
    assert "Switch to 3D Plush Robot" in app
    assert 'Try 3D robot (beta)' not in app
    assert "self.root.withdraw()" in app
    assert "self._three_d_active=False" in app
    assert "self.root.after(180,self._poll_real3d_mode)" in app
    assert 'if getattr(self,\'_three_d_active\',False):return' in app
    for x in ('def quick_run(self):','def open_editor(self):','def background_update_check(',
              'def start_microphone(self):','def minimize(self):','def restore(self):',
              'def toggle_aqua_menu(self):','def _orb_track_eyes(self):','def _restart_when_safe(self):'):
        assert x in app,x
    assert z.read('app/visual3d/MuhammadRobot3D.exe')[:2]==b'MZ'
    assert z.getinfo('app/visual3d/MuhammadRobot3D.exe').file_size>25_000_000
    tree=ast.parse(app)
    clazz=next(c for c in tree.body if isinstance(c,ast.ClassDef) and c.name=='RobotApp')
    methods=[n for n in clazz.body if isinstance(n,ast.FunctionDef)
             and n.name in ('open_real3d_preview','_poll_real3d_mode')]
    extracted=ast.Module(body=[ast.ClassDef(name='SUT',bases=[],keywords=[],decorator_list=[],body=methods)],type_ignores=[])
    ast.fix_missing_locations(extracted)
    fake_scope={}
    import tkinter as tk
    fake_scope['tk']=tk
    with tempfile.TemporaryDirectory() as temp:
        d=Path(temp)
        (d/'visual3d').mkdir()
        (d/'Data').mkdir()
        (d/'visual3d'/'MuhammadRobot3D.exe').write_bytes(b'MZfake')
        (d/'visual3d'/'MuhammadRobot3D.pck').write_bytes(b'PCKfake')
        class DummyProcess:
            def __init__(self):self.ended=False
            def poll(self):return 0 if self.ended else None
            def terminate(self):self.ended=True
        processes=[]
        class FakeSubprocess:
            def Popen(self,args,**kw):
                assert args[0].endswith('.exe') and '--robot-bridge' in args and '--' in args,args
                p=DummyProcess();processes.append(p);return p
        fake_scope['HERE']=d
        fake_scope['local_root']=lambda:d
        fake_scope['subprocess']=FakeSubprocess()
        import subprocess as real_subprocess
        # Method imports subprocess internally: patch module Popen during isolated test only.
        old_popen=real_subprocess.Popen
        real_subprocess.Popen=fake_scope['subprocess'].Popen
        class Box:
            def showerror(self,*args,**kw):raise AssertionError('Unexpected dialog: '+str(args))
        fake_scope['messagebox']=Box()
        exec(compile(extracted,'mode_handoff.py','exec'),fake_scope)
        class Root:
            def __init__(self):self.is_hidden=False;self.jobs=[]
            def withdraw(self):self.is_hidden=True
            def after(self,ms,cb):self.jobs.append((ms,cb))
        root=Root()
        reactions=[]
        state=SimpleNamespace(root=root,editor=None,orb=None,aqua_menu=None,
                              minimized=False,preview_3d_process=None)
        state.restore=lambda:reactions.append('restore')
        state.quick_run=lambda:reactions.append('run')
        state.open_editor=lambda:reactions.append('editor')
        state.open_real3d_preview=MethodType(fake_scope['SUT'].open_real3d_preview,state)
        state._poll_real3d_mode=MethodType(fake_scope['SUT']._poll_real3d_mode,state)
        try:
            state.open_real3d_preview()
            assert root.is_hidden and state.minimized and state._three_d_active
            assert len(processes)==1
            state.open_real3d_preview()
            assert len(processes)==1,'Spawned a second 3D robot'
            bridge=state._three_d_bridge
            bridge.write_text('run',encoding='utf8')
            state._poll_real3d_mode()
            assert reactions==['run'] and state._three_d_active
            bridge.write_text('classic',encoding='utf8')
            state._poll_real3d_mode()
            assert not state._three_d_active and reactions==['run','restore']
            state.open_real3d_preview()
            bridge=state._three_d_bridge
            bridge.write_text('editor',encoding='utf8')
            state._poll_real3d_mode()
            assert reactions[-1]=='restore' and not state._three_d_active
            root.jobs[-1][1]()
            assert reactions[-1]=='editor'
            print('PASS: one visible robot, bridge Run, 3D->Classic restore, Studio handoff, no duplicate launch')
        finally:
            real_subprocess.Popen=old_popen
