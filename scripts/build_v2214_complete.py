#!/usr/bin/env python3
"""v2.2.14 stable whole-robot re-render.

From user-approved compact 84x108 original image (not patched v2.2.13 art).
Keep entire cream torso and original glossy visor. Animate the antenna from a
separate region. Eye movement is tiny and stays INSIDE original visor.
All 72 frames are RGB with exact magenta transparency KEY, NEVER blended.
The on-device ZIP has 84 entries and keeps the previous safety limit intact.
"""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFilter
import math,base64,hashlib,io,json,sys,zipfile

BASE_SHA='5d64d108566e79395af65327334da28dcaa4edc0638384a9f113e036b1e3b5c8'
W,H=100,112
KEY=(255,0,254)
MOODS=('center','left','right','up','down','blink','happy','tilt_left','tilt_right')
N=8

def approved_original():
    encoded=(Path(__file__).parent/'cream_front_small.webp.b64').read_text('ascii').strip()
    src=Image.open(io.BytesIO(base64.b64decode(encoded,validate=True))).convert('RGBA')
    if src.size!=(84,108):raise ValueError('Original artwork size mismatch')
    if src.getpixel((0,0))[3]!=0:raise ValueError('Original artwork is not transparent')
    return src

def build_frame(source,mood,j):
    angle=2*math.pi*j/N
    core=source.copy()
    # Detach only the tip/stalk ABOVE the furry head without touching eyes/torso.
    antenna=Image.new('RGBA',source.size)
    for y in range(0,25):
        for x in range(source.width):
            c=source.getpixel((x,y))
            if c[3]:
                antenna.putpixel((x,y),c)
                core.putpixel((x,y),(c[0],c[1],c[2],0))
    # Recombine head and swinging antenna in exact same 100x112 canvas.
    canvas=Image.new('RGBA',(W,H))
    canvas.alpha_composite(core,(8,3))
    upper=Image.new('RGBA',(W,H))
    upper.alpha_composite(antenna,(8,3))
    rotation=10*math.sin(angle)
    upper=upper.rotate(rotation,Image.Resampling.BICUBIC,center=(46,28))
    canvas.alpha_composite(upper)
    # Retain one face and two original eyes. Nudge real eye patches 1px
    # instead of painting any additional visor or new eyes on the body.
    offsets={'center':(0,0),'left':(-1,0),'right':(1,0),
             'up':(0,-1),'down':(0,1),'blink':(0,0),
             'happy':(0,0),'tilt_left':(-1,0),'tilt_right':(1,0)}
    ex,ey=offsets[mood]
    if ex or ey:
        before=canvas.copy()
        regions=((44,61,6,8),(68,60,6,8))
        mask=Image.new('L',(W,H),0)
        d=ImageDraw.Draw(mask)
        for x,y,rx,ry in regions:d.ellipse((x-rx,y-ry,x+rx,y+ry),fill=255)
        mask=mask.filter(ImageFilter.GaussianBlur(0.65))
        shade=Image.new('RGBA',(W,H),(7,11,35,255))
        canvas=Image.composite(shade,canvas,mask)
        copied=before.copy()
        copied.putalpha(mask)
        canvas.alpha_composite(copied,(ex,ey))
    # Reaction uses whole-body gentle 2-degree roll, no fragmentation.
    if mood=='tilt_left':
        canvas=canvas.rotate(2,Image.Resampling.BICUBIC,center=(50,69))
    elif mood=='tilt_right':
        canvas=canvas.rotate(-2,Image.Resampling.BICUBIC,center=(50,69))
    dy=round(1.0*math.sin(angle))
    lifted=Image.new('RGBA',(W,H))
    lifted.alpha_composite(canvas,(0,dy))
    # Opaque image: Windows color-key transparency is binary.
    # Keep original RGB instead of blending any pixel with magenta.
    rgb=lifted.convert('RGB').load()
    alpha=lifted.getchannel('A').load()
    result=Image.new('RGB',(W,H),KEY);out=result.load()
    for y in range(H):
        for x in range(W):
            if alpha[x,y]>=145:
                out[x,y]=rgb[x,y]
    buf=io.BytesIO();result.save(buf,'PNG',optimize=True)
    return buf.getvalue()

def build(source_zip,dest):
    source_zip=Path(source_zip);dest=Path(dest)
    if hashlib.sha256(source_zip.read_bytes()).hexdigest()!=BASE_SHA:
        raise ValueError('Expected immutable v2.2.13 baseline')
    original=approved_original()
    sprites={}
    for i,mood in enumerate(MOODS):
        for k in range(N):
            sprites[f'app/assets/frame_{i*N+k:03d}.png']=build_frame(original,mood,k)
    dest.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(source_zip) as src,zipfile.ZipFile(dest,'w',compression=zipfile.ZIP_DEFLATED) as out:
        if src.testzip() is not None or len(src.namelist())!=84:
            raise ValueError('Source ZIP invalid or layout unknown')
        files_changed=[]
        for entry in src.infolist():
            path=entry.filename
            raw=src.read(path)
            if path in sprites:
                raw=sprites[path];files_changed.append(path)
            elif path=='app/robot_core.py':
                code=raw.decode('utf8')
                old="APP_VERSION = '2.2.13'"
                if code.count(old)!=1:raise ValueError('Wrong source version')
                code=code.replace(old,"APP_VERSION = '2.2.14'")
                compile(code,path,'exec')
                raw=code.encode('utf8');files_changed.append(path)
            out.writestr(entry,raw)
    if len(files_changed)!=73:raise ValueError('Unexpected files altered')
    with zipfile.ZipFile(dest) as z:
        if z.testzip() is not None or len(z.namelist())!=84:raise ValueError('Bad output')
        assert all(z.getinfo(k).file_size>0 for k in sprites)
    mf={'version':'2.2.14','zip':dest.name,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()}
    (dest.parent/'manifest.json').write_text(json.dumps(mf,indent=2)+'\n',encoding='utf8')
    print('PASS 84 entries, intact 3D cream robot, animated antenna',json.dumps(mf))
if __name__=='__main__':build(sys.argv[1],sys.argv[2])
