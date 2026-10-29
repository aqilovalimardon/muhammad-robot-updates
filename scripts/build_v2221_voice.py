#!/usr/bin/env python3
"""Package v2.2.21: recover voice commands and add dizzy spiral eyes."""
import ast
import hashlib
import json
from pathlib import Path
import sys
import zipfile

BASE_SHA256 = '924dc947c6fdba05e3f799929d367898a5609a61ebdfb8e9d5f0c4f84322cc2d'


def patch_app(code):
    anchor='        self.mic_debug_window=None\n'
    if code.count(anchor)!=1:raise ValueError('Unexpected microphone initialization')
    code=code.replace(anchor,anchor+"        self._mic_requested=False\n        self._mic_generation=0\n        self._mic_retry_at=0.0\n        self._mic_retry_count=0\n")
    for name in ('restart','exit'):
        anchor=f'    def {name}(self):\n'
        if code.count(anchor)!=1:raise ValueError('Unexpected shutdown method')
        code=code.replace(anchor,anchor+'        self._mic_requested=False\n        self._mic_generation=getattr(self,"_mic_generation",0)+1\n')
    root=Path(__file__).resolve().parents[1]/'runtime'
    voice=(root/'host_voice.py').read_text(encoding='utf-8')
    host=(root/'host_microphone.py').read_text(encoding='utf-8')
    old=ast.parse(code)
    old_voice=next(n for n in old.body if isinstance(n,ast.ClassDef) and n.name=='Voice')
    new_voice=next(n for n in ast.parse(voice).body if isinstance(n,ast.ClassDef) and n.name=='Voice')
    edits=[(old_voice.lineno-1,old_voice.end_lineno,ast.get_source_segment(voice,new_voice)+'\n')]
    target=next(n for n in old.body if isinstance(n,ast.ClassDef) and n.name=='RobotApp')
    overrides=next(n for n in ast.parse(host).body if isinstance(n,ast.ClassDef))
    methods={n.name:n for n in target.body if isinstance(n,ast.FunctionDef)}
    lines=host.splitlines(keepends=True)
    additions=[]
    for method in overrides.body:
        if not isinstance(method,ast.FunctionDef):continue
        replacement=''.join(lines[method.lineno-1:method.end_lineno])
        previous=methods.get(method.name)
        if previous:edits.append((previous.lineno-1,previous.end_lineno,replacement))
        else:additions.append('\n'+replacement)
    edits.append((target.end_lineno,target.end_lineno,''.join(additions)))
    lines=code.splitlines(keepends=True)
    for start,end,text in sorted(edits,reverse=True):lines[start:end]=[text]
    code=''.join(lines)
    compile(code,'robot_app.py','exec')
    return code


def build(source, pack, output):
    source, pack, output = map(Path, (source, pack, output))
    if hashlib.sha256(source.read_bytes()).hexdigest() != BASE_SHA256:
        raise ValueError('Expected exact official v2.2.20 ZIP')
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
            if item.filename == 'app/robot_app.py':
                data = patch_app(data.decode('utf-8')).encode('utf-8')
            elif item.filename in ('app/voice_commands.py', 'app/windows_speech.py'):
                data = (Path(__file__).resolve().parents[1] / 'runtime' / Path(item.filename).name).read_bytes()
            elif item.filename == 'app/robot_core.py':
                code = data.decode('utf-8')
                if code.count("APP_VERSION = '2.2.20'") != 1:
                    raise ValueError('Bad base version')
                data = code.replace("APP_VERSION = '2.2.20'", "APP_VERSION = '2.2.21'").encode('utf-8')
            elif item.filename == 'app/visual3d/MuhammadRobot3D.pck':
                data = pck
            new.writestr(item, data)
    with zipfile.ZipFile(output) as z:
        if z.testzip() or z.namelist() != names:
            raise ValueError('Unexpected ZIP layout')
        if len(names) > 100 or sum(i.file_size for i in z.infolist()) > 120_000_000 or output.stat().st_size > 80_000_000:
            raise ValueError('Existing updater caps exceeded')
    manifest = {'version': '2.2.21', 'zip': output.name, 'sha256': hashlib.sha256(output.read_bytes()).hexdigest()}
    (output.parent / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print('PASS: v2.2.21 package built; voice recovery, bounded speech, dizzy eyes; EXE and user files preserved')


if __name__ == '__main__':
    build(*sys.argv[1:])
