#!/usr/bin/env python3
"""Release blocker: test body and eyes together, plus actual desktop updater cap."""
import ast,hashlib,io,json,re,sys,tkinter as tk,zipfile,tempfile
from pathlib import Path
from PIL import Image,ImageChops
from types import SimpleNamespace,MethodType

installed=Path(sys.argv[1])
new=Path(sys.argv[2])
manifest=json.loads((new.parent/'manifest.json').read_text('utf8'))
# The same validator currently installed on Muhammad's laptop.
with zipfile.ZipFile(installed) as z:
    source=z.read('app/robot_core.py').decode('utf8')
t=ast.parse(source)
funcs=[n for n in t.body if isinstance(n,ast.FunctionDef)
       and n.name in ('inspect_release','version_tuple')]
cls=ast.ClassDef(name='UpdateError',bases=[ast.Name(id='Exception',ctx=ast.Load())],
                 keywords=[],body=[ast.Pass()],decorator_list=[])
module=ast.Module(body=[cls]+funcs,type_ignores=[])
ast.fix_missing_locations(module)
ctx={'hashlib':hashlib,'zipfile':zipfile,'Path':Path,'re':re,
     'VERSION_RE':re.compile(r'^\d+\.\d+\.\d+$')}
exec(compile(module,'installed_updater.py','exec'),ctx)
assert ctx['inspect_release'](manifest,new)
print('PASS: Existing v2.2.10 safety validator accepts v2.2.13, no bypass')
with zipfile.ZipFile(new) as z:
    assert z.testzip() is None and len(z.infolist())==84
    app=z.read('app/robot_app.py').decode('utf8')
    core=z.read('app/robot_core.py').decode('utf8')
    assert "APP_VERSION = '2.2.13'" in core
    for method in ('def animate(self):','def switch_robot_look(self):',
                   'def toggle_aqua_menu(self):','def open_editor(self):',
                   'def start_microphone(self):','def background_update_check(',
                   'def quick_run(self):','def _orb_track_eyes(self):'):
        assert method in app,method
    assert 'index=(variant*8+(self.t//2)%8)%len(self.frames)' in app
    assert 'self.main.coords(self.sprite,self.win_width//2,self.win_height//2)' in app
    arts=[Image.open(io.BytesIO(z.read(f'app/assets/frame_{i:03d}.png'))).convert('RGB') for i in range(72)]
    for i,im in enumerate(arts):
        assert im.size==(100,112) and im.getpixel((0,0))==(255,0,254)
        px=im.load()
        # Compact full cream body must exist BELOW visor, not isolated pupils.
        torso=sum(
            max(r,g,b)>145 and min(r,g,b)>80 and (r,g,b)!=(255,0,254)
            for y in range(70,104) for x in range(27,73)
            for r,g,b in [px[x,y]])
        assert torso>400,(i,'Torso missing',torso)
        # Dark original visor is inside the head and doesn't extend beyond it.
        face=sum(
            r<100 and g<110 and b<125 and (r,g,b)!=(255,0,254)
            for y in range(35,73) for x in range(24,76)
            for r,g,b in [px[x,y]])
        assert face>110,(i,'Face missing',face)
        visible=sum(p!=(255,0,254) for p in im.getdata())
        assert 2600<visible<9000,(i,visible)
        bad=sum(1 for r,g,b in im.getdata()
                if r>225 and g<75 and b>195 and (r,g,b)!=(255,0,254))
        assert bad==0,(i,'pink edge present',bad)
    assert ImageChops.difference(arts[0],arts[8]).getbbox(), 'Eyes do not move'
    assert ImageChops.difference(arts[8],arts[16]).getbbox(), 'No right gaze'
    assert ImageChops.difference(arts[0],arts[1]).getbbox(), 'No idle motion'
    # Test that real Tk animation references full 100 x 112 frames consistently.
    tree=ast.parse(app)
    cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='RobotApp')
    animate=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='animate')
    s=ast.Module(body=[ast.ClassDef(name='Runner',bases=[],keywords=[],
       body=[animate],decorator_list=[])],type_ignores=[])
    ast.fix_missing_locations(s)
    ctx2={'tk':tk,'math':__import__('math')}
    exec(compile(s,'animate.py','exec'),ctx2)
    with tempfile.TemporaryDirectory() as td:
        d=Path(td)
        root=tk.Tk();root.geometry('100x112+130+90')
        canvas=tk.Canvas(root,width=100,height=112,
                         bg='#ff00fe',bd=0,highlightthickness=0)
        canvas.pack()
        img=[]
        for i in range(72):
            f=d/f'{i:03d}.png'; f.write_bytes(z.read(f'app/assets/frame_{i:03d}.png'))
            img.append(tk.PhotoImage(file=str(f),master=root))
        handle=canvas.create_image(50,56,image=img[0])
        ring=canvas.create_oval(39,73,61,95,tags=('cream_belly',))
        root.update()
        class Proxy:
            def winfo_pointerxy(self):return (155,150)
            def winfo_rootx(self):return 130
            def winfo_rooty(self):return 90
            def after(self,ms,fn):pass
        proxy=Proxy()
        fake=SimpleNamespace(root=proxy,main=canvas,frames=img,sprite=handle,
             win_width=100,win_height=112,minimized=False,t=0,belly_ring=ring,
             _cream_style='living',_drag_sway=0,_drag_dir=0,_talk_ticks=0,
             _cream_variants={n:i for i,n in enumerate(
               ('center','left','right','up','down','blink','happy','tilt_left','tilt_right'))})
        fake.animate=MethodType(ctx2['Runner'].animate,fake)
        for _ in range(160):
            fake.animate()
            assert canvas.coords(handle)==[50.0,56.0]
        root.destroy()
print('PASS: face, body, eyes are co-located; Windows transparency; 72 frames; 160 real Tk ticks; other code unchanged')
