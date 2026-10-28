#!/usr/bin/env python3
"""Verify 3D primary v2.2.17 without risky changes to installed Python code."""
import ast,hashlib,json,re,sys,tempfile,zipfile
from pathlib import Path
from types import MethodType,SimpleNamespace

old=Path(sys.argv[1]);new=Path(sys.argv[2])
manifest=json.loads((new.parent/'manifest.json').read_text('utf8'))
with zipfile.ZipFile(old) as z:
    source=z.read('app/robot_core.py').decode('utf8')
    oldpaths=z.namelist()
tree=ast.parse(source)
funcs=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('inspect_release','version_tuple')]
err=ast.ClassDef(name='UpdateError',bases=[ast.Name(id='Exception',ctx=ast.Load())],keywords=[],body=[ast.Pass()],decorator_list=[])
mod=ast.Module(body=[err]+funcs,type_ignores=[])
ast.fix_missing_locations(mod)
scope={'hashlib':hashlib,'zipfile':zipfile,'Path':Path,'re':re,
       'VERSION_RE':re.compile(r'^\d+\.\d+\.\d+$')}
exec(compile(mod,'actual_device_validator.py','exec'),scope)
assert scope['inspect_release'](manifest,new)
print('PASS: deployed versioned ZIP security, SHA256, archive limits')
with zipfile.ZipFile(old) as orig,zipfile.ZipFile(new) as z:
    assert z.testzip() is None and z.namelist()==oldpaths
    exceptions={'app/robot_app.py','app/robot_core.py','app/visual3d/MuhammadRobot3D.exe','app/visual3d/MuhammadRobot3D.pck'}
    for item in oldpaths:
        if item not in exceptions:assert orig.read(item)==z.read(item),item
    code=z.read('app/robot_app.py').decode('utf8')
    assert "APP_VERSION = '2.2.17'" in z.read('app/robot_core.py').decode('utf8')
    for requirement in ("self.root.after(1400,self._start_default_3d)",
                        "self.store.settings.get('robot_visual_mode','3d')",
                        "self.store.setting('robot_visual_mode','3d')",
                        "self.store.setting('robot_visual_mode','classic')",
                        "'--robot-signal',str(signal)",
                        "def _signal_real3d(self,command):",
                        "if cmd=='editor':",
                        "self.open_editor()",
                        "self._signal_real3d('show')",
                        "self._signal_real3d('hide')",
                        "def start_microphone(self):",
                        "def _poll_mic_events(self):",
                        "def _poll_real3d_mode(self):",
                        "def background_update_check(self, manual=False):",
                        "def _restart_when_safe(self):",
                        "if self.minimized and not getattr(self,'_three_d_active',False):"):
        assert requirement in code,requirement
    # Extract and execute tested methods with a mock host (no live microphone).
    syntax=ast.parse(code)
    clazz=next(x for x in syntax.body if isinstance(x,ast.ClassDef) and x.name=='RobotApp')
    chosen={'_signal_real3d','_start_default_3d','open_editor','minimize','restore'}
    methods=[x for x in clazz.body if isinstance(x,ast.FunctionDef) and x.name in chosen]
    isolated=ast.Module(body=[ast.ClassDef(name='RobotUnit',bases=[],keywords=[],body=methods,
         decorator_list=[])],type_ignores=[])
    ast.fix_missing_locations(isolated)
    fake={'tk':SimpleNamespace(TclError=Exception)}
    exec(compile(isolated,'test_methods.py','exec'),fake)
    with tempfile.TemporaryDirectory() as td:
        signal=Path(td)/'voice.cmd'
        actions=[]
        class Store:
            settings={}
            def setting(self,k,v):self.settings[k]=v
        class FakeRoot:
            def after(self,ms,cb):actions.append(('after',ms,cb))
        host=SimpleNamespace(root=FakeRoot(),store=Store(),editor=None,minimized=True,
             _three_d_active=True,_three_d_signal=signal)
        host._signal_real3d=MethodType(fake['RobotUnit']._signal_real3d,host)
        host.minimize=MethodType(fake['RobotUnit'].minimize,host)
        host.restore=MethodType(fake['RobotUnit'].restore,host)
        host.minimize()
        assert signal.read_text('utf8')=='hide'
        host.restore()
        assert signal.read_text('utf8')=='show'
        def fake_editor_open():actions.append(('studio_open',))
        class EditorFake:
            def __init__(self,h):fake_editor_open()
        fake['Editor']=EditorFake
        host.open_editor=MethodType(fake['RobotUnit'].open_editor,host)
        host.open_editor()
        assert ('studio_open',) in actions
        assert signal.read_text('utf8')=='show'
        # Default boot must open 3D; fallback mode must remain classic.
        host.open_real3d_preview=lambda:actions.append(('start_3d',))
        host._start_default_3d=MethodType(fake['RobotUnit']._start_default_3d,host)
        host._start_default_3d()
        assert ('start_3d',) in actions
        actions.clear()
        host.store.setting('robot_visual_mode','classic')
        host._start_default_3d()
        assert ('start_3d',) not in actions
print('PASS: Close voice hides cream orb, Open voice restores 3D, Studio does not switch Classic, 3D default + Classic fallback')
