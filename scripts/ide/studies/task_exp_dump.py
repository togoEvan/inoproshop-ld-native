# -*- coding: utf-8 -*-
# @ipy2
"""只 dump 消息分类（不执行任何命令）。

参数 ipc/exp_args.json: {"note": "..."}
输出 ipc/exp/<note>.msg.log
"""
import io
import json
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
ARGS = json.loads(io.open(os.path.join(IPC, u"exp_args.json"), "r",
                          encoding="utf-8").read())
NOTE = unicode(ARGS.get(u"note") or u"dump")
LOG = os.path.join(IPC, u"exp", NOTE + u".msg.log")
_lf = io.open(LOG, "w", encoding="utf-8")


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


try:
    for c in system.get_message_categories():
        try:
            desc = unicode(system.get_message_category_description(c))
        except Exception:
            desc = unicode(c)
        msgs = list(system.get_messages(c))
        zzz = 0
        L(u"=== %s : %d 条 ===" % (desc, len(msgs)))
        for m in msgs:
            s = unicode(m)
            if u"ZZZ" in s:
                zzz += 1
                L(u"    ZZZ> %s" % s)
        if zzz:
            L(u"    (ZZZ 命中 %d)" % zzz)
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
