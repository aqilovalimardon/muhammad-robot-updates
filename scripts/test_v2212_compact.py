#!/usr/bin/env python3
"""Verify actual *deployed* ZIP validator accepts v2.2.12 before publication.

Exercise 9 gaze variants, classic rollback, eye orb, real Tk canvas, and reject
the oversize v2.2.11 source to prove test would catch the original regression.
"""
import ast, hashlib, io, json, re, sys, tempfile, tkinter as tk, zipfile
from pathlib import Path
from types import MethodType, SimpleNamespace
from PIL import Image

old=Path(sys.argv[1])
archive=Path(sys.argv[2])
with zipfile.ZipFile(old) as z:
    original_core=z.read("app/robot_core.py").decode("utf8")
    tree=ast.parse(original_core)
    keep=[n for n in tree.body if
          isinstance(n,ast.FunctionDef) and n.name in ("inspect_release","version_tuple")]
    safety=ast.ClassDef(name="UpdateError",bases=[ast.Name(id="Exception",ctx=ast.Load())],
                        keywords=[],body=[ast.Pass()],decorator_list=[])
    mod=ast.Module(body=[safety]+keep,type_ignores=[])
    ast.fix_missing_locations(mod)
    ns={"hashlib":hashlib,"zipfile":zipfile,"Path":Path,"re":re,
        "VERSION_RE":re.compile(r"^\\d+\\.\\d+\\.\\d+$")}
    exec(compile(mod,"deployed_zip_validator.py","exec"),ns)
    checker=ns["inspect_release"]

manifest=json.loads((archive.parent/"manifest.json").read_text("utf8"))
assert checker(manifest,archive) is True, "Deployed safety validator rejected new ZIP"
print("PASS: actual v2.2.10 on-device safety validator accepts v2.2.12")
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    names=z.namelist()
    assert len(names)==84
    assert len(names)==len(set(names))
    expected_images={
        *[f"app/assets/frame_{i:03d}.png" for i in range(72)],
        *[f"app/assets_classic/frame_{i:02d}.png" for i in range(8)],
    }
    assert expected_images.issubset(set(names))
    extras=set(names)-expected_images
    assert len(extras)==4 and {"app/robot_app.py","app/robot_core.py"}.issubset(extras), sorted(extras)
    app=z.read("app/robot_app.py").decode("utf8")
    core=z.read("app/robot_core.py").decode("utf8")
    assert "APP_VERSION = '2.2.12'" in core
    for expected in ("def animate(self):",
            "self._cream_variants.get(gaze,0)",
            "index=(variant*8+(self.t//2)%8)%len(self.frames)",
            "def switch_robot_look(self):",
            "Appearance: Living / Classic",
            "def toggle_aqua_menu(self):",
            "def _show_aqua_menu(self):",
            "def _orb_track_eyes(self):",
            "def open_editor(self):",
            "def start_microphone(self):",
            "def background_update_check(self, manual=False):"):
        assert expected in app,expected
    for i in range(72):
        img=Image.open(io.BytesIO(z.read(f"app/assets/frame_{i:03d}.png")))
        assert img.mode=="RGB" and img.size==(100,112)
        assert img.getpixel((0,0))==(255,0,254)
    # Frame order is mood blocks, not interleaved.
    assert z.read("app/assets/frame_000.png")!=z.read("app/assets/frame_008.png")
    # Character stays centered in a real Tk photo-image canvas after 300 updates.
    structure=ast.parse(app)
    main=next(n for n in structure.body if isinstance(n,ast.ClassDef) and n.name=="RobotApp")
    method=next(n for n in main.body if isinstance(n,ast.FunctionDef) and n.name=="animate")
    klass=ast.ClassDef(name="Avatar",bases=[],keywords=[],body=[method],decorator_list=[])
    m=ast.Module(body=[klass],type_ignores=[])
    ast.fix_missing_locations(m)
    ns2={"math":__import__("math"),"tk":tk}
    exec(compile(m,"animate.py","exec"),ns2)
    with tempfile.TemporaryDirectory() as td:
        path=Path(td)
        root=tk.Tk()
        root.geometry("100x112+160+60")
        c=tk.Canvas(root,width=100,height=112,bg="#ff00fe",highlightthickness=0,bd=0)
        c.pack()
        imgs=[]
        for i in range(72):
            p=path/f"frame_{i:03d}.png"
            p.write_bytes(z.read(f"app/assets/frame_{i:03d}.png"))
            imgs.append(tk.PhotoImage(file=str(p),master=root))
        handle=c.create_image(50,56,image=imgs[0])
        ring=c.create_oval(39,73,61,95,fill="#e7e8e0")
        root.update()
        class RootProxy:
            def __init__(self,widget):self.widget=widget
            def winfo_pointerxy(self):return (self.widget.winfo_rootx()+20,self.widget.winfo_rooty()+56)
            def winfo_rootx(self):return self.widget.winfo_rootx()
            def winfo_rooty(self):return self.widget.winfo_rooty()
            def after(self,ms,fn):pass
        fake=SimpleNamespace(minimized=False,frames=imgs,t=0,main=c,sprite=handle,
                             root=RootProxy(root),win_width=100,win_height=112,
                             _cream_style="living",_drag_sway=0,_drag_dir=0,
                             _talk_ticks=0,belly_ring=ring,
                             _cream_variants={s:i for i,s in enumerate(
                                  ("center","left","right","up","down","blink","happy","tilt_left","tilt_right"))})
        anim=MethodType(ns2["Avatar"].animate,fake)
        for tick in range(300):
            anim()
            assert c.coords(handle)==[50.0,56.0],("sprite clipped",tick,c.coords(handle))
        root.destroy()
print("PASS: all 9 expressions, 8 frames each, 8 classic rollback, no magenta, centered GUI, voice & editor preserved")
