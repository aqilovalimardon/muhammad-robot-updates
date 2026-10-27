#!/usr/bin/env python3
"""Exercise exact five-button Tk widget construction from released robot code."""
import sys, tempfile, zipfile, tkinter as tk
from pathlib import Path
from types import SimpleNamespace
from contextlib import redirect_stdout
from io import StringIO

zpath=Path(sys.argv[1])
with zipfile.ZipFile(zpath) as z:
    assert z.testzip() is None
    src=z.read('app/robot_app.py').decode('utf-8')
    assert "APP_VERSION = '2.2.6'" in z.read('app/robot_core.py').decode('utf-8')
    assert '    def _orb_track_eyes(self):' in src
    start=src.index('        for idx,(x,symbol,hint,fn) in enumerate([')
    end=src.index('        self.drag_at=None;',start)
    block=src[start:end]
    assert block.count('btn=tk.Button(')==1
    assert "'Hide robot',self.minimize" in block
    assert block.count(",'")>=5
    ns={'tk':tk}
    exec("def build_controls(self):\n"+block,ns)
    root=tk.Tk()
    root.withdraw()
    canvas=tk.Canvas(root,width=190,height=196)
    canvas.pack()
    actions=[]
    fake=SimpleNamespace(
      root=root,main=canvas,buttons=[],button_windows=[],
      open_editor=lambda:actions.append('edit'),
      quick_run=lambda:actions.append('run'),
      learn=lambda:actions.append('learn'),
      toggle_pin=lambda:actions.append('pin'),
      minimize=lambda:actions.append('hide'),
      _hover_button=lambda n,is_over:None,
      _pressed_button=lambda n:None
    )
    ns['build_controls'](fake)
    root.update()
    assert len(fake.buttons)==5, len(fake.buttons)
    assert [int(float(canvas.coords(w)[0])) for w in fake.button_windows]==[74,94,114,134,154]
    assert [int(float(canvas.coords(w)[1])) for w in fake.button_windows]==[140]*5
    assert fake.buttons[4].cget('text')=='−'
    fake.buttons[4].invoke()
    assert actions==['hide'], actions
    # Existing four commands retained in original order.
    for b in fake.buttons[:4]:b.invoke()
    assert actions==['hide','edit','run','learn','pin'],actions
    root.destroy()
print('PASS: five belly icons, hide control, existing callbacks, v2.2.6, orb preserved')
