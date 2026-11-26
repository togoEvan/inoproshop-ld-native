# -*- coding: utf-8 -*-
"""从 IDE 导出 Cam1_F07V 回读，验证曲线数据（Points/Segments）确实生效。

输出：ipc/f07_out/Cam1_F07V_readback.native
      ipc/cam1_readback.log
"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[0])))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
OUT = os.path.join(IPC, u"f07_out", u"Cam1_F07V_readback.native")
LOG = os.path.join(IPC, u"cam1_readback.log")
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
        if unicode(o.get_name()) == u"F07_CAM_Verify":
            top = o
            break
    if top is None:
        raise RuntimeError(u"F07_CAM_Verify not found")

    cam = None
    for k in kids(top):
        if unicode(k.get_name()) == u"Cam1_F07V":
            cam = k
            break
    if cam is None:
        raise RuntimeError(u"Cam1_F07V not found")

    L(u"found Cam1_F07V")
    if os.path.exists(OUT):
        os.remove(OUT)
    cam.export_native(unicode(OUT))
    L(u"exported -> %d bytes" % os.path.getsize(OUT))
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
print(u"done")
