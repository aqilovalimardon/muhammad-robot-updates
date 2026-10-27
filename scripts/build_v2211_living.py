#!/usr/bin/env python3
"""Build v2.2.11 Living Mini Cream from exact published v2.2.10.

The Windows Tk host still uses its stable keyed-transparent window. To avoid
the magenta alpha fringe, all runtime frames are fully-opaque RGB with only
a pure #ff00fe background key. Pre-render fur, eye direction, blinking, antenna
and subtle wobble offline using Pillow. Pillow is NOT needed on the laptop.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter
import base64,hashlib,io,json,math,random,sys,zipfile,zlib

PINNED='982d9cf12d0b3e0cbd21a35b07bc4fa87ae5df4f3b95f7bcd2636a9e56d19b17'
KEY=(255,0,254)
SIZE=(100,112)
S=3
N=16
MOODS=['center','left','right','up','down','blink','happy','tilt_left','tilt_right']
SOURCE=Path(__file__).parent/'reference_A_cream_asset.txt'

def source_image():
    # Original chosen 3D cream mascot source from the user's approved A variant.
    parts=SOURCE.read_text(encoding='ascii').strip().splitlines()
    if len(parts)!=2:raise ValueError('Reference mascot source should have 2 data lines')
    jpeg=base64.b64decode(parts[0],validate=True)
    alphabytes=zlib.decompress(base64.b64decode(parts[1],validate=True))
    if len(alphabytes)!=95*98:raise ValueError('Bad source alpha')
    src=Image.open(io.BytesIO(jpeg)).convert('RGBA')
    if src.size!=(190,196):raise ValueError('Bad reference image')
    alpha=Image.frombytes('L',(95,98),alphabytes).resize(src.size,Image.Resampling.BICUBIC)
    src.putalpha(alpha)
    return src

def photo_base(source):
    hi=Image.new('RGBA',(SIZE[0]*S,SIZE[1]*S))
    alpha=source.getchannel('A')
    bbox=alpha.getbbox()
    source=source.crop(bbox)
    source.thumbnail((88*S,104*S),Image.Resampling.LANCZOS)
    hi.alpha_composite(source,((hi.width-source.width)//2,5))
    return hi

def add_cream_fur(image, seed):
    """Sparse radial fine filaments at the actual silhouette, not a solid border."""
    rng=random.Random(2781+seed)
    a=image.getchannel('A')
    w,h=image.size
    d=ImageDraw.Draw(image,'RGBA')
    # Only the exterior boundary gets hair; the face visor remains untouched.
    for y in range(14,h-9,3):
        for x in range(9,w-9,3):
            v=a.getpixel((x,y))
            if v<170 or rng.random()>.49:continue
            nbr=[(dx,dy) for dx,dy in ((-3,0),(3,0),(0,-3),(0,3))
                 if a.getpixel((x+dx,y+dy))<60]
            if not nbr:continue
            dx,dy=rng.choice(nbr)
            ext=2+rng.randint(0,4)
            f=ext/3.0
            brightness=230+rng.randrange(18)
            # A single hair is subpixel after 3x downsample.
            d.line([(x,y),(x+dx*f,y+dy*f)],
                   fill=(brightness,min(255,brightness+4),max(195,brightness-13),
                         120+rng.randrange(100)),width=1)
    return image

def draw_eye_face(img,gaze):
    """New glossy visor and expressive irises, composited at 3x for smooth detail."""
    draw=ImageDraw.Draw(img,'RGBA')
    def co(vals):return tuple(int(round(x*S)) for x in vals)
    face=(26,44,76,72)
    # Dark inset, subtle glossy border and depth from original ref.
    draw.rounded_rectangle(co((24.7,42.7,77.3,73.2)),radius=14*S,
                           fill=(16,26,51,235),outline=(169,151,132,220),width=2*S)
    draw.rounded_rectangle(co(face),radius=13*S,
                           fill=(5,10,32,250),outline=(64,67,100,215),width=1*S)
    draw.arc(co((28,45,73,62)),180,340,fill=(106,137,185,90),width=1*S)
    offsets={'center':(0,0),'left':(-2.3,.1),'right':(2.3,.1),
             'up':(0,-1.7),'down':(0,1.7),'blink':(0,0),
             'happy':(0,0),'tilt_left':(-1.3,0),'tilt_right':(1.3,0)}
    dx,dy=offsets[gaze]
    if gaze in ('blink','happy'):
        for cx in (40,62):
            # Smiling closed eyes have restrained electric-blue curves.
            draw.arc(co((cx-7,51,cx+7,65)),175,355,
                     fill=(138,224,255,230),width=2*S)
        return img
    for cx in (40,62):
        # Blue irises never leave the face. Glows and highlights are pre-rendered.
        draw.ellipse(co((cx-7.5,51,cx+7.5,67)),fill=(35,79,191,175))
        draw.ellipse(co((cx-6.5+dx,51+dy,cx+6.5+dx,65+dy)),
                     fill=(185,234,255,245),outline=(81,133,255,240),width=1*S)
        draw.ellipse(co((cx-3.3+dx,53+dy,cx+4.6+dx,64+dy)),
                     fill=(13,32,110,255))
        draw.ellipse(co((cx-3.6+dx,53+dy,cx-.1+dx,57+dy)),
                     fill=(255,255,255,255))
    return img

def generate(base,mood,frame):
    theta=2*math.pi*frame/N
    image=base.copy()
    # Gentle flying motion and slight antenna movement are baked into each PNG.
    shift=round(1.3*S*math.sin(theta))
    antenna=round(2*S*math.sin(theta+0.45))
    blank=Image.new('RGBA',image.size)
    blank.alpha_composite(image,(0,shift))
    image=blank
    if antenna:
        upper=image.crop((0,0,image.width,29*S))
        transparent=Image.new('RGBA',upper.size)
        transparent.alpha_composite(upper,(antenna,0))
        # Displace the antenna only in the top part where there is no face.
        image.paste(transparent,(0,0))
    image=draw_eye_face(image,mood)
    image=add_cream_fur(image,frame)
    if mood.startswith('tilt_'):
        angle=2.5 if mood=='tilt_left' else -2.5
        image=image.rotate(angle,resample=Image.Resampling.BICUBIC,
                           center=(image.width/2,image.height*.59))
    # RGB color-key transparency: NEVER mix partial alpha against magenta.
    # Floyd dithering of alpha would create magenta halos, so instead apply a
    # compact ordered micro-stipple on fur pixels.
    down=image.resize(SIZE,Image.Resampling.LANCZOS)
    rgb=down.convert('RGB')
    a=down.getchannel('A')
    out=Image.new('RGB',SIZE,KEY)
    pix=rgb.load();alph=a.load();dest=out.load()
    bayer=((0,8,2,10),(12,4,14,6),(3,11,1,9),(15,7,13,5))
    for y in range(SIZE[1]):
        for x in range(SIZE[0]):
            aa=alph[x,y]
            # Threshold dither only outer fringe, pixels themselves retain
            # *original cream RGB*, never magenta background mixture.
            thresh=105+(bayer[y%4][x%4]-8)*8
            if aa>=thresh:
                color=pix[x,y]
                if color==KEY:color=(254,0,253)
                dest[x,y]=color
    buffer=io.BytesIO()
    out.save(buffer,'PNG',optimize=True)
    return buffer.getvalue()

OLD_ANIMATE="""    def animate(self):
        if not self.minimized and self.frames:
            self.t+=1
            frame=self.frames[(self.t//4)%len(self.frames)]
            self.main.itemconfigure(self.sprite,image=frame)
            self.main.coords(self.sprite,self.win_width//2,self.win_height//2)
        self.root.after(75,self.animate)
"""
NEW_ANIMATE="""    def animate(self):
        if not self.minimized and self.frames:
            self.t+=1
            gaze='center'
            if getattr(self,'_cream_style','living')=='classic':
                index=(self.t//4)%len(self.frames)
            else:
                gaze='center'
                try:
                    px,py=self.root.winfo_pointerxy()
                    cx=self.root.winfo_rootx()+self.win_width/2
                    cy=self.root.winfo_rooty()+self.win_height/2
                    dx=px-cx
                    dy=py-cy
                    if math.hypot(dx,dy)<145:
                        if abs(dx)>max(12,abs(dy)*0.75):
                            gaze='left' if dx<0 else 'right'
                        elif abs(dy)>12:
                            gaze='up' if dy<0 else 'down'
                    if getattr(self,'_drag_sway',0)>0:
                        gaze='tilt_left' if getattr(self,'_drag_dir',0)<0 else 'tilt_right'
                        self._drag_sway-=1
                    elif self.t%106 in (104,105):
                        gaze='blink'
                    elif getattr(self,'_talk_ticks',0)>0:
                        gaze='happy'
                        self._talk_ticks-=1
                except tk.TclError:
                    pass
                variant=self._cream_variants.get(gaze,0)
                index=(variant*16+(self.t//2)%16)%len(self.frames)
            self.main.itemconfigure(self.sprite,image=self.frames[index])
            self.main.coords(self.sprite,self.win_width//2,self.win_height//2)
            try:
                if getattr(self,'belly_ring',None) is not None:
                    self.main.itemconfigure(self.belly_ring,
                        outline='#58dcff' if gaze!='center' else '#b2e9ff')
            except tk.TclError:
                pass
        self.root.after(75,self.animate)
"""
def patch_app(code):
    if code.count(OLD_ANIMATE)!=1:raise ValueError('Current stable animate method not found')
    code=code.replace(OLD_ANIMATE,NEW_ANIMATE)
    old="self.drag_at=None;self.editor=None;self.minimized=False;self.t=0"
    new="""self.drag_at=None;self.editor=None;self.minimized=False;self.t=0
        self._cream_variants={name:i for i,name in enumerate(
            ('center','left','right','up','down','blink','happy','tilt_left','tilt_right'))}
        self._drag_sway=0
        self._drag_dir=0
        self._talk_ticks=0
        self._cream_style='living'
        self._living_frames=self.frames
        self._classic_frames=None"""
    if code.count(old)!=1:raise ValueError('Missing init section')
    code=code.replace(old,new)
    old="""            self.root.geometry(f'+{wx+event.x_root-x}+{wy+event.y_root-y}')"""
    new="""            self.root.geometry(f'+{wx+event.x_root-x}+{wy+event.y_root-y}')
            self._drag_dir=1 if event.x_root>x else -1
            self._drag_sway=6"""
    if code.count(old)!=1:raise ValueError('Missing drag motion')
    code=code.replace(old,new)
    old="    def say(self,text):\n        self.voice.speak(text)"
    new="""    def say(self,text):
        self._talk_ticks=12
        self.voice.speak(text)"""
    if code.count(old)!=1:raise ValueError('Missing TTS callback')
    code=code.replace(old,new)
    # Recovery choice: if the new design does not suit this notebook, instantly
    # choose stable classic sprites; never uninstall or touch saved Python code.
    before="    def _hover_button(self, idx, entering):"
    toggle="""    def switch_robot_look(self):
        if self._cream_style=='living':
            if self._classic_frames is None:
                self._classic_frames=[]
                for p in sorted((HERE/'assets_classic').glob('frame_*.png')):
                    try:self._classic_frames.append(tk.PhotoImage(file=str(p)))
                    except tk.TclError:pass
            if not self._classic_frames:
                messagebox.showwarning('Robot appearance','Classic assets not available.')
                return
            self.frames=self._classic_frames
            self._cream_style='classic'
        else:
            self.frames=self._living_frames
            self._cream_style='living'
        self.t=0

"""
    if code.count(before)!=1:raise ValueError('Missing toggle insertion')
    code=code.replace(before,toggle+before)
    menu="self.menu.add_command(label='About robot / version',command=self.show_version)"
    if code.count(menu)!=1:raise ValueError('Missing context menu anchor')
    code=code.replace(menu,
        "self.menu.add_command(label='Appearance: Living / Classic',command=self.switch_robot_look)\n        "+menu)
    compile(code,'robot_app.py','exec')
    return code

def build(src,dest):
    src=Path(src);dest=Path(dest)
    if hashlib.sha256(src.read_bytes()).hexdigest()!=PINNED:
        raise ValueError('v2.2.10 published ZIP checksum does not match')
    base=photo_base(source_image())
    generated={}
    for i,mood in enumerate(MOODS):
        for j in range(N):
            generated[f'app/assets/frame_{i*N+j:03d}.png']=generate(base,mood,j)
    dest.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(src) as z,zipfile.ZipFile(dest,'w',compression=zipfile.ZIP_DEFLATED) as out:
        if z.testzip() is not None:raise ValueError('Bad source ZIP')
        names=z.namelist()
        if len(set(names))!=len(names):raise ValueError('Duplicate members')
        # Preserve last known good mini appearance as a one-click safety switch.
        for entry in z.infolist():
            data=z.read(entry.filename)
            if entry.filename=='app/robot_app.py':
                data=patch_app(data.decode('utf8')).encode('utf8')
            elif entry.filename=='app/robot_core.py':
                code=data.decode('utf8')
                old="APP_VERSION = '2.2.10'"
                if code.count(old)!=1:raise ValueError('Bad base version')
                code=code.replace(old,"APP_VERSION = '2.2.11'")
                compile(code,'robot_core.py','exec')
                data=code.encode('utf8')
            if entry.filename.startswith('app/assets/frame_') and entry.filename.endswith('.png'):
                out.writestr(entry.filename.replace('app/assets/','app/assets_classic/'),data)
                continue
            out.writestr(entry,data)
        for name,data in generated.items():
            out.writestr(name,data)
    with zipfile.ZipFile(dest) as result:
        if result.testzip() is not None:raise ValueError('Bad built ZIP')
        assert len([n for n in result.namelist() if n.startswith('app/assets/frame_')])==len(generated)
        assert len([n for n in result.namelist() if n.startswith('app/assets_classic/frame_')])==36
    manifest={'version':'2.2.11','zip':dest.name,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()}
    (dest.parent/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8')
    print('PASS: Living Mini Cream',len(generated),'lightweight pre-rendered sprites',
          'with classic fallback',json.dumps(manifest))
if __name__=='__main__':
    if len(sys.argv)!=3:raise SystemExit('Usage: build_v2211_living.py v2210.zip result.zip')
    build(sys.argv[1],sys.argv[2])
