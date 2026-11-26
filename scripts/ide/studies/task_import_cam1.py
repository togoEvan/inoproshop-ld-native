# -*- coding: utf-8 -*-
# @ipy2
"""把 Cam1_F07V.native 导入已存在的 F07_CAM_Verify 文件夹，并回读校验。

前置：F07_CAM_Verify 已存在（F07 轮已建）。
输出：ipc/cam1_import.log
"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
SRC = os.path.join(IPC, u"f07_out", u"Cam1_F07V.native")
TOPNAME = u"F07_CAM_Verify"
LOG = os.path.join(IPC, u"cam1_import.log")
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
    L(u"target folder: %s" % TOPNAME)

    L(u"--- before ---")
    for k in kids(top):
        L(u"  - %s" % unicode(k.get_name()))

    if not os.path.isfile(SRC):
        raise RuntimeError(u"source not found: %s" % SRC)
    L(u"source: %s (%d bytes)" % (SRC, os.path.getsize(SRC)))

    r = top.import_native(unicode(SRC))
    L(u"import_native -> %r" % (r,))

    L(u"--- after ---")
    names = []
    for k in kids(top):
        n = unicode(k.get_name())
        names.append(n)
        L(u"  - %s" % n)

    if u"Cam1_F07V" in names:
        L(u"RESULT: OK, Cam1_F07V present")
    else:
        L(u"RESULT: FAIL, Cam1_F07V missing")
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
print(u"done")
