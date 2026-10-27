#!/usr/bin/env python3
"""Block publication unless front-facing cream body, antenna sway and update safety pass."""
import ast,hashlib,io,json,re,sys,tkinter as tk,zipfile,tempfile
from pathlib import Path
from PIL import Image,ImageChops
from types import MethodType,SimpleNamespace
old=Path(sys.argv[1]);new=Path(sys.argv[2])
manifest=json.loads((new.parent/'manifest.json').read_text('utf8'))
with zipfile.ZipFile(old) as z:
    tree=ast.parse(z.read('app/robot_core.py').decode())
functions=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('inspect_release','version_tuple')]
klass=ast.ClassDef(name='UpdateError',bases=[ast.Name(id='Exception',ctx=ast.Load())],keywords=[],body=[ast.Pass()],decorator_list=[])
mod=ast.Module(body=[klass]+functions,type_ignores=[])
ast.fix_missing_locations(mod)
ns={'hashlib':hashlib,'zipfile':zipfile,'Path':Path,'re':re,'VERSION_RE':re.compile(r'^\d+\.\d+\.\d+$')}
exec(compile(mod,'installed_validator.py','exec'),ns)
assert ns['inspect_release'](manifest,new)
print('PASS: deployed v2.2.10 ZIP validator accepts release')
with zipfile.ZipFile(new) as z:
    assert len(z.namelist())==84 and z.testzip() is None
    s=z.read('app/robot_app.py').decode()
    assert "APP_VERSION = '2.2.14'" in z.read('app/robot_core.py').decode()
    for marker in ('def animate(self):','def switch_robot_look(self):','def minimize(self):',
                   'def open_editor(self):','def quick_run(self):',
                   'def background_update_check(self, manual=False):',
                   'def _orb_track_eyes(self):','def _show_aqua_menu(self):'):
        assert marker in s,marker
    frames=[Image.open(io.BytesIO(z.read(f'app/assets/frame_{i:03d}.png'))).convert('RGB') for i in range(72)]
    for n,img in enumerate(frames):
        assert img.size==(100,112) and img.getpixel((0,0))==(255,0,254)
        p=img.load()
        # The whole robot's torso must remain continuous below original visor.
        cream=sum(1 for y in range(76,103) for x in range(30,72)
                  if p[x,y]!=(255,0,254) and min(p[x,y])>90)
        assert cream>440,('missing cream body',n,cream)
        # Face dark region has to stay inside head, not separated.
        dark=sum(1 for y in range(42,75) for x in range(33,70)
                 if p[x,y]!=(255,0,254) and max(p[x,y])<105)
        assert dark>70,('missing face',n,dark)
        pink=sum(1 for r,g,b in img.getdata()
                 if (r,g,b)!=(255,0,254) and r>200 and b>170 and g<80)
        assert pink==0,('pink fringe',n,pink)
    assert ImageChops.difference(frames[0],frames[2]).getbbox(), 'antenna not moving'
    assert ImageChops.difference(frames[0],frames[8]).getbbox(), 'eyes not moving'
    print('PASS: 72 intact original-style cream robot frames; antenna and eyes visibly change')
    tree=ast.parse(s)
    clazz=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='RobotApp')
    animate=next(n for n in clazz.body if isinstance(n,ast.FunctionDef) and n.name=='animate')
    isolated=ast.Module(body=[ast.ClassDef(name='Runner',bases=[],keywords=[],
          body=[animate],decorator_list=[])],type_ignores=[])
    ast.fix_missing_locations(isolated)
    env={'tk':tk,'math':__import__('math')}
    exec(compile(isolated,'test_animation.py','exec'),env)
    with tempfile.TemporaryDirectory() as td:
        root=tk.Tk();root.geometry('100x112+110+80')
        canvas=tk.Canvas(root,width=100,height=112,bg='#ff00fe',highlightthickness=0,bd=0);canvas.pack()
        photos=[]
        for i in range(72):
            filename=Path(td)/f'{i:03d}.png'
            filename.write_bytes(z.read(f'app/assets/frame_{i:03d}.png'))
            photos.append(tk.PhotoImage(file=str(filename)))
        sprite=canvas.create_image(50,56,image=photos[0])
        ring=canvas.create_oval(39,73,61,95)
        root.update()
        class Root:
            def winfo_pointerxy(self):return (145,135)
            def winfo_rootx(self):return 110
            def winfo_rooty(self):return 80
            def after(self,*args):pass
        state=SimpleNamespace(main=canvas,root=Root(),frames=photos,sprite=sprite,
          win_width=100,win_height=112,belly_ring=ring,minimized=False,t=0,
          _cream_style='living',_drag_sway=0,_drag_dir=0,_talk_ticks=0,
          _cream_variants={m:i for i,m in enumerate(('center','left','right','up','down','blink','happy','tilt_left','tilt_right'))})
        state.animate=MethodType(env['Runner'].animate,state)
        for _ in range(190):
            state.animate()
            assert canvas.coords(sprite)==[50.0,56.0]
        root.destroy()
print('PASS: 190 real animation steps without crop; 84 entry package; voice/editor untouched')
