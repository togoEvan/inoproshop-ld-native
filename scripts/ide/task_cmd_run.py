# -*- coding: utf-8 -*-
"""执行指定的 IDE 命令（按 GUID 字符串，遍历 commands 找到匹配项后 execute）。

参数 ipc/cmd_args.json: {"guid": "...", "label": "编译"}
输出 ipc/cmd_run.log
"""
import io
import json
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[0])))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
_lf = io.open(os.path.join(IPC, u"cmd_run.log"), "w", encoding="utf-8")
ARGS = json.loads(io.open(os.path.join(IPC, u"cmd_args.json"), "r",
                          encoding="utf-8").read())

WANT = unicode(ARGS[u"guid"]).strip().lower()
LABEL = unicode(ARGS.get(u"label") or WANT)


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
    L(u"=== 查找并执行命令 %s (%s) ===" % (LABEL, WANT))
    target = None
    for c in system.commands:
        g = attr(c, u"guid").strip().lower()
        if g == WANT:
            target = c
            break
    if target is None:
        L(u"未找到该 guid")
    else:
        L(u"  name = %s" % attr(target, u"name"))
        L(u"  desc = %s" % attr(target, u"description"))
        r = target.execute()
        L(u"  execute() -> %r" % (r,))
        L(u"  执行返回")
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
