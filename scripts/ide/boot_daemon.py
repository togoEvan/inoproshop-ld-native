# -*- coding: utf-8 -*-
# =====================================================================
#  在 InoProShop IDE 内启动守护进程（IronPython 2.7，IDE 内运行）
#
#  唯一守护注入入口：IDE 菜单自绘（UIA/GetMenu 都读不到，无法自动点），
#  必须人工执行：工具 → 脚本 → 执行脚本文件... → 选本文件。
#
#  要点：
#  - 不直接跑 plc_daemon.py：它依赖 projects/online/system 三个 IDE 注入
#    全局，间接加载时不在命名空间；本脚本显式塞进 exec 命名空间，两种情形通用
#  - 改写 sys.argv[0] 为同目录 plc_daemon.py，保证 BASE 推导与 bridge.py 一致
#  - 命名空间挂 sys._plc_mcp_keep：防 exec 命名空间被回收后守护静默死掉
#    （症状：daemon.log 0 字节、无 heartbeat）
# =====================================================================
import os
import sys
import traceback

# ── 解析本脚本所在目录 ──────────────────────────────────────────────
# 两种执行方式，sys.argv[0] 的含义不同：
#   ① IDE 菜单「执行脚本文件...」→ sys.argv[0] = 本脚本绝对路径 ✓
#   ② 通过某个已运行守护的 eval_file 通道执行 → sys.argv[0] 仍是
#      那个旧守护的路径，指不到这里 ✗
# 所以先试 sys.argv[0]，不成立再退到「sys.modules 里已加载的
# plc_daemon 模块的 __file__」，两者都失败才报错。
def _resolve_ide_dir():
    # 0) 调用方显式指定（eval_file 包装脚本用）：globals 里预置 PLC_IDE_DIR
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
    # 已加载的 plc_daemon 模块（eval_file 通道的典型情形）
    try:
        for _n in list(sys.modules.keys()):
            _m = sys.modules.get(_n)
            _f = getattr(_m, u"__file__", None) if _m is not None else None
            if _f and unicode(_f).replace(u"\\", u"/").endswith(u"/plc_daemon.py"):
                cands.append(os.path.dirname(os.path.abspath(_f)))
    except Exception:
        pass
    # 优先选「同时含 boot_daemon.py 与 plc_daemon.py」的目录 ——
    # 那才是本技能包自己的 ide/，而不是某个历史遗留目录
    for d in cands:
        if (os.path.isfile(os.path.join(d, u"plc_daemon.py"))
                and os.path.isfile(os.path.join(d, u"boot_daemon.py"))):
            return d
    for d in cands:
        if os.path.isfile(os.path.join(d, u"plc_daemon.py")):
            return d
    return cands[0] if cands else u""


IDE_DIR = _resolve_ide_dir()
BASE = os.path.dirname(IDE_DIR)
DAEMON = os.path.join(IDE_DIR, u"plc_daemon.py")
IPC = os.path.join(BASE, u"ipc")

_rep = [u"boot_daemon.py start"]


def _report(msg):
    _rep.append(unicode(msg))


def _flush():
    try:
        if not os.path.isdir(IPC):
            os.makedirs(IPC)
        fh = open(os.path.join(IPC, u"boot_daemon.log"), "w")
        fh.write(u"\n".join(_rep))
        fh.close()
    except Exception:
        pass


_report(u"IDE_DIR = %s" % IDE_DIR)
_report(u"BASE    = %s" % BASE)

if not os.path.isfile(DAEMON):
    _report(u"FATAL: daemon missing: %s" % DAEMON)
    _flush()
else:
    # 1) 改写 argv[0]，让 _base 的 derive 逻辑推导出本 BASE
    _old = sys.argv[0] if len(sys.argv) > 0 else u""
    sys.argv[0] = DAEMON
    _report(u"argv0: %s -> %s" % (_old, DAEMON))

    # 2) 清掉可能已缓存的旧模块，强制重新加载本目录的 _base / plc_daemon
    for _m in (u"_base", u"plc_daemon"):
        if _m in sys.modules:
            try:
                del sys.modules[_m]
                _report(u"purged module: %s" % _m)
            except Exception, e:
                _report(u"purge %s failed: %s" % (_m, e))

    if IDE_DIR not in sys.path:
        sys.path.insert(0, IDE_DIR)
        _report(u"sys.path prepended: %s" % IDE_DIR)

    # 3) 组装 exec 命名空间，把 IDE 注入的全局对象显式带进去
    _ns = {u"__name__": u"__plc_daemon__", u"__file__": DAEMON}
    for _k in (u"projects", u"online", u"system"):
        try:
            _ns[_k] = globals()[_k]
            _report(u"injected global: %s" % _k)
        except Exception, e:
            _report(u"global %s MISSING: %s" % (_k, e))

    # 4) 钉住命名空间，防止 exec 返回后被 GC（守护会静默死掉）
    try:
        if not hasattr(sys, u"_plc_mcp_keep"):
            sys._plc_mcp_keep = {}
        sys._plc_mcp_keep[u"daemon"] = _ns
        _report(u"namespace pinned: sys._plc_mcp_keep['daemon']")
    except Exception, e:
        _report(u"pin failed: %s" % e)

    # 5) 清理陈旧的存活标记
    #    plc_daemon 的 _acquire_instance() 用「心跳新鲜度」判断是否已有实例。
    #    若上一次守护异常退出（或 IDE 重开），心跳文件还留着但时间很旧，
    #    必须清掉，否则新实例会以为「已有守护在跑」而直接 SystemExit 退出。
    _HEARTBEAT_FRESH = 8.0
    _hb = os.path.join(IPC, u"heartbeat")
    _stale = True
    if os.path.exists(_hb):
        try:
            import time as _t
            _age = _t.time() - os.path.getmtime(_hb)
            _stale = _age >= _HEARTBEAT_FRESH
            _report(u"heartbeat age = %.1fs -> %s"
                    % (_age, u"stale, will clean" if _stale else u"FRESH, another daemon alive"))
        except Exception, e:
            _report(u"heartbeat stat failed: %s" % e)
    else:
        _report(u"no heartbeat file")

    if _stale:
        for _n in (u"heartbeat", u"instance.lock", u"daemon.pid",
                   u"ready.flag", u"cmd.json", u"running.json", u"result.json"):
            _p = os.path.join(IPC, _n)
            if os.path.exists(_p):
                try:
                    os.remove(_p)
                    _report(u"cleaned: %s" % _n)
                except Exception, e:
                    _report(u"clean %s failed: %s" % (_n, e))

    # 6) 读源码并执行（顶层代码会自己起后台线程）
    _src = None
    try:
        f = open(DAEMON, "r")
        _src = f.read()
        f.close()
        _report(u"source read: %d bytes" % len(_src))
    except Exception, e:
        _report(u"FATAL read: %s" % e)

    if _src:
        try:
            exec(compile(_src, DAEMON, "exec"), _ns)
            _report(u"exec OK")
            _report(u"  BASE    = %s" % _ns.get(u"BASE", u"?"))
            _report(u"  CMD_DIR = %s" % _ns.get(u"CMD_DIR", u"?"))
            _b = _ns.get(u"_base")
            if _b is not None:
                _report(u"  SOURCE  = %s" % getattr(_b, u"SOURCE", u"?"))
            _th = _ns.get(u"_th")
            if _th is not None:
                try:
                    _report(u"  thread alive = %s" % _th.IsAlive)
                except Exception:
                    _report(u"  thread = %r" % _th)
        except SystemExit, e:
            # plc_daemon 在「已有实例存活」时 raise SystemExit。
            # ⚠ 必须单独捕获：IronPython 里 SystemExit 不继承 Exception，
            #   它会穿透 except Exception 一路抛出 exec，把整个脚本宿主
            #   （连同正在跑的守护线程）一起干掉 —— 实测 2026-11-25：
            #   第二次注入后心跳在 0.7s 内停摆，正是这个原因。
            _report(u"SystemExit caught: %s" % e)
            _report(u"  -> 已有守护在运行，本次不重复启动")
        except BaseException, e:
            _report(u"FATAL exec (%s): %s" % (type(e).__name__, e))
            _report(traceback.format_exc())

    _flush()
    _report(u"done")
