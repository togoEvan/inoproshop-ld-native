# -*- coding: utf-8 -*-
"""决定性实验：清空消息后只做一件事，再看预编译分类里有没有 ZZZ。

参数 ipc/exp_args.json: {"op": "build"|"check"|"nothing", "note": "..."}
输出 ipc/exp/<note>.clear.log
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
OP = unicode(ARGS.get(u"op") or u"nothing")
NOTE = unicode(ARGS.get(u"note") or u"clear")
LOG = os.path.join(IPC, u"exp", NOTE + u".clear.log")
_lf = io.open(LOG, "w", encoding="utf-8")

CHECK_PROGRAM = u"ab02b3c3-a0b0-405c-9841-987504c7088d"


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


def dump(tag):
    for c in system.get_message_categories():
        try:
            desc = unicode(system.get_message_category_description(c))
        except Exception:
            desc = unicode(c)
        msgs = [unicode(x) for x in system.get_messages(c)]
        zzz = [x for x in msgs if u"ZZZ" in x]
        L(u"  [%s] %s : %d 条 (ZZZ %d)" % (tag, desc, len(msgs), len(zzz)))
        for z in zzz:
            L(u"      ZZZ> %s" % z)


try:
    L(u"=== op=%s ===" % OP)
    L(u"-- clear_messages 前 --")
    dump(u"before")
    for _c in system.get_message_categories():
        try:
            system.clear_messages(_c)
        except Exception, _e:
            L(u"  clear fail %s" % _e)
    L(u"-- 清空后 --")
    dump(u"after_clear")

    if OP == u"build":
        t0 = time.time()
        projects.primary.active_application.build()
        L(u"build() 用了 %.2fs" % (time.time() - t0))
    elif OP == u"check":
        for c in system.commands:
            if attr(c, u"guid").strip().lower() == CHECK_PROGRAM:
                c.execute()
                L(u"执行 检查程序")
                break
    else:
        L(u"什么都不做（对照组）")

    L(u"-- 动作后（注意：命令可能是异步的，结果见后续 dump）--")
    dump(u"after_action")
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
