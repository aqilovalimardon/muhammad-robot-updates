"""Non-modal shared robot menu: keep Tk voice and bridge timers running."""


class PopupChanges:
    def toggle_aqua_menu(self):
        self._show_shared_menu()

    def _show_aqua_menu(self):
        self._show_shared_menu()

    def _show_shared_menu(self,event=None):
        if getattr(self,'_shared_popup',None) is not None:
            self._dismiss_shared_menu()
            return
        active=getattr(self,'_three_d_active',False)
        for label in ('Show next 3D emotion','3D effect sounds: On / Off','Switch to Classic (backup)'):
            self.menu.entryconfigure(label,state='normal' if active else 'disabled')
        self.menu.entryconfigure('Switch to 3D Plush Robot',state='disabled' if active else 'normal')
        x=event.x_root if event is not None else self.root.winfo_pointerx()
        y=event.y_root if event is not None else self.root.winfo_pointery()
        win=tk.Toplevel(self.root)
        win.withdraw()
        win.overrideredirect(True)
        win.attributes('-topmost',True)
        win.configure(bg='#4dc8ed')
        self._shared_popup=win
        self._shared_popup_job=None
        panel=tk.Frame(win,bg='#082943')
        panel.pack(fill='both',expand=True,padx=1,pady=1)
        tk.Label(panel,text='Muhammad Robot',anchor='w',bg='#082943',fg='#d8faff',
                 font=('Segoe UI',10,'bold')).pack(fill='x',padx=10,pady=(7,0))
        self._shared_voice_text=tk.StringVar(value=self._popup_voice_status())
        tk.Label(panel,textvariable=self._shared_voice_text,anchor='w',bg='#082943',fg='#9bc8dc',
                 font=('Segoe UI',8),wraplength=300).pack(fill='x',padx=10,pady=(1,5))
        canvas=tk.Canvas(panel,bg='#082943',bd=0,highlightthickness=0,width=320)
        scrollbar=tk.Scrollbar(panel,orient='vertical',command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side='left',fill='both',expand=True)
        rows=tk.Frame(canvas,bg='#082943')
        item=canvas.create_window(0,0,window=rows,anchor='nw')
        canvas.bind('<Configure>',lambda e:canvas.itemconfigure(item,width=e.width))
        self._shared_popup_buttons={}
        for index in range((self.menu.index('end') or 0)+1):
            if self.menu.type(index)=='separator':
                tk.Frame(rows,bg='#346078',height=1).pack(fill='x',padx=9,pady=4)
                continue
            label=self.menu.entrycget(index,'label')
            button=tk.Button(rows,text=label,anchor='w',relief='flat',bd=0,
                bg='#082943',fg='#e1f4fb',activebackground='#245473',activeforeground='white',
                disabledforeground='#688393',font=('Segoe UI',9),padx=10,pady=3,
                state=self.menu.entrycget(index,'state'),
                command=lambda n=index:self._invoke_shared_action(n))
            button.pack(fill='x',padx=3)
            self._shared_popup_buttons[label]=button
        rows.update_idletasks()
        canvas.configure(scrollregion=canvas.bbox('all'))
        height=rows.winfo_reqheight()
        available=max(120,self.root.winfo_screenheight()-95)
        canvas.configure(height=min(height,available))
        if height>available:scrollbar.pack(side='right',fill='y')
        def scroll(event):
            canvas.yview_scroll(-1 if event.delta>0 else 1,'units')
            return 'break'
        win.bind('<MouseWheel>',scroll)
        win.bind('<Escape>',lambda e:self._dismiss_shared_menu())
        win.bind('<FocusOut>',lambda e:win.after_idle(lambda:self._popup_check_focus(win)))
        win.update_idletasks()
        width=win.winfo_reqwidth()
        height=win.winfo_reqheight()
        x=max(0,min(int(x),max(0,self.root.winfo_screenwidth()-width-8)))
        y=max(0,min(int(y),max(0,self.root.winfo_screenheight()-height-8)))
        win.geometry(f'{width}x{height}+{x}+{y}')
        self._shared_popup_mouse=self._popup_pointer()[0]
        win.deiconify()
        win.lift()
        win.focus_force()
        # No tk_popup, grab or wait_window: microphone polling keeps running.
        self._shared_popup_job=self.root.after(30,self._poll_shared_popup)

    def _popup_voice_status(self):
        if not getattr(self,'_mic_requested',False):return 'Voice: off'
        return 'Voice: '+str(getattr(self,'mic_state','Starting'))[:85]

    def _popup_pointer(self):
        # Poll only while this menu exists. No global hook or background recorder.
        import sys
        if sys.platform=='win32':
            import ctypes
            from ctypes import wintypes
            api=getattr(self,'_popup_user32',None)
            if api is None:
                api=ctypes.WinDLL('user32',use_last_error=True)
                api.GetAsyncKeyState.argtypes=[ctypes.c_int]
                api.GetAsyncKeyState.restype=ctypes.c_short
                api.GetCursorPos.argtypes=[ctypes.POINTER(wintypes.POINT)]
                api.GetCursorPos.restype=wintypes.BOOL
                self._popup_user32=api
            point=wintypes.POINT()
            if api.GetCursorPos(ctypes.byref(point)):
                buttons=sum((1<<n) for n,key in enumerate((1,2,4)) if api.GetAsyncKeyState(key)&0x8000)
                return buttons,point.x,point.y
        x,y=self.root.winfo_pointerxy()
        return 0,x,y

    def _popup_check_focus(self,expected=None):
        win=getattr(self,'_shared_popup',None)
        if win is None or (expected is not None and win is not expected):return
        try:
            focus=win.focus_get()
            if focus is None or focus.winfo_toplevel()!=win:self._dismiss_shared_menu()
        except (tk.TclError,KeyError):self._dismiss_shared_menu()

    def _poll_shared_popup(self):
        win=getattr(self,'_shared_popup',None)
        self._shared_popup_job=None
        if win is None:return
        try:
            buttons,x,y=self._popup_pointer()
            pressed=buttons & ~self._shared_popup_mouse
            self._shared_popup_mouse=buttons
            inside=(win.winfo_rootx()<=x<win.winfo_rootx()+win.winfo_width() and
                    win.winfo_rooty()<=y<win.winfo_rooty()+win.winfo_height())
            if pressed and not inside:
                self._dismiss_shared_menu()
                return
            text=self._popup_voice_status()
            if self._shared_voice_text.get()!=text:self._shared_voice_text.set(text)
            self._shared_popup_job=self.root.after(30,self._poll_shared_popup)
        except tk.TclError:self._dismiss_shared_menu()

    def _dismiss_shared_menu(self):
        win=getattr(self,'_shared_popup',None)
        self._shared_popup=None
        job=getattr(self,'_shared_popup_job',None)
        self._shared_popup_job=None
        if job is not None:
            try:self.root.after_cancel(job)
            except tk.TclError:pass
        if win is not None:
            try:win.destroy()
            except tk.TclError:pass

    def _invoke_shared_action(self,index):
        self._dismiss_shared_menu()
        self.menu.invoke(index)
