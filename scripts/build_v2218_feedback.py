#!/usr/bin/env python3
"""Add expressive Godot feedback to the pinned v2.2.17 updater package."""
from pathlib import Path
import hashlib
import json
import sys
import zipfile

BASE_SHA256 = 'a2c523e305f2c5413aed16bde1a636a428d15be33c7b319292f02dd0c434afab'


def patch_app(code):
    before = 'self.root.after(250,self._poll_mic_events)'
    if code.count(before) != 2:
        raise ValueError('Unexpected microphone polling anchors')
    code = code.replace(before, 'self.root.after(50,self._poll_mic_events)')
    before = """        try:signal.write_text(command,encoding='utf-8')
        except OSError:pass"""
    after = """        # Publish a complete command atomically for the fast Godot poller.
        pending=signal.with_suffix('.tmp')
        try:
            pending.write_text(command,encoding='utf-8')
            pending.replace(signal)
        except OSError:
            try:pending.unlink(missing_ok=True)
            except OSError:pass"""
    if code.count(before) != 1:
        raise ValueError('Unexpected voice signal anchor')
    code = code.replace(before, after)
    compile(code, 'robot_app.py', 'exec')
    return code


def build(source, pack, output):
    source, pack, output = map(Path, (source, pack, output))
    if hashlib.sha256(source.read_bytes()).hexdigest() != BASE_SHA256:
        raise ValueError('Expected the exact released v2.2.17 ZIP')
    pck = pack.read_bytes()
    if not pck.startswith(b'GDPC') or len(pck) < 1000:
        raise ValueError('Expected an exported Godot resource pack')
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(source) as old, zipfile.ZipFile(
            output, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=7) as new:
        if old.testzip():
            raise ValueError('Corrupt baseline ZIP')
        names = old.namelist()
        for item in old.infolist():
            data = old.read(item)
            if item.filename == 'app/robot_app.py':
                data = patch_app(data.decode('utf-8')).encode('utf-8')
            elif item.filename == 'app/robot_core.py':
                text = data.decode('utf-8')
                before = "APP_VERSION = '2.2.17'"
                if text.count(before) != 1:
                    raise ValueError('Unexpected base version')
                data = text.replace(before, "APP_VERSION = '2.2.18'").encode('utf-8')
            elif item.filename == 'app/visual3d/MuhammadRobot3D.pck':
                data = pck
            new.writestr(item, data)
    with zipfile.ZipFile(output) as z:
        if z.testzip() or z.namelist() != names:
            raise ValueError('Unexpected archive layout')
        if (len(names) > 100 or sum(i.file_size for i in z.infolist()) > 120_000_000
                or output.stat().st_size > 80_000_000):
            raise ValueError('Update exceeds existing device limits')
    manifest = {'version': '2.2.18', 'zip': output.name,
                'sha256': hashlib.sha256(output.read_bytes()).hexdigest()}
    (output.parent / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print('PASS: v2.2.18 package built; existing Windows engine and user-data layout retained')


if __name__ == '__main__':
    if len(sys.argv) != 4:
        raise SystemExit('build_v2218_feedback.py baseline.zip new.pck output.zip')
    build(*sys.argv[1:])
