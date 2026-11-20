"""Upgrade a populated v2.2.22 install, then exercise the shipped 3D-only host."""
import argparse
import ast
from contextlib import ExitStack
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import traceback
from types import SimpleNamespace
from unittest.mock import patch
import zipfile

from build_v2223_plush import APP, CORE, FILES, PACK, VERSION
from test_v2221_voice import load_commands, make_host, test_audio_stream, test_recognition_tools, test_recovery, test_speech
from test_v2222_popup import popup_checks, pump


def upgrade(baseline, archive, root, motion=False):
    previous, version = ('2.2.23','2.2.24') if motion else ('2.2.22',VERSION)
    manifest = json.loads((archive.parent / 'manifest.json').read_text())
    assert manifest['version'] == version and manifest['zip'] == archive.name
    with zipfile.ZipFile(baseline) as old, zipfile.ZipFile(archive) as new:
        assert new.testzip() is None and set(new.namelist()) == FILES
        changed = {APP, CORE, PACK}
        if motion:
            voice = 'app/voice_commands.py'
            assert new.read(voice) != old.read(voice)
            assert new.read(voice) == (Path(__file__).resolve().parents[1]/'runtime/voice_commands.py').read_bytes()
            changed.add(voice)
        for name in FILES - changed:
            assert new.read(name) == old.read(name), name
        assert new.read(CORE) == old.read(CORE).replace(f"'{previous}'".encode(), f"'{version}'".encode(), 1)
        assert old.read(PACK) != new.read(PACK)
        for name in FILES:
            if name.endswith('.py'):
                compile(new.read(name), name, 'exec')
        before = ast.parse(old.read(APP))
        after = ast.parse(new.read(APP))
        for name in ('Voice', 'Editor'):
            get_class = lambda tree: next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == name)
            assert ast.dump(get_class(before)) == ast.dump(get_class(after)), name
        old_core = {}
        exec(compile(old.read(CORE), CORE, 'exec'), old_core)
        old.extractall(root / 'versions' / previous)
        previous_app = old.read(APP)
    (root / 'current.json').write_text(json.dumps({'version': previous}))
    drive = root.parent / 'Drive'
    settings = dict(microphone_enabled=False, microphone_user_disabled=True, voice_recovery_v2221=True,
                    voice_intro_seen=True, robot_visual_mode='classic', last_script='my_lesson',
                    drive_folder=str(drive), custom_preference={'level': 3})
    settings_bytes = json.dumps(settings, ensure_ascii=False, indent=2).encode()
    source = b'robot.say("My saved lesson")\n'
    samples = {root / 'Data/settings.json': settings_bytes, root / 'Data/MyCode/my_lesson.py': source,
               root / 'Data/Backups/existing.py': b'# previous save\n',
               root / 'Voice/model/am/final.mdl': b'existing user-installed voice model',
               drive / 'Memory/settings.json': settings_bytes, drive / 'MyCode/my_lesson.py': source}
    for path, data in samples.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    for _ in range(2):
        assert old_core['install_release'](manifest, archive, root)
        assert json.loads((root / 'current.json').read_text()) == {'version': version, 'previous': previous}
        assert all(path.read_bytes() == data for path, data in samples.items())
    assert (root / 'versions' / previous / APP).read_bytes() == previous_app
    if not motion:
        assert (root / 'versions/2.2.22/app/assets_classic/frame_00.png').is_file()
    current_app = root / 'versions' / version / 'app'
    assert not (current_app / 'assets').exists() and not (current_app / 'assets_classic').exists()
    print('PASS: the deployed updater installs and retries without changing user settings, Studio files, Drive, voice model or rollback')
    return current_app, settings


def check_host(current_app, install, settings, godot):
    roaming = install.parent / 'Roaming'
    user_data = roaming / 'Godot/app_userdata' if sys.platform == 'win32' else roaming / 'godot/app_userdata'
    prefs = user_data / 'Muhammad Robot 3D/feedback.cfg'
    prefs.parent.mkdir(parents=True)
    prefs.write_text('[sounds]\n\nenabled=false\n\n[custom]\n\ntest="keep"\n')
    marker = install / 'launch_pending.json'
    marker.write_text('{}')
    launch = subprocess.Popen
    child = None
    failures = []

    def run_avatar(args, **kwargs):
        # The exported release uses the same resource pack on both platforms.
        # Use the headless display so Windows CI does not need a GPU driver.
        expected = current_app / 'visual3d/MuhammadRobot3D.exe'
        # Windows TEMP may use a short (8.3) alias for the resolved install path.
        assert Path(args[0]).samefile(expected), (args[0], expected)
        engine = [args[0]] if sys.platform == 'win32' else [godot, '--main-pack', str(Path(args[0]).with_suffix('.pck'))]
        return launch(engine + ['--headless'] + args[1:], **kwargs)

    with ExitStack() as stack:
        stack.enter_context(patch.dict(os.environ, {'LOCALAPPDATA': str(install.parent), 'APPDATA': str(roaming),
                                                   'XDG_DATA_HOME': str(roaming)}))
        stack.enter_context(patch.object(sys, 'path', [str(current_app)] + sys.path))
        module = importlib.import_module('robot_app')
        voice = SimpleNamespace(speaking=threading.Event(), speak=lambda msg: None)
        stack.enter_context(patch.object(module, 'Voice', return_value=voice))
        stack.enter_context(patch.object(module.RobotApp, 'background_update_check', lambda self: None))
        stack.enter_context(patch.object(module.RobotApp, '_offer_3d_retry', lambda self, why: failures.append(why)))
        stack.enter_context(patch.object(subprocess, 'Popen', run_avatar))
        app = module.RobotApp()
        app.root.report_callback_exception = lambda *exc: failures.append(''.join(traceback.format_exception(*exc)))
        try:
            pump(app.root, lambda: bool(failures) or not marker.exists(), 12)
            assert not failures, failures
            child = app.preview_3d_process
            assert child.poll() is None and app.root.state() == 'withdrawn'
            assert app.store.settings == settings and app.store.cloud == Path(settings['drive_folder'])
            assert not hasattr(app, 'switch_to_classic') and not hasattr(app, 'main')
            for value in ('true', 'false'):
                app._toggle_3d_effects()
                pump(app.root, lambda: ('enabled=' + value) in prefs.read_text(), 6)
                assert 'test="keep"' in prefs.read_text()
            app._three_d_bridge.write_text('editor')
            pump(app.root, lambda: app.editor is not None)
            assert app.editor.current == 'my_lesson'
            assert app.editor.code.get('1.0', 'end-1c') == 'robot.say("My saved lesson")\n'
            assert app._three_d_active and child.poll() is None
            app._three_d_bridge.write_text('menu')
            pump(app.root, lambda: getattr(app, '_shared_popup', None) is not None)
            app.minimize()
            assert app._shared_popup is None
            pump(app.root, lambda: not app._three_d_signal.exists())
            app.restore()
            pump(app.root, lambda: not app._three_d_signal.exists())
            assert not failures, failures
        finally:
            child = app.preview_3d_process
            app.exit()
            if child is not None:
                child.wait(timeout=8)
    assert not list((install / 'Data').glob('3d_*'))
    assert json.loads((install / 'Data/settings.json').read_text()) == settings
    print('PASS: 3D-only startup, saved sound Off, Studio and shared menu, Open/Close and joint exit')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('baseline', type=Path)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--ui', action='store_true')
    parser.add_argument('--motion', action='store_true', help='Test the v2.2.23 to v2.2.24 upgrade and motion vocabulary')
    parser.add_argument('--godot', type=Path, help='Linux Godot executable for the exported-pack host test')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as temp:
        folder = Path(temp)
        install = folder / 'MuhammadRobot'
        current_app, settings = upgrade(args.baseline, args.archive, install, args.motion)
        source = (current_app / 'robot_app.py').read_text(encoding='utf-8')
        commands = load_commands(args.archive)
        test_recognition_tools(commands)
        test_recovery(source, folder)
        test_speech(source, folder)
        test_audio_stream(commands, folder)
        if args.motion:
            check_motion_voice(commands, source, folder)
        if args.ui:
            popup_checks(args.baseline, args.archive, only_3d=True)
            if sys.platform != 'win32' and args.godot is None:
                parser.error('--ui on Linux requires --godot')
            check_host(current_app, install, settings, str(args.godot.resolve()) if args.godot else None)


def check_motion_voice(commands, source, folder):
    grammar = json.loads(commands.GRAMMAR)
    assert all(c+' robot' in grammar for c in ('hello','fly','stop','jump','close','open'))
    for c in ('fly','stop','jump'):
        assert commands.normalize_command(c.upper()+' robot!') == c
    for text in ('stop', 'the fly', 'jump rope', 'do not fly robot', 'robot'):
        assert commands.normalize_command(text) is None
    gate = commands.CommandGate()
    assert gate.accept('stop robot',False,1.0) is None
    assert gate.accept('stop robot',False,1.2) == 'stop'
    assert gate.accept('stop robot',True,1.45) is None
    for c in ('fly','jump'):
        assert gate.accept(c+' robot',False,2.0) is None
        assert gate.accept(c+' robot',False,2.3) is None
        assert gate.accept(c+' robot',True,2.5) == c
    h = make_host(source, folder)
    h._three_d_signal.unlink(missing_ok=True)
    h._enable_existing_mic()
    for c in ('fly','jump','stop','hello','close','open'):
        h.listener.events.put(('command', c))
    h._poll_mic_events()
    # Stop supersedes queued jumps and Close supersedes an unread wave.
    for expected in ('fly','stop','hide','show'):
        assert h._three_d_signal.read_text() == expected
        h._three_d_signal.unlink()
        h._poll_mic_events()
    assert not h._pending_3d and not h._three_d_signal.exists()
    print('PASS: six offline commands, immediate Stop, no duplicate jump and ordered 3D delivery')


if __name__ == '__main__':
    main()
