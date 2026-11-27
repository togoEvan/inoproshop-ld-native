# -*- coding: utf-8 -*-
# @ipy2
"""列出 Application 下全部直接子对象，找 F 系列顶层文件夹（含 F20）。"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
LOG = os.path.join(IPC, "list_top.log")
_lf = io.open(LOG, "w", encoding="utf-8")


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


app = projects.primary.active_application
L(u"app = %s" % app.get_name())
for o in app.get_children():
    nm = unicode(o.get_name())
    kids = u""
    try:
        kids = u"  (%d children)" % len(o.get_children())
    except Exception:
        pass
    L(u"  %s%s" % (nm, kids))
L(u"=== done ===")
_lf.close()
print(u"done")
