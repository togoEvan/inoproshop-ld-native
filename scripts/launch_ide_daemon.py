# -*- coding: utf-8 -*-
"""启动 InoProShop（UI 模式），并用 --runscript 让守护脚本自动执行。
不点菜单、不动鼠标、不抢焦点。
用法: python launch_ide_daemon.py [wait_sec]
"""
import subprocess, sys, os, time, io

IDE = os.environ.get("INOPROSHOP_EXE") or r"E:\汇川\中型1.10.0.3\CODESYS\Common\InoProShop.exe"
PROFILE = "InoProShop(V1.10.0.3)"
PROJ = (r"D:\Users\inopack\inopack\InoPack-包装行业编程模板V1.0.0.4"
        r"（当前仅支持到1.9版本）\InoPack包装PLC模板程序_V1.0.0.4.project")
BASE = os.environ.get("PLC_MCP_BASE") or r"D:\小艺Work工作空间\20261123160323\plc_mcp"
DAEMON = os.path.join(BASE, "ide", "plc_daemon.py")
IPC = os.path.join(BASE, "ipc")
READY = os.path.join(IPC, "ready.flag")
BOOTLOG = os.path.join(IPC, "daemon_boot.log")


def main():
    wait = int(sys.argv[1]) if len(sys.argv) > 1 else 240

    # 清理旧状态
    for f in ("ready.flag", "cmd.json", "result.json", "stop.flag",
              "instance.lock", "heartbeat", "daemon.pid", "daemon_boot.log"):
        p = os.path.join(IPC, f)
        try:
            os.remove(p)
        except OSError:
            pass

    args = [IDE,
            "--profile=" + PROFILE,
            "--project=" + PROJ,
            "--runscript=" + DAEMON]
    print("launch:", " ".join('"%s"' % a for a in args))
    p = subprocess.Popen(args)

    deadline = time.time() + wait
    while time.time() < deadline:
        time.sleep(1.0)
        if os.path.exists(READY):
            print("READY at +%.1fs" % (wait - (deadline - time.time())))
            print("ide pid:", p.pid)
            return 0
        if p.poll() is not None:
            print("IDE exited early, code=", p.returncode)
            break
    print("NOT READY after %ss (ide alive=%s pid=%s)" % (
        wait, p.poll() is None, p.pid))
    if os.path.exists(BOOTLOG):
        with io.open(BOOTLOG, "r", encoding="utf-8", errors="replace") as f:
            print("--- boot log ---")
            print(f.read()[-3000:])
    else:
        print("(no daemon_boot.log)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
