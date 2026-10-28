#!/usr/bin/env python3
"""Exercise the actual Tk context menu while its Classic avatar is withdrawn."""
import ast
from pathlib import Path
import sys
from types import SimpleNamespace
import tkinter as tk
import zipfile
from test_v2218_feedback import selected_class


def windows_popup(host,event):
    # Win32 TrackPopupMenu runs a native modal loop: Tk after() cannot dismiss it.
    # Observe this process's real popup from a helper thread, then send Escape.
    import ctypes
    from ctypes import wintypes
    import os
    import threading
    import time
    api=ctypes.WinDLL('user32',use_last_error=True)
    enum_type=ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
    api.EnumWindows.argtypes=[enum_type,wintypes.LPARAM]
    api.GetWindowThreadProcessId.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.DWORD)]
    api.GetClassNameW.argtypes=[wintypes.HWND,wintypes.LPWSTR,ctypes.c_int]
    api.IsWindowVisible.argtypes=[wintypes.HWND]
    api.GetAncestor.argtypes=[wintypes.HWND,wintypes.UINT]
    api.GetAncestor.restype=wintypes.HWND
    api.PostMessageW.argtypes=[wintypes.HWND,wintypes.UINT,wintypes.WPARAM,wintypes.LPARAM]
    owner=api.GetAncestor(host.root.winfo_id(),2)
    seen=[]
    def dismiss():
        for attempt in range(25):
            time.sleep(0.1)
            found=[]
            @enum_type
            def visit(hwnd,_):
                pid=wintypes.DWORD()
                api.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
                title=ctypes.create_unicode_buffer(128)
                api.GetClassNameW(hwnd,title,128)
                if pid.value==os.getpid() and title.value=='#32768' and api.IsWindowVisible(hwnd):
                    found.append(hwnd)
                return True
            api.EnumWindows(visit,0)
            if found:
                seen.append(True)
                # Escape is delivered only after this test's menu is visibly open.
                api.keybd_event(0x1B,0,0,0)
                api.keybd_event(0x1B,0,2,0)
                api.PostMessageW(owner,0x001F,0,0)  # WM_CANCELMODE
                return
        api.PostMessageW(owner,0x001F,0,0)
        api.PostMessageW(owner,0x0010,0,0)  # fail closed, never hang the test runner
    worker=threading.Thread(target=dismiss,daemon=True)
    worker.start()
    host.popup(event)
    worker.join(timeout=4)
    assert seen==[True], 'This process did not show a native Windows popup'
    assert host.root.state()=='withdrawn', 'Classic avatar must stay hidden'


def labels(menu):
    return [menu.entrycget(i,'label') for i in range(menu.index('end')+1)
            if menu.type(i) != 'separator']


def main(baseline, output):
    with zipfile.ZipFile(baseline) as old, zipfile.ZipFile(output) as new:
        before=old.read('app/robot_app.py').decode('utf-8')
        code=new.read('app/robot_app.py').decode('utf-8')
    old_class=next(n for n in ast.parse(before).body if isinstance(n,ast.ClassDef) and n.name=='RobotApp')
    old_menu=next(n for n in old_class.body if isinstance(n,ast.FunctionDef) and n.name=='_build_menu')
    required={kw.value.value for node in ast.walk(old_menu) if isinstance(node,ast.Call)
              for kw in node.keywords if kw.arg=='label' and isinstance(kw.value,ast.Constant)}
    Robot=selected_class(code,'RobotApp',{'_build_menu','_show_shared_menu','popup'}, {'tk':tk})
    host=Robot()
    host.root=tk.Tk()
    host.root.configure(bg='#ff00fe')
    host.root.overrideredirect(True)
    host.root.attributes('-topmost',True)
    if sys.platform=='win32':host.root.wm_attributes('-transparentcolor','#ff00fe')
    host.root.withdraw()
    host.root.update()
    actions=[]
    for name in ('open_editor','quick_run','learn','say','restore','minimize','_cycle_3d_emotion',
                 '_toggle_3d_effects','toggle_microphone','show_mic_status','drive_settings',
                 'switch_robot_look','open_real3d_preview','switch_to_classic','show_version',
                 'check_updates_now','natural_voice_setup','exit'):
        setattr(host,name,lambda *a,n=name:actions.append(n))
    host._build_menu()
    original_menu=host.menu
    assert required <= set(labels(host.menu)), required-set(labels(host.menu))
    host._three_d_active=True
    # Route actual menu entries to callbacks, using Tk's invocation semantics.
    expected={'Edit Python code':'open_editor','Run Python code':'quick_run','Learn Python':'learn',
              'Enable / Disable offline voice commands':'toggle_microphone',
              'Voice status / restart microphone':'show_mic_status','Drive folder settings':'drive_settings',
              'About robot / version':'show_version','Check GitHub updates':'check_updates_now',
              'Natural voice setup (optional)':'natural_voice_setup','Exit Robot':'exit',
              'Show next 3D emotion':'_cycle_3d_emotion','3D effect sounds: On / Off':'_toggle_3d_effects'}
    for label,callback in expected.items():
        host.menu.invoke(label)
        assert actions[-1]==callback,(label,actions)
    for active in (True,False):
        host._three_d_active=active
        if sys.platform=='win32':
            windows_popup(host,SimpleNamespace(x_root=100,y_root=100))
            assert host.menu is original_menu and required <= set(labels(host.menu))
            continue
        seen=[]
        errors=[]
        def open_menu():
            try:host.popup(SimpleNamespace(x_root=100,y_root=100))
            except Exception as exc:errors.append(str(exc))
        def close_menu():
            seen.append((host.root.state(),bool(host.menu.winfo_ismapped())))
            host.menu.unpost()
            host.root.quit()
        host.root.after(0,open_menu)
        host.root.after(180,close_menu)
        timer=host.root.after(3000,host.root.quit)
        host.root.mainloop()
        host.root.after_cancel(timer)
        assert not errors,errors
        assert seen==[('withdrawn',True)],(active,seen)
        assert host.menu is original_menu and required <= set(labels(host.menu))
        state=host.menu.entrycget('Switch to Classic (backup)','state')
        assert state==('normal' if active else 'disabled')
    host.root.destroy()
    print('PASS: real Tk popup visible with hidden Classic root, one shared menu, all original commands, callback routing')


if __name__=='__main__':main(*sys.argv[1:])
