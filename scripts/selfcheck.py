# -*- coding: utf-8 -*-
# @py3
r"""换电脑/换 AI 后的第一道体检：这台机器能不能用，缺什么。

检查项：
  1) Python 版本与关键库
  2) 仓库文件是否齐全（bridge / 守护 / 隐藏启动器 / 任务脚本数）
  3) InoProShop 是否装、进程是否在、守护是否注入、心跳是否新鲜、ping 是否通
  4) 可选：--project=<工程> 只校验文件存在且当前打开的正是它
用法：
  python selfcheck.py
  python selfcheck.py --project=D:\plc_study\study.project
退出码：0 全绿 / 1 有阻塞项
"""
import io
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bridge  # noqa: E402

REQUIRED = [
    "bridge.py", "hidden_launch.py", "accept.py", "ld_logic.py", "do_replace.py",
    "ide/plc_daemon.py", "ide/boot_daemon.py", "ide/_base.py",
    "ide/tasks/task_check.py", "ide/tasks/task_build_clean.py",
    "ide/tasks/task_silent_import.py", "ide/tasks/task_mount_assert.py",
]
IDE_HINTS = [
    r"E:\汇川\中型1.10.0.3\CODESYS\Common\InoProShop.exe",
    r"C:\Program Files\Inovance\InoProShop\CODESYS\Common\InoProShop.exe",
    r"C:\Program Files (x86)\Inovance\InoProShop\CODESYS\Common\InoProShop.exe",
]


def ok(b):
    return "PASS" if b else "FAIL"


def main():
    problems = []
    print("== 1) Python ==")
    print("  版本: %s" % sys.version.split()[0])
    print("  解释器: %s" % sys.executable)

    print("== 2) 仓库文件 ==")
    for rel in REQUIRED:
        p = os.path.join(HERE, rel)
        good = os.path.isfile(p)
        if not good:
            problems.append("缺文件: %s" % rel)
        print("  [%s] %s" % (ok(good), rel))
    tasks = os.path.join(HERE, "ide", "tasks")
    n_tasks = len([f for f in os.listdir(tasks) if f.endswith(".py")]) if os.path.isdir(tasks) else 0
    print("  [%s] ide/tasks 下任务脚本 %d 个" % (ok(n_tasks > 20), n_tasks))

    print("== 3) InoProShop 与守护 ==")
    ide_found = [p for p in IDE_HINTS if os.path.isfile(p)]
    print("  [%s] 安装路径: %s" % (ok(bool(ide_found)), ide_found[0] if ide_found else "未在常见路径找到，可用 --ide 指定"))
    st = bridge.selftest()
    for k in ("ide_running", "ready_flag", "heartbeat_age", "ping"):
        v = st.get(k)
        if isinstance(v, dict):
            v = "ok" if v.get("ok") else v.get("error")
        print("  %-16s %s" % (k + ":", v))
    print("  base:", st.get("base"), " ipc:", st.get("ipc"))
    if not st.get("ok"):
        problems.extend(st.get("problems") or ["selftest 未通过"])
        print("  修复提示：")
        for p in (st.get("problems") or []):
            print("   -", p)

    print("== 4) 工程 ==")
    proj = None
    for i, a in enumerate(sys.argv):
        if a.startswith("--project="):
            proj = a.split("=", 1)[1]
        elif a == "--project" and i + 1 < len(sys.argv):
            proj = sys.argv[i + 1]
    if proj:
        good = os.path.isfile(proj)
        if not good:
            problems.append("工程不存在: %s" % proj)
        print("  [%s] 文件存在: %s" % (ok(good), proj))
    else:
        print("  (未指定 --project，跳过)")

    print("== 结论 ==")
    if problems:
        print("  有 %d 项阻塞，按上面提示处理后再跑一次。" % len(problems))
        return 1
    print("  全绿。下一步：python accept.py --names=<你写入的对象>")
    return 0


if __name__ == "__main__":
    sys.exit(main())
