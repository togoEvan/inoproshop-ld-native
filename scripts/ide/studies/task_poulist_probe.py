# -*- coding: utf-8 -*-
# @ipy2
"""探测 ScriptPouObjectList 的增删 API（把 POU 挂进任务调用列表）。"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
_lf = io.open(os.path.join(IPC, u"poulist_probe.log"), "w", encoding="utf-8")


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


try:
    proj = projects.primary
    app = proj.active_application
    tc = None
    for o in app.get_children():
        if unicode(o.get_name()) == u"Task Configuration":
            tc = o
            break
    for t in tc.get_children():
        L(u"=== task %s ===" % unicode(t.get_name()))
        pl = t.pous
        L(u"  type: %s" % unicode(type(pl)))
        L(u"  dir: %s" % u", ".join(sorted([n for n in dir(pl) if not n.startswith(u"_")])))
        try:
            L(u"  len: %d" % len(pl))
        except Exception, e:
            L(u"  len ERR %s" % e)
        try:
            for x in pl:
                L(u"    - %r" % unicode(x))
        except Exception, e:
            L(u"  iter ERR %s" % e)
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
