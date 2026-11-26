import ctypes
import ctypes.wintypes as wt

user32 = ctypes.windll.user32
EnumWindows = user32.EnumWindows
EnumChildWindows = user32.EnumChildWindows
GetWindowTextW = user32.GetWindowTextW
GetClassNameW = user32.GetClassNameW
GetWindowThreadProcessId = user32.GetWindowThreadProcessId
IsWindowVisible = user32.IsWindowVisible
IsWindowEnabled = user32.IsWindowEnabled
GetDlgCtrlID = user32.GetDlgCtrlID
SendMessageW = user32.SendMessageW
BM_CLICK = 0x00F5

results = []


@ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
def on_win(h, lp):
    pid = ctypes.c_ulong()
    GetWindowThreadProcessId(h, ctypes.byref(pid))
    if pid.value == 36704:
        buf = ctypes.create_unicode_buffer(512)
        GetWindowTextW(h, buf, 512)
        if buf.value:
            results.append((h, buf.value, bool(IsWindowVisible(h)),
                            bool(IsWindowEnabled(h))))
    return True


EnumWindows(on_win, None)
print("=== IDE 顶层窗口 ===")
for h, t, vis, en in results:
    print("hwnd=%d vis=%s en=%s text=%r" % (h, vis, en, t))

kids = []


@ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
def on_child(h, lp):
    buf = ctypes.create_unicode_buffer(512)
    GetWindowTextW(h, buf, 512)
    cls = ctypes.create_unicode_buffer(256)
    GetClassNameW(h, cls, 256)
    kids.append((h, buf.value, cls.value, GetDlgCtrlID(h)))
    return True


for h, t, vis, en in results:
    print("=== children of %r (%s) ===" % (t, "vis" if vis else "hidden"))
    del kids[:]
    EnumChildWindows(h, on_child, None)
    for c, txt, cls, cid in kids:
        if txt or u"Button" in cls:
            print("  hwnd=%d cls=%s id=%d text=%r" % (c, cls, cid, txt))
