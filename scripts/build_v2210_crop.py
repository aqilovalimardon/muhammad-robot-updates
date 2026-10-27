#!/usr/bin/env python3
"""Critical bugfix v2.2.10: fix cropped image after 100x112 resize.

Root cause: app initializes sprite at (50,56) but animate() resets its center
to stale coordinates (95,98) 13 times/second. The camera cuts off 50% of mascot.
Patch ONLY this coordinate and APP_VERSION from verified GitHub Release v2.2.9.
"""
from pathlib import Path
import hashlib,json,sys,zipfile

PINNED='7746b31a031a156c3a970a16fd9d77de824c84f95184fc0839bee19619db7479'
OLD="self.main.coords(self.sprite,95,98)"
NEW="self.main.coords(self.sprite,self.win_width//2,self.win_height//2)"

def build(baseline,dest):
    baseline=Path(baseline);dest=Path(dest)
    if hashlib.sha256(baseline.read_bytes()).hexdigest()!=PINNED:
        raise ValueError('Source must equal verified v2.2.9 GitHub Release ZIP')
    dest.parent.mkdir(parents=True,exist_ok=True)
    modified=[]
    with zipfile.ZipFile(baseline) as zin,zipfile.ZipFile(dest,'w') as zout:
        if zin.testzip() is not None:raise ValueError('Bad baseline ZIP')
        names=zin.namelist()
        if len(names)!=len(set(names)):raise ValueError('Duplicate ZIP members')
        for entry in zin.infolist():
            contents=zin.read(entry.filename)
            if entry.filename=='app/robot_app.py':
                code=contents.decode('utf-8')
                if code.count(OLD)!=1 or "self.win_width=100;self.win_height=112" not in code:
                    raise ValueError('Unexpected robot app or incorrect prior size')
                code=code.replace(OLD,NEW)
                compile(code,'app/robot_app.py','exec')
                contents=code.encode('utf-8')
                modified.append(entry.filename)
            elif entry.filename=='app/robot_core.py':
                code=contents.decode('utf-8')
                version="APP_VERSION = '2.2.9'"
                if code.count(version)!=1:raise ValueError('Unexpected old APP_VERSION')
                code=code.replace(version,"APP_VERSION = '2.2.10'")
                compile(code,'app/robot_core.py','exec')
                contents=code.encode('utf-8')
                modified.append(entry.filename)
            zout.writestr(entry,contents)
    if sorted(modified)!=['app/robot_app.py','app/robot_core.py']:
        raise ValueError('Unexpected files patched: '+str(modified))
    with zipfile.ZipFile(dest) as z:
        if z.testzip() is not None or z.namelist()!=names:
            raise ValueError('Output corrupt or changed structure')
        for name in names:
            if name not in modified and z.read(name)!=zin.read(name):
                raise AssertionError('Unrelated file changed: '+name)
    mf={'version':'2.2.10','zip':dest.name,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()}
    (dest.parent/'manifest.json').write_text(json.dumps(mf,indent=2)+'\n',encoding='utf8')
    print('PASS: app animate center fixed, all sprites/code unchanged',json.dumps(mf))

if __name__=='__main__':
    if len(sys.argv)!=3:raise SystemExit('Usage: build_v2210_crop.py old.zip output.zip')
    build(sys.argv[1],sys.argv[2])
