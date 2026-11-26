# @py3
# -*- coding: utf-8 -*-
"""统一入口：跑 build -> 等 45s -> check，自动点掉覆盖/确认弹框。

用法：
  python run_build_check.py            # 全流程
  python run_build_check.py --task X   # 只跑某个 IDE 任务脚本
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
TASKS = os.path.join(HERE, "ide", "tasks")

sys.path.insert(0, HERE)
import click_overwrite_all as clicker


def run_ide(script):
    p = subprocess.run([PY, BRIDGE, "eval_file", json.dumps({"path": script})],
                       cwd=HERE, capture_output=True, text=True, timeout=1800)
    return p.stdout or ""


def pump(seconds, label):
    """在等待期间持续点掉弹框。"""
    end = time.time() + seconds
    n = 0
    while time.time() < end:
        hits = clicker.click_all()
        n += len(hits)
        time.sleep(1.5)
    print("[%s] waited %ds, clicked %d" % (label, seconds, n))
    return n


def main():
    only = None
    if "--task" in sys.argv:
        only = sys.argv[sys.argv.index("--task") + 1]

    if only:
        p = only if os.path.isabs(only) else os.path.join(TASKS, only)
        if not os.path.exists(p) and not os.path.isabs(only):
            p = os.path.join(HERE, "ide", "studies", only)
        print(run_ide(p))
        return

    print("=== build ===")
    print(run_ide(os.path.join(TASKS, "task_build.py")))
    pump(45, "rebuild-window")
    print("=== check ===")
    print(run_ide(os.path.join(TASKS, "task_check.py")))
    log = os.path.join(IPC, "check.log")
    if os.path.exists(log):
        print("=== check.log ===")
        with open(log, "r", encoding="utf-8", errors="replace") as f:
            print(f.read())


if __name__ == "__main__":
    main()
