# -*- coding: utf-8 -*-
"""bridge.py 协议回归测试（本地 Python 3 运行，不碰真实 IDE）

为什么要这个测试：
  bridge.py 的三项新机制（run_id 对账 / 心跳看门狗 / 取消代数）都属于
  「出问题时才显形」的类型 —— 平时跑得好好的，一旦守护慢一拍就会
  给出错误的成功。这类代码不能只靠「在真实工程里跑一次没问题」来验证，
  必须能在不启动 IDE 的前提下，把每个失败路径都精确复现一遍。

做法：
  起一个**假守护线程**（纯 Python 3，只用文件 IPC，不 import CODESYS 任何东西），
  它按 plc_daemon.py 的新协议工作：领取-改名、回带 run_id、写心跳、检查 cancel.gen。
  然后逐项断言 bridge 的行为。

覆盖：
  T1 正常往返：run_id 一致，ok=True
  T2 迟到结果：上一轮的结果文件残留，新一轮不能被它冒充
  T3 旧版守护（不回带 run_id）：退化为出现即认，且标 legacy_daemon
  T4 心跳停摆：守护线程停了 → 立刻抛 E_HEARTBEAT_STALE，不干等满超时
  T5 取消：另一个线程 cancel() → 抛 E_CANCELLED，且守护没被杀
  T6 并发：两个线程同时 call() 不会互相踩 cmd.json
  T7 锁陈旧：锁文件的持有者进程已死 → 能自动抢占
  T8 selftest：守护缺席时 fail-closed，problems 非空

用法：
  python test_bridge_protocol.py
  退出码 0 = 全过
"""
import io
import json
import os
import shutil
import sys
import tempfile
import threading
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# 必须在 import bridge 之前把 IPC 指到临时目录，否则会污染真实 ipc/
_TMP = tempfile.mkdtemp(prefix="bridge_test_")
os.environ["PLC_MCP_IPC"] = _TMP
os.environ["PLC_MCP_BASE"] = HERE

import bridge  # noqa: E402

# bridge 在 import 时已经读了环境变量，这里再钉一次（防御性）
bridge.IPC = _TMP
bridge.CMD = os.path.join(_TMP, "cmd.json")
bridge.CMD_RUNNING = os.path.join(_TMP, "running.json")
bridge.RES = os.path.join(_TMP, "result.json")
bridge.READY = os.path.join(_TMP, "ready.flag")
bridge.STOP = os.path.join(_TMP, "stop.flag")
bridge.HEARTBEAT = os.path.join(_TMP, "heartbeat")
bridge.CANCEL_GEN = os.path.join(_TMP, "cancel.gen")
bridge.LOCK = os.path.join(_TMP, "bridge.lock")

RESULTS = []


def ok(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))
    print("[%s] %s%s" % (" OK " if cond else "FAIL", name,
                         ("  <- " + detail) if detail and not cond else ""))


# ---------------------------------------------------------------------------
# 假守护
# ---------------------------------------------------------------------------
class FakeDaemon(object):
    """按 plc_daemon.py 的新协议工作的假守护。

    behaviors 可调：
      echo_run_id   True=回带 run_id（新版）；False=不回带（模拟旧版守护）
      delay         处理每条命令前的延迟（秒）
      beat          是否发心跳
    """

    def __init__(self, echo_run_id=True, delay=0.0, beat=True, work=None):
        self.echo_run_id = echo_run_id
        self.delay = delay
        self.beat = beat
        self.work = work or (lambda cmd: {"ok": True, "echo": cmd.get("action")})
        self._stop = threading.Event()
        self.threads = []

    def start(self):
        self.threads.append(threading.Thread(target=self._beat_loop, daemon=True))
        self.threads.append(threading.Thread(target=self._poll_loop, daemon=True))
        for t in self.threads:
            t.start()
        # 等 ready.flag
        deadline = time.time() + 3
        while time.time() < deadline and not os.path.exists(bridge.READY):
            time.sleep(0.02)
        return self

    def _beat_loop(self):
        while not self._stop.is_set():
            if self.beat:
                with io.open(bridge.HEARTBEAT, "w") as f:
                    f.write(str(time.time()))
            time.sleep(0.2)

    def _poll_loop(self):
        with io.open(bridge.READY, "w") as f:
            f.write("ready")
        while not self._stop.is_set():
            if not os.path.exists(bridge.CMD):
                time.sleep(0.02)
                continue
            try:
                os.rename(bridge.CMD, bridge.CMD_RUNNING)
            except OSError:
                continue
            time.sleep(0.02)
            try:
                with io.open(bridge.CMD_RUNNING, "r", encoding="utf-8") as f:
                    cmd = json.load(f)
            except Exception:
                cmd = None
            if cmd:
                rid = cmd.get("run_id")
                gen0 = int(cmd.get("cancel_gen_at_send") or 0)
                if self.delay:
                    # 延迟期间仍响应取消（模拟长任务可被打断）
                    t0 = time.time()
                    while time.time() - t0 < self.delay:
                        if bridge.current_cancel_gen() > gen0:
                            break
                        time.sleep(0.02)
                if bridge.current_cancel_gen() > gen0:
                    res = {"ok": False, "cancelled": True,
                           "error": "cancelled during execution"}
                else:
                    try:
                        res = self.work(cmd)
                    except Exception as e:
                        res = {"ok": False, "error": str(e)}
                if not isinstance(res, dict):
                    res = {"result": res}
                if self.echo_run_id and rid is not None:
                    res["run_id"] = rid
                res.setdefault("cancelled", False)
                tmp = bridge.RES + ".tmp"
                with io.open(tmp, "w", encoding="utf-8") as f:
                    f.write(json.dumps(res, ensure_ascii=False))
                os.replace(tmp, bridge.RES)
            try:
                os.remove(bridge.CMD_RUNNING)
            except OSError:
                pass

    def stop(self):
        self._stop.set()
        for t in self.threads:
            t.join(timeout=2)
        for p in (bridge.READY, bridge.HEARTBEAT):
            try:
                os.remove(p)
            except OSError:
                pass


def reset_ipc():
    """清空 IPC 目录（保留目录本身）"""
    for name in os.listdir(_TMP):
        p = os.path.join(_TMP, name)
        try:
            if os.path.isdir(p):
                shutil.rmtree(p)
            else:
                os.remove(p)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# 测试
# ---------------------------------------------------------------------------
def t1_normal():
    reset_ipc()
    d = FakeDaemon().start()
    try:
        r = bridge.call("ping", timeout=5)
        ok("T1 正常往返：ok=True", r.get("ok") is True, repr(r))
        ok("T1 正常往返：run_id 回带", r.get("run_id") is not None, repr(r))
        ok("T1 正常往返：无 legacy 标记", not r.get("legacy_daemon"), repr(r))
    finally:
        d.stop()


def t2_late_result():
    """上一轮的迟到结果不能冒充本轮。"""
    reset_ipc()
    d = FakeDaemon().start()
    try:
        # 手工塞一个 run_id 完全不匹配的旧结果
        with io.open(bridge.RES, "w", encoding="utf-8") as f:
            f.write(json.dumps({"ok": True, "run_id": "STALE-OLD-RUN",
                                "echo": "I_AM_OLD"}))
        r = bridge.call("ping", timeout=5)
        ok("T2 迟到结果被丢弃（不返回 I_AM_OLD）",
           r.get("echo") != "I_AM_OLD", repr(r))
        ok("T2 拿到的是本轮结果", r.get("ok") is True and r.get("run_id"),
           repr(r))
    finally:
        d.stop()


def t3_legacy_daemon():
    reset_ipc()
    d = FakeDaemon(echo_run_id=False).start()
    try:
        r = bridge.call("ping", timeout=5)
        ok("T3 旧版守护：仍能拿到结果", r.get("ok") is True, repr(r))
        ok("T3 旧版守护：标记 legacy_daemon", r.get("legacy_daemon") is True, repr(r))
    finally:
        d.stop()


def t4_heartbeat_stale():
    """守护线程死了 → 立刻报 E_HEARTBEAT_STALE，不等满超时。"""
    reset_ipc()
    d = FakeDaemon().start()
    # 让它写出 ready 但不处理命令（work 卡住），然后杀掉心跳
    d.stop()                     # 守护整个停掉（ready/heartbeat 都删了）
    # 手工造一个「ready 在、心跳很旧」的状态
    with io.open(bridge.READY, "w") as f:
        f.write("ready")
    with io.open(bridge.HEARTBEAT, "w") as f:
        f.write(str(time.time() - 60))
    # ⚠ mtime 必须真的改到 60s 前：看门狗读的是 os.path.getmtime，
    #   不是文件内容。之前这里写成 os.utime(path, (old, old)) 且 old 取自
    #   当前 mtime，等于把 mtime 重新钉回「现在」，于是测出来的 8.8s
    #   其实是「等心跳自然过期」，不是 fail-fast —— 测试自己在骗自己。
    _stale_ts = time.time() - 60
    os.utime(bridge.HEARTBEAT, (_stale_ts, _stale_ts))

    t0 = time.time()
    err = None
    try:
        bridge.call("ping", timeout=30)     # 超时给 30s，看是否 fail-fast
    except bridge.BridgeError as e:
        err = e
    dt = time.time() - t0
    ok("T4 心跳停摆：抛 BridgeError", err is not None, repr(err))
    ok("T4 心跳停摆：错误码是 E_HEARTBEAT_STALE",
       err is not None and err.code == bridge.E_HEARTBEAT_STALE,
       err.code if err else "none")
    ok("T4 心跳停摆：fail-fast（<5s，而非等满 30s）", dt < 5.0, "%.2fs" % dt)


def t5_cancel():
    """cancel() 只取消当前命令，不杀守护。"""
    reset_ipc()
    d = FakeDaemon(delay=3.0).start()
    try:
        box = {}

        def run():
            try:
                box["r"] = bridge.call("slow", timeout=20)
            except bridge.BridgeError as e:
                box["err"] = e

        th = threading.Thread(target=run)
        th.start()
        time.sleep(0.6)                 # 等命令确实被领取
        gen = bridge.cancel("test")
        th.join(timeout=10)
        ok("T5 取消：抛 BridgeError", "err" in box, repr(box))
        ok("T5 取消：错误码是 E_CANCELLED",
           box.get("err") is not None and box["err"].code == bridge.E_CANCELLED,
           box["err"].code if box.get("err") else "none")
        ok("T5 取消：cancel.gen 已递增", gen >= 1, str(gen))
        # 关键：守护还活着 —— 后续命令应当正常
        time.sleep(3.2)                 # 让假守护从长任务里走出来
        r = bridge.call("ping", timeout=5)
        ok("T5 取消：守护没被杀，后续命令正常", r.get("ok") is True, repr(r))
    finally:
        d.stop()


def t6_concurrent():
    """两个线程同时 call()，不能互相踩。"""
    reset_ipc()
    d = FakeDaemon(work=lambda cmd: {"ok": True, "echo": cmd.get("tag")}).start()
    try:
        got = {}

        def run(tag):
            try:
                got[tag] = bridge.call("work", timeout=15, tag=tag)
            except bridge.BridgeError as e:
                got[tag] = e

        ths = [threading.Thread(target=run, args=("A",)),
               threading.Thread(target=run, args=("B",))]
        for t in ths:
            t.start()
        for t in ths:
            t.join(timeout=20)
        a, b = got.get("A"), got.get("B")
        ok("T6 并发：两个都成功",
           isinstance(a, dict) and isinstance(b, dict)
           and a.get("ok") and b.get("ok"),
           "A=%r B=%r" % (a, b))
        # 每个调用必须拿到自己 tag 的结果（不能串）
        ok("T6 并发：结果不串（A 拿到 A，B 拿到 B）",
           isinstance(a, dict) and a.get("echo") == "A"
           and isinstance(b, dict) and b.get("echo") == "B",
           "A=%r B=%r" % (a, b))
    finally:
        d.stop()


def t7_stale_lock():
    """锁文件持有者已死 → 能自动抢占。"""
    reset_ipc()
    d = FakeDaemon().start()
    try:
        # 造一个 pid 几乎肯定不存在的锁
        with io.open(bridge.LOCK, "w", encoding="utf-8") as f:
            f.write(json.dumps({"pid": 999999, "ts": time.time()}))
        t0 = time.time()
        r = bridge.call("ping", timeout=8)
        dt = time.time() - t0
        ok("T7 陈旧锁：能抢占并成功", r.get("ok") is True, repr(r))
        ok("T7 陈旧锁：抢占够快（<3s）", dt < 3.0, "%.2fs" % dt)
    finally:
        d.stop()


def t8_selftest():
    reset_ipc()
    r = bridge.selftest()
    ok("T8 selftest：守护缺席时 ok=False", r.get("ok") is False, repr(r))
    ok("T8 selftest：problems 非空", len(r.get("problems") or []) > 0, repr(r))
    ok("T8 selftest：明确提示注入方法",
       any("boot_daemon.py" in p for p in r.get("problems") or []),
       repr(r.get("problems")))
    # 有守护时应当通过（除了 IDE 进程检测那一项）
    d = FakeDaemon().start()
    try:
        r2 = bridge.selftest()
        # ide_running 在测试环境可能为 False（IDE 开着也可能为 True），
        # 只断言 ping 成功、legacy 未标记
        ok("T8 selftest：有守护时 ping 成功",
           isinstance(r2.get("ping"), dict) and r2["ping"].get("ok") is True,
           repr(r2.get("ping")))
    finally:
        d.stop()


def main():
    print("IPC 临时目录：%s\n" % _TMP)
    tests = [t1_normal, t2_late_result, t3_legacy_daemon, t4_heartbeat_stale,
             t5_cancel, t6_concurrent, t7_stale_lock, t8_selftest]
    for fn in tests:
        print("--- %s ---" % fn.__name__)
        try:
            fn()
        except Exception:
            RESULTS.append((fn.__name__, False, "异常"))
            print("[FAIL] %s 抛异常：" % fn.__name__)
            traceback.print_exc()
        print("")

    passed = sum(1 for _, okv, _ in RESULTS if okv)
    total = len(RESULTS)
    print("=" * 60)
    print("结果：%d/%d 通过" % (passed, total))
    if passed != total:
        print("失败项：")
        for name, okv, detail in RESULTS:
            if not okv:
                print("  - %s  %s" % (name, detail))
    print("=" * 60)

    try:
        shutil.rmtree(_TMP)
    except Exception:
        pass
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
