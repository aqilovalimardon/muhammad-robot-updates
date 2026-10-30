#!/usr/bin/env python3
"""Real shared Tk popup: outside clicks, timers, actions and voice while open."""
import ast
from pathlib import Path
import sys
import tempfile
import time
import tkinter as tk
from types import MethodType,SimpleNamespace
import zipfile
from test_v2219_plush import selected_class,main as package_checks
from test_v2221_voice import make_host,load_commands,test_recovery,test_speech,test_audio_stream,test_recognition_tools

POPUP_METHODS={'_build_menu','popup','toggle_aqua_menu','_show_aqua_menu','_show_shared_menu',
    '_popup_voice_status','_popup_pointer','_popup_check_focus','_poll_shared_popup',
    '_dismiss_shared_menu','_invoke_shared_action'}
CALLBACKS=('open_editor','quick_run','learn','say','restore','minimize','_cycle_3d_emotion',
    '_toggle_3d_effects','toggle_microphone','show_mic_status','drive_settings','switch_robot_look',
    'open_real3d_preview','switch_to_classic','show_version','check_updates_now','natural_voice_setup','exit')


def attach_popup(host,source,legacy=False):
    methods={'_build_menu','popup','_show_shared_menu'} if legacy else POPUP_METHODS
    Menu=selected_class(source,'RobotApp',methods,{'tk':tk})
    for name in methods:setattr(host,name,MethodType(getattr(Menu,name),host))
    host.root=tk.Tk()
    host.root.withdraw()
    host.root.update()
    host.ui_errors=[]
    host.root.report_callback_exception=lambda *exc:host.ui_errors.append(exc)
    host.actions=[]
    for name in CALLBACKS:
        if not hasattr(host,name):setattr(host,name,lambda *a,n=name:host.actions.append(n))
    host._build_menu()
    return host


def pump(root,condition,timeout=2):
    until=time.monotonic()+timeout
    while time.monotonic()<until:
        root.update()
        if condition():return
        time.sleep(.005)
    raise AssertionError('Tk event deadline exceeded')


def popup_checks(baseline,output):
    with zipfile.ZipFile(baseline) as old,zipfile.ZipFile(output) as new:
        before=old.read('app/robot_app.py').decode('utf-8')
        source=new.read('app/robot_app.py').decode('utf-8')
    with tempfile.TemporaryDirectory() as tmp:
        folder=Path(tmp)
        if sys.platform=='win32':
            from test_v2219_native_menu import windows_popup
            legacy=attach_popup(make_host(before,folder),before,legacy=True)
            tick=[]
            legacy.root.after(30,lambda:tick.append(True))
            windows_popup(legacy,SimpleNamespace(x_root=100,y_root=100))
            assert not tick,'Expected baseline native menu to suspend Tk timers'
            legacy.root.update()
            assert tick
            legacy.root.destroy()
            print('PASS: reproduced v2.2.21 Windows popup blocking the voice event timer')
        h=attach_popup(make_host(source,folder),source)
        h.mic_active=h._mic_requested=True
        h.mic_state='Listening (offline)'
        h._poll_mic_events()
        try:
            labels=[h.menu.entrycget(i,'label') for i in range(h.menu.index('end')+1) if h.menu.type(i)!='separator']
            for active in (True,False):
                h._three_d_active=active
                h.popup(SimpleNamespace(x_root=100,y_root=80))
                win=h._shared_popup
                tick=[]
                h.root.after(35,lambda:tick.append(True))
                pump(h.root,lambda:bool(tick))
                assert h._shared_popup is win and win.winfo_viewable()
                assert h.root.state()=='withdrawn' and h.root.grab_current() is None
                assert list(h._shared_popup_buttons)==labels
                assert h._shared_popup_buttons['Switch to Classic (backup)'].cget('state')==('normal' if active else 'disabled')
                if active and sys.platform=='win32':
                    from PIL import ImageGrab
                    x,y=win.winfo_rootx(),win.winfo_rooty()
                    ImageGrab.grab(bbox=(x,y,x+win.winfo_width(),y+win.winfo_height())).save('popup-review.png')
                # Button commands close first, then use the ORIGINAL Tk menu action.
                h._shared_popup_buttons['Run Python code'].invoke()
                assert h._shared_popup is None and h.actions[-1]=='quick_run'
            h._three_d_active=True
            for command,expected in [('close','hide'),('open','show'),('close','hide'),('open','show')]:
                h.popup(SimpleNamespace(x_root=100,y_root=80))
                h.root.after(40,lambda c=command:h.mic_events.put(('command',c)))
                pump(h.root,lambda:h._shared_popup is None)
                assert h._three_d_signal.read_text()==expected
            # Opening button still held must not dismiss; a NEW outside press must.
            pointer=h._popup_pointer
            point=[1,20,20]
            h._popup_pointer=lambda:tuple(point)
            h.popup(SimpleNamespace(x_root=100,y_root=80))
            h._poll_shared_popup()
            assert h._shared_popup is not None
            point[0]=0
            h._poll_shared_popup()
            point[0]=1
            h._poll_shared_popup()
            assert h._shared_popup is None and h._shared_popup_job is None
            h._popup_pointer=pointer
            h.popup(SimpleNamespace(x_root=100,y_root=80))
            win=h._shared_popup
            h.root.update()
            win.event_generate('<Escape>')
            pump(h.root,lambda:h._shared_popup is None)
            # Click through to another real window; no grab should swallow it.
            peer=tk.Toplevel(h.root)
            peer.geometry('170x100+500+50')
            peer.title('Outside click test')
            clicks=[]
            peer.bind('<Button-1>',lambda e:clicks.append(True))
            peer.update()
            h.popup(SimpleNamespace(x_root=100,y_root=80))
            h.root.update()
            if sys.platform=='win32':
                import ctypes
                from ctypes import wintypes
                api=ctypes.WinDLL('user32',use_last_error=True)
                api.SetCursorPos.argtypes=[ctypes.c_int,ctypes.c_int]
                api.mouse_event.argtypes=[wintypes.DWORD,wintypes.DWORD,wintypes.DWORD,wintypes.DWORD,ctypes.c_size_t]
                api.SetCursorPos(peer.winfo_rootx()+40,peer.winfo_rooty()+40)
                api.mouse_event(2,0,0,0,0)
                try:pump(h.root,lambda:h._shared_popup is None and bool(clicks))
                finally:api.mouse_event(4,0,0,0,0)
            else:
                peer.focus_force()
                pump(h.root,lambda:h._shared_popup is None)
            peer.destroy()
            assert not h.ui_errors,h.ui_errors
        finally:h.root.destroy()
    print('PASS: non-modal shared menu, actual outside click/focus dismissal, unchanged callbacks, live voice Close/Open while menu is open')


def main(baseline,output,ui=False):
    package_checks(baseline,output,expected_version='2.2.22')
    with zipfile.ZipFile(output) as z:source=z.read('app/robot_app.py').decode('utf-8')
    commands=load_commands(output)
    test_recognition_tools(commands)
    with tempfile.TemporaryDirectory() as tmp:
        folder=Path(tmp)
        test_recovery(source,folder)
        test_speech(source,folder)
        test_audio_stream(commands,folder)
    if ui:popup_checks(baseline,output)
    print('PASS: v2.2.22 updater, retained voice recovery and popup regressions')


if __name__=='__main__':main(*sys.argv[1:])
