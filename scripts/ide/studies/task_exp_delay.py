# -*- coding: utf-8 -*-
"""测「检查程序」命令后预编译消息的到达延迟。

关键：命令 execute() 后不 sleep，立即返回；主机侧按 1/2/3/5/8/13/20s 逐次
读一次（每次都独立 eval_file），记录预编译条数。

参数 ipc/exp_args.json: {"guid": "...", "note": "..."}
输出 ipc/exp/<note>.delay.log（主机侧追加）
"""
import io
import json
import os
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
ARGS = json.loads(io.open(os.path.join(IPC, u"exp_args.json"), "r",
                          encoding="utf-8").read())
GUID = unicode(ARGS.get(u"guid") or u"").strip().lower()
NOTE = unicode(ARGS.get(u"note") or u"delay")
LOG = os.path.join(IPC, u"exp", NOTE + u".delay.log")
_lf = io.open(LOG, "a", encoding="utf-8")

PRE = u"217bc73e-759b-4a3c-bfa1-991c938a6541"


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


def attr(obj, name):
    try:
        return unicode(getattr(obj, name))
    except Exception:
        pass
    try:
        p = obj.GetType().GetProperty(name)
        if p is not None:
            return unicode(p.GetValue(obj, None))
    except Exception:
        pass
    return u""


def count_pre():
    for c in system.get_message_categories():
        if unicode(c).lower() == PRE:
            msgs = [unicode(x) for x in system.get_messages(c)]
            zzz = [x for x in msgs if u"ZZZ" in x]
            return len(msgs), len(zzz)
    return -1, -1


try:
    t0 = time.time()
    # 先清空
    for c in system.get_message_categories():
        try:
            system.clear_messages(c)
        except Exception:
            pass
    n0, z0 = count_pre()
    L(u"[%s] 清空后 预编译 %d 条 / ZZZ %d" % (time.strftime(u"%H:%M:%S"), n0, z0))

    if GUID:
        for c in system.commands:
            if attr(c, u"guid").strip().lower() == GUID:
                c.execute()
                L(u"[%s] 已执行 %s (t=0.00s)" % (time.strftime(u"%H:%M:%S"), attr(c, u"name")))
                break
        else:
            L(u"命令未找到 %s" % GUID)
    else:
        L(u"未指定 guid，只做清空")

    # 立即读一次（t≈0）
    n, z = count_pre()
    L(u"  t=%5.2fs  预编译 %d 条 / ZZZ %d" % (time.time() - t0, n, z))
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

_lf.close()
