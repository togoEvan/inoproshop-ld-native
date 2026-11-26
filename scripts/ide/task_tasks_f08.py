# -*- coding: utf-8 -*-
"""列出 Task Configuration 下全部任务名与其 POU 列表。

背景：轴组必须在「轴所在的那个任务」里引用，否则报
  「轴组 xxx 与所选轴所在任务不同: 不能再在任务 yyy 中被引用」
需要确认轴到底挂在哪个任务，以及任务名精确拼写。

输出 ipc/f08_tasks.log
"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[0])))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
LOG = os.path.join(IPC, u"f08_tasks.log")
_lf = io.open(LOG, "w", encoding="utf-8")


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

    L(u"=== Task Configuration 下的任务 ===")
    for k in kids(tc):
        L(u"[Task] %r" % nm(k))
        try:
            pl = k.pous
            L(u"   pous = %s" % [unicode(x) for x in pl])
        except Exception, e:
            L(u"   pous !! %s: %s" % (type(e).__name__, e))
        # 任务属性
        for attr in (u"interval", u"interval_unit", u"priority", u"kind_of_task"):
            try:
                L(u"   %s = %r" % (attr, getattr(k, attr)))
            except Exception:
                pass
        L(u"")
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
print(u"done")
