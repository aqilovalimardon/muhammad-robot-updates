#!/usr/bin/env python3
"""Regression checks for v2.2.8 cream robot appearance without extra libraries."""
from pathlib import Path
from PIL import Image
import io,sys,zipfile
zpath=Path(sys.argv[1])
with zipfile.ZipFile(zpath) as z:
    assert z.testzip() is None
    names=z.namelist()
    assets=[n for n in names if n.startswith('app/assets/frame_') and n.endswith('.png')]
    assert len(assets)==20
    versions=z.read('app/robot_core.py').decode('utf-8')
    assert "APP_VERSION = '2.2.8'" in versions
    app=z.read('app/robot_app.py').decode('utf-8')
    assert "TRANSPARENT='#ff00fe'" in app
    assert "'-transparentcolor',TRANSPARENT" in app
    for needed in ['def toggle_aqua_menu','def _show_aqua_menu',
                   'def minimize','def restore','def background_update_check',
                   'def open_editor','def start_microphone','def quick_run',
                   'def restart','def show_version']:
        assert needed in app,needed
    assert 'self.toggle_aqua_menu' in app
    assert 'self.root.after(70,self.animate)' in app
    assert "window=btn,width=23,height=23" in app
    images=[Image.open(io.BytesIO(z.read(n))).convert('RGBA') for n in sorted(assets)]
    for img in images:
        assert img.size==(190,196)
        assert img.getpixel((0,0))==(255,0,254,0)
        # The artwork is creamy, not flat electric pink or neon blue.
        px=[img.getpixel((x,y)) for x,y in [(95,113),(83,125),(105,130),(73,151)]]
        assert any(r>160 and g>140 and b>110 and a>180 for r,g,b,a in px),px
        magenta=sum(1 for r,g,b,a in img.getdata() if r>220 and g<60 and b>220 and a>100)
        assert magenta==0,('Visible pink leaked into the artwork',magenta)
        opaque=sum(1 for r,g,b,a in img.getdata() if a>180)
        assert opaque>6000 and opaque<30000,opaque
    assert images[0].tobytes()!=images[5].tobytes(),'Antenna/bob animation absent'
print('PASS: 3D cream reference, transparent color key, no visible magenta, 20 frames, existing commands untouched')
