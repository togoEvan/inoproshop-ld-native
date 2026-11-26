# -*- coding: utf-8 -*-
"""与 IDE 内守护进程通信的客户端（文件队列 IPC）

═══════════════════════════════════════════════════════════════════════
设计要点（2026-11-26 重写，融入 dsh-computer-use-win 的若干工程实践）
═══════════════════════════════════════════════════════════════════════

【要点 1】run_id 对账 —— 迟到的结果绝不冒充本轮结果
  旧实现只做「删 result.json → 写 cmd.json → 等 result.json 出现」。
  如果上一条命令超时了、守护过一会儿才把结果写出来，这条**迟到的结果**
  会被下一次 send() 当成自己的结果读走 —— 调用方拿到的是上一次的输出，
  却以为成功了。这是最阴险的一类假成功：json 能解析、ok 也是 true，
  只是内容根本不是这条命令的。
  修复：每条命令带唯一 run_id，守护写回结果时原样带回；对不上就丢弃继续等。

【要点 2】心跳看门狗 —— 守护死了立刻报错，不干等满超时
  旧实现只有一个 `while time.time() < deadline` 死等，守护线程崩了也要
  等满 180s 才报「命令超时」，而且报的是「超时」不是「守护已死」，
  排查方向直接跑偏。
  修复：轮询期间同时看 heartbeat 的 mtime，超过 STALE 秒没更新就立刻抛
  E_HEARTBEAT_STALE，并在错误里带上最后一次心跳的年龄。

【要点 3】取消代数（cancel generation）—— 「取消这条命令」不等于「杀掉守护」
  旧实现 stop_daemon() 写 stop.flag 让守护退出，还顺手删掉 ready.flag，
  结果下一次调用又得重新注入 —— 取消一条命令的代价是丢掉整个守护。
  而且布尔 flag 无法区分「这条命令的取消」和「上一条命令的取消」。
  修复：cancel.gen 单调递增；守护每条命令开始前记下当时的代数，执行中
  发现代数变了就尽快收尾并标记 cancelled。新命令天然不受旧取消影响。

【要点 4】进程内互斥 —— 并发调用不互相踩 cmd.json
  旧实现两个线程同时 send() 会互相删除/覆盖 cmd.json，可能一条命令被执行
  两遍（或两条都丢）。修复：ipc/bridge.lock 具名锁，陈旧锁（持有者已死）
  自动抢占，抢不到就排队。

【要点 5】结构化错误 —— 错误码是稳定的，人话是可变的
  所有失败都抛 BridgeError(code=..., detail=...)，调用方按 code 分支，
  不要 match 中文文案。错误码表见 ERRORS。

【要点 6】selftest —— 一条命令给出可诊断的健康快照
  旧的排错方式是「跑 probe_daemon.py 看第 2 段」，而那个文件长期不存在
  （README/SKILL 都引用了它，但仓库里没有）。现在 bridge.py 自带
  selftest，不用另找脚本，且 fail-closed：任何一项探测失败都显式报出来。

═══════════════════════════════════════════════════════════════════════
兼容性
═══════════════════════════════════════════════════════════════════════
  - `send()/call()` 的签名与返回值不变，老的调用方（do_replace.py 等）无需改。
  - 结果里新增 `run_id` / `cancelled` 字段，老代码忽略即可。
  - 守护若还是旧版（不回带 run_id），本客户端退化为「按文件出现即认」，
    并在返回值里标 `legacy_daemon: true` —— 向后兼容，但会失去要点 1 的保护。
"""
import errno
import io
import json
import os
import subprocess
import sys
import time
import uuid

# ---------------------------------------------------------------------------
# 错误码：调用方按 code 分支，不要 match 文案
# ---------------------------------------------------------------------------
E_NO_DAEMON = "E_NO_DAEMON"                    # 守护没起且自动注入失败
E_NO_IDE = "E_NO_IDE"                          # InoProShop 进程不存在
E_HEARTBEAT_STALE = "E_HEARTBEAT_STALE"        # 守护心跳停摆（线程已死/IDE 卡住）
E_TIMEOUT = "E_TIMEOUT"                        # 命令超时（守护还活着但没回）
E_CANCELLED = "E_CANCELLED"                    # 命令被 cancel() 取消
E_LOCK_TIMEOUT = "E_LOCK_TIMEOUT"              # 抢不到进程内互斥锁
E_BAD_RESULT = "E_BAD_RESULT"                  # 结果文件存在但解析不出来
E_TRIGGER_FAILED = "E_TRIGGER_FAILED"          # 注入脚本执行失败

ERRORS = {
    E_NO_DAEMON: "守护进程未运行，且自动注入失败",
    E_NO_IDE: "InoProShop 未运行，请先打开 IDE 并打开工程",
    E_HEARTBEAT_STALE: "守护心跳停摆（守护线程已死或 IDE 主线程卡住）",
    E_TIMEOUT: "命令超时（守护仍在心跳，但未在限期内返回结果）",
    E_CANCELLED: "命令已被取消",
    E_LOCK_TIMEOUT: "另一个 bridge 调用持有锁且未释放",
    E_BAD_RESULT: "结果文件无法解析",
    E_TRIGGER_FAILED: "触发 IDE 执行守护脚本失败",
}


class BridgeError(Exception):
    """所有 bridge 失败的统一异常。code 稳定，detail 供人看。"""

    def __init__(self, code, detail="", **extra):
        self.code = code
        self.detail = detail
        self.extra = extra
        msg = ERRORS.get(code, code)
        if detail:
            msg = "%s：%s" % (msg, detail)
        Exception.__init__(self, msg)

    def as_dict(self):
        d = {"ok": False, "error": self.detail or ERRORS.get(self.code, self.code),
             "code": self.code}
        d.update(self.extra)
        return d


# ---------------------------------------------------------------------------
# 路径解析（与 ide/_base.py 的优先级保持一致）
# ---------------------------------------------------------------------------
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
            with io.open(cfg, "r", encoding="utf-8") as f:
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
CMD_RUNNING = os.path.join(IPC, "running.json")
RES = os.path.join(IPC, "result.json")
READY = os.path.join(IPC, "ready.flag")
STOP = os.path.join(IPC, "stop.flag")
HEARTBEAT = os.path.join(IPC, "heartbeat")
CANCEL_GEN = os.path.join(IPC, "cancel.gen")
LOCK = os.path.join(IPC, "bridge.lock")
DAEMON_PY = os.path.join(BASE, "ide", "plc_daemon.py")
TRIGGER_PS1 = os.path.join(BASE, "ide_trigger.ps1")

# 心跳超过这个秒数没更新就认定守护已死。
# 与 plc_daemon.HEARTBEAT_FRESH 对齐：守护每 0.5s 一跳，8s 是很宽的余量。
HEARTBEAT_STALE = 8.0
# 结果文件出现后等它稳定（守护先写 .tmp 再 rename，理论上无需再等，留一点余量）
RESULT_SETTLE = 0.06


def _ensure_dirs():
    if not os.path.isdir(IPC):
        os.makedirs(IPC)


# ---------------------------------------------------------------------------
# 进程判活（要点 4 的依赖）
# ---------------------------------------------------------------------------
def _pid_alive(pid):
    """pid 对应进程是否还活着。

    ⚠ 不能用 os.kill(pid, 0) 判活 —— 实测（Windows 11 / Python 3.12）：
        os.kill(999999, 0) -> errno 22 (WinError 87 参数错误)
        os.kill(4, 0)      -> errno 13 (WinError 5  拒绝访问)
        os.kill(36704, 0)  -> errno 22 (WinError 87)  ← 这个 pid 明明活着（InoProShop）
       即「不存在的 pid」与「活着的 pid」抛出的是**同一个** errno 22，
       照 POSIX 的 ESRCH 判活会把所有进程都判成死的（陈旧锁永远能抢，等于没锁）。
    Windows 上走 OpenProcess + GetExitCodeProcess：拿得到句柄且
    STILL_ACTIVE(259) 才算活。
    """
    if pid <= 0:
        return False
    if os.name != "nt":
        try:
            os.kill(pid, 0)
            return True
        except OSError as e:
            return getattr(e, "errno", None) != errno.ESRCH
        except Exception:
            return False
    try:
        import ctypes
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        STILL_ACTIVE = 259
        k32 = ctypes.windll.kernel32
        h = k32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid))
        if not h:
            return False
        try:
            code = ctypes.c_ulong(0)
            if not k32.GetExitCodeProcess(h, ctypes.byref(code)):
                return False
            return code.value == STILL_ACTIVE
        finally:
            k32.CloseHandle(h)
    except Exception:
        # 判不了就当作「活着」：宁可等锁超时，也不要抢活人的锁
        return True


# ---------------------------------------------------------------------------
# 进程内互斥（要点 4）
# ---------------------------------------------------------------------------
class _IpcLock(object):
    """跨进程的文件锁，带陈旧锁抢占。

    不用 msvcrt.locking：它在文件被另一个进程以写方式打开时会抛
    PermissionError 而非阻塞，行为不如自己实现可控。
    这里用「原子创建 + 内容带 pid/timestamp」：创建失败就检查持有者是否还活着。
    """

    def __init__(self, path, timeout=60.0, stale=120.0):
        self.path = path
        self.timeout = timeout
        self.stale = stale
        self._held = False

    def _read_pid(self):
        try:
            with io.open(self.path, "r", encoding="utf-8") as f:
                return json.load(f).get("pid")
        except Exception:
            return "?"

    def _holder_dead(self):
        """持有者进程是否已死（或锁太旧）。"""
        try:
            with io.open(self.path, "r", encoding="utf-8") as f:
                info = json.load(f)
            pid = int(info.get("pid") or 0)
            ts = float(info.get("ts") or 0)
        except Exception:
            # 读不出来就当陈旧（可能是被写了一半就崩了）
            try:
                return (time.time() - os.path.getmtime(self.path)) > self.stale
            except OSError:
                return True
        if ts and (time.time() - ts) > self.stale:
            return True
        if pid <= 0:
            return True
        if pid == os.getpid():
            return False
        return not _pid_alive(pid)

    def acquire(self):
        deadline = time.time() + self.timeout
        payload = json.dumps({"pid": os.getpid(), "ts": time.time()})
        while True:
            try:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                try:
                    os.write(fd, payload.encode("utf-8"))
                finally:
                    os.close(fd)
                self._held = True
                return self
            except OSError:
                if self._holder_dead():
                    try:
                        os.remove(self.path)
                    except OSError:
                        pass
                    continue
                if time.time() >= deadline:
                    raise BridgeError(E_LOCK_TIMEOUT,
                                      "锁文件 %s 被 pid=%s 持有超过 %.0fs"
                                      % (self.path, self._read_pid(), self.timeout))
                time.sleep(0.05)

    def release(self):
        if not self._held:
            return
        try:
            os.remove(self.path)
        except OSError:
            pass
        self._held = False

    def __enter__(self):
        return self.acquire()

    def __exit__(self, *a):
        self.release()
        return False


# ---------------------------------------------------------------------------
# 环境探测
# ---------------------------------------------------------------------------
def is_ide_running():
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "(Get-Process InoProShop -ErrorAction SilentlyContinue | Measure-Object).Count"],
            capture_output=True, text=True, timeout=20)
        return int((out.stdout or "0").strip() or "0") > 0
    except Exception:
        return False


def heartbeat_age():
    """守护心跳距今秒数；心跳文件不存在返回 None。"""
    try:
        return time.time() - os.path.getmtime(HEARTBEAT)
    except OSError:
        return None


def is_daemon_alive(timeout=8):
    if not os.path.exists(READY):
        return False
    try:
        send({"action": "ping"}, timeout=timeout)
        return True
    except Exception:
        return False


def start_daemon(timeout=90):
    """静默触发 IDE 执行守护脚本（UIA InvokePattern，不移动鼠标）"""
    _ensure_dirs()
    if not is_ide_running():
        raise BridgeError(E_NO_IDE)
    try:
        os.remove(READY)
    except OSError:
        pass
    cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
           "-File", TRIGGER_PS1, "-ScriptPath", DAEMON_PY,
           "-TimeoutSec", str(timeout)]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 60)
    except subprocess.TimeoutExpired:
        raise BridgeError(E_TRIGGER_FAILED, "注入脚本执行超过 %ss" % (timeout + 60))
    out = (p.stdout or "") + (p.stderr or "")
    if p.returncode != 0:
        raise BridgeError(E_TRIGGER_FAILED,
                          "exit=%s: %s" % (p.returncode, out.strip()[:500]))
    deadline = time.time() + 30
    while time.time() < deadline:
        if os.path.exists(READY):
            return True
        time.sleep(0.2)
    raise BridgeError(E_NO_DAEMON, "ready.flag 未生成（注入脚本返回成功但守护没起来）")


# ---------------------------------------------------------------------------
# 取消（要点 3）
# ---------------------------------------------------------------------------
def _read_gen(path):
    try:
        with io.open(path, "r", encoding="utf-8") as f:
            return int((f.read() or "0").strip() or "0")
    except Exception:
        return 0


def current_cancel_gen():
    return _read_gen(CANCEL_GEN)


def cancel(reason="user"):
    """取消当前正在执行的命令。守护下一条命令开始前会重新取代数，所以
    取消只影响「正在跑的那条」，不影响后续命令 —— 这是与旧 stop_daemon()
    的本质区别（那个是杀守护）。

    返回取消后的代数，便于日志核对。
    """
    _ensure_dirs()
    gen = current_cancel_gen() + 1
    tmp = CANCEL_GEN + ".tmp"
    with io.open(tmp, "w", encoding="utf-8") as f:
        f.write(str(gen))
    os.replace(tmp, CANCEL_GEN)
    # 顺带写一份人能看的理由（不影响判定）
    try:
        with io.open(os.path.join(IPC, "cancel.reason"), "w", encoding="utf-8") as f:
            f.write("%s %s" % (time.strftime("%H:%M:%S"), reason))
    except Exception:
        pass
    return gen


def stop_daemon():
    """让守护进程退出（注意：这是「杀守护」，不是「取消当前命令」）。
    要取消单条命令请用 cancel()。"""
    _ensure_dirs()
    try:
        with io.open(STOP, "w", encoding="utf-8") as f:
            f.write("stop")
    except Exception:
        pass
    deadline = time.time() + 5
    while time.time() < deadline:
        if not os.path.exists(READY):
            break
        time.sleep(0.1)
    for p in (STOP, READY):
        try:
            os.remove(p)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# 发送命令（要点 1 + 2）
# ---------------------------------------------------------------------------
def _new_run_id():
    return "%s-%s" % (time.strftime("%Y%m%d%H%M%S"), uuid.uuid4().hex[:8])


def _read_result():
    """读并删除 result.json。读失败抛 E_BAD_RESULT（不吞成「没结果」）。"""
    try:
        with io.open(RES, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        raise BridgeError(E_BAD_RESULT, "%s（文件 %s）" % (e, RES))
    try:
        os.remove(RES)
    except OSError:
        pass
    return data


def send(payload, timeout=180):
    """发送命令并等待结果。

    payload 必须含 action；本函数会自动补 run_id。
    返回守护写回的 dict（含 run_id / ok / ...）。
    """
    _ensure_dirs()
    run_id = payload.get("run_id") or _new_run_id()
    payload = dict(payload)
    payload["run_id"] = run_id
    # 让守护知道本命令对应的取消基线（守护也会自己读，这里显式带上更可靠）
    payload.setdefault("cancel_gen_at_send", current_cancel_gen())

    with _IpcLock(LOCK):
        # 清掉可能残留的上一轮结果（有 run_id 对账兜底，这里只是减少噪声）
        try:
            os.remove(RES)
        except OSError:
            pass
        tmp = CMD + ".tmp"
        with io.open(tmp, "w", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False))
        os.replace(tmp, CMD)

        deadline = time.time() + timeout
        last_beat_check = 0.0
        while time.time() < deadline:
            time.sleep(0.12)
            if os.path.exists(RES):
                time.sleep(RESULT_SETTLE)
                data = _read_result()
                got = data.get("run_id")
                if got is None:
                    # 旧版守护不回带 run_id：退化为「出现即认」，但要标记出来
                    data["legacy_daemon"] = True
                    return data
                if got == run_id:
                    return data
                # 迟到的上一轮结果 —— 丢弃，继续等本轮
                continue

            # 心跳看门狗（要点 2）：每 ~1s 检查一次，别把循环拖慢
            now = time.time()
            if now - last_beat_check > 1.0:
                last_beat_check = now
                age = heartbeat_age()
                if age is not None and age > HEARTBEAT_STALE:
                    # 守护线程死了。清掉 cmd.json 免得它复活后补跑一条过期命令。
                    try:
                        os.remove(CMD)
                    except OSError:
                        pass
                    raise BridgeError(
                        E_HEARTBEAT_STALE,
                        "最后心跳在 %.1fs 前（阈值 %.0fs），命令 %s 已放弃"
                        % (age, HEARTBEAT_STALE, payload.get("action")),
                        heartbeat_age=round(age, 1), run_id=run_id)

            # 取消检查：调用方在另一个线程里 cancel() 时，这里尽快返回
            if current_cancel_gen() > int(payload.get("cancel_gen_at_send") or 0):
                try:
                    os.remove(CMD)
                except OSError:
                    pass
                raise BridgeError(E_CANCELLED, "命令 %s 被取消" % payload.get("action"),
                                  run_id=run_id)

        raise BridgeError(E_TIMEOUT, "%ss 内未返回：%s" % (timeout, payload.get("action")),
                          run_id=run_id)


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


# ---------------------------------------------------------------------------
# 自检（要点 6）
# ---------------------------------------------------------------------------
def selftest(ping_timeout=10):
    """一次给出可诊断的健康快照。不抛异常，全部失败都体现在返回结构里。

    返回 dict：
      ok            全部关键项通过
      base          解析到的工作根目录
      ipc           目录是否可写
      ide           InoProShop 进程是否存在
      daemon        ready.flag / 心跳年龄 / 是否已死
      ping          ping 命令结果
      cancel_gen    当前取消代数
      legacy_daemon 守护是否还是旧版（不回带 run_id）
      problems      [字符串] 逐条说明哪里不对、下一步该干什么
    """
    problems = []
    r = {"ok": False, "base": BASE, "ipc": IPC,
         "daemon_py": DAEMON_PY, "trigger_ps1": TRIGGER_PS1}

    # 1) 文件是否齐
    for label, path in (("daemon_py", DAEMON_PY), ("trigger_ps1", TRIGGER_PS1)):
        if not os.path.isfile(path):
            problems.append("%s 缺失：%s" % (label, path))

    # 2) IPC 可写
    _ensure_dirs()
    probe = os.path.join(IPC, ".selftest_%d" % os.getpid())
    try:
        with io.open(probe, "w", encoding="utf-8") as f:
            f.write("ok")
        os.remove(probe)
        r["ipc_writable"] = True
    except Exception as e:
        r["ipc_writable"] = False
        problems.append("IPC 目录不可写：%s（%s）" % (IPC, e))

    # 3) IDE 进程
    ide = is_ide_running()
    r["ide_running"] = ide
    if not ide:
        problems.append("InoProShop 未运行 —— 先打开 IDE 并打开工程")

    # 4) 守护状态
    ready = os.path.exists(READY)
    age = heartbeat_age()
    r["ready_flag"] = ready
    r["heartbeat_age"] = None if age is None else round(age, 2)
    r["heartbeat_stale_threshold"] = HEARTBEAT_STALE
    if not ready:
        problems.append("ready.flag 不存在 —— 守护没注入。"
                        "在 IDE 里人工点一次：工具 → 脚本 → 执行脚本文件… → "
                        "选 %s" % os.path.join(BASE, "ide", "boot_daemon.py"))
    elif age is None:
        problems.append("ready.flag 存在但没有心跳文件 —— 守护可能已崩，建议重新注入")
    elif age > HEARTBEAT_STALE:
        problems.append("心跳已停摆 %.1fs（阈值 %.0fs）—— 守护线程死了，"
                        "重新注入 %s" % (age, HEARTBEAT_STALE,
                                        os.path.join(BASE, "ide", "boot_daemon.py")))

    # 5) ping
    if ready:
        try:
            pong = send({"action": "ping"}, timeout=ping_timeout)
            r["ping"] = pong
            if pong.get("legacy_daemon"):
                r["legacy_daemon"] = True
                problems.append("守护是旧版（结果不带 run_id）—— 命令与结果无法对账，"
                                "建议重新注入以加载新版 plc_daemon.py")
        except BridgeError as e:
            r["ping"] = e.as_dict()
            problems.append("ping 失败 [%s]：%s" % (e.code, e.detail))
    else:
        r["ping"] = None

    r["cancel_gen"] = current_cancel_gen()
    r["problems"] = problems
    r["ok"] = not problems
    return r


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: bridge.py <action> [json-args]")
        print("       bridge.py selftest")
        sys.exit(1)
    act = sys.argv[1]
    if act == "selftest":
        print(json.dumps(selftest(), ensure_ascii=False, indent=2))
        sys.exit(0)
    if act == "cancel":
        print(json.dumps({"ok": True, "cancel_gen": cancel(
            sys.argv[2] if len(sys.argv) > 2 else "cli")}, ensure_ascii=False))
        sys.exit(0)
    kw = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    try:
        r = call(act, **kw)
    except BridgeError as e:
        r = e.as_dict()
    print(json.dumps(r, ensure_ascii=False, indent=2))
