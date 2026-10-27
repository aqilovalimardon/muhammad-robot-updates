#!/usr/bin/env python3
"""v2.2.9 / Mini Cream: half-size, pure color-key transparency, animated mascot.

Build only: Pillow is never installed on Muhammad's notebook. Keeps the
versioned launcher, editor, speech listener, updates, saved code and recovery orb.
"""
from pathlib import Path
from PIL import Image, ImageDraw
import base64, hashlib, io, json, math, sys, zipfile

PINNED_SHA='56c71f58ff50c8cb235befbc38fd09c24131f7a5cd87fd50a2ba64a65d0ff4fb'
KEY=(255,0,254)
WIDTH, HEIGHT=100,112
FRAME_COUNT=36

def load_reference():
    b64=(Path(__file__).parent/'cream_front_small.webp.b64').read_text(encoding='ascii').strip()
    im=Image.open(io.BytesIO(base64.b64decode(b64,validate=True))).convert('RGBA')
    if im.size!=(84,108): raise ValueError(f'Unexpected reference art dimensions {im.size}')
    if im.getpixel((0,0))[3]!=0: raise ValueError('Art must have a transparent corner')
    return im

def render(src,num):
    angle=2*math.pi*num/FRAME_COUNT
    bob=round(1.4*math.sin(angle))
    bend=3.4*math.sin(angle+0.3)
    rgba=Image.new('RGBA',(WIDTH,HEIGHT),(0,0,0,0))
    # Transform only the soft antenna at top; no facial distortion.
    for y in range(src.height):
        top=max(0,(25-y)/25)
        antenna_x=round(bend*top)
        strip=src.crop((0,y,src.width,y+1))
        py=y+2+bob
        if 0<=py<HEIGHT:
            rgba.alpha_composite(strip,((WIDTH-src.width)//2+antenna_x,py))
    # Soft blink every ~2.5s, pre-rendered (nothing dynamically drawn on laptop).
    # Reference eyes remain untouched in every normal frame.
    # Tk color-key is binary, not alpha blending. A partially transparent pixel
    # draws mixed with the MAGENTA window color, causing bright pink outlines.
    # Use a *fully opaque RGB image* and exact pure key outside the silhouette.
    # The threshold keeps only trustworthy source colors, never blends with key.
    final=Image.new('RGB',(WIDTH,HEIGHT),KEY)
    rgb=rgba.convert('RGB')
    alpha=rgba.getchannel('A')
    srcpix=rgb.load();alphapix=alpha.load();dst=final.load()
    for y in range(HEIGHT):
        for x in range(WIDTH):
            if alphapix[x,y]>=145:
                r,g,b=srcpix[x,y]
                # Avoid accidental exact key match inside the robot.
                dst[x,y]=(r,g,b) if (r,g,b)!=KEY else (254,0,253)
    buffer=io.BytesIO()
    final.save(buffer,format='PNG',optimize=True)
    return buffer.getvalue()

# Replace ONLY the old belly widget with a genuinely rounded Canvas button.
# The floating five-option bubble menu remains completely unchanged.
BEGIN="        for idx,(x,symbol,hint,fn) in enumerate(["
END="        self.drag_at=None;self.editor=None;self.minimized=False;self.t=0"
CANVAS_BELLY="""        # A round, canvas-native glass-like button (no black rectangular widget).
        self.belly_ring=self.main.create_oval(
            39,73,61,95,fill='#e7e8e0',outline='#b2e9ff',width=1,
            tags=('cream_belly',))
        self.belly_dot=self.main.create_oval(
            46,80,54,88,fill='#7dbedc',outline='#e8fcff',
            tags=('cream_belly',))
        self.main.tag_bind('cream_belly','<Button-1>',
            lambda event:self.toggle_aqua_menu())
        self.main.tag_bind('cream_belly','<Enter>',
            lambda event:self.main.itemconfigure(self.belly_ring,outline='#3db8ff'))
        self.main.tag_bind('cream_belly','<Leave>',
            lambda event:self.main.itemconfigure(self.belly_ring,outline='#b2e9ff'))
"""
def patch_gui(code):
    changes=[
        ("self.win_width=190;self.win_height=196",
         "self.win_width=100;self.win_height=112"),
        ("f'{self.win_width}x{self.win_height}+{max(20,sw-220)}+70'",
         "f'{self.win_width}x{self.win_height}+{max(20,sw-130)}+70'"),
        ("self.main=tk.Canvas(self.root,width=190,height=196,",
         "self.main=tk.Canvas(self.root,width=100,height=112,"),
        ("self.sprite=self.main.create_image(95,98,",
         "self.sprite=self.main.create_image(50,56,"),
    ]
    for old,new in changes:
        if code.count(old)!=1:
            raise ValueError('Source layout unexpected: '+old)
        code=code.replace(old,new)
    a=code.index(BEGIN);b=code.index(END,a)
    existing=code[a:b]
    if "self.toggle_aqua_menu" not in existing or "self.buttons.append(btn)" not in existing:
        raise ValueError('Expected v2.2.8 single belly button')
    code=code[:a]+CANVAS_BELLY+code[b:]
    # Prevent dragging the robot when its tiny belly button is clicked.
    old="self.main.bind('<Button-1>',self.drag_start)"
    new="""self.main.bind('<Button-1>',lambda event:
            None if self.main.find_withtag('current') and
            'cream_belly' in self.main.gettags('current')
            else self.drag_start(event))"""
    if code.count(old)!=1:raise ValueError('Unexpected drag binding')
    code=code.replace(old,new)
    # For existing hover helpers keep the old unused lists in place.
    # Also retain existing escape, right-click, editor, mic, menu and updater.
    compile(code,'robot_app.py','exec')
    return code

def build(source,dest):
    if hashlib.sha256(Path(source).read_bytes()).hexdigest()!=PINNED_SHA:
        raise ValueError('Published v2.2.8 baseline SHA-256 does not match')
    sprite=load_reference()
    frames={f'app/assets/frame_{i:02d}.png':render(sprite,i) for i in range(FRAME_COUNT)}
    dest=Path(dest);dest.parent.mkdir(parents=True,exist_ok=True)
    changed=[]
    with zipfile.ZipFile(source) as zin,zipfile.ZipFile(dest,'w') as out:
        names=zin.namelist()
        if zin.testzip() is not None:raise ValueError('Baseline damaged')
        if len(set(names))!=len(names):raise ValueError('Duplicate source members')
        for entry in zin.infolist():
            data=zin.read(entry.filename)
            if entry.filename in frames:
                data=frames[entry.filename]
                changed.append(entry.filename)
            elif entry.filename=='app/robot_app.py':
                data=patch_gui(data.decode('utf-8')).encode('utf-8')
                changed.append(entry.filename)
            elif entry.filename=='app/robot_core.py':
                body=data.decode('utf-8')
                if body.count("APP_VERSION = '2.2.8'")!=1:
                    raise ValueError('Unexpected version')
                body=body.replace("APP_VERSION = '2.2.8'","APP_VERSION = '2.2.9'")
                compile(body,'robot_core.py','exec')
                data=body.encode('utf-8')
                changed.append(entry.filename)
            out.writestr(entry,data)
        for path in sorted(set(frames)-set(names)):
            out.writestr(path,frames[path])
            changed.append(path)
    if len(changed)!=FRAME_COUNT+2:
        raise ValueError('Wrong number of files patched')
    with zipfile.ZipFile(dest) as z:
        if z.testzip() is not None:raise ValueError('Bad result ZIP')
        for path in frames:
            img=Image.open(io.BytesIO(z.read(path)))
            if img.mode!='RGB' or img.size!=(WIDTH,HEIGHT):
                raise ValueError('Bad sprite '+path)
            if img.getpixel((0,0))!=KEY:raise ValueError('Color key mismatch '+path)
    mf={'version':'2.2.9','zip':dest.name,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()}
    (dest.parent/'manifest.json').write_text(json.dumps(mf,indent=2)+'\n',encoding='utf-8')
    print('PASS: half-sized cream robot, no alpha/magenta bleed, 36 lightweight frames')
    print(json.dumps(mf))
if __name__=='__main__':
    if len(sys.argv)!=3:raise SystemExit('Usage: build_v229_cream.py baseline.zip result.zip')
    build(sys.argv[1],sys.argv[2])
