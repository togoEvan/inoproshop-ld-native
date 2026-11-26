# -*- coding: utf-8 -*-
# =====================================================================
#  热重载守护（IronPython 2.7，经 eval_file 通道在 IDE 内执行）
#
#  改了 plc_daemon.py 后让内存里的旧守护换新，无需人工点菜单重新注入。
#
#  要点：
#  - 先写 stop.flag 停旧守护（新守护看到新鲜心跳会判「已有实例」而退出）
#  - stop.flag 在本命令执行期间写入，旧循环要到本命令返回后才看到 ——
#    主线程等它 = 自己等自己（死锁），所以必须由**后台线程**等
#    ready.flag 消失后再 exec boot_daemon.py
#  - eval_file 的 globals 已带 projects/online/system，原样转交即可
# =====================================================================
import os
import sys
import time
import traceback

_REP = [u"reload_daemon.py start"]


def _report(msg):
    _REP.append(unicode(msg))


def _flush():
    try:
        import io
        p = os.path.join(_ipc(), u"reload_daemon.log")
        f = io.open(p, "w", encoding="utf-8")
        try:
            f.write(u"\n".join(_REP))
        finally:
            f.close()
    except Exception:
        pass


def _ide_dir():
    """定位本技能包自己的 ide/ 目录（含 plc_daemon.py 与 boot_daemon.py）"""
    try:
        _forced = globals().get(u"PLC_IDE_DIR")
        if _forced and os.path.isfile(os.path.join(_forced, u"plc_daemon.py")):
            return _forced
    except Exception:
        pass
    cands = []
    try:
        if len(sys.argv) > 0 and sys.argv[0]:
            cands.append(os.path.dirname(os.path.abspath(sys.argv[0])))
    except Exception:
        pass
    try:
        for _n in list(sys.modules.keys()):
            _m = sys.modules.get(_n)
            _f = getattr(_m, u"__file__", None) if _m is not None else None
            if _f and unicode(_f).replace(u"\\", u"/").endswith(u"/plc_daemon.py"):
                cands.append(os.path.dirname(os.path.abspath(_f)))
    except Exception:
        pass
    for d in cands:
        if (os.path.isfile(os.path.join(d, u"plc_daemon.py"))
                and os.path.isfile(os.path.join(d, u"boot_daemon.py"))):
            return d
    for d in cands:
        if os.path.isfile(os.path.join(d, u"plc_daemon.py")):
            return d
    return cands[0] if cands else u""


_IDE_DIR = _ide_dir()
_BASE = os.path.dirname(_IDE_DIR)
_IPC = os.path.join(_BASE, u"ipc")
_READY = os.path.join(_IPC, u"ready.flag")
_STOP = os.path.join(_IPC, u"stop.flag")
_HEARTBEAT = os.path.join(_IPC, u"heartbeat")
_BOOT = os.path.join(_IDE_DIR, u"boot_daemon.py")

_report(u"IDE_DIR = %s" % _IDE_DIR)
_report(u"BASE    = %s" % _BASE)


def _ipc():
    return _IPC


def _wait_and_boot():
    """后台线程：等旧守护退干净，再用 boot_daemon 起新的。"""
    try:
        # 1) 等 ready.flag 消失（旧循环 break 时会删）
        t0 = time.time()
        while os.path.exists(_READY):
            if time.time() - t0 > 20:
                _report(u"WARN: ready.flag 20s 未消失，强制继续")
                break
            time.sleep(0.2)
        _report(u"old daemon gone (%.1fs)" % (time.time() - t0))

        # 2) 补清残留（旧守护正常退出会自己删，这里只兜异常路径）
        for _n in (u"heartbeat", u"ready.flag", u"cmd.json", u"running.json",
                   u"result.json", u"instance.lock", u"stop.flag"):
            _p = os.path.join(_IPC, _n)
            if os.path.exists(_p):
                try:
                    os.remove(_p)
                    _report(u"cleaned: %s" % _n)
                except Exception, e:
                    _report(u"clean %s failed: %s" % (_n, e))

        # 3) 读 boot_daemon.py 源码
        import io
        f = io.open(_BOOT, "r", encoding="utf-8")
        try:
            src = f.read()
        finally:
            f.close()
        _report(u"boot_daemon source: %d bytes" % len(src))

        # 4) exec，命名空间里塞 IDE 注入的全局对象
        ns = {u"__name__": u"__reload_boot__", u"__file__": _BOOT}
        for _k in (u"projects", u"online", u"system"):
            try:
                ns[_k] = globals()[_k]
                _report(u"injected global: %s" % _k)
            except Exception, e:
                _report(u"global %s MISSING: %s" % (_k, e))
        exec(compile(src, _BOOT, "exec"), ns)
        _report(u"boot exec done")
        # 5) 确认新守护起来了
        t1 = time.time()
        while time.time() - t1 < 20:
            if os.path.exists(_READY):
                _report(u"NEW daemon ready (%.1fs)" % (time.time() - t1))
                break
            time.sleep(0.2)
        else:
            _report(u"WARN: 新守护 20s 内没写 ready.flag")
    except SystemExit, e:
        _report(u"SystemExit: %s" % e)
    except BaseException, e:
        _report(u"FATAL (%s): %s" % (type(e).__name__, e))
        _report(traceback.format_exc())
    finally:
        _flush()


if not os.path.isfile(_BOOT):
    _report(u"FATAL: boot_daemon.py missing: %s" % _BOOT)
    _flush()
else:
    # 先写 stop.flag 让旧循环在**本命令返回后**退出
    try:
        import io
        f = io.open(_STOP, "w")
        f.write(u"stop")
        f.close()
        _report(u"stop.flag written")
    except Exception, e:
        _report(u"write stop.flag failed: %s" % e)
    import System
    import System.Threading
    _t = System.Threading.Thread(System.Threading.ThreadStart(_wait_and_boot))
    _t.IsBackground = True
    _t.Name = u"PLC_MCP_Reload"
    _t.Start()
    _report(u"reload thread started")
    _flush()
