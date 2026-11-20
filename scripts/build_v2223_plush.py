"""Build the 3D-only update from the deployed v2.2.22 Windows runtime."""
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile


VERSION = '2.2.23'
BASE_SHA256 = '890f49efef35c1b92cc68fea004af9fdf7a550c3dc99f6fe2360e6204757d2c3'
APP = 'app/robot_app.py'
CORE = 'app/robot_core.py'
PACK = 'app/visual3d/MuhammadRobot3D.pck'
FILES = {APP, CORE, PACK, 'app/voice_commands.py', 'app/windows_speech.py',
         'app/visual3d/MuhammadRobot3D.exe'}


def build(baseline, resource_pack, output, *, previous='2.2.22', version=VERSION,
          base_sha=BASE_SHA256, update_voice=False):
    baseline, resource_pack, output = map(Path, (baseline, resource_pack, output))
    if hashlib.sha256(baseline.read_bytes()).hexdigest() != base_sha:
        raise ValueError(f'Expected the official v{previous} package')
    if output.name != f'MuhammadRobot-{version}.zip':
        raise ValueError('Unexpected release filename')
    pack = resource_pack.read_bytes()
    if not pack.startswith(b'GDPC') or len(pack) < 1000:
        raise ValueError('Invalid Godot resource pack')
    runtime = Path(__file__).resolve().parents[1] / 'runtime'
    app = (runtime / 'robot_app.py').read_bytes()
    compile(app, APP, 'exec')
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(baseline) as old:
        retained = [item for item in old.infolist()
                    if not re.fullmatch(r'app/assets(?:_classic)?/frame_\d+\.png', item.filename)]
        if {item.filename for item in retained} != FILES or len(retained) != len(FILES):
            raise ValueError('Unexpected runtime layout')
        core = old.read(CORE)
        version_line = f"APP_VERSION = '{previous}'".encode()
        if core.count(version_line) != 1:
            raise ValueError('Unexpected runtime version')
        replacements = {APP: app, CORE: core.replace(version_line, f"APP_VERSION = '{version}'".encode()),
                        PACK: pack}
        if update_voice:
            voice = (runtime / 'voice_commands.py').read_bytes()
            compile(voice, 'voice_commands.py', 'exec')
            replacements['app/voice_commands.py'] = voice
        with zipfile.ZipFile(output, 'w') as new:
            for item in retained:
                data = replacements[item.filename] if item.filename in replacements else old.read(item)
                new.writestr(item, data)
    manifest = {'version': version, 'zip': output.name, 'sha256': hashlib.sha256(output.read_bytes()).hexdigest()}
    (output.parent / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(f'Built {output.name} with {len(FILES)} program files')


if __name__ == '__main__':
    build(*sys.argv[1:])
