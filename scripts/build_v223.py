#!/usr/bin/env python3
"""Build 2.2.3 GitHub update fix from the previous published release."""
from pathlib import Path
import json, hashlib, zipfile, sys
src=Path(sys.argv[1]); target=Path(sys.argv[2]); target.parent.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(src,'r') as z, zipfile.ZipFile(target,'w') as out:
    assert 'app/robot_core.py' in z.namelist()
    for entry in z.infolist():
        data=z.read(entry.filename)
        if entry.filename == 'app/robot_core.py':
            core=data.decode('utf-8')
            patterns=[
                ("APP_VERSION = '2.2.2'", "APP_VERSION = '2.2.3'"),
                ('    def download(url,limit):', "    def download(url,limit,accept='application/octet-stream'):"),
                ("            'Accept':'application/octet-stream'})", "            'Accept':accept})"),
                ("rel=json.loads(download(api,750_000))", "rel=json.loads(download(api,750_000,accept='application/vnd.github+json'))"),
            ]
            for old,new in patterns:
                if core.count(old)!=1: raise RuntimeError('Unexpected release version or format: '+old)
                core=core.replace(old,new)
            compile(core,'robot_core.py','exec')
            data=core.encode('utf8')
        out.writestr(entry,data)
with zipfile.ZipFile(target) as z:
    assert z.testzip() is None
    assert b"accept='application/vnd.github+json'" in z.read('app/robot_core.py')
manifest={"version":"2.2.3","zip":target.name,"sha256":hashlib.sha256(target.read_bytes()).hexdigest()}
(target.parent/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8')
print(json.dumps(manifest))
