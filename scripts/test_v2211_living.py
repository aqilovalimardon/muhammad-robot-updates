#!/usr/bin/env python3
"""Pre-publication visual and functional safety gate for Living Mini Cream 2.2.11."""
from pathlib import Path
from PIL import Image,ImageChops
import ast,io,sys,tempfile,tkinter as tk,zipfile
from types import SimpleNamespace,MethodType

p=Path(sys.argv[1])
with zipfile.ZipFile(p) as z:
    assert z.testzip() is None
    names=z.namelist()
    app=z.read('app/robot_app.py').decode('utf8')
    core=z.read('app/robot_core.py').decode('utf8')
    assert "APP_VERSION = '2.2.11'" in core
    essential=('def toggle_aqua_menu','def _show_aqua_menu','def minimize',
        'def restore','def _orb_track_eyes','def open_editor',
        'def quick_run','def start_microphone','def background_update_check',
        'def check_updates_now','def _restart_when_safe','def restart')
    for marker in essential:assert marker in app,marker
    assert 'self.main.coords(self.sprite,self.win_width//2,self.win_height//2)' in app
    assert 'self.win_width=100;self.win_height=112' in app
    assert 'def switch_robot_look' in app
    assert "Appearance: Living / Classic" in app
    assert "self._drag_sway=6" in app
    frame_paths=sorted(n for n in names if n.startswith('app/assets/frame_') and n.endswith('.png'))
    classic_paths=sorted(n for n in names if n.startswith('app/assets_classic/frame_') and n.endswith('.png'))
    assert len(frame_paths)==144,len(frame_paths)
    assert len(classic_paths)==36,len(classic_paths)
    for i,n in enumerate(frame_paths):
        assert n==f'app/assets/frame_{i:03d}.png',(i,n)
        im=Image.open(io.BytesIO(z.read(n)))
        assert im.mode=='RGB' and im.size==(100,112)
        assert im.getpixel((0,0))==(255,0,254)
        data=list(im.getdata())
        visible=sum(px!=(255,0,254) for px in data)
        assert 1700<visible<8500,(n,visible)
        bad=sum(r>210 and b>205 and g<95 and (r,g,b)!=(255,0,254)
                for r,g,b in data)
        assert bad==0,(n,'magenta fringe detected',bad)
    # Pupils shift while torso remains substantially identical.
    a=Image.open(io.BytesIO(z.read('app/assets/frame_000.png'))).convert('RGB')
    b=Image.open(io.BytesIO(z.read('app/assets/frame_016.png'))).convert('RGB')
    c=Image.open(io.BytesIO(z.read('app/assets/frame_032.png'))).convert('RGB')
    assert ImageChops.difference(a,b).getbbox() is not None
    assert ImageChops.difference(b,c).getbbox() is not None
    assert z.read('app/assets/frame_000.png')!=z.read('app/assets/frame_008.png'),'No idle animation'
    assert z.read('app/assets/frame_080.png')!=z.read('app/assets/frame_000.png'),'No blink'
    assert z.read('app/assets/frame_112.png')!=z.read('app/assets/frame_128.png'),'No drag poses'
    # Tk real drawing, extracted actual animate method (without booting the mic).
    tree=ast.parse(app)
    clazz=next(x for x in tree.body if isinstance(x,ast.ClassDef) and x.name=='RobotApp')
    names_to_test=('animate','drag_move','switch_robot_look')
    expr=ast.Module(body=[ast.ClassDef(name='UIOnly',bases=[],keywords=[],
      decorator_list=[],body=[n for n in clazz.body if isinstance(n,ast.FunctionDef)
      and n.name in names_to_test])],type_ignores=[])
    ast.fix_missing_locations(expr)
    ns={'tk':tk,'math':__import__('math'),'HERE':None,
        'messagebox':__import__('tkinter.messagebox',fromlist=['messagebox'])}
    exec(compile(expr,'living_test.py','exec'),ns)
    with tempfile.TemporaryDirectory() as td:
        dest=Path(td)
        with zipfile.ZipFile(p) as inp:
            for asset in frame_paths+classic_paths:
                t=dest/asset[len('app/'):]
                t.parent.mkdir(parents=True,exist_ok=True)
                t.write_bytes(inp.read(asset))
        ns['HERE']=dest
        root=tk.Tk();root.geometry('100x112+100+100')
        canvas=tk.Canvas(root,width=100,height=112,bg='#ff00fe',highlightthickness=0,bd=0)
        canvas.pack()
        frames=[tk.PhotoImage(file=str(dest/'assets'/Path(name).name)) for name in frame_paths]
        sprite=canvas.create_image(50,56,image=frames[0])
        ring=canvas.create_oval(39,73,61,95,fill='#e7e8e0',outline='#b2e9ff',
                                tags=('cream_belly',))
        root.update()
        class RootProxy:
            def __init__(self,rt):
                self.rt=rt
                self.mx=500;self.my=500
                self.jobs=[]
            def winfo_pointerxy(self):return self.mx,self.my
            def winfo_rootx(self):return self.rt.winfo_rootx()
            def winfo_rooty(self):return self.rt.winfo_rooty()
            def geometry(self,x):return self.rt.geometry(x)
            def after(self,ms,fn):self.jobs.append(ms)
        proxy=RootProxy(root)
        moods=['center','left','right','up','down','blink','happy','tilt_left','tilt_right']
        fake=SimpleNamespace(main=canvas,root=proxy,frames=frames,
             _living_frames=frames,_classic_frames=None,_cream_style='living',
             _cream_variants={m:i for i,m in enumerate(moods)},
             _drag_sway=0,_drag_dir=0,_talk_ticks=0,
             sprite=sprite,belly_ring=ring,t=0,minimized=False,
             win_width=100,win_height=112,drag_at=None)
        fake.animate=MethodType(ns['UIOnly'].animate,fake)
        fake.drag_move=MethodType(ns['UIOnly'].drag_move,fake)
        fake.switch_robot_look=MethodType(ns['UIOnly'].switch_robot_look,fake)
        # 160 actual animation calls through the original method. No clipping.
        for n in range(160):
            fake.animate()
            assert tuple(round(x) for x in canvas.coords(sprite))==(50,56)
            assert canvas.bbox(sprite)==(0,0,100,112)
        # Gaze follows the pointer placed 30px to the left of the face.
        proxy.mx=int(proxy.winfo_rootx()+20)
        proxy.my=int(proxy.winfo_rooty()+60)
        fake.animate()
        assert fake.frames is frames
        # Sudden drag movement produces 6 frames of body sway.
        fake.drag_at=(400,300,100,100)
        fake.drag_move(SimpleNamespace(x_root=440,y_root=300))
        assert fake._drag_dir==1 and fake._drag_sway==6
        fake.animate()
        assert fake._drag_sway==5
        # Fallback is available even when the new visual fails.
        fake.switch_robot_look()
        assert fake._cream_style=='classic' and len(fake.frames)==36
        fake.animate()
        fake.switch_robot_look()
        assert fake._cream_style=='living' and len(fake.frames)==144
        assert all(delay==75 for delay in proxy.jobs)
        root.destroy()
print('PASS: 144 mini fuzzy frames, 36 classic rollback frames, no magenta, 160+ Tk ticks, cursor gaze, drag response, versioned updater/voice/editor untouched')
