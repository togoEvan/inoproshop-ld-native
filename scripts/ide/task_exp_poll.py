# -*- coding: utf-8 -*-
"""只读预编译分类条数（主机侧轮询用，不改任何东西）。

参数 ipc/exp_args.json: {"note": "..."}
输出 ipc/exp/<note>.poll.log（每次追加一行）
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
NOTE = unicode(ARGS.get(u"note") or u"poll")
TAG = unicode(ARGS.get(u"tag") or u"")
LOG = os.path.join(IPC, u"exp", NOTE + u".poll.log")
_lf = io.open(LOG, "a", encoding="utf-8")

PRE = u"217bc73e-759b-4a3c-bfa1-991c938a6541"
COMP = u"97f48d64-a2a3-4856-b640-75c046e37ea9"


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


def stat(guid):
    for c in system.get_message_categories():
        if unicode(c).lower() == guid:
            msgs = [unicode(x) for x in system.get_messages(c)]
            return len(msgs), len([x for x in msgs if u"ZZZ" in x])
    return -1, -1


try:
    n, z = stat(PRE)
    cn, cz = stat(COMP)
    L(u"[%s] %-6s 预编译 %4d 条 / ZZZ %d   编译 %4d 条 / ZZZ %d"
      % (time.strftime(u"%H:%M:%S"), TAG, n, z, cn, cz))
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

_lf.close()
