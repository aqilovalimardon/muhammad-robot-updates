#!/usr/bin/env python3
"""Package v2.2.20 against the exact tested v2.2.19 release; keep the host intact."""
import hashlib
import json
from pathlib import Path
import sys
import zipfile

BASE_SHA256 = '0339b0c3eb82b9f33fc4a707863dfc0b6a3ac93deaab85a95ce9a38b6de83f56'


def build(source, pack, output):
    source, pack, output = map(Path, (source, pack, output))
    if hashlib.sha256(source.read_bytes()).hexdigest() != BASE_SHA256:
        raise ValueError('Expected exact official v2.2.19 ZIP')
    pck = pack.read_bytes()
    if not pck.startswith(b'GDPC') or len(pck) < 1000:
        raise ValueError('Invalid Godot pack')
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(source) as old, zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=7) as new:
        if old.testzip():
            raise ValueError('Corrupt baseline')
        names = old.namelist()
        for item in old.infolist():
            data = old.read(item)
            if item.filename == 'app/robot_core.py':
                code = data.decode('utf-8')
                if code.count("APP_VERSION = '2.2.19'") != 1:
                    raise ValueError('Bad base version')
                data = code.replace("APP_VERSION = '2.2.19'", "APP_VERSION = '2.2.20'").encode('utf-8')
            elif item.filename == 'app/visual3d/MuhammadRobot3D.pck':
                data = pck
            new.writestr(item, data)
    with zipfile.ZipFile(output) as z:
        if z.testzip() or z.namelist() != names:
            raise ValueError('Unexpected ZIP layout')
        if len(names) > 100 or sum(i.file_size for i in z.infolist()) > 120_000_000 or output.stat().st_size > 80_000_000:
            raise ValueError('Existing updater caps exceeded')
    manifest = {'version': '2.2.20', 'zip': output.name, 'sha256': hashlib.sha256(output.read_bytes()).hexdigest()}
    (output.parent / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print('PASS: v2.2.20 package built; host, EXE, voice and user settings unchanged')


if __name__ == '__main__':
    build(*sys.argv[1:])
