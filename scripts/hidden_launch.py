# -*- coding: utf-8 -*-
# @py3
"""在隐藏桌面上启动 InoProShop 并注入守护（纯 ctypes，不需要 .NET）。

用法:
    python hidden_launch.py --project=<工程> [--ide=<InoProShop.exe>] [--base=<工作根>] [--wait=180]
    python hidden_launch.py --status
    python hidden_launch.py --stop

原理: CreateDesktopW 建一个不可见桌面 → CreateProcessW + STARTUPINFO.lpDesktop
把 IDE 生到该桌面 → 追加 --runscript=<BASE>/ide/plc_daemon.py。
窗口存在但不在当前输入桌面，用户看不到、点不到，也不抢前台。
本进程是监督者：一直等到 IDE 退出，期间不要让桌面句柄先释放。

工程怎么打开（重要）:
    默认「先空 IDE 起守护，READY 后再用 bridge 的 open_project 打开工程」。
    不要给 IDE 传 --project=：命令行打开会与设备/库初始化抢跑，带
    EtherCAT/CANOpen 的复杂工程编译时会冒出 500 个「未知类型: Tparam_*」
    （实测 study.project 副本 errors=500；空启动再 open_project 是 0 错误）。
    确实要复现旧行为用 --raw-project。
"""
import ctypes
import ctypes.wintypes as wt
import json
import os
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PROFILE_DEFAULT = "InoProShop(V1.10.0.3)"
GENERIC_ALL = 0x10000000
IDE_CANDIDATES = [
    r"E:\汇川\中型1.10.0.3\CODESYS\Common\InoProShop.exe",
    r"E:\汇川\中小型1.10.0.3\CODESYS\Common\InoProShop.exe",
    r"C:\Program Files\Inovance\InoProShop\CODESYS\Common\InoProShop.exe",
    r"C:\Program Files (x86)\Inovance\InoProShop\CODESYS\Common\InoProShop.exe",
    r"D:\Program Files\Inovance\InoProShop\CODESYS\Common\InoProShop.exe",
]


class STARTUPINFO(ctypes.Structure):
    _fields_ = [
        ("cb", wt.DWORD), ("lpReserved", wt.LPWSTR), ("lpDesktop", wt.LPWSTR),
        ("lpTitle", wt.LPWSTR), ("dwX", wt.DWORD), ("dwY", wt.DWORD),
        ("dwXSize", wt.DWORD), ("dwYSize", wt.DWORD), ("dwXCountChars", wt.DWORD),
        ("dwYCountChars", wt.DWORD), ("dwFillAttribute", wt.DWORD),
        ("dwFlags", wt.DWORD), ("wShowWindow", wt.WORD), ("cbReserved2", wt.WORD),
        ("lpReserved2", ctypes.POINTER(ctypes.c_byte)),
        ("hStdInput", wt.HANDLE), ("hStdOutput", wt.HANDLE), ("hStdError", wt.HANDLE),
    ]


class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [("hProcess", wt.HANDLE), ("hThread", wt.HANDLE),
                ("dwProcessId", wt.DWORD), ("dwThreadId", wt.DWORD)]


user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
user32.CreateDesktopW.restype = wt.HANDLE
user32.CreateDesktopW.argtypes = [wt.LPCWSTR, wt.LPVOID, wt.LPVOID, wt.DWORD, wt.DWORD, wt.LPVOID]
user32.CloseDesktop.argtypes = [wt.HANDLE]
kernel32.CreateProcessW.restype = wt.BOOL
kernel32.CreateProcessW.argtypes = [wt.LPCWSTR, wt.LPWSTR, wt.LPVOID, wt.LPVOID, wt.BOOL,
                                    wt.DWORD, wt.LPVOID, wt.LPCWSTR,
                                    ctypes.POINTER(STARTUPINFO), ctypes.POINTER(PROCESS_INFORMATION)]
kernel32.WaitForSingleObject.argtypes = [wt.HANDLE, wt.DWORD]
kernel32.GetExitCodeProcess.argtypes = [wt.HANDLE, ctypes.POINTER(wt.DWORD)]
kernel32.CloseHandle.argtypes = [wt.HANDLE]


def parse(argv):
    opts = {}
    for a in argv[1:]:
        if a.startswith("--"):
            if "=" in a:
                k, v = a[2:].split("=", 1)
                opts[k.lower()] = v
            else:
                opts[a[2:].lower()] = True
    return opts


def resolve(opts):
    base = (opts.get("base") or os.environ.get("PLC_MCP_BASE") or HERE).strip().strip('"')
    base = os.path.abspath(base)
    ide = (opts.get("ide") or os.environ.get("INOPROSHOP_EXE") or "").strip().strip('"')
    if not ide or not os.path.isfile(ide):
        ide = next((c for c in IDE_CANDIDATES if os.path.isfile(c)), "")
    proj = (opts.get("project") or os.environ.get("PLC_PROJECT") or "").strip().strip('"')
    prof = opts.get("profile") or os.environ.get("INOPROSHOP_PROFILE") or PROFILE_DEFAULT
    return base, ide, proj, prof


def paths(base):
    ipc = os.path.join(base, "ipc")
    return ipc, os.path.join(ipc, "hidden.json")


def read_state(base):
    try:
        with open(paths(base)[1], "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def alive(pid):
    try:
        out = subprocess.run(["tasklist", "/FI", "PID eq %s" % pid, "/NH"],
                             capture_output=True, text=True, timeout=15).stdout
        return str(pid) in (out or "")
    except Exception:
        return False


def do_status(base):
    st = read_state(base)
    if not st:
        print("no hidden instance recorded under", base)
        return 1
    pid = st.get("pid")
    ok = alive(pid)
    ready = os.path.exists(os.path.join(base, "ipc", "ready.flag"))
    print("pid      :", pid, "(alive)" if ok else "(dead)")
    print("desktop  :", st.get("desktop"))
    print("project  :", st.get("project"))
    print("base     :", st.get("base"))
    print("daemon   :", "READY" if ready else "not ready")
    return 0 if (ok and ready) else 1


def do_stop(base):
    st = read_state(base)
    if not st:
        print("nothing to stop")
        return 0
    pid = st.get("pid")
    if not alive(pid):
        print("pid", pid, "already gone")
        return 0
    subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True)
    print("killed pid", pid)
    try:
        os.remove(os.path.join(base, "ipc", "ready.flag"))
    except OSError:
        pass
    return 0


def open_project(base, proj, timeout=300):
    """守护 READY 之后用 bridge 打开工程（而不是给 IDE 传 --project=）。

    命令行 --project= 会让工程初始化与设备库/设备参数类型生成抢跑：
    带 EtherCAT/CANOpen 设备的工程（InoPack 模板）会报几百个
    「未知类型: Tparam_64_...」；空 IDE 起来后再 open_project 则是 0 错误。
    """
    bridge = os.path.join(base, "bridge.py")
    if not os.path.isfile(bridge):
        print("OPEN: skipped, no bridge.py under %s" % base, flush=True)
        return False
    env = os.environ.copy()
    env["PLC_MCP_BASE"] = base
    env["PLC_MCP_IPC"] = os.path.join(base, "ipc")
    arg = json.dumps({"path": proj}, ensure_ascii=False)
    t0 = time.time()
    try:
        p = subprocess.run([sys.executable, bridge, "open_project", arg],
                           cwd=base, env=env, capture_output=True, text=True,
                           timeout=timeout)
    except subprocess.TimeoutExpired:
        print("OPEN: timeout after %ss" % timeout, flush=True)
        return False
    out = ((p.stdout or "") + (p.stderr or "")).strip().replace("\n", " ")
    print("OPEN: %s (+%.1fs)" % (out[:400], time.time() - t0), flush=True)
    return '"ok": true' in out


def launch(base, ide, proj, prof, wait_s, open_after=True, raw_project=False):
    if not ide or not os.path.isfile(ide):
        print("FAIL: 找不到 InoProShop.exe，用 --ide=<完整路径> 指定")
        return 2
    if proj and not os.path.isfile(proj):
        print("FAIL: 工程不存在:", proj)
        return 3
    daemon = os.path.join(base, "ide", "plc_daemon.py")
    if not os.path.isfile(daemon):
        print("FAIL: 找不到守护脚本:", daemon)
        return 4

    ipc, state_f = paths(base)
    if not os.path.isdir(ipc):
        os.makedirs(ipc)
    for f in ("ready.flag", "cmd.json", "result.json", "stop.flag",
              "instance.lock", "heartbeat", "daemon.pid", "daemon_boot.log"):
        try:
            os.remove(os.path.join(ipc, f))
        except OSError:
            pass

    # IDE 内脚本读不到 shell 环境变量；让子进程继承本进程的环境块
    os.environ["PLC_MCP_BASE"] = base
    os.environ["PLC_MCP_IPC"] = ipc
    # 标记「这是隐藏实例」：验收脚本据此才敢清消息（不抹用户面板）
    os.environ["PLC_MCP_HIDDEN"] = "1"

    desktop = "DSHHidden_" + os.urandom(4).hex()
    hdesk = user32.CreateDesktopW(desktop, None, None, 0, GENERIC_ALL, None)
    if not hdesk:
        print("FAIL: CreateDesktopW err=", ctypes.get_last_error())
        return 5

    args = [ide, "--profile=" + prof]
    if proj and raw_project:
        # 旧路径：命令行带工程。复杂工程会 500 个未知 Tparam_*，仅供对照实验
        print("WARN: --raw-project 用 --project= 打开工程，复杂工程会编译失败；"
              "推荐去掉它，走 READY 后的 open_project", flush=True)
        args.append("--project=" + proj)
    args.append("--runscript=" + daemon)
    cmdline = subprocess.list2cmdline(args)

    si = STARTUPINFO()
    si.cb = ctypes.sizeof(STARTUPINFO)
    si.lpDesktop = desktop
    pi = PROCESS_INFORMATION()
    ok = kernel32.CreateProcessW(None, ctypes.c_wchar_p(cmdline), None, None, False, 0,
                                 None, os.path.dirname(ide), ctypes.byref(si), ctypes.byref(pi))
    if not ok:
        print("FAIL: CreateProcessW err=", ctypes.get_last_error())
        user32.CloseDesktop(hdesk)
        return 6

    pid = pi.dwProcessId
    with open(state_f, "w", encoding="utf-8") as fh:
        json.dump({"pid": pid, "desktop": desktop, "project": proj, "ide": ide,
                   "base": base, "started": time.strftime("%Y-%m-%d %H:%M:%S")},
                  fh, ensure_ascii=False, indent=2)
    print("desktop:", desktop, "pid:", pid, flush=True)

    ready = os.path.join(ipc, "ready.flag")
    deadline = time.time() + wait_s
    got = False
    while time.time() < deadline:
        if os.path.exists(ready):
            got = True
            print("READY at +%.1fs" % (wait_s - (deadline - time.time())), flush=True)
            break
        time.sleep(0.5)
    if not got:
        print("NOT READY after %ss" % wait_s, flush=True)
        boot = os.path.join(ipc, "daemon_boot.log")
        if os.path.isfile(boot):
            print("--- daemon_boot.log (tail) ---")
            print(open(boot, "r", encoding="utf-8", errors="replace").read()[-2500:])
    elif proj and open_after and not raw_project:
        open_project(base, proj)

    print("supervising (Ctrl+C 不会杀 IDE，收尾请用 --stop)", flush=True)
    try:
        kernel32.WaitForSingleObject(pi.hProcess, 0xFFFFFFFF)
    except KeyboardInterrupt:
        print("supervisor interrupted; IDE pid", pid, "still running")
        return 7
    ec = wt.DWORD(0)
    kernel32.GetExitCodeProcess(pi.hProcess, ctypes.byref(ec))
    kernel32.CloseHandle(pi.hThread)
    kernel32.CloseHandle(pi.hProcess)
    user32.CloseDesktop(hdesk)
    print("ide exited, code=", ec.value, flush=True)
    return 0


def main():
    opts = parse(sys.argv)
    base = (opts.get("base") or os.environ.get("PLC_MCP_BASE") or HERE).strip().strip('"')
    base = os.path.abspath(base)
    if opts.get("status"):
        return do_status(base)
    if opts.get("stop"):
        return do_stop(base)
    b, ide, proj, prof = resolve(opts)
    return launch(b, ide, proj, prof, int(opts.get("wait") or 180),
                  open_after=not opts.get("no-open"),
                  raw_project=bool(opts.get("raw-project")))


if __name__ == "__main__":
    sys.exit(main())
