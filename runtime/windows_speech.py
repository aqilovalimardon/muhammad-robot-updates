import sys
class NativeWindowsSpeech:
    """Windows SAPI 5 COM Automation through Python's built-in ctypes.

    Runs only in the dedicated speech thread. Does not require pip or admin.
    """
    def __init__(self):
        import ctypes
        import uuid
        from ctypes import wintypes

        if sys.platform != "win32":
            raise OSError("Windows speech is available only on Windows.")
        self.ctypes = ctypes
        self.ole32 = ctypes.WinDLL("ole32")
        self.oleaut = ctypes.WinDLL("oleaut32")

        class GUID(ctypes.Structure):
            _fields_ = [("Data1", ctypes.c_uint32), ("Data2", ctypes.c_uint16),
                        ("Data3", ctypes.c_uint16), ("Data4", ctypes.c_ubyte * 8)]

        class Value(ctypes.Union):
            _fields_ = [("bstrVal", ctypes.c_void_p), ("lVal", ctypes.c_long),
                        ("decimal", ctypes.c_ubyte * 16)]

        class VARIANT(ctypes.Structure):
            _fields_ = [("vt", ctypes.c_ushort), ("reserved1", ctypes.c_ushort),
                        ("reserved2", ctypes.c_ushort), ("reserved3", ctypes.c_ushort),
                        ("value", Value)]

        class DISPPARAMS(ctypes.Structure):
            _fields_ = [("rgvarg", ctypes.POINTER(VARIANT)),
                        ("rgdispidNamedArgs", ctypes.POINTER(ctypes.c_long)),
                        ("cArgs", ctypes.c_uint), ("cNamedArgs", ctypes.c_uint)]

        self.GUID, self.VARIANT, self.DISPPARAMS = GUID, VARIANT, DISPPARAMS
        self.voice = ctypes.c_void_p()
        self.com_initialized = False
        self.ole32.CoInitializeEx.argtypes = [ctypes.c_void_p, ctypes.c_uint]
        self.ole32.CoInitializeEx.restype = ctypes.c_long
        self.ole32.CoUninitialize.argtypes = []
        self.ole32.CLSIDFromProgID.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(GUID)]
        self.ole32.CLSIDFromProgID.restype = ctypes.c_long
        self.ole32.CoCreateInstance.argtypes = [ctypes.POINTER(GUID), ctypes.c_void_p,
                                                ctypes.c_uint, ctypes.POINTER(GUID),
                                                ctypes.POINTER(ctypes.c_void_p)]
        self.ole32.CoCreateInstance.restype = ctypes.c_long
        self.oleaut.SysAllocString.argtypes = [ctypes.c_wchar_p]
        self.oleaut.SysAllocString.restype = ctypes.c_void_p
        self.oleaut.VariantClear.argtypes = [ctypes.POINTER(VARIANT)]
        self.oleaut.VariantClear.restype = ctypes.c_long

        try:
            hr = self.ole32.CoInitializeEx(None, 2)  # COINIT_APARTMENTTHREADED
            self._check(hr, "Initialize COM")
            self.com_initialized = True
            clsid = GUID()
            self._check(self.ole32.CLSIDFromProgID("SAPI.SpVoice", ctypes.byref(clsid)),
                        "Find Windows speech voice")
            iid_dispatch = GUID.from_buffer_copy(uuid.UUID(
                "00020400-0000-0000-C000-000000000046").bytes_le)
            self._check(self.ole32.CoCreateInstance(ctypes.byref(clsid), None, 5,
                                                    ctypes.byref(iid_dispatch),
                                                    ctypes.byref(self.voice)),
                        "Create Windows speech voice")
            vtbl = ctypes.cast(self.voice, ctypes.POINTER(
                ctypes.POINTER(ctypes.c_void_p))).contents
            fn = ctypes.WINFUNCTYPE
            self.release_fn = fn(ctypes.c_ulong, ctypes.c_void_p)(vtbl[2])
            self.get_ids = fn(ctypes.c_long, ctypes.c_void_p, ctypes.POINTER(GUID),
                              ctypes.POINTER(ctypes.c_wchar_p), ctypes.c_uint,
                              ctypes.c_uint, ctypes.POINTER(ctypes.c_long))(vtbl[5])
            self.invoke = fn(ctypes.c_long, ctypes.c_void_p, ctypes.c_long,
                             ctypes.POINTER(GUID), ctypes.c_uint, ctypes.c_ushort,
                             ctypes.POINTER(DISPPARAMS), ctypes.c_void_p,
                             ctypes.c_void_p, ctypes.c_void_p)(vtbl[6])
            self.iid_null = GUID()
            name = (ctypes.c_wchar_p * 1)("Speak")
            self.speak_id = ctypes.c_long()
            self._check(self.get_ids(self.voice, ctypes.byref(self.iid_null), name,
                                     1, 0x0409, ctypes.byref(self.speak_id)),
                        "Find speech command")
            name = (ctypes.c_wchar_p * 1)("WaitUntilDone")
            self.wait_id = ctypes.c_long()
            self._check(self.get_ids(self.voice, ctypes.byref(self.iid_null), name,
                                     1, 0x0409, ctypes.byref(self.wait_id)),
                        "Find speech completion command")
        except Exception:
            self.close()
            raise

    @staticmethod
    def _check(hr, operation):
        if hr < 0:
            raise OSError(f"{operation} failed (Windows error 0x{hr & 0xffffffff:08X}).")

    def speak(self, text):
        # Bound the audio wait so a stalled output device cannot mute the mic forever.
        self._speak_flags(text, 1)  # SVSFlagsAsync
        ct = self.ctypes
        arg = (self.VARIANT * 1)()
        arg[0].vt = 3
        arg[0].value.lVal = min(25000, max(5000, len(str(text)) * 100))
        params = self.DISPPARAMS(arg, None, 1, 0)
        result = self.VARIANT()
        try:
            self._check(self.invoke(self.voice, self.wait_id.value,
                                    ct.byref(self.iid_null), 0x0409, 1,
                                    ct.byref(params), ct.byref(result), None, None),
                        "Wait for speech")
            if not result.value.lVal:
                raise TimeoutError("Windows voice playback timed out")
        except Exception:
            self._speak_flags('', 3)  # Purge the old queue asynchronously.
            raise
        finally:self.oleaut.VariantClear(ct.byref(result))

    def _speak_flags(self, text, flags):
        ct = self.ctypes
        args = (self.VARIANT * 2)()
        args[0].vt = 3
        args[0].value.lVal = flags
        args[1].vt = 8  # VT_BSTR
        args[1].value.bstrVal = self.oleaut.SysAllocString(str(text))
        if not args[1].value.bstrVal:
            raise MemoryError("Not enough memory for voice text")
        params = self.DISPPARAMS(args, None, 2, 0)
        try:
            self._check(self.invoke(self.voice, self.speak_id.value,
                                    ct.byref(self.iid_null), 0x0409, 1,
                                    ct.byref(params), None, None, None),
                        "Speak")
        finally:
            self.oleaut.VariantClear(ct.byref(args[1]))

    def close(self):
        if getattr(self, "voice", None) and self.voice.value:
            self.release_fn(self.voice)
            self.voice = self.ctypes.c_void_p()
        if self.com_initialized:
            self.ole32.CoUninitialize()
            self.com_initialized = False


