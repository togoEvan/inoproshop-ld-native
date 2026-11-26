# -*- coding: utf-8 -*-
# @ipy2
"""清空 F11_POU_MainTask_Verify 下的全部子对象（重导入前用「改名让位法」的删除半边）。

输出 ipc/f11_purge.log
"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
LOG = os.path.join(IPC, u"f11_purge.log")
_lf = io.open(LOG, "w", encoding="utf-8")

TOPNAME = u"F11_POU_MainTask_Verify"


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


try:
    app = projects.primary.active_application
    top = None
    for o in app.get_children():
        if unicode(o.get_name()) == TOPNAME:
            top = o
            break
    if top is None:
        raise RuntimeError(u"%s not found" % TOPNAME)

    kids = list(top.get_children())
    L(u"children before: %d" % len(kids))
    for k in kids:
        n = unicode(k.get_name())
        try:
            k.remove()
            L(u"  removed %s" % n)
        except Exception, e:
            L(u"  FAIL %s: %s" % (n, e))
    L(u"children after: %d" % len(list(top.get_children())))
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
print(u"done")
