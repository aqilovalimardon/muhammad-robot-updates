#!/usr/bin/env python3
"""Gate v2.2.15: require exact on-device updater safety rules AND old app preservation."""
from pathlib import Path
import ast,hashlib,json,re,sys,zipfile

old=Path(sys.argv[1]);built=Path(sys.argv[2])
manifest=json.loads((built.parent/'manifest.json').read_text('utf8'))
with zipfile.ZipFile(old) as z:
    source=z.read('app/robot_core.py').decode('utf8')
    main=z.read('app/robot_app.py').decode('utf8')
    paths=z.namelist()
tree=ast.parse(source)
fns=[x for x in tree.body if isinstance(x,ast.FunctionDef)
     and x.name in ('inspect_release','version_tuple')]
err=ast.ClassDef(name='UpdateError',bases=[ast.Name(id='Exception',ctx=ast.Load())],
                 keywords=[],body=[ast.Pass()],decorator_list=[])
mod=ast.Module(body=[err]+fns,type_ignores=[])
ast.fix_missing_locations(mod)
env={'hashlib':hashlib,'Path':Path,'zipfile':zipfile,'re':re,
     'VERSION_RE':re.compile(r'^\d+\.\d+\.\d+$')}
exec(compile(mod,'installed_updater.py','exec'),env)
assert env['inspect_release'](manifest,built) is True
print('PASS: exact existing on-device ZIP security validator accepts v2.2.15')
with zipfile.ZipFile(old) as before,zipfile.ZipFile(built) as after:
    assert after.testzip() is None
    names=after.namelist()
    assert len(names)==len(paths)+2 and len(names)<=100
    added=set(names)-set(paths)
    assert added=={'app/visual3d/MuhammadRobot3D.exe','app/visual3d/MuhammadRobot3D.pck'}
    for name in paths:
        if name not in ('app/robot_app.py','app/robot_core.py'):
            assert after.read(name)==before.read(name),('Unexpected change',name)
    app=after.read('app/robot_app.py').decode('utf8')
    for marker in ('def open_real3d_preview(self):','Try 3D robot (beta)',
                   'def open_editor(self):','def quick_run(self):',
                   'def background_update_check(self, manual=False):',
                   'def start_microphone(self):','def minimize(self):',
                   'def toggle_aqua_menu(self):','def switch_robot_look(self):'):
        assert marker in app,marker
    assert "APP_VERSION = '2.2.15'" in after.read('app/robot_core.py').decode('utf8')
    assert after.read('app/visual3d/MuhammadRobot3D.exe')[:2]==b'MZ'
    assert len(after.read('app/visual3d/MuhammadRobot3D.pck'))>100
    assert 'Your current Python robot stays working.' in app
print('PASS: 3D EXE automatically packaged, opt-in UI, old voice/Python editor unchanged')
