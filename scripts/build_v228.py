#!/usr/bin/env python3
"""v2.2.8: replace flawed semi-alpha procedural aqua art with actual 3D sprite.

Windows Tk canvas uses #ff00fe color-key. Any partially transparent pixels
blend with magenta, leaving a pink halo and pink body: use strict 0/255 alpha.
Build-time Pillow only; the deployed robot needs no new runtime libraries.
"""
from pathlib import Path
import base64,hashlib,io,json,math,re,sys,zipfile
from PIL import Image

SOURCE_ZIP_SHA="08f0e2dc4252d9aee195a708b70c7557eb637747bac1d83b633e6d40467e346c"
SOURCE_ART_SHA="47c9c7747619bf81fa7da2b69e35d93f43d919ac34971c3fd45ccb748fd4f240"
START="        # A single translucent central controller opens animated bubble controls.\n"
END="        self.drag_at=None;self.editor=None;self.minimized=False;self.t=0"
CONTROLS="""        # Borderless canvas-drawn glass button; NO opaque square Tk button.
        self.aqua_button_bg=self.main.create_oval(
            80,117,110,147,fill='#125a82',outline='#bbf9ff',
            width=2,tags=('aqua_trigger',))
        self.aqua_button_icon=self.main.create_text(
            95,132,text='✦',fill='#e9ffff',font=('Segoe UI Symbol',12,'bold'),
            tags=('aqua_trigger',))
        self.main.tag_bind('aqua_trigger','<Button-1>',
                           lambda event:self.toggle_aqua_menu())
        self.main.tag_bind('aqua_trigger','<Enter>',
                           lambda event:self._aqua_button_hover(True))
        self.main.tag_bind('aqua_trigger','<Leave>',
                           lambda event:self._aqua_button_hover(False))
"""
HOVER="""    def _aqua_button_hover(self,on):
        try:
            self.main.itemconfigure(self.aqua_button_bg,
                    fill='#2489b5' if on else '#125a82',
                    outline='#ffffff' if on else '#bbf9ff')
        except tk.TclError:
            pass

"""
def load_art():
    encoded=(Path(__file__).resolve().parent.parent/'assets'/'aqua_3d_rgba.webp.b64').read_text().strip()
    raw=base64.b64decode(encoded,validate=True)
    if hashlib.sha256(raw).hexdigest()!=SOURCE_ART_SHA:
        raise ValueError('Art file checksum mismatch')
    img=Image.open(io.BytesIO(raw)).convert('RGBA')
    if img.size!=(135,177):
        raise ValueError('Unexpected mascot dimensions')
    alphas=set(img.getchannel('A').getdata())
    if not alphas.issubset({0,255}):
        raise ValueError('Mascot contains partial transparency (pink halo risk)')
    return img

def render_frames(source):
    pixels=source.load()
    frames=[]
    for frame in range(20):
        t=2*math.pi*frame/20
        bob=round(1.5*math.sin(t))
        sway=2.5*math.sin(t+.2)
        w,h=source.size
        # Gentle antenna wobble in the first 56 rows (precalculated, no GPU).
        wiggle=Image.new('RGBA',source.size,(0,0,0,0))
        dest=wiggle.load()
        for y in range(h):
            shift=round(sway*max(0,(62-y)/62))
            for x in range(w):
                dx=x+shift
                if 0<=dx<w:dest[dx,y]=pixels[x,y]
        frame_img=Image.new('RGBA',(190,196),(0,0,0,0))
        frame_img.alpha_composite(wiggle,(27,7+bob))
        alphas=set(frame_img.getchannel('A').getdata())
        if not alphas.issubset({0,255}):
            raise ValueError('Frame alpha must be strictly binary')
        buff=io.BytesIO()
        frame_img.save(buff,format='PNG',optimize=True)
        frames.append(buff.getvalue())
    return frames

def make(src_path,dest_path):
    src_path=Path(src_path);dest_path=Path(dest_path)
    if hashlib.sha256(src_path.read_bytes()).hexdigest()!=SOURCE_ZIP_SHA:
        raise ValueError('Wrong base ZIP; expected v2.2.7')
    frames=render_frames(load_art())
    dest_path.parent.mkdir(parents=True,exist_ok=True)
    changed={'app/robot_app.py':0,'app/robot_core.py':0}
    sprite_count=0
    with zipfile.ZipFile(src_path) as zin,zipfile.ZipFile(dest_path,'w') as zout:
        if zin.testzip() is not None:raise ValueError('Corrupted original archive')
        names=zin.namelist()
        if len(set(names))!=len(names) or any(not p.startswith('app/') or '..' in Path(p).parts for p in names):
            raise ValueError('Unexpected app layout')
        for item in zin.infolist():
            contents=zin.read(item.filename)
            if item.filename=='app/robot_app.py':
                code=contents.decode('utf-8')
                if code.count(START)!=1 or code.count(END)!=1:
                    raise ValueError('Missing unique control anchor')
                begin=code.index(START)
                finish=code.index(END,begin)
                code=code[:begin]+CONTROLS+code[finish:]
                anchor='    def _hover_button(self, idx, entering):'
                if code.count(anchor)!=1:raise ValueError('Missing hover anchor')
                code=code.replace(anchor,HOVER+anchor)
                compile(code,'robot_app.py','exec')
                contents=code.encode('utf-8')
                changed[item.filename]+=1
            elif item.filename=='app/robot_core.py':
                code=contents.decode('utf-8')
                old="APP_VERSION = '2.2.7'"
                if code.count(old)!=1:raise ValueError('Wrong source version')
                code=code.replace(old,"APP_VERSION = '2.2.8'")
                compile(code,'robot_core.py','exec')
                contents=code.encode('utf-8')
                changed[item.filename]+=1
            elif re.fullmatch(r'app/assets/frame_\d{2}\.png',item.filename):
                number=int(item.filename[-6:-4])
                if number>=len(frames):raise ValueError('Unexpected frame number')
                contents=frames[number]
                sprite_count+=1
            zout.writestr(item,contents)
    if changed!={'app/robot_app.py':1,'app/robot_core.py':1} or sprite_count!=20:
        raise ValueError('Unexpected patch counts')
    with zipfile.ZipFile(dest_path) as z:
        if z.testzip() is not None:raise ValueError('Corrupted finished release')
        for i in range(20):
            im=Image.open(io.BytesIO(z.read(f'app/assets/frame_{i:02}.png'))).convert('RGBA')
            assert im.size==(190,196)
            assert set(im.getchannel('A').getdata()).issubset({0,255})
    manifest={'version':'2.2.8','zip':dest_path.name,
              'sha256':hashlib.sha256(dest_path.read_bytes()).hexdigest()}
    (dest_path.parent/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print('PASS v2.2.8: crisp real 3D art with binary alpha; original code and data preserved')
    print(json.dumps(manifest))

if __name__=='__main__':
    if len(sys.argv)!=3:raise SystemExit('build_v228.py baseline.zip destination.zip')
    make(sys.argv[1],sys.argv[2])
