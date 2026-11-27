# -*- coding: utf-8 -*-
# @ipy2
"""只读：打印 Task Configuration 下每个任务的 pous 列表 + Application 顶层对象名。
输出 ipc/taskcfg_read.log
"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
_lf = io.open(os.path.join(IPC, u"taskcfg_read.log"), "w", encoding="utf-8")


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


def kids(o):
    try:
        return list(o.get_children())
    except Exception:
        return []


def nm(o):
    try:
        return unicode(o.get_name())
    except Exception:
        return u"?"


try:
    app = projects.primary.active_application
    tc = None
    for o in kids(app):
        if nm(o) == u"Task Configuration":
            tc = o
            break
    if tc is None:
        raise RuntimeError(u"Task Configuration not found")
    for k in kids(tc):
        try:
            L(u"[%s] pous = %s" % (nm(k), [unicode(x) for x in k.pous]))
        except Exception, e:
            L(u"[%s] err %s" % (nm(k), e))
    L(u"--- Application top objects ---")
    for o in kids(app):
        L(u"  %s" % nm(o))
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
print(u"done")
