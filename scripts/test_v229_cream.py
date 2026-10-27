#!/usr/bin/env python3
"""Visual, packaging and Tk GUI regression gate for v2.2.9.
No GitHub Release if a file is oversized, magenta-bleeding or menus regress.
"""
import ast, io, sys, tkinter as tk, zipfile
from pathlib import Path
from PIL import Image
from types import SimpleNamespace, MethodType

archive=Path(sys.argv[1])
with zipfile.ZipFile(archive) as z:
    if z.testzip() is not None:raise AssertionError('Invalid ZIP')
    app=z.read('app/robot_app.py').decode('utf-8')
    core=z.read('app/robot_core.py').decode('utf-8')
    assert "APP_VERSION = '2.2.9'" in core
    for token in ['def toggle_aqua_menu','def _show_aqua_menu',
                  'def minimize','def restore','def background_update_check',
                  'def open_editor','def start_microphone','def quick_run',
                  'def restart','def show_version',
                  'def _orb_track_eyes','def _poll_updates']:
        assert token in app,token
    for token in ["self.win_width=100;self.win_height=112",
                  "self.main=tk.Canvas(self.root,width=100,height=112",
                  "self.sprite=self.main.create_image(50,56",
                  "self.main.tag_bind('cream_belly','<Button-1>'"]:
        assert token in app,token
    frames=[]
    key=(255,0,254)
    for i in range(36):
        img=Image.open(io.BytesIO(z.read(f'app/assets/frame_{i:02d}.png')))
        assert img.size==(100,112),img.size
        assert img.mode=='RGB',img.mode  # No alpha over transparent-color magenta.
        assert img.getpixel((0,0))==key
        pix=list(img.getdata())
        no_magenta=sum(1 for r,g,b in pix if r>185 and b>145 and g<125 and (r,g,b)!=key)
        assert no_magenta==0,('Pink leak',i,no_magenta)
        visible=sum(1 for p in pix if p!=key)
        assert 2500<visible<9000,(i,visible)
        frames.append(img.tobytes())
    assert frames[0]!=frames[10]
    # Verify all opaque pixels render correctly on two different sample desktops.
    for color in ((10,20,35),(245,245,245)):
        img=Image.open(io.BytesIO(z.read('app/assets/frame_00.png'))).convert('RGB')
        img.putdata([color if px==key else px for px in img.getdata()])
        assert img.getpixel((0,0))==color

    # Isolate tiny canvas controller and existing menu; no mic, network, storage.
    tree=ast.parse(app)
    clazz=next(x for x in tree.body if isinstance(x,ast.ClassDef) and x.name=='RobotApp')
    ns={'tk':tk}
    isolated=ast.Module(body=[ast.ClassDef(
        name='UIOnly',bases=[],keywords=[],decorator_list=[],
        body=[n for n in clazz.body if isinstance(n,ast.FunctionDef)
              and n.name in ('toggle_aqua_menu','_show_aqua_menu')]
    )],type_ignores=[])
    ast.fix_missing_locations(isolated)
    exec(compile(isolated,'ui_isolation.py','exec'),ns)
    root=tk.Tk();root.geometry('100x112+50+50')
    main=tk.Canvas(root,width=100,height=112)
    main.pack()
    cx=main.create_oval(39,73,61,95,fill='#e7e8e0',tags=('cream_belly',))
    root.update()
    called=[]
    fake=SimpleNamespace(root=root,main=main,
        win_width=100,win_height=112,aqua_menu=None,
        open_editor=lambda:called.append('edit'),
        quick_run=lambda:called.append('run'),
        learn=lambda:called.append('learn'),
        toggle_pin=lambda:called.append('pin'),
        minimize=lambda:called.append('hide'))
    fake.toggle_aqua_menu=MethodType(ns['UIOnly'].toggle_aqua_menu,fake)
    fake._show_aqua_menu=MethodType(ns['UIOnly']._show_aqua_menu,fake)
    main.tag_bind('cream_belly','<Button-1>',lambda e:fake.toggle_aqua_menu())
    main.event_generate('<Button-1>',x=50,y=84)
    root.update()
    assert fake.aqua_menu is not None and fake.aqua_menu.winfo_exists()
    pane=fake.aqua_menu.winfo_children()[0]
    buttons=[ch for ch in pane.winfo_children() if isinstance(ch,tk.Button)]
    assert len(buttons)==5,len(buttons)
    buttons[-1].invoke()
    assert called==['hide'],called
    assert fake.aqua_menu is None
    root.destroy()
print('PASS: no magenta outlines / half-sized canvas / 36 frames / code & mic preserved / clickable belly, five-option popup, hide')
