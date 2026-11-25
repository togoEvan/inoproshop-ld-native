# -*- coding: utf-8 -*-
"""删除临时验证 POU（prg_GvlVerifyUse），保留 F99_GVLVerify 文件夹。"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[0])))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
_lf = io.open(os.path.join(IPC, u"cleanup_test_pou.log"), "w", encoding="utf-8")

TARGETS = [u"prg_GvlVerifyUse", u"prg_PouTypeProbeX"]


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


try:
    proj = projects.primary
    app = proj.active_application
    for t in TARGETS:
        hit = None
        for o in app.get_children():
            if unicode(o.get_name()) == t:
                hit = o
                break
        if hit is None:
            L(u"%s: not found (already clean)" % t)
            continue
        hit.remove()
        L(u"%s: removed" % t)
    proj.save()
    L(u"saved")
    L(u"children: %s" % u", ".join([unicode(k.get_name()) for k in app.get_children()]))
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
