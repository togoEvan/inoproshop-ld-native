# -*- coding: utf-8 -*-
"""删除 F07_CAM_Verify 下的指定子对象（默认 Cam1_F07V），为重新导入让位。

输出：ipc/cam1_delete.log
"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[0])))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
TARGET = u"Cam1_F07V"
TOPNAME = u"F07_CAM_Verify"
LOG = os.path.join(IPC, u"cam1_delete.log")
_lf = io.open(LOG, "w", encoding="utf-8")


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


def kids(o):
    try:
        return list(o.get_children())
    except Exception:
        return []


try:
    app = projects.primary.active_application
    top = None
    for o in app.get_children():
        if unicode(o.get_name()) == TOPNAME:
            top = o
            break
    if top is None:
        raise RuntimeError(u"%s not found" % TOPNAME)

    victim = None
    for k in kids(top):
        if unicode(k.get_name()) == TARGET:
            victim = k
            break

    if victim is None:
        L(u"%s not present, nothing to delete" % TARGET)
    else:
        L(u"deleting %s ..." % TARGET)
        r = None
        try:
            r = top.remove(victim)
            L(u"top.remove(obj) -> %r" % (r,))
        except Exception, e1:
            L(u"remove(obj) failed: %s" % e1)
            try:
                idx = -1
                for i, k in enumerate(kids(top)):
                    if unicode(k.get_name()) == TARGET:
                        idx = i
                        break
                L(u"index = %d" % idx)
                r = top.replace(idx, u"")
                L(u"top.replace(idx,'') -> %r" % (r,))
            except Exception, e2:
                L(u"replace fallback failed: %s" % e2)

    L(u"--- after ---")
    for k in kids(top):
        L(u"  - %s" % unicode(k.get_name()))
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
print(u"done")
