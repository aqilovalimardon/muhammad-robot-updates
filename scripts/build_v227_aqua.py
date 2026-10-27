#!/usr/bin/env python3
"""Mini Soft Aqua (v2.2.7), based on verified v2.2.6.

Draw a translucent milk-blue gel mascot offline using Pillow and install a
single glass-like belly button with animated popup.  No 3D runtime, networking,
extra processes or native dependencies are introduced into robot.
"""
import hashlib,json,math,sys,zipfile,io
from pathlib import Path
from PIL import Image,ImageDraw,ImageFilter
SOURCE_SHA='4f886d54ff85abc4c78f8033aba0ed79dc5e5f65aba19b20cb0c87d50a3b1253'
ROOT_SIZE=(190,196)
SCALE=3
W,H=(x*SCALE for x in ROOT_SIZE)
TRANSPARENT=(0,0,0,0)

def aqua_frame(index):
    t=2*math.pi*index/20
    # Composite translucent jelly surfaces, bright glossy rim and creamy core.
    img=Image.new('RGBA',(W,H),TRANSPARENT)
    d=ImageDraw.Draw(img,'RGBA')
    def oval(rect,fill,outline=None,width=1):
        box=tuple(round(a*SCALE) for a in rect)
        d.ellipse(box,fill=fill,outline=outline,width=width*SCALE)
    def line(pts,fill,width=2):
        d.line([(round(x*SCALE),round(y*SCALE)) for x,y in pts],fill=fill,width=width*SCALE,joint='curve')
    # Limited hover motion: entire body shifts under 3px; no per-frame computation on laptop.
    dy=1.4*math.sin(t)
    wobble=math.sin(t)*1.8
    # modest blue halo (precomputed)
    halo=Image.new('RGBA',(W,H),TRANSPARENT)
    hd=ImageDraw.Draw(halo,'RGBA')
    hd.ellipse(tuple(int(q*SCALE) for q in (47,17+dy,143,150+dy)),fill=(84,207,255,70))
    halo=halo.filter(ImageFilter.GaussianBlur(12*SCALE))
    img.alpha_composite(halo)
    d=ImageDraw.Draw(img,'RGBA')
    # short rounded feet and arms; milk-glass cyan
    oval((59,132+dy,86,161+dy),(192,244,253,215),(88,206,248,180),2)
    oval((103,132+dy,131,161+dy),(192,244,253,215),(88,206,248,180),2)
    oval((34,93+dy,65,130+dy),(167,235,254,195),(61,175,231,160),2)
    oval((127,93+dy,156,130+dy),(170,237,253,195),(61,175,231,160),2)
    # gel body oval + layered highlights
    oval((47,87+dy,143,156+dy),(124,217,248,218),(146,249,255,240),2)
    oval((54,96+dy,135,148+dy),(210,249,253,115))
    oval((64,121+dy,126,150+dy),(243,251,245,165))
    # soft ears
    oval((29,67+dy,60,106+dy),(156,232,250,212),(110,213,255,240),2)
    oval((131,67+dy,162,106+dy),(156,232,250,212),(110,213,255,240),2)
    # Large round head & luminous milk-blue edge.
    oval((40,20+dy,150,126+dy),(134,214,247,226),(181,246,255,249),3)
    oval((46,24+dy,143,119+dy),(211,244,249,110))
    oval((52,26+dy,138,66+dy),(249,252,247,95))
    oval((49,72+dy,141,122+dy),(95,185,236,76))
    # upper brow specular marks
    line([(65,36+dy),(83,30+dy),(100,30+dy)],(255,255,255,182),3)
    # black-blue inset digital eyes are clear at 160-pixel robot size
    d.rounded_rectangle(tuple(int(v*SCALE) for v in (56,55+dy,134,103+dy)),
        radius=22*SCALE,fill=(7,25,48,237),outline=(139,244,255,235),width=2*SCALE)
    for x in (76,114):
        oval((x-12,64+dy,x+10,92+dy),(118,236,255,250))
        oval((x-6,66+dy,x+6,88+dy),(9,66,130,255))
        oval((x-4,66+dy,x+2,73+dy),(249,255,255,255))
    # tiny grin
    d.arc(tuple(int(v*SCALE) for v in (91,84+dy,103,94+dy)),
          start=10,end=170,fill=(160,247,255,235),width=2*SCALE)
    # antenna stalk sways around its base
    sway=4.8*math.sin(t+0.3)
    line([(94,22+dy),(94+sway*0.4,11+dy),(93+sway,5+dy)],(161,236,255,242),3)
    oval((87+sway,1+dy,101+sway,15+dy),(224,251,249,237),(164,231,255,254),2)
    oval((90+sway,3+dy,95+sway,7+dy),(255,255,255,240))
    # belly glass button outline, placed beneath actual Tk button
    oval((82,119+dy,108,145+dy),(78,199,232,145),(230,255,255,235),2)
    oval((89,126+dy,101,138+dy),(218,252,249,95))
    return img.resize(ROOT_SIZE,Image.Resampling.LANCZOS)

NEW_BUTTONS="""        # A single translucent central controller opens animated bubble controls.
        for idx,(x,symbol,hint,fn) in enumerate([
            (95,'◉','Open aqua menu',self.toggle_aqua_menu)]):
"""
OLD_BEGIN="        for idx,(x,symbol,hint,fn) in enumerate(["
OLD_END="            (154,'−','Hide robot',self.minimize)]):"
NEW_METHODS=r"""
    def toggle_aqua_menu(self):
        if getattr(self,'aqua_menu',None) is not None:
            try:
                if self.aqua_menu.winfo_exists():
                    self.aqua_menu.destroy()
                    self.aqua_menu=None
                    return
            except tk.TclError: pass
        self.aqua_menu=None
        self._show_aqua_menu()

    def _show_aqua_menu(self):
        # No network and no new thread: ~220ms non-blocking Tk after animation.
        names=[
            ('✎','Python Studio',self.open_editor),
            ('▶','Run Python',self.quick_run),
            ('▢','Lessons',self.learn),
            ('♧','Always on top',self.toggle_pin),
            ('−','Hide robot',self.minimize),
        ]
        win=tk.Toplevel(self.root)
        win.overrideredirect(True)
        win.attributes('-topmost',True)
        win.configure(bg='#061d37')
        self.aqua_menu=win
        sw=self.root.winfo_screenwidth()
        sh=self.root.winfo_screenheight()
        rx=self.root.winfo_rootx();ry=self.root.winfo_rooty()
        x=rx+self.win_width+5
        if x+176>sw:x=max(0,rx-183)
        y=max(0,min(ry+12,sh-222))
        win.geometry(f'178x1+{x}+{y}')
        panel=tk.Frame(win,bg='#082943',highlightbackground='#4dc8ed',
                       highlightcolor='#4dc8ed',highlightthickness=1)
        panel.pack(expand=True,fill='both',padx=2,pady=2)
        for symbol,hint,command in names:
            def invoke(fn=command):
                try:
                    win.destroy()
                except tk.TclError:pass
                self.aqua_menu=None
                fn()
            b=tk.Button(panel,text=symbol+'   '+hint,command=invoke,anchor='w',
                        bg='#103b5c',fg='#d8faff',activebackground='#2c7196',
                        activeforeground='white',relief='flat',bd=0,
                        font=('Segoe UI',9,'bold'),cursor='hand2')
            b.pack(fill='x',padx=5,pady=3,ipady=3)
        win.bind('<Escape>',lambda event:self.toggle_aqua_menu())
        # Short vertical bubble reveal. Schedule, never sleep inside GUI.
        def grow(step=1):
            try:
                if self.aqua_menu is not win or not win.winfo_exists():return
                height=min(221,int(1+(221-1)*step/12))
                win.geometry(f'178x{height}+{x}+{y}')
                if step<12:win.after(18,lambda:grow(step+1))
            except tk.TclError:pass
        grow()
"""
def build(src,out):
    if hashlib.sha256(Path(src).read_bytes()).hexdigest()!=SOURCE_SHA:
        raise ValueError('Verified v2.2.6 baseline required')
    out=Path(out);out.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(src) as zin,zipfile.ZipFile(out,'w') as zout:
        if zin.testzip() is not None:raise ValueError('Invalid base ZIP')
        names=zin.namelist()
        for obj in zin.infolist():
            content=zin.read(obj.filename)
            if obj.filename=='app/robot_app.py':
                code=content.decode('utf-8')
                a=code.index(OLD_BEGIN)
                b=code.index(OLD_END,a)+len(OLD_END)
                if code[a:b].count("self.minimize")!=1 or code[a:b].count('for idx')!=1:
                    raise ValueError('Unexpected button layout')
                code=code[:a]+NEW_BUTTONS.rstrip()+code[b:]
                entry='    def _hover_button(self, idx, entering):'
                if code.count(entry)!=1:raise ValueError('No GUI insertion anchor')
                code=code.replace(entry,NEW_METHODS+'\n'+entry)
                # Button remains visible over the 3D sprite's glass belly.
                code=code.replace("window=btn,width=19,height=19","window=btn,width=23,height=23")
                code=code.replace("wid=self.main.create_window(x,140,","wid=self.main.create_window(x,132,")
                # Menu safely closes when robot is hidden, avoiding a stray floating window.
                mark="    def minimize(self):"
                if code.count(mark)!=1:raise ValueError('No minimize method')
                code=code.replace(mark,
                    "    def minimize(self):\n"
                    "        if getattr(self,'aqua_menu',None) is not None:\n"
                    "            try:self.aqua_menu.destroy()\n"
                    "            except tk.TclError:pass\n"
                    "            self.aqua_menu=None\n")
                compile(code,'robot_app.py','exec')
                content=code.encode('utf-8')
            if obj.filename=='app/robot_core.py':
                code=content.decode('utf-8')
                old="APP_VERSION = '2.2.6'"
                if code.count(old)!=1:raise ValueError('Unexpected version')
                code=code.replace(old,"APP_VERSION = '2.2.7'")
                compile(code,'robot_core.py','exec')
                content=code.encode('utf-8')
            if obj.filename.startswith('app/assets/frame_') and obj.filename.endswith('.png'):
                num=int(Path(obj.filename).stem.split('_')[-1])
                buffer=io.BytesIO()
                aqua_frame(num%20).save(buffer,format='PNG',optimize=True)
                content=buffer.getvalue()
            zout.writestr(obj,content)
    with zipfile.ZipFile(out) as z:
        assert z.testzip() is None
        assert b"Open aqua menu" in z.read('app/robot_app.py')
        assert z.namelist()==names
    manifest={'version':'2.2.7','zip':out.name,
              'sha256':hashlib.sha256(out.read_bytes()).hexdigest()}
    (out.parent/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print('PASS',json.dumps(manifest))
if __name__=='__main__':
    build(sys.argv[1],sys.argv[2])
