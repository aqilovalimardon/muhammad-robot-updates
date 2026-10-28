#!/usr/bin/env python3
"""Run the installed validator and host methods against the exact new ZIP."""
import ast
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile
from types import SimpleNamespace
import zipfile


def selected_class(source, name, methods, scope):
    tree = ast.parse(source)
    original = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == name)
    nodes = [n for n in original.body if isinstance(n, ast.FunctionDef) and n.name in methods]
    assert {n.name for n in nodes} == methods
    module = ast.Module(body=[ast.ClassDef(name=name, bases=[], keywords=[],
                        body=nodes, decorator_list=[])], type_ignores=[])
    ast.fix_missing_locations(module)
    exec(compile(module, 'real_host_methods.py', 'exec'), scope)
    return scope[name]


def main(baseline, output):
    baseline, output = Path(baseline), Path(output)
    manifest = json.loads((output.parent / 'manifest.json').read_text())
    with zipfile.ZipFile(baseline) as old, zipfile.ZipFile(output) as new:
        assert new.testzip() is None and new.namelist() == old.namelist()
        changed = {n for n in old.namelist() if old.read(n) != new.read(n)}
        assert changed == {'app/robot_app.py', 'app/robot_core.py',
                           'app/visual3d/MuhammadRobot3D.pck'}, changed
        app = new.read('app/robot_app.py').decode('utf-8')
        core = new.read('app/robot_core.py').decode('utf-8')
        assert "APP_VERSION = '2.2.19'" in core
        for item in new.namelist():
            if item.endswith('.py'):
                compile(new.read(item), item, 'exec')
        # Execute the validator shipped on the device, not a new approximation.
        tree = ast.parse(old.read('app/robot_core.py').decode('utf-8'))
        nodes = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))
                 and n.name in {'version_tuple', 'inspect_release', 'UpdateError'}]
        scope = dict(hashlib=hashlib, zipfile=zipfile, Path=Path, re=re,
                     VERSION_RE=re.compile(r'^\d+\.\d+\.\d+$'))
        module = ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[]))
        exec(compile(module, 'installed_validator.py', 'exec'), scope)
        assert scope['inspect_release'](manifest, output)
    actions = []

    class Store:
        def __init__(self): self.settings = {}
        def setting(self, key, value): self.settings[key] = value

    class Process:
        ended = False
        def poll(self): return 0 if self.ended else None
        def terminate(self): self.ended = True

    class Editor:
        def __init__(self, host): actions.append('editor')

    scope = {'tk': SimpleNamespace(TclError=Exception), 'Editor': Editor}
    methods = {'_signal_real3d', '_start_default_3d', 'open_editor', 'minimize',
               'restore', '_poll_real3d_mode', '_stop_real3d', 'switch_to_classic', '_build_menu', '_show_shared_menu', 'popup', '_toggle_3d_effects', '_cycle_3d_emotion', 'exit'}
    Robot = selected_class(app, 'RobotApp', methods, scope)
    with tempfile.TemporaryDirectory() as temporary:
        host = Robot()
        host.root = SimpleNamespace(after=lambda ms, cb: actions.append(('after', ms)))
        host.store = Store()
        host.editor = None
        host.orb = None
        host.minimized = True
        host._three_d_active = True
        host._three_d_return_editor = False
        host._three_d_signal = Path(temporary) / 'voice.cmd'
        host._three_d_bridge = Path(temporary) / 'bridge.cmd'
        host.preview_3d_process = Process()
        host.minimize()
        assert host._three_d_signal.read_text() == 'hide'
        host.restore()
        assert host._three_d_signal.read_text() == 'show'
        assert not host._three_d_signal.with_suffix('.tmp').exists()
        host.open_real3d_preview = lambda: actions.append('3d')
        host._start_default_3d()
        assert '3d' in actions
        actions.clear()
        host.store.setting('robot_visual_mode', 'classic')
        host._start_default_3d()
        assert '3d' in actions and host.store.settings['robot_visual_mode'] == '3d'
        host._show_shared_menu=lambda: actions.append('shared_menu')
        callbacks=[]
        host.root.after=lambda ms,cb: callbacks.append((ms,cb))
        host._three_d_bridge.write_text('menu')
        host._poll_real3d_mode()
        assert callbacks[0][0]==0 and host._three_d_active
        callbacks[0][1]()
        assert 'shared_menu' in actions and not host.preview_3d_process.ended
        host._three_d_bridge.write_text('editor')
        host._poll_real3d_mode()
        assert 'editor' in actions and host._three_d_active
        assert not host.preview_3d_process.ended
        host._three_d_bridge.write_text('classic')
        host.restore = lambda: actions.append('restore_classic')
        process = host.preview_3d_process
        host._poll_real3d_mode()
        assert process.ended and not host._three_d_active
        assert 'restore_classic' in actions and host.store.settings['robot_visual_mode'] == '3d'
        process=Process()
        host.preview_3d_process=process
        host._three_d_active=True
        host.listener=None
        host.editor=None
        host.root.destroy=lambda:actions.append('root_destroyed')
        host.exit()
        assert process.ended and 'root_destroyed' in actions, 'Exit must stop both avatars'
    assert 'self.root.after(100,self._start_default_3d)' in app
    assert app.count('self.root.after(50,self._poll_mic_events)') == 2
    print('PASS: deployed updater, SHA256, exact ZIP diff, Python compile, atomic commands, shared menu, unconditional 3D startup, Studio stays 3D, temporary Classic fallback')


if __name__ == '__main__':
    main(*sys.argv[1:])
