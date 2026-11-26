# -*- coding: utf-8 -*-
"""F04 收尾：摘测试 POU 任务槽 + 删除 prg_F05VerifyUse。输出 ipc/f05_cleanup.log
"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
_lf = io.open(os.path.join(IPC, u"f05_cleanup.log"), "w", encoding="utf-8")


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


try:
    proj = projects.primary
    app = proj.active_application
    POU = u"prg_F05VerifyUse"
    tc = None
    for o in app.get_children():
        if unicode(o.get_name()) == u"Task Configuration":
            tc = o
            break
    for t in tc.get_children():
        try:
            names = [unicode(x) for x in t.pous]
        except Exception:
            continue
        if POU in names:
            idx = names.index(POU)
            try:
                t.pous.remove(idx)
                L(u"removed idx %d of %s from %s" % (idx, POU, unicode(t.get_name())))
            except Exception, e:
                L(u"remove() failed: %s" % e)
                t.pous.replace(idx, u"")
                L(u"replace fallback on %s" % unicode(t.get_name()))
    for o in app.get_children():
        if unicode(o.get_name()) == POU:
            o.remove()
            L(u"deleted %s" % POU)
            break
    proj.save()
    L(u"saved")
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
print(u"done")
