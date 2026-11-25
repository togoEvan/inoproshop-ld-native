# -*- coding: utf-8 -*-
"""守护进程诊断：一次看清「到底卡在哪一步」。

用法：
    python probe_daemon.py

输出四段：
    1. IDE 进程      有没有在跑、PID、窗口标题
    2. 候选 BASE     本机所有可能的 BASE，各自的 ready.flag / 心跳年龄
    3. bridge 视角    bridge.py 自己解析到的 BASE 与 IPC
    4. ping 结果      实际能不能通

典型判读：
    · 「候选 BASE 里某个心跳很新，但不是 bridge 用的那个」
      → 守护挂错目录。用 bridge.call('eval_file', path=<run_boot_daemon.py>)
        重新注入，或直接改 bridge 的 BASE。
    · 「所有 BASE 都没有心跳」
      → 守护确实没起。IDE 里执行 工具 → 脚本 → 执行脚本文件... →
        选 scripts/ide/boot_daemon.py
    · 「心跳很新但 ping 失败」
      → 守护活着但命令队列不通，看 ipc/daemon.log。
"""
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))   # <BASE>/ide
BASE = os.path.dirname(HERE)                        # <BASE>
sys.path.insert(0, BASE)


def _ps(cmd):
    """跑 PowerShell 并取 stdout。
    ⚠ 必须显式指定编码：Windows PowerShell 5.1 默认按系统 ANSI(GBK) 输出，
       而 subprocess 默认按 UTF-8 解码，遇到中文会 UnicodeDecodeError。"""
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "[Console]::OutputEncoding=[Text.Encoding]::UTF8; " + cmd],
            capture_output=True, timeout=30)
        raw = out.stdout or b""
        for enc in ("utf-8", "gbk"):
            try:
                return raw.decode(enc).strip()
            except Exception:
                continue
        return raw.decode("utf-8", "replace").strip()
    except Exception as e:
        return "ERR: %s" % e


def sec(title):
    print("")
    print("=" * 66)
    print(title)
    print("=" * 66)


def ide_status():
    sec("1. IDE 进程")
    n = _ps("(Get-Process InoProShop -ErrorAction SilentlyContinue | Measure-Object).Count")
    print("InoProShop 进程数: %s" % n)
    if n.strip() in ("0", ""):
        print("!! IDE 没在运行，守护不可能存在")
        return False
    info = _ps(
        "Get-Process InoProShop | Where-Object {$_.MainWindowHandle -ne 0} | "
        "ForEach-Object { \"$($_.Id)|$($_.MainWindowTitle)\" }")
    for line in info.splitlines():
        if "|" in line:
            pid, title = line.split("|", 1)
            print("  PID %s  窗口: %s" % (pid, title[:70]))
    return True


def candidate_bases():
    sec("2. 候选 BASE（哪些目录里有守护的存活标记）")
    cands = []

    # 本技能包：<BASE> = scripts/（本文件在 scripts/ide/ 下）
    cands.append(BASE)

    # 历史遗留 / 其他常见位置
    for p in (r"D:\plc_mcp",
              os.path.join(os.path.dirname(BASE), "plc_mcp"),
              r"D:\小艺Work工作空间\20261123160323\plc_mcp"):
        if p not in cands:
            cands.append(p)

    env = (os.environ.get("PLC_MCP_BASE") or "").strip()
    if env and env not in cands:
        cands.append(env)

    now = time.time()
    for b in cands:
        ipc = os.path.join(b, "ipc")
        exists = os.path.isdir(ipc)
        ready = os.path.exists(os.path.join(ipc, "ready.flag"))
        hb = os.path.join(ipc, "heartbeat")
        age = None
        if os.path.exists(hb):
            try:
                age = now - os.path.getmtime(hb)
            except Exception:
                pass
        flag = "  <-- 存活" if (ready and age is not None and age < 8) else ""
        print("  %s" % b)
        print("     ipc 存在=%s  ready.flag=%s  心跳年龄=%s%s"
              % (exists, ready,
                 ("%.1fs" % age) if age is not None else "无",
                 flag))
    return cands


def bridge_view():
    sec("3. bridge 视角（它自己要找哪个目录）")
    try:
        import bridge
        print("bridge.BASE = %s" % bridge.BASE)
        print("bridge.IPC  = %s" % bridge.IPC)
        print("bridge.READY 存在 = %s" % os.path.exists(bridge.READY))
        dpy = getattr(bridge, "DAEMON_PY", None)
        print("bridge.DAEMON_PY = %s" % dpy)
        print("      存在 = %s" % (os.path.exists(dpy) if dpy else "?"))
        return bridge
    except Exception as e:
        print("!! import bridge 失败: %s" % e)
        return None


def ping(bridge):
    sec("4. ping")
    if bridge is None:
        print("跳过（bridge 不可用）")
        return
    if not os.path.exists(bridge.READY):
        print("!! bridge 的 IPC 里没有 ready.flag")
        print("   -> 守护没起，或起在了别的 BASE（见第 2 段）")
        return
    try:
        t0 = time.time()
        r = bridge.call("ping", timeout=15)
        print("OK  %.2fs  %s" % (time.time() - t0,
                                 json.dumps(r, ensure_ascii=False)))
    except Exception as e:
        print("!! ping 失败: %s" % e)
        print("   -> 守护标记在但命令队列不通，看 ipc/daemon.log")


def main():
    print("InoProShop 守护进程诊断")
    print("脚本目录: %s" % HERE)
    if not ide_status():
        return
    candidate_bases()
    b = bridge_view()
    ping(b)
    print("")
    print("=" * 66)
    print("判读提示")
    print("=" * 66)
    print("· 某候选 BASE 心跳很新但不是 bridge 用的那个 -> 守护挂错目录")
    print("  修：用 bridge.call('eval_file', path=<run_boot_daemon.py>) 重新注入")
    print("· 所有 BASE 都没心跳 -> 守护没起")
    print("  修：IDE 里 工具 -> 脚本 -> 执行脚本文件... -> 选 ide/boot_daemon.py")
    print("· 心跳新但 ping 失败 -> 看 ipc/daemon.log")


if __name__ == "__main__":
    main()
