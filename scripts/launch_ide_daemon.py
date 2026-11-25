# -*- coding: utf-8 -*-
"""启动 InoProShop（UI 模式）并注入守护脚本。不点菜单、不动鼠标、不抢焦点。

用法:
    python launch_ide_daemon.py [wait_sec]

参数来源（高 → 低）:
    IDE 路径   --ide=<路径>        环境变量 INOPROSHOP_EXE      自动搜索常见安装位置
    工程路径   --project=<路径>    环境变量 PLC_PROJECT         不指定则只开 IDE 空窗口
    工作根目录 --base=<目录>       环境变量 PLC_MCP_BASE       本脚本所在目录

重要：本脚本用 subprocess 启动 IDE，IDE 会继承当前进程的环境变量。
      所以「用本脚本启动 IDE」是唯一能让 PLC_MCP_BASE 对 IDE 内脚本生效的方式。
      如果你手动双击图标开 IDE，环境变量不会传进去，IDE 内脚本会靠
      scripts/ide/_base.py 从自身路径反推 BASE（见该文件说明）。
"""
import io
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PROFILE = os.environ.get("INOPROSHOP_PROFILE") or "InoProShop(V1.10.0.3)"

# 常见安装位置，仅作为「自动搜索」的候选，不是唯一答案
IDE_CANDIDATES = [
    r"E:\汇川\中型1.10.0.3\CODESYS\Common\InoProShop.exe",
    r"C:\Program Files\Inovance\InoProShop\CODESYS\Common\InoProShop.exe",
    r"C:\Program Files (x86)\Inovance\InoProShop\CODESYS\Common\InoProShop.exe",
    r"D:\Program Files\Inovance\InoProShop\CODESYS\Common\InoProShop.exe",
]


def parse_argv(argv):
    """解析 --key=value 形式的参数，其余位置参数忽略"""
    opts = {}
    for a in argv[1:]:
        if a.startswith("--") and "=" in a:
            k, v = a[2:].split("=", 1)
            opts[k.lower()] = v
    return opts


def find_ide(opts):
    p = opts.get("ide") or os.environ.get("INOPROSHOP_EXE")
    if p:
        p = p.strip().strip('"')
        if os.path.isfile(p):
            return p
        print("WARN: 指定的 IDE 路径不存在，改为自动搜索: %s" % p)
    for c in IDE_CANDIDATES:
        if os.path.isfile(c):
            return c
    return None


def main():
    opts = parse_argv(sys.argv)
    # 位置参数：第一个纯数字视为等待秒数
    wait = 240
    for a in sys.argv[1:]:
        if not a.startswith("--") and a.isdigit():
            wait = int(a)
            break
    if "wait" in opts and opts["wait"].isdigit():
        wait = int(opts["wait"])

    base = (opts.get("base") or os.environ.get("PLC_MCP_BASE") or HERE).strip().strip('"')
    base = os.path.abspath(base)
    proj = (opts.get("project") or os.environ.get("PLC_PROJECT") or "").strip().strip('"')

    ide = find_ide(opts)
    if not ide:
        print("FAIL: 找不到 InoProShop.exe")
        print("  请用 --ide=<完整路径> 指定，或设环境变量 INOPROSHOP_EXE")
        return 2
    if proj and not os.path.isfile(proj):
        print("FAIL: 工程文件不存在: %s" % proj)
        print("  请用 --project=<完整路径> 指定，或设环境变量 PLC_PROJECT")
        return 3

    ipc = os.path.join(base, "ipc")
    for d in (ipc,):
        if not os.path.isdir(d):
            try:
                os.makedirs(d)
            except OSError:
                pass

    daemon = os.path.join(base, "ide", "plc_daemon.py")
    if not os.path.isfile(daemon):
        print("FAIL: 找不到守护脚本: %s" % daemon)
        print("  请把 scripts/ 整个目录铺到 %s" % base)
        return 4

    ready = os.path.join(ipc, "ready.flag")
    bootlog = os.path.join(ipc, "daemon_boot.log")

    # 清理旧状态
    for f in ("ready.flag", "cmd.json", "result.json", "stop.flag",
              "instance.lock", "heartbeat", "daemon.pid", "daemon_boot.log"):
        try:
            os.remove(os.path.join(ipc, f))
        except OSError:
            pass

    # 关键：把 BASE 写进环境，子进程 IDE 会继承，IDE 内 _base.py 优先读它
    env = os.environ.copy()
    env["PLC_MCP_BASE"] = base
    env["PLC_MCP_IPC"] = ipc

    args = [ide, "--profile=" + PROFILE, "--runscript=" + daemon]
    if proj:
        args.insert(2, "--project=" + proj)

    print("BASE   :", base)
    print("IDE    :", ide)
    print("PROJECT:", proj or "(不指定，只开 IDE)")
    print("launch :", " ".join('"%s"' % a for a in args))

    p = subprocess.Popen(args, env=env)

    deadline = time.time() + wait
    while time.time() < deadline:
        time.sleep(1.0)
        if os.path.exists(ready):
            print("READY at +%.1fs" % (wait - (deadline - time.time())))
            print("ide pid:", p.pid)
            return 0
        if p.poll() is not None:
            print("IDE exited early, code=", p.returncode)
            break

    print("NOT READY after %ss (ide alive=%s pid=%s)" % (
        wait, p.poll() is None, p.pid))
    if os.path.exists(bootlog):
        with io.open(bootlog, "r", encoding="utf-8", errors="replace") as f:
            print("--- boot log ---")
            print(f.read()[-3000:])
    else:
        print("(no daemon_boot.log)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
