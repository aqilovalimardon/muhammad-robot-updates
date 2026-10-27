#!/usr/bin/env python3
"""v2.2.13: repair Living Mini Cream's detached/double face.

Rebuild the 72 RGB color-keyed sprites from the ORIGINAL approved intact
cream-white reference, not the previously enlarged overdrawn face. Render only
TWO small eyes within the original visor, never a second head/visor. Preserve
existing 8 classic fallback frames, menus, voice, editor and updater.
"""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFilter
import base64,hashlib,io,json,math,random,sys,zipfile,zlib

SOURCE_SHA='82c5e0326a4174f3387d2f98fa3167b7acca820e1b7bcf3dac15ad0215b3fbad'
KEY=(255,0,254)
SIZE=(100,112)
MOODS=('center','left','right','up','down','blink','happy','tilt_left','tilt_right')
FRAME_COUNT=8

def original_reference():
    p=Path(__file__).parent/'reference_A_cream_asset.txt'
    lines=p.read_text('ascii').strip().splitlines()
    if len(lines)!=2:raise ValueError('Missing approved cream 3D reference')
    rgb=Image.open(io.BytesIO(base64.b64decode(lines[0],validate=True))).convert('RGBA')
    alpha=zlib.decompress(base64.b64decode(lines[1],validate=True))
    assert len(alpha)==95*98 and rgb.size==(190,196)
    rgb.putalpha(Image.frombytes('L',(95,98),alpha).resize((190,196),Image.Resampling.BICUBIC))
    return rgb

def eyes_without_second_visors(original,mood):
    """Carefully modify only the interior of the ORIGINAL visor.

    All geometric locations are normalized from the approved reference photo.
    These are not screen coordinates or a new face panel.
    """
    src=original.copy()
    # Approved reference was rasterized 190x196 from a 342x315 cutout.
    # Transform reference-space eye coords into JPEG coordinates.
    def box(x0,y0,x1,y1):
        return tuple(round(v*s) for v,s in zip((x0,y0,x1,y1),
                    (190/342,196/315,190/342,196/315)))
    # Interior fill erases old eyes but does not cover the bevel/robot body.
    mask=Image.new('L',src.size,0)
    d=ImageDraw.Draw(mask)
    d.rounded_rectangle(box(105,128,224,191),radius=round(24*190/342),fill=234)
    mask=mask.filter(ImageFilter.GaussianBlur(1.1))
    dark=Image.new('RGBA',src.size,(8,10,28,255))
    src=Image.composite(dark,src,mask)
    dr=ImageDraw.Draw(src,'RGBA')
    delta={'center':(0,0),'left':(-5,0),'right':(5,0),
           'up':(0,-4),'down':(0,4),'blink':(0,0),'happy':(0,0),
           'tilt_left':(-3,0),'tilt_right':(3,0)}[mood]
    for cx,cy in ((137,163),(197,159)):
        x,y=cx+delta[0],cy+delta[1]
        if mood in ('blink','happy'):
            dr.arc(box(x-17,y-8,x+17,y+8),0,180,
                   fill=(167,218,255,248),width=2)
        else:
            dr.ellipse(box(x-17,y-20,x+17,y+20),fill=(43,67,169,187))
            dr.ellipse(box(x-15,y-18,x+15,y+18),fill=(223,242,255,250))
            dr.ellipse(box(x-4,y-16,x+15,y+12),fill=(14,25,98,255))
            dr.ellipse(box(x+4,y-13,x+9,y-8),fill=(255,255,255,255))
    return src

def make_frame(reference,mood,n):
    # Start with the same complete body and correct rounded silhouette.
    body=eyes_without_second_visors(reference,mood)
    # Original output has 190x196 canvas; scale to 94x106 into a 100x112
    # avatar without clipping. Tiny vertical movement only (max 1 pixel).
    body.thumbnail((94,106),Image.Resampling.LANCZOS)
    bob=round(1.1*math.sin(2*math.pi*n/FRAME_COUNT))
    backdrop=Image.new('RGBA',SIZE)
    tx=(SIZE[0]-body.width)//2
    ty=max(0,(SIZE[1]-body.height)//2+bob)
    backdrop.alpha_composite(body,(tx,ty))
    if mood.startswith('tilt_'):
        # One mild 2-degree animation, not a new overlaid object.
        backdrop=backdrop.rotate(2 if mood=='tilt_left' else -2,
                                 resample=Image.Resampling.BICUBIC,
                                 center=(SIZE[0]/2,SIZE[1]*.6))
    # Tkinter uses a binary per-pixel KEY. Never preblend image with pink.
    src=backdrop.convert('RGB')
    a=backdrop.getchannel('A')
    image=Image.new('RGB',SIZE,KEY)
    s=src.load();opacity=a.load();dest=image.load()
    for y in range(SIZE[1]):
        for x in range(SIZE[0]):
            if opacity[x,y]>=140:
                pix=s[x,y]
                dest[x,y]=pix if pix!=KEY else (254,0,253)
    buf=io.BytesIO()
    image.save(buf,format='PNG',optimize=True)
    return buf.getvalue()

def build(src,dst):
    src=Path(src);dst=Path(dst)
    if hashlib.sha256(src.read_bytes()).hexdigest()!=SOURCE_SHA:
        raise ValueError('Only exactly published v2.2.12 ZIP permitted')
    reference=original_reference()
    frame_data={}
    for i,mood in enumerate(MOODS):
        for n in range(FRAME_COUNT):
            frame_data[f'app/assets/frame_{i*FRAME_COUNT+n:03d}.png']=make_frame(reference,mood,n)
    dst.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(src) as previous,zipfile.ZipFile(dst,'w',compression=zipfile.ZIP_DEFLATED) as out:
        if previous.testzip() is not None:raise ValueError('Invalid original ZIP')
        names=previous.namelist()
        assert len(names)==84 and len(names)==len(set(names))
        updated=[]
        for entry in previous.infolist():
            path=entry.filename
            content=previous.read(path)
            if path in frame_data:
                content=frame_data[path]
                updated.append(path)
            elif path=='app/robot_core.py':
                code=content.decode('utf8')
                if code.count("APP_VERSION = '2.2.12'")!=1:
                    raise ValueError('Unexpected version')
                code=code.replace("APP_VERSION = '2.2.12'","APP_VERSION = '2.2.13'")
                compile(code,path,'exec')
                content=code.encode('utf8')
                updated.append(path)
            out.writestr(entry,content)
    if len(updated)!=73:raise ValueError('Invalid update scope')
    with zipfile.ZipFile(src) as before,zipfile.ZipFile(dst) as after:
        if after.testzip() is not None or after.namelist()!=names:
            raise ValueError('Changed ZIP layout')
        for name in names:
            if name not in updated and before.read(name)!=after.read(name):
                raise ValueError('Touched unrelated code or backup: '+name)
    mf={'version':'2.2.13','zip':dst.name,
        'sha256':hashlib.sha256(dst.read_bytes()).hexdigest()}
    (dst.parent/'manifest.json').write_text(json.dumps(mf,indent=2)+'\n','utf8')
    print('PASS: restored coherent full-body reference; 72 frames; exactly 84 ZIP entries',json.dumps(mf))
if __name__=='__main__':
    if len(sys.argv)!=3:raise SystemExit('Usage: build_v2213_face_repair.py base.zip result.zip')
    build(sys.argv[1],sys.argv[2])
