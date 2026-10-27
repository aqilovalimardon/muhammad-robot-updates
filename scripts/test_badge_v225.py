#!/usr/bin/env python3
"""GUI smoke test of the actual staged v2.2.5 ZIP using Xvfb/Tk."""
import sys
import tempfile
import tkinter as tk
import zipfile
from pathlib import Path
from types import MethodType, SimpleNamespace

archive=Path(sys.argv[1]).resolve()
with tempfile.TemporaryDirectory() as td:
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        z.extractall(td)
    sys.path.insert(0,str(Path(td)/'app'))
    from robot_app import RobotApp
    root=tk.Tk()
    root.withdraw()
    fake=SimpleNamespace(root=root,orb=None,minimized=True,restore_count=0)
    fake.restore=lambda: setattr(fake,'restore_count',fake.restore_count+1)
    fake._orb_track_eyes=MethodType(RobotApp._orb_track_eyes,fake)
    RobotApp._show_restore_orb(fake)
    root.update()
    assert (fake.orb.winfo_width(),fake.orb.winfo_height())==(44,44)
    assert len(fake.orb_pupils)==2
    assert fake.orb_canvas.itemcget(fake.orb_ring,'fill')=='#071c33'
    before=fake.orb_canvas.coords(fake.orb_pupils[0])
    fake.orb_canvas.event_generate('<Motion>',x=44,y=22,warp=True)
    root.update()
    fake._orb_track_eyes()
    after=fake.orb_canvas.coords(fake.orb_pupils[0])
    assert before!=after,(before,after)
    fake.orb_canvas.event_generate('<Button-1>',x=18,y=20)
    root.update()
    assert fake.restore_count==1
    fake.minimized=False
    fake.orb.destroy()
    root.update()
    root.destroy()
    print('Badge smoke test PASS: round, two eyes tracking, clickable, clean close')
