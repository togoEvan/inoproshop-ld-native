# @py3
# -*- coding: utf-8 -*-
"""点掉 InoProShop 的「覆盖确认」模态框：点「全部(&A)」按钮。

只用 SendMessageW(BM_CLICK)，不动鼠标、不抢焦点。
可单独运行，也可被其它主机侧脚本 import 复用。
"""
import ctypes
import sys

user32 = ctypes.windll.user32
EnumWindows = user32.EnumWindows
EnumChildWindows = user32.EnumChildWindows
GetWindowTextW = user32.GetWindowTextW
GetClassNameW = user32.GetClassNameW
GetWindowThreadProcessId = user32.GetWindowThreadProcessId
IsWindowVisible = user32.IsWindowVisible
SendMessageW = user32.SendMessageW
BM_CLICK = 0x00F5

TITLE_KEY = u"已经存在"          # 覆盖确认框的说明文字特征
BTN_ALL = u"全部"                # 「全部(&A)」：只全选，不提交
BTN_OK = u"确定"                 # 「&确定」：真正提交覆盖


def _pids(name=u"InoProShop"):
    import subprocess
    out = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "(Get-Process %s -ErrorAction SilentlyContinue).Id" % name],
        capture_output=True, text=True, timeout=30)
    return set(int(x) for x in (out.stdout or "").split() if x.strip().isdigit())


def _children(h):
    res = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def cb(c, l):
        buf = ctypes.create_unicode_buffer(1024)
        GetWindowTextW(c, buf, 1024)
        res.append((c, buf.value))
        return True

    EnumChildWindows(h, cb, None)
    return res


def click_all(pid_filter=None, verbose=False):
    """扫描顶层窗口，找到覆盖确认框：先点「全部」全选，再点「确定」提交。

    两步是必须的——「全部」只勾选列表项，不关闭对话框。
    返回 [(pid, 动作)] 列表。
    """
    hits = []
    import time

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def cb(h, l):
        pid = ctypes.c_ulong()
        GetWindowThreadProcessId(h, ctypes.byref(pid))
        if pid_filter and pid.value not in pid_filter:
            return True
        if not IsWindowVisible(h):
            return True
        kids = _children(h)
        texts = [t for t, _ in ((x[1], x[0]) for x in kids) if t]
        if not any(TITLE_KEY in t for t in texts):
            return True

        def find_btn(key):
            for c, t in kids:
                tt = (t or "").replace(u"&", u"")
                if tt == key:
                    return c, t
            return None, None

        c, t = find_btn(BTN_ALL)
        if c:
            SendMessageW(c, BM_CLICK, 0, 0)
            hits.append((pid.value, u"click " + t))
            if verbose:
                print(u"clicked %r in pid=%d" % (t, pid.value))
            time.sleep(0.4)

        c, t = find_btn(BTN_OK)
        if c:
            SendMessageW(c, BM_CLICK, 0, 0)
            hits.append((pid.value, u"click " + t))
            if verbose:
                print(u"clicked %r in pid=%d" % (t, pid.value))
        return True

    EnumWindows(cb, None)
    return hits


if __name__ == "__main__":
    pf = _pids() or None
    hits = click_all(pf, verbose=True)
    print("clicked: %d" % len(hits))
    sys.exit(0 if hits else 1)
