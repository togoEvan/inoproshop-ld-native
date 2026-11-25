# -*- coding: utf-8 -*-
"""列出 Application 下的全部对象（含 Folder/GVL），并展开 F01_Variable。"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[0])))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
out = io.open(os.path.join(IPC, "tree_dump.log"), "w", encoding="utf-8")


def L(m):
    out.write(u"%s\n" % unicode(m))
    out.flush()


def walk(obj, depth=0):
    ind = u"  " * depth
    try:
        nm = unicode(obj.get_name())
    except Exception:
        nm = u"?"
    tg = u""
    try:
        tg = unicode(obj.type)
    except Exception:
        pass
    L(u"%s%s   [%s]" % (ind, nm, tg))
    if depth >= 3:
        return
    try:
        kids = list(obj.get_children())
    except Exception:
        kids = []
    for k in kids:
        walk(k, depth + 1)


try:
    proj = projects.primary
    app = proj.active_application
    L(u"=== Application children ===")
    for o in app.get_children():
        walk(o, 1)
except Exception, e:
    import traceback
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))
finally:
    out.close()
print(u"done")
