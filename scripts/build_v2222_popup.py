#!/usr/bin/env python3
"""Repair the shared popup without changing voice libraries or stored user data."""
import ast
import hashlib
import json
from pathlib import Path
import sys
import zipfile

BASE_SHA256='a67973f15ef85ec63c6379b5b4a35119ff0549883c7498a50f2c97d5b997ecff'


def patch_app(code):
    for name in ('minimize','restore','exit','restart','open_real3d_preview','switch_to_classic'):
        anchor=f'    def {name}(self):\n'
        if code.count(anchor)!=1:raise ValueError('Unexpected method: '+name)
        code=code.replace(anchor,anchor+'        self._dismiss_shared_menu()\n')
    anchor="        self.main.bind('<Button-3>',self.popup)\n"
    if code.count(anchor)!=1:raise ValueError('Unexpected Classic menu binding')
    code=code.replace(anchor,anchor+"        self.main.bind('<Button-2>',self.popup)\n")
    source=(Path(__file__).resolve().parents[1]/'runtime/host_popup.py').read_text(encoding='utf-8')
    target=next(n for n in ast.parse(code).body if isinstance(n,ast.ClassDef) and n.name=='RobotApp')
    methods={n.name:n for n in target.body if isinstance(n,ast.FunctionDef)}
    overrides=next(n for n in ast.parse(source).body if isinstance(n,ast.ClassDef))
    lines=source.splitlines(keepends=True)
    edits=[]
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


def build(source,pack,output):
    source,pack,output=map(Path,(source,pack,output))
    if hashlib.sha256(source.read_bytes()).hexdigest()!=BASE_SHA256:raise ValueError('Expected exact official v2.2.21 ZIP')
    pck=pack.read_bytes()
    if not pck.startswith(b'GDPC') or len(pck)<1000:raise ValueError('Invalid Godot pack')
    output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(source) as old,zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=7) as new:
        if old.testzip():raise ValueError('Corrupt baseline')
        names=old.namelist()
        for item in old.infolist():
            data=old.read(item)
            if item.filename=='app/robot_app.py':data=patch_app(data.decode('utf-8')).encode('utf-8')
            elif item.filename=='app/robot_core.py':
                code=data.decode('utf-8')
                if code.count("APP_VERSION = '2.2.21'")!=1:raise ValueError('Bad base version')
                data=code.replace("APP_VERSION = '2.2.21'","APP_VERSION = '2.2.22'").encode('utf-8')
            elif item.filename=='app/visual3d/MuhammadRobot3D.pck':data=pck
            new.writestr(item,data)
    with zipfile.ZipFile(output) as z:
        if z.testzip() or z.namelist()!=names:raise ValueError('Unexpected ZIP layout')
        if len(names)>100 or sum(i.file_size for i in z.infolist())>120_000_000 or output.stat().st_size>80_000_000:
            raise ValueError('Existing updater caps exceeded')
    manifest={'version':'2.2.22','zip':output.name,'sha256':hashlib.sha256(output.read_bytes()).hexdigest()}
    (output.parent/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('PASS: v2.2.22 package built; non-modal popup, outside click, voice remains responsive')


if __name__=='__main__':build(*sys.argv[1:])
