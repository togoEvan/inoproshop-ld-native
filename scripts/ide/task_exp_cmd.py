# -*- coding: utf-8 -*-
"""只执行一个 IDE 命令，不读消息（避免读消息时把结果混进来）。

参数 ipc/exp_args.json: {"guid": "...", "note": "..."}
输出 ipc/exp/<note>.cmd.log
"""
import io
import json
import os
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[0])))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
ARGS = json.loads(io.open(os.path.join(IPC, u"exp_args.json"), "r",
                          encoding="utf-8").read())
GUID = unicode(ARGS[u"guid"]).strip().lower()
NOTE = unicode(ARGS.get(u"note") or u"cmd")
LOG = os.path.join(IPC, u"exp", NOTE + u".cmd.log")
_lf = io.open(LOG, "w", encoding="utf-8")


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


try:
    hit = False
    for c in system.commands:
        if attr(c, u"guid").strip().lower() == GUID:
            L(u"found: %s / %s" % (attr(c, u"name"), attr(c, u"description")))
            r = c.execute()
            L(u"execute() -> %r at %s" % (r, time.strftime(u"%H:%M:%S")))
            hit = True
            break
    if not hit:
        L(u"command not found: %s" % GUID)
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
