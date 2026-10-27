#!/usr/bin/env python3
"""Faithful A-style milky cream robot v2.2.8 from user-approved 3D reference.

Uses a small compressed reference art source, not procedural flat illustration.
The mascot is pre-rendered into 20 Windows color-keyed PNG frames. There is NO
new runtime library, image decoding load, GPU renderer or polling thread.
"""
from pathlib import Path
from PIL import Image
import base64, hashlib, io, json, math, sys, zipfile, zlib

SHA227='08f0e2dc4252d9aee195a708b70c7557eb637747bac1d83b633e6d40467e346c'
KEY=(255,0,254,0)
ASSET=Path(__file__).parent/'reference_A_cream_asset.txt'

def artwork():
    data=ASSET.read_text(encoding='ascii').splitlines()
    if len(data)!=2 or not data[0].startswith('/9j/'):
        raise ValueError('A style reference art was not correctly embedded')
    jpeg=base64.b64decode(data[0],validate=True)
    alpha_raw=zlib.decompress(base64.b64decode(data[1],validate=True))
    if len(alpha_raw)!=95*98:
        raise ValueError('Alpha mask length mismatch')
    rgb=Image.open(io.BytesIO(jpeg))
    rgb.load()       # Image decoding must pass before release
    if rgb.size!=(190,196):
        raise ValueError('Invalid art dimensions')
    mask=Image.frombytes('L',(95,98),alpha_raw).resize((190,196),Image.Resampling.BICUBIC)
    pic=rgb.convert('RGBA')
    pic.putalpha(mask)
    if pic.getpixel((0,0))[3]>3:
        raise ValueError('Artwork has an opaque corner')
    return pic

def animation_frame(source,index):
    phase=2*math.pi*index/20
    # Floating offset at most one pixel; antenna waves two pixels at the tip.
    bob=round(math.sin(phase)*1.2)
    bend=math.sin(phase+0.25)
    out=Image.new('RGBA',(190,196),KEY)
    for y in range(196):
        shift=round(2.4*bend*max(0,(68-y)/68)) if y<68 else 0
        row=source.crop((0,y,190,y+1))
        out.alpha_composite(row,(shift,y+bob)) if 0<=y+bob<196 else None
    # Crucial Windows -transparentcolor fix: an invisible source pixel must have
    # RGB #ff00fe (the app's configured transparency key), not black (0,0,0).
    pixels=out.load()
    for y in range(196):
        for x in range(190):
            r,g,b,a=pixels[x,y]
            if a<=3:
                pixels[x,y]=KEY
    buffer=io.BytesIO()
    out.save(buffer,format='PNG',optimize=True)
    return buffer.getvalue()

OLD_ROW="        for idx,(x,symbol,hint,fn) in enumerate([\n            (95,'◉','Open aqua menu',self.toggle_aqua_menu)]):"
# Existing bubble-menu functions and their callbacks remain untouched.
NEW_ROW="        for idx,(x,symbol,hint,fn) in enumerate([\n            (95,'◉','Open aqua menu',self.toggle_aqua_menu)]):"
def app_update(code):
    if code.count(OLD_ROW)!=1:raise ValueError('Unexpected v2.2.7 belly button code')
    # Keep working tkinter callback; restyle black square to cream/glass dot.
    old="btn=tk.Button(self.root,text=symbol,command=fn,bg='#071e39',fg='#8beaff',"
    new="btn=tk.Button(self.root,text=symbol,command=fn,bg='#dbeff4',fg='#278bbe',"
    if code.count(old)!=1:raise ValueError('Unexpected button style')
    code=code.replace(old,new)
    old2="activebackground='#164b77',activeforeground='white'"
    new2="activebackground='#c2eaf8',activeforeground='#24699d'"
    if code.count(old2)!=1:raise ValueError('Unexpected highlight style')
    code=code.replace(old2,new2)
    compile(code,'robot_app.py','exec')
    return code

def build(src,out):
    if hashlib.sha256(Path(src).read_bytes()).hexdigest()!=SHA227:
        raise ValueError('Expected exact GitHub v2.2.7 baseline')
    ref=artwork()
    out=Path(out);out.parent.mkdir(parents=True,exist_ok=True)
    frames={f'app/assets/frame_{i:02d}.png':animation_frame(ref,i) for i in range(20)}
    updated=[]
    with zipfile.ZipFile(src) as zin,zipfile.ZipFile(out,'w') as zout:
        names=zin.namelist()
        if zin.testzip() is not None or len(set(names))!=len(names):
            raise ValueError('Baseline damaged')
        for entry in zin.infolist():
            data=zin.read(entry.filename)
            if entry.filename in frames:
                data=frames[entry.filename];updated.append(entry.filename)
            elif entry.filename=='app/robot_app.py':
                data=app_update(data.decode('utf-8')).encode('utf-8')
                updated.append(entry.filename)
            elif entry.filename=='app/robot_core.py':
                code=data.decode('utf-8')
                old="APP_VERSION = '2.2.7'"
                if code.count(old)!=1:raise ValueError('Unexpected baseline version')
                code=code.replace(old,"APP_VERSION = '2.2.8'")
                compile(code,'robot_core.py','exec')
                data=code.encode('utf-8')
                updated.append(entry.filename)
            zout.writestr(entry,data)
    if len(updated)!=22:raise ValueError('Wrong files changed')
    with zipfile.ZipFile(out) as z:
        if z.testzip() is not None or z.namelist()!=names:raise ValueError('Invalid result ZIP')
        img=Image.open(io.BytesIO(z.read('app/assets/frame_00.png')))
        if img.mode!='RGBA' or img.getpixel((0,0))!=KEY:
            raise ValueError('Transparent key incorrect: magenta rectangle risk')
    manifest={'version':'2.2.8','zip':out.name,
              'sha256':hashlib.sha256(out.read_bytes()).hexdigest()}
    (out.parent/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print('PASS: cream model + Windows transparency + 20 light frames',json.dumps(manifest))
if __name__=='__main__':
    build(sys.argv[1],sys.argv[2])
