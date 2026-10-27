#!/usr/bin/env python3
"""GUI regression for real 3D 2.2.8 Aqua icon, menu, restore and alpha."""
import ast, io, sys, tempfile, zipfile, tkinter as tk
from pathlib import Path
from types import MethodType, SimpleNamespace
from PIL import Image
p=Path(sys.argv[1])
with zipfile.ZipFile(p) as z:
    assert z.testzip() is None
    code=z.read('app/robot_app.py').decode('utf-8')
    assert "APP_VERSION = '2.2.8'" in z.read('app/robot_core.py').decode()
    assert "TRANSPARENT='#ff00fe'" in code, 'Windows chroma key changed unexpectedly'
    assert 'self._orb_track_eyes()' in code, 'Restorable eye orb disappeared'
    for i in range(20):
        im=Image.open(io.BytesIO(z.read(f'app/assets/frame_{i:02}.png'))).convert('RGBA')
        assert im.size==(190,196)
        assert set(im.getchannel('A').getdata()).issubset({0,255})
        # Check that no bright pink is ever drawn in an opaque foreground pixel.
        for r,g,b,a in im.getdata():
            if a==255:assert not (r>230 and g<40 and b>210),(i,(r,g,b,a))
    # Extract real button setup and actual methods without starting mic or updater.
    first=code.index("        # Borderless canvas-drawn glass button;")
    last=code.index("        self.drag_at=None;",first)
    setup=code[first:last]
    ns={'tk':tk}
    exec('def setup(self):\n'+setup,ns)
    tree=ast.parse(code)
    app=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='RobotApp')
    funcs=['toggle_aqua_menu','_show_aqua_menu','_aqua_button_hover']
    cls=ast.Module(body=[ast.ClassDef(name='MiniUI',bases=[],keywords=[],
       body=[n for n in app.body if isinstance(n,ast.FunctionDef) and n.name in funcs],
       decorator_list=[])],type_ignores=[])
    ast.fix_missing_locations(cls)
    exec(compile(cls,'miniui.py','exec'),ns)
    root=tk.Tk();root.geometry('190x196+120+90')
    bg=tk.Canvas(root,width=190,height=196,bg='#ff00fe',bd=0,highlightthickness=0)
    bg.pack()
    actions=[]
    f=SimpleNamespace(root=root,main=bg,win_width=190,win_height=196,
      aqua_menu=None,
      open_editor=lambda:actions.append('edit'),
      quick_run=lambda:actions.append('run'),
      learn=lambda:actions.append('learn'),
      toggle_pin=lambda:actions.append('pin'),
      minimize=lambda:actions.append('hide'))
    for name in funcs:
        setattr(f,name,MethodType(getattr(ns['MiniUI'],name),f))
    ns['setup'](f)
    root.update()
    assert bg.type(f.aqua_button_bg)=='oval'
    assert bg.type(f.aqua_button_icon)=='text'
    f._aqua_button_hover(True)
    assert bg.itemcget(f.aqua_button_bg,'outline')=='#ffffff'
    f._aqua_button_hover(False)
    assert bg.itemcget(f.aqua_button_bg,'outline')=='#bbf9ff'
    # Clicking exactly on circle triggers popup without a rectangular Tk button.
    bg.event_generate('<Motion>',x=95,y=132,warp=True)
    root.update()
    bg.event_generate('<Button-1>',x=95,y=132)
    root.update()
    assert f.aqua_menu is not None and f.aqua_menu.winfo_exists(), 'Glass button not clickable'
    panel=f.aqua_menu.winfo_children()[0]
    controls=[c for c in panel.winfo_children() if isinstance(c,tk.Button)]
    assert len(controls)==5, len(controls)
    assert 'Hide robot' in controls[-1].cget('text')
    controls[-1].invoke()
    assert actions==['hide'],actions
    root.destroy()
print('PASS: real translucent-appearance art, NO partial/pink alpha, canvas clickable glass button, 5 menu actions, eye orb kept')
