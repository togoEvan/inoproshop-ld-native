# -*- coding: utf-8 -*-
# @py3
"""主机侧：异步触发 IDE 内覆盖式导入，并在等待期间自动点掉「覆盖确认」模态框。

为什么不在 IDE 脚本里等：IDE 脚本跑在主线程，sleep/轮询会冻死界面。
这里把等待放在主机侧 Python，IDE 只管调一次 import_native。

用法：python run_overwrite_import.py
"""
import ctypes
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
BRIDGE = os.path.join(HERE, "bridge.py")
IPC = os.path.join(HERE, "ipc")
LOG = os.path.join(IPC, "import_overwrite.log")

TASK = os.path.join(HERE, "ide", "tasks", "task_import_overwrite.py")

user32 = ctypes.windll.user32
EnumWindows = user32.EnumWindows
GetWindowThreadProcessId = user32.GetWindowThreadProcessId
IsWindowVisible = user32.IsWindowVisible
IsWindowEnabled = user32.IsWindowEnabled
GetWindowTextW = user32.GetWindowTextW
GetClassNameW = user32.GetClassNameW
GetDlgCtrlID = user32.GetDlgCtrlID
SendMessageW = user32.SendMessageW
EnumChildWindows = user32.EnumChildWindows
BM_CLICK = 0x00F5


def pids_of(name):
    out = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "(Get-Process %s -ErrorAction SilentlyContinue).Id" % name],
        capture_output=True, text=True, timeout=30)
    return [int(x) for x in (out.stdout or "").split() if x.strip().isdigit()]


def windows_of(pid):
    res = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def cb(h, l):
        p = ctypes.c_ulong()
        GetWindowThreadProcessId(h, ctypes.byref(p))
        if p.value == pid and IsWindowVisible(h):
            buf = ctypes.create_unicode_buffer(512)
            GetWindowTextW(h, buf, 512)
            cls = ctypes.create_unicode_buffer(256)
            GetClassNameW(h, cls, 256)
            res.append((h, buf.value, cls.value, bool(IsWindowEnabled(h))))
        return True

    EnumWindows(cb, None)
    return res


def children(h):
    res = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def cb(c, l):
        buf = ctypes.create_unicode_buffer(512)
        GetWindowTextW(c, buf, 512)
        cls = ctypes.create_unicode_buffer(256)
        GetClassNameW(c, cls, 256)
        res.append((c, buf.value, cls.value, GetDlgCtrlID(c)))
        return True

    EnumChildWindows(h, cb, None)
    return res


def click_all(hwnd):
    """在弹窗里找「全部」按钮并点击。"""
    for c, txt, cls, cid in children(hwnd):
        t = (txt or "").replace("&", "")
        if u"全部" in t:
            SendMessageW(c, BM_CLICK, 0, 0)
            return t
    return None


def main():
    if os.path.exists(LOG):
        try:
            os.remove(LOG)
        except OSError:
            pass

    p = subprocess.Popen([PY, BRIDGE, "eval_file", json.dumps({"path": TASK})],
                         cwd=HERE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         text=True)
    print("bridge started, pid=%d" % p.pid)

    deadline = time.time() + 600
    clicked = 0
    while time.time() < deadline:
        time.sleep(1.0)
        for pid in pids_of("InoProShop"):
            for h, title, cls, enabled in windows_of(pid):
                # ⚠ 2026-11-26 实测修正：覆盖确认模态框挂在**未被禁用**的
                # 框架窗口（标题 InoProShop(V1.10.0.3)）下，主工程窗口才被禁用。
                # 旧逻辑 `if enabled: continue` 跳过了它，导致弹框永远扫不到、
                # import_native 卡 400+ 秒直到人工干预。
                # 修法：不再看 enabled，直接在每个顶层窗口的子控件里找按钮。
                kids = children(h)
                names = [k[1] for k in kids if k[1]]
                if any(u"全部" in (n or u"") for n in names):
                    hit = click_all(h)
                    print("clicked dialog button: %s (pid=%d, window=%r)"
                          % (hit, pid, title))
                    clicked += 1
        if p.poll() is not None:
            break

    out = p.stdout.read() if p.stdout else ""
    print("--- bridge output ---")
    print(out.strip()[:2000])
    print("clicked dialogs: %d" % clicked)
    print("--- import_overwrite.log ---")
    if os.path.exists(LOG):
        with open(LOG, "r", encoding="utf-8") as f:
            print(f.read())


if __name__ == "__main__":
    main()
