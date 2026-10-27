#!/usr/bin/env python3
"""Patch verified v2.2.4 ZIP into v2.2.5 (only UI badge and version)."""
import hashlib
import json
import sys
import zipfile
from pathlib import Path

SHA224='77d14d64994f0e2bdb59bf7d8c53aaf27a5d42f0b9c795d3dbf3a266f52a97e7'

def build(baseline, output):
    baseline=Path(baseline)
    output=Path(output)
    if hashlib.sha256(baseline.read_bytes()).hexdigest()!=SHA224:
        raise ValueError('Baseline must be the verified published v2.2.4 ZIP')
    fragment=(Path(__file__).parent/'restore_badge_v225.txt').read_text(encoding='utf-8')
    assert fragment.startswith('    def _show_restore_orb(self):\n')
    assert '    def _orb_track_eyes(self):' in fragment
    output.parent.mkdir(parents=True,exist_ok=True)
    touched=[]
    with zipfile.ZipFile(baseline) as z,zipfile.ZipFile(output,'w') as out:
        if z.testzip() is not None:raise ValueError('Bad source ZIP')
        names=z.namelist()
        if len(set(names))!=len(names):raise ValueError('Duplicate paths')
        if names.count('app/robot_app.py')!=1 or names.count('app/robot_core.py')!=1:
            raise ValueError('Missing app source')
        if any(not name.startswith('app/') or '..' in Path(name).parts for name in names):
            raise ValueError('Unexpected app path')
        for info in z.infolist():
            contents=z.read(info.filename)
            if info.filename=='app/robot_app.py':
                code=contents.decode('utf-8')
                start=code.index('    def _show_restore_orb(self):\n')
                stop=code.index('    def restore(self):\n',start)
                old=code[start:stop]
                if old.count("b=tk.Button(self.orb,text='R'")!=1:
                    raise ValueError('Unsupported old badge implementation')
                code=code[:start]+fragment+code[stop:]
                compile(code,'robot_app.py','exec')
                contents=code.encode('utf-8')
                touched.append(info.filename)
            elif info.filename=='app/robot_core.py':
                code=contents.decode('utf-8')
                old="APP_VERSION = '2.2.4'"
                if code.count(old)!=1:raise ValueError('Incorrect source version')
                code=code.replace(old,"APP_VERSION = '2.2.5'")
                compile(code,'robot_core.py','exec')
                contents=code.encode('utf-8')
                touched.append(info.filename)
            out.writestr(info,contents)
    assert sorted(touched)==['app/robot_app.py','app/robot_core.py']
    with zipfile.ZipFile(output) as z:
        if z.testzip() is not None:raise ValueError('Invalid output ZIP')
        assert 'self._orb_track_eyes()' in z.read('app/robot_app.py').decode('utf-8')
    mf={'version':'2.2.5','zip':output.name,
        'sha256':hashlib.sha256(output.read_bytes()).hexdigest()}
    (output.parent/'manifest.json').write_text(json.dumps(mf,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(mf))

if __name__=='__main__':
    if len(sys.argv)!=3:raise SystemExit('build_v225.py source.zip destination.zip')
    build(sys.argv[1],sys.argv[2])
