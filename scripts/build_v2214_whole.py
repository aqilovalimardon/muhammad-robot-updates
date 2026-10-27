#!/usr/bin/env python3
"""v2.2.14: Rebuild Mini Cream as a SINGLE intact approved 3D sprite.

v2.2.13 improperly composited a second visor and eyes onto the body. Here the
source is the ORIGINAL whole front-facing cream-colored character, supplied
in scripts/cream_front_small.webp.b64. No second face is EVER drawn.  A separate
antenna is rotated around its attachment point on a padded canvas, preventing
its glowing tip from being clipped. Gentle bob, cursor-responsive tiny highlights
and a dragged-body tilt are pre-rendered offline (Pillow build-only).

Published package has 84 entries (72 + 8 classic + 4 code) and passes installed
v2.2.10 ZIP checker (max 100 entries). All application functions unchanged.
"""
from pathlib import Path
from PIL import Image, ImageDraw
import base64, hashlib, io, json, math, sys, zipfile

PINNED_SHA='5d64d108566e79395af65327334da28dcaa4edc0638384a9f113e036b1e3b5c8'
TRANSPARENT=(255,0,254)
SIZE=(100,112)
MOODS=('center','left','right','up','down','blink','happy','tilt_left','tilt_right')
FRAME_COUNT=8
SOURCE=Path(__file__).parent/'cream_front_small.webp.b64'

def load_source():
    raw=base64.b64decode(SOURCE.read_text('ascii').strip(),validate=True)
    im=Image.open(io.BytesIO(raw)).convert('RGBA')
    if im.size!=(84,108):raise ValueError('Unexpected source image dimensions')
    # IMPORTANT: this is a full intact cream baby avatar, not the buggy 190px
    # JPEG which had a cut-off second figure / left-aligned character.
    assert im.getchannel('A').getbbox()==(0,0,84,108)
    return im

def draw_sway(source, mood, phase):
    """Return premultiplied-looking image with full body, without a cut visor.

    The antenna occupies rows 0:25 and meets the top of the plush head at
    (38,25). Rotate ONLY that isolated transparent region on a 100x112 canvas.
    """
    source=source.copy()
    px=source.load()
    ant=Image.new('RGBA',source.size)
    ax=ant.load()
    for y in range(25):
        for x in range(source.width):
            q=px[x,y]
            ax[x,y]=q
            px[x,y]=(q[0],q[1],q[2],0)
    avatar=Image.new('RGBA',SIZE)
    avatar.alpha_composite(source,(8,3))
    antenna_canvas=Image.new('RGBA',SIZE)
    antenna_canvas.alpha_composite(ant,(8,3))
    angle=14.0*math.sin(2*math.pi*phase)
    antenna_canvas=antenna_canvas.rotate(angle,
             resample=Image.Resampling.BICUBIC,center=(46,28))
    avatar.alpha_composite(antenna_canvas)
    # Keep original face untouched: a second inset or separately painted
    # oval is the exact failure reported in v2.2.11/v2.2.13.
    # Cursor movement changes tiny glints *inside* the existing eyes.
    offsets={'center':(0,0),'left':(-2,0),'right':(2,0),
             'up':(0,-1),'down':(0,1),'blink':(0,0),'happy':(0,0),
             'tilt_left':(-1,0),'tilt_right':(1,0)}
    gx,gy=offsets[mood]
    if gx or gy:
        d=ImageDraw.Draw(avatar,'RGBA')
        for cx,cy in ((44,59),(69,56)):
            d.ellipse((cx+gx,cy+gy,cx+gx+1,cy+gy+1),
                      fill=(190,231,255,220))
    if mood.startswith('tilt_'):
        avatar=avatar.rotate(3 if mood=='tilt_left' else -3,
                             resample=Image.Resampling.BICUBIC,center=(50,67))
    bob=round(math.sin(2*math.pi*phase))
    final_rgba=Image.new('RGBA',SIZE)
    final_rgba.alpha_composite(avatar,(0,bob))
    # Tk's -transparentcolor is a binary key, not true partial alpha.
    # Never composite semi-transparent edges against the magenta key.
    rgb=final_rgba.convert('RGB')
    alpha=final_rgba.getchannel('A')
    result=Image.new('RGB',SIZE,TRANSPARENT)
    srcpix=rgb.load();opacity=alpha.load();dst=result.load()
    for y in range(SIZE[1]):
        for x in range(SIZE[0]):
            if opacity[x,y]>=142:
                q=srcpix[x,y]
                dst[x,y]=q if q!=TRANSPARENT else (254,0,253)
    buf=io.BytesIO()
    result.save(buf,format='PNG',optimize=True)
    return buf.getvalue()

def build(baseline,outpath):
    baseline=Path(baseline)
    outpath=Path(outpath)
    if hashlib.sha256(baseline.read_bytes()).hexdigest()!=PINNED_SHA:
        raise ValueError('Expected exact published v2.2.13 baseline')
    source=load_source()
    frames={f'app/assets/frame_{i*FRAME_COUNT+k:03d}.png':
               draw_sway(source,mood,k/FRAME_COUNT)
            for i,mood in enumerate(MOODS)
            for k in range(FRAME_COUNT)}
    outpath.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(baseline) as z,zipfile.ZipFile(outpath,'w',zipfile.ZIP_DEFLATED) as target:
        if z.testzip() is not None:raise ValueError('Source ZIP damaged')
        names=z.namelist()
        if len(names)!=84 or len(names)!=len(set(names)):
            raise ValueError('Unexpected base ZIP layout')
        changed=[]
        for entry in z.infolist():
            data=z.read(entry.filename)
            if entry.filename in frames:
                data=frames[entry.filename]
                changed.append(entry.filename)
            elif entry.filename=='app/robot_core.py':
                code=data.decode('utf8')
                old="APP_VERSION = '2.2.13'"
                if code.count(old)!=1:raise ValueError('Source version missing')
                code=code.replace(old,"APP_VERSION = '2.2.14'")
                compile(code,entry.filename,'exec')
                data=code.encode('utf8')
                changed.append(entry.filename)
            target.writestr(entry,data)
    if len(changed)!=73:raise ValueError('Wrong scope of modification')
    with zipfile.ZipFile(baseline) as src,zipfile.ZipFile(outpath) as final:
        if final.testzip() is not None or final.namelist()!=names:raise ValueError('ZIP layout damaged')
        for name in names:
            if name not in changed and src.read(name)!=final.read(name):
                raise ValueError('Unrelated user-facing code changed: '+name)
    manifest={'version':'2.2.14','zip':outpath.name,
              'sha256':hashlib.sha256(outpath.read_bytes()).hexdigest()}
    (outpath.parent/'manifest.json').write_text(
              json.dumps(manifest,indent=2)+'\n',encoding='utf8')
    print('PASS: whole 3D source, complete antenna, 72 frames, 84 safe entries, unchanged app/editor/voice')
    print(json.dumps(manifest))
if __name__=='__main__':
    if len(sys.argv)!=3:raise SystemExit('Usage: build_v2214_whole.py base.zip result.zip')
    build(sys.argv[1],sys.argv[2])
