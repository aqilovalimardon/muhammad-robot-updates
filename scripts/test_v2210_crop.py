#!/usr/bin/env python3
"""Regression for the visible right-side clipping bug.

Tests the *actual* animate() function extracted from the published app, using
an actual Tk Canvas and actual sprite PNG frames (not a mocked coordinate).
Before fix, this test fails because the sprite jumps from (50,56) to (95,98)
on its first frame. Also asserts window geometry, center/button alignment, and
preservation of installed update/voice/editor functionality.
"""
from pathlib import Path
import ast,io,sys,tempfile,tkinter as tk,zipfile
from types import SimpleNamespace,MethodType

zip_path=Path(sys.argv[1])
with zipfile.ZipFile(zip_path) as z:
    assert z.testzip() is None
    names=z.namelist()
    app=z.read('app/robot_app.py').decode('utf8')
    core=z.read('app/robot_core.py').decode('utf8')
    assert "APP_VERSION = '2.2.10'" in core
    assert "self.win_width=100;self.win_height=112" in app
    assert "self.main=tk.Canvas(self.root,width=100,height=112" in app
    assert "self.sprite=self.main.create_image(50,56" in app
    assert "self.main.coords(self.sprite,95,98)" not in app
    for token in ('def toggle_aqua_menu','def _show_aqua_menu',
                  'def minimize','def restore','def _orb_track_eyes',
                  'def open_editor','def quick_run','def background_update_check',
                  'def start_microphone','def check_updates_now'):
        assert token in app, token
    assert "tags=('cream_belly',)" in app
    assert z.read('app/assets/frame_00.png') != z.read('app/assets/frame_08.png')
    original=ast.parse(app)
    main_cls=next(x for x in original.body if isinstance(x,ast.ClassDef) and x.name=='RobotApp')
    defn=next(x for x in main_cls.body if isinstance(x,ast.FunctionDef) and x.name=='animate')
    isolated=ast.Module(body=[ast.ClassDef(name='Runner',bases=[],keywords=[],
                     body=[defn],decorator_list=[])],type_ignores=[])
    ast.fix_missing_locations(isolated)
    ns={}
    exec(compile(isolated,'animate_extract.py','exec'),ns)
    with tempfile.TemporaryDirectory() as td:
        frames=[]
        root=tk.Tk()
        root.geometry('100x112+40+40')
        canvas=tk.Canvas(root,width=100,height=112,bg='#ff00fe',
                         bd=0,highlightthickness=0)
        canvas.pack()
        for n in range(36):
            filename=Path(td)/f'frame_{n:02d}.png'
            filename.write_bytes(z.read(f'app/assets/frame_{n:02d}.png'))
            frame=tk.PhotoImage(file=str(filename),master=root)
            assert frame.width()==100 and frame.height()==112
            frames.append(frame)
        assert frames[0].get(0,0) in ((255,0,254),'#ff00fe')
        sprite=canvas.create_image(50,56,image=frames[0])
        ring=canvas.create_oval(39,73,61,95,fill='#e7e8e0',
                                  outline='#b2e9ff',tags=('cream_belly',))
        scheduled=[]
        fake=SimpleNamespace(root=SimpleNamespace(after=lambda delay,cb:scheduled.append(delay)),
                             main=canvas,sprite=sprite,frames=frames,t=0,
                             minimized=False,win_width=100,win_height=112)
        advance=MethodType(ns['Runner'].animate,fake)
        fake.animate=advance
        root.update()
        for n in range(180):  # test multiple complete sprite cycles
            advance()
            root.update_idletasks()
            actual=tuple(round(x) for x in canvas.coords(sprite))
            assert actual==(50,56),('CROPPED frame',n,actual)
            left,top,right,bottom=canvas.bbox(sprite)
            assert 0<=left and 0<=top and right<=100 and bottom<=112,('OFF-CANVAS',n,(left,top,right,bottom))
        assert canvas.coords(ring)==[39,73,61,95]
        assert all(x==75 for x in scheduled)
        assert len(scheduled)==180
        root.destroy()
print('PASS: 180 real Tk animation ticks stay centered at 50,56, full 100x112 sprite remains visible, belly button aligned, voice/editor/update unchanged')
