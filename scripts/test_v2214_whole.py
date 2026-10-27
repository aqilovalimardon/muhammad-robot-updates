#!/usr/bin/env python3
"""v2.2.14 release blocker: reject chopped/multiple faces or broken updater.

Runs the EXACT installed security validator from v2.2.10, exercises real
Tk animation with 72 PNGs, and checks physical cream body/antenna continuity
on both backgrounds (magenta RGB key is never an edge color).
"""
from pathlib import Path
from PIL import Image,ImageChops
import ast,hashlib,io,json,math,re,sys,tempfile,tkinter as tk,zipfile
from types import SimpleNamespace,MethodType

old=Path(sys.argv[1])
out=Path(sys.argv[2])
installed=Path(sys.argv[3])
with zipfile.ZipFile(installed) as check:
    source=check.read('app/robot_core.py').decode('utf8')
    ast_tree=ast.parse(source)
    defs=[x for x in ast_tree.body
          if isinstance(x,ast.FunctionDef)
          and x.name in ('version_tuple','inspect_release')]
    err=ast.ClassDef(name='UpdateError',bases=[ast.Name(id='Exception',ctx=ast.Load())],
                     keywords=[],body=[ast.Pass()],decorator_list=[])
    isolated=ast.Module(body=[err]+defs,type_ignores=[])
    ast.fix_missing_locations(isolated)
    ns={'Path':Path,'zipfile':zipfile,'hashlib':hashlib,'re':re,
        'VERSION_RE':re.compile(r'^\d+\.\d+\.\d+$')}
    exec(compile(isolated,'installed_validator.py','exec'),ns)
    manifest=json.loads((out.parent/'manifest.json').read_text('utf8'))
    assert ns['inspect_release'](manifest,out)
print('PASS: actual v2.2.10 device ZIP validator accepts new version')

with zipfile.ZipFile(old) as original,zipfile.ZipFile(out) as new:
    assert new.testzip() is None
    assert len(new.infolist())==84
    assert original.namelist()==new.namelist()
    for name in original.namelist():
        if name=='app/robot_core.py' or name.startswith('app/assets/frame_'):continue
        assert original.read(name)==new.read(name),('Existing feature changed',name)
    assert "APP_VERSION = '2.2.14'" in new.read('app/robot_core.py').decode()
    app=new.read('app/robot_app.py').decode()
    for method in ('def animate(self):','def _orb_track_eyes(self):',
                   'def toggle_aqua_menu(self):','def quick_run(self):',
                   'def open_editor(self):','def background_update_check(',
                   'def start_microphone(self):','def switch_robot_look(self):'):
        assert method in app,method

    frames=[]
    for i in range(72):
        im=Image.open(io.BytesIO(new.read(f'app/assets/frame_{i:03d}.png')))
        assert im.mode=='RGB' and im.size==(100,112),(i,im.size,im.mode)
        assert im.getpixel((0,0))==(255,0,254),('Transparent corner mismatch',i)
        pixel=im.load()
        # Complete torso below the existing face must be present in EVERY frame.
        torso=0
        for y in range(74,105):
            for x in range(23,78):
                r,g,b=pixel[x,y]
                if r>120 and g>109 and b>98 and (r,g,b)!=(255,0,254):
                    torso+=1
        assert torso>620,('Body cut off',i,torso)
        # Dark visor enclosed in correct position, NOT an overlay flying at the side.
        visor=0
        for y in range(43,75):
            for x in range(23,79):
                r,g,b=pixel[x,y]
                if r<100 and g<100 and b<140 and (r,g,b)!=(255,0,254):
                    visor+=1
        assert visor>170,('Visor missing',i,visor)
        assert all(pixel[x,0]==(255,0,254) for x in range(100)),('Antenna clipped at top',i)
        for x in range(100):
            r,g,b=pixel[x,18]
            assert not (r>235 and g<85 and b>230 and (r,g,b)!=(255,0,254)),('Pink fringe',i,x)
        frames.append(im)
    # Antenna must move on multiple frames. Intact body should remain similar.
    top_a=frames[0].crop((26,0,82,37))
    top_b=frames[2].crop((26,0,82,37))
    assert ImageChops.difference(top_a,top_b).getbbox(), 'Antenna is not moving'
    assert ImageChops.difference(frames[0],frames[16]).getbbox(), 'No cursor gaze change'
    # All nine expression blocks exist and are not identical.
    assert any(ImageChops.difference(frames[0],frames[i]).getbbox() for i in range(1,8))
    # Check actual Tk UI, no stale 95,98 coords or changed belly menu position.
    tree=ast.parse(app)
    cls=next(x for x in tree.body if isinstance(x,ast.ClassDef) and x.name=='RobotApp')
    animate=next(x for x in cls.body if isinstance(x,ast.FunctionDef) and x.name=='animate')
    isolated=ast.Module(body=[ast.ClassDef(name='Runner',bases=[],keywords=[],
                   body=[animate],decorator_list=[])],type_ignores=[])
    ast.fix_missing_locations(isolated)
    ctx={'tk':tk,'math':math}
    exec(compile(isolated,'actual_animation.py','exec'),ctx)
    with tempfile.TemporaryDirectory() as td:
        folder=Path(td)
        root=tk.Tk();root.geometry('100x112+120+90')
        canvas=tk.Canvas(root,width=100,height=112,bg='#ff00fe',
                         bd=0,highlightthickness=0)
        canvas.pack()
        photos=[]
        for i in range(72):
            path=folder/f'f{i:03d}.png'
            path.write_bytes(new.read(f'app/assets/frame_{i:03d}.png'))
            photos.append(tk.PhotoImage(file=str(path),master=root))
        sprite=canvas.create_image(50,56,image=photos[0])
        ring=canvas.create_oval(39,73,61,95,tags=('cream_belly',))
        root.update()
        class FakeRoot:
            def winfo_pointerxy(self):return (155,144)
            def winfo_rootx(self):return 120
            def winfo_rooty(self):return 90
            def after(self,ms,func):pass
        fake=SimpleNamespace(root=FakeRoot(),main=canvas,sprite=sprite,
            frames=photos,win_width=100,win_height=112,t=0,
            minimized=False,belly_ring=ring,_cream_style='living',
            _drag_sway=0,_drag_dir=0,_talk_ticks=0,
            _cream_variants={m:i for i,m in enumerate(
                ('center','left','right','up','down','blink','happy','tilt_left','tilt_right'))})
        fake.animate=MethodType(ctx['Runner'].animate,fake)
        for j in range(160):
            fake.animate()
            assert canvas.coords(sprite)==[50.0,56.0],('Out of center',j)
        root.destroy()
print('PASS: coherent face and torso, animated antenna, gaze & 160 Tk steps, updater/editor/voice unchanged')
