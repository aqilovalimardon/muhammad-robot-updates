#!/usr/bin/env python3
"""Build Muhammad Robot v2.2.6 from pinned v2.2.5 ZIP.

Adds a fifth belly control (minimize) alongside Edit/Run/Lesson/Pin.
Leaves voice, orb restore, lessons, persistent storage and updater untouched.
"""
import hashlib, json, sys, zipfile
from pathlib import Path

SOURCE_SHA = 'fe0b4e140c384fc9d763e316e2abb4b22ecd7e209ea516d2869d9b805d579af6'
OLD_BUTTONS = """        for idx,(x,symbol,hint,fn) in enumerate([
            (84,'✎','Edit Python',self.open_editor),
            (104,'▶','Run code',self.quick_run),
            (124,'▢','Python lesson',self.learn),
            (144,'♧','Always on top',self.toggle_pin)]):
"""
NEW_BUTTONS = """        for idx,(x,symbol,hint,fn) in enumerate([
            (74,'✎','Edit Python',self.open_editor),
            (94,'▶','Run code',self.quick_run),
            (114,'▢','Python lesson',self.learn),
            (134,'♧','Always on top',self.toggle_pin),
            (154,'−','Hide robot',self.minimize)]):
"""
def main(src,out):
    src=Path(src); out=Path(out)
    if hashlib.sha256(src.read_bytes()).hexdigest()!=SOURCE_SHA:
        raise ValueError('Expected original v2.2.5 ZIP checksum')
    out.parent.mkdir(parents=True,exist_ok=True)
    changed=[]
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(out,'w') as zout:
        if zin.testzip() is not None:
            raise ValueError('Source ZIP corrupt')
        names=zin.namelist()
        if len(set(names))!=len(names) or any(not n.startswith('app/') or '..' in Path(n).parts for n in names):
            raise ValueError('Unexpected source ZIP contents')
        for member in zin.infolist():
            raw=zin.read(member.filename)
            if member.filename=='app/robot_app.py':
                code=raw.decode('utf-8')
                if code.count(OLD_BUTTONS)!=1:
                    raise ValueError('Cannot find unique old button row')
                assert code.count('    def minimize(self):')==1
                code=code.replace(OLD_BUTTONS,NEW_BUTTONS)
                compile(code,member.filename,'exec')
                raw=code.encode('utf-8')
                changed.append(member.filename)
            elif member.filename=='app/robot_core.py':
                code=raw.decode('utf-8')
                old="APP_VERSION = '2.2.5'"
                if code.count(old)!=1:raise ValueError('Unexpected version')
                code=code.replace(old,"APP_VERSION = '2.2.6'")
                compile(code,member.filename,'exec')
                raw=code.encode('utf-8')
                changed.append(member.filename)
            zout.writestr(member,raw)
    if sorted(changed)!=['app/robot_app.py','app/robot_core.py']:
        raise ValueError('Incorrect files patched')
    with zipfile.ZipFile(out) as zin:
        assert zin.testzip() is None
        assert zin.namelist()==names
        patched=zin.read('app/robot_app.py').decode('utf-8')
        assert patched.count("'Hide robot',self.minimize")==1
        assert '_orb_track_eyes' in patched
    mf={'version':'2.2.6','zip':out.name,'sha256':hashlib.sha256(out.read_bytes()).hexdigest()}
    (out.parent/'manifest.json').write_text(json.dumps(mf,indent=2)+'\n',encoding='utf-8')
    print('PASS',json.dumps(mf))
if __name__=='__main__':
    if len(sys.argv)!=3:raise SystemExit('Usage: build_v226.py source.zip out.zip')
    main(sys.argv[1],sys.argv[2])
