# -*- coding: utf-8 -*-
"""与 IDE 内守护进程通信的客户端（文件队列 IPC）"""
import json
import os
import subprocess
import sys
import time

def _resolve_base():
    """工作根目录解析，与 ide/_base.py 保持一致的优先级：
       环境变量 PLC_MCP_BASE > <本目录>/base_path.txt > 本目录
    """
    env = (os.environ.get("PLC_MCP_BASE") or "").strip().strip('"')
    if env:
        return os.path.abspath(env)
    here = os.path.dirname(os.path.abspath(__file__))
    cfg = os.path.join(here, "base_path.txt")
    if os.path.isfile(cfg):
        try:
            with open(cfg, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip().strip('"')
                    if line and not line.startswith("#"):
                        return os.path.abspath(line)
        except Exception:
            pass
    return here


BASE = _resolve_base()
IPC = os.environ.get("PLC_MCP_IPC") or os.path.join(BASE, "ipc")
CMD = os.path.join(IPC, "cmd.json")
RES = os.path.join(IPC, "result.json")
READY = os.path.join(IPC, "ready.flag")
STOP = os.path.join(IPC, "stop.flag")
DAEMON_PY = os.path.join(BASE, "ide", "plc_daemon.py")
TRIGGER_PS1 = os.path.join(BASE, "ide_trigger.ps1")


class BridgeError(Exception):
    pass


def _ensure_dirs():
    if not os.path.isdir(IPC):
        os.makedirs(IPC)


def is_ide_running():
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "(Get-Process InoProShop -ErrorAction SilentlyContinue | Measure-Object).Count"],
            capture_output=True, text=True, timeout=20)
        return int((out.stdout or "0").strip() or "0") > 0
    except Exception:
        return False


def is_daemon_alive():
    if not os.path.exists(READY):
        return False
    # 发个 ping 验证
    try:
        send({"action": "ping"}, timeout=8)
        return True
    except Exception:
        return False


def start_daemon(timeout=90):
    """静默触发 IDE 执行守护脚本（UIA InvokePattern，不移动鼠标）"""
    _ensure_dirs()
    if not is_ide_running():
        raise BridgeError("InoProShop 未运行，请先打开 InoProShop 并打开工程")
    try:
        os.remove(READY)
    except OSError:
        pass
    cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
           "-File", TRIGGER_PS1, "-ScriptPath", DAEMON_PY,
           "-TimeoutSec", str(timeout)]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 60)
    out = (p.stdout or "") + (p.stderr or "")
    if p.returncode != 0:
        raise BridgeError("触发 IDE 脚本失败 (exit=%s): %s" % (p.returncode, out.strip()[:500]))
    deadline = time.time() + 30
    while time.time() < deadline:
        if os.path.exists(READY):
            return True
        time.sleep(0.2)
    raise BridgeError("守护进程未就绪（ready.flag 未生成）")


def stop_daemon():
    _ensure_dirs()
    try:
        with open(STOP, "w") as f:
            f.write("stop")
    except Exception:
        pass
    time.sleep(1.5)
    for p in (STOP, READY):
        try:
            os.remove(p)
        except OSError:
            pass


def send(payload, timeout=180):
    """发送命令并等待结果"""
    _ensure_dirs()
    for p in (RES, CMD):
        try:
            os.remove(p)
        except OSError:
            pass
    tmp = CMD + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    os.replace(tmp, CMD)

    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(0.12)
        if os.path.exists(RES):
            time.sleep(0.06)
            try:
                with open(RES, "r", encoding="utf-8") as f:
                    data = json.load(f)
                try:
                    os.remove(RES)
                except OSError:
                    pass
                return data
            except Exception:
                time.sleep(0.1)
                continue
    raise BridgeError("命令超时（%ss）: %s" % (timeout, payload.get("action")))


def call(action, timeout=180, **kwargs):
    payload = {"action": action}
    payload.update(kwargs)
    if not os.path.exists(READY):
        start_daemon()
    return send(payload, timeout=timeout)


def restart_daemon(timeout=90):
    """停掉旧守护并重新静默启动（用于加载修改后的 plc_daemon.py）"""
    stop_daemon()
    return start_daemon(timeout=timeout)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: bridge.py <action> [json-args]")
        sys.exit(1)
    act = sys.argv[1]
    kw = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    try:
        r = call(act, **kw)
    except BridgeError as e:
        r = {"ok": False, "error": str(e)}
    print(json.dumps(r, ensure_ascii=False, indent=2))
