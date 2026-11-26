# -*- coding: utf-8 -*-
# @py3
"""主机侧：异步触发 IDE 内覆盖式导入，并在等待期间自动点掉「覆盖确认」模态框。

为什么不在 IDE 脚本里等：IDE 脚本跑在主线程，sleep/轮询会冻死界面。
这里把等待放在主机侧 Python，IDE 只管调一次 import_native。

用法：python run_overwrite_import.py
"""
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

sys.path.insert(0, HERE)
import click_overwrite_all as clicker


def pids_of(name):
    out = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "(Get-Process %s -ErrorAction SilentlyContinue).Id" % name],
        capture_output=True, text=True, timeout=30)
    return set(int(x) for x in (out.stdout or "").split() if x.strip().isdigit())


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

    deadline = time.time() + 900
    clicked = 0
    while time.time() < deadline:
        time.sleep(1.0)
        # 统一走 click_overwrite_all：先「全部(&A)」全选，再「&确定」提交。
        # ⚠ 2026-11-26 实测：只点「全部」不点「确定」对话框不关闭，
        # import_native 一直阻塞（实测 323.79s 直到人工补点确定）。
        # 另外不要按「窗口是否被禁用」筛选——弹框挂在未被禁用的框架窗口下。
        hits = clicker.click_all(pids_of("InoProShop") or None)
        for pid, act in hits:
            print("%s (pid=%d)" % (act, pid))
        clicked += len(hits)
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
