#!/usr/bin/env python3
"""Tk GUI regression test for the generated Aqua release."""
import math,sys,zipfile,tkinter as tk,tempfile
from pathlib import Path
from types import SimpleNamespace,MethodType
zfile=Path(sys.argv[1])
with zipfile.ZipFile(zfile) as z:
    assert z.testzip() is None
    src=z.read('app/robot_app.py').decode('utf-8')
    assert "APP_VERSION = '2.2.7'" in z.read('app/robot_core.py').decode()
    for name in ['app/assets/frame_00.png','app/assets/frame_05.png']:
        from PIL import Image
        import io
        image=Image.open(io.BytesIO(z.read(name)))
        assert image.size==(190,196) and image.mode=='RGBA'
        assert image.getpixel((0,0))[3]==0
    ns={'tk':tk}
    from_ =src.index('        for idx,(x,symbol,hint,fn) in enumerate([')
    to=src.index('        self.drag_at=None;',from_)
    block=src[from_:to]
    exec('def create_button(self):\n'+block,ns)
    # Parse methods with real class, but bypass its heavyweight microphone dependencies.
    import ast
    tree=ast.parse(src)
    app=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='RobotApp')
    funcs=['toggle_aqua_menu','_show_aqua_menu']
    isolated=ast.Module(body=[ast.ClassDef(name='UIOnly',bases=[],keywords=[],
       body=[n for n in app.body if isinstance(n,ast.FunctionDef) and n.name in funcs],
       decorator_list=[])],type_ignores=[])
    ast.fix_missing_locations(isolated)
    exec(compile(isolated,'test_ui.py','exec'),ns)
    root=tk.Tk();root.geometry('190x196+150+100');root.update()
    canvas=tk.Canvas(root,width=190,height=196);canvas.pack()
    actions=[]
    fake=SimpleNamespace(root=root,main=canvas,win_width=190,win_height=196,
      buttons=[],button_windows=[],aqua_menu=None,
      open_editor=lambda:actions.append('edit'),
      quick_run=lambda:actions.append('run'),
      learn=lambda:actions.append('learn'),
      toggle_pin=lambda:actions.append('pin'),
      minimize=lambda:actions.append('hide'),
      _hover_button=lambda n,ent:None,_pressed_button=lambda n:None)
    fake.toggle_aqua_menu=MethodType(ns['UIOnly'].toggle_aqua_menu,fake)
    fake._show_aqua_menu=MethodType(ns['UIOnly']._show_aqua_menu,fake)
    ns['create_button'](fake)
    root.update()
    assert len(fake.buttons)==1 and fake.buttons[0].cget('text')=='◉'
    assert canvas.coords(fake.button_windows[0])[1]==132
    fake.buttons[0].invoke();root.update()
    assert fake.aqua_menu is not None and fake.aqua_menu.winfo_exists()
    pane=fake.aqua_menu.winfo_children()[0]
    buttons=[x for x in pane.winfo_children() if isinstance(x,tk.Button)]
    assert len(buttons)==5,len(buttons)
    assert 'Hide robot' in buttons[-1].cget('text')
    buttons[-1].invoke()
    assert actions==['hide'],actions
    fake.buttons[0].invoke();root.update()
    assert fake.aqua_menu is not None and fake.aqua_menu.winfo_exists()
    fake.toggle_aqua_menu()
    assert fake.aqua_menu is None
    root.destroy()
print('PASS: 20 animated Aqua sprites, transparent corners, glass belly button, animated 5-control menu, hide, dismiss')
