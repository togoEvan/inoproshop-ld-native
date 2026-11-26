# -*- coding: utf-8 -*-
# @ipy2
"""收尾：把验证 POU 从 MainTask 调用列表摘掉并删除，只保留 F99_GVLVerify 文件夹。"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
_lf = io.open(os.path.join(IPC, u"cleanup_final.log"), "w", encoding="utf-8")

POU = u"prg_GvlVerifyUse"


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
    if tc is not None:
        for t in tc.get_children():
            pl = t.pous
            names = [unicode(x) for x in pl]
            if POU in names:
                pl.remove(POU)
                L(u"removed %s from task %s" % (POU, unicode(t.get_name())))
            L(u"task %s pous: %s" % (unicode(t.get_name()),
                                     u", ".join([unicode(x) for x in pl])))

    hit = None
    for o in app.get_children():
        if unicode(o.get_name()) == POU:
            hit = o
            break
    if hit is not None:
        hit.remove()
        L(u"deleted %s" % POU)
    else:
        L(u"%s not found" % POU)

    proj.save()
    L(u"saved")
    L(u"children: %s" % u", ".join([unicode(k.get_name()) for k in app.get_children()]))
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
