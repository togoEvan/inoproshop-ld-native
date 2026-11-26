# -*- coding: utf-8 -*-
"""收尾（SF01 轮）：删除 prg_Sf01VerifyUse + 摘任务槽 + 保存。

与 task_f02_cleanup.py 同构。输出 ipc/f02b_cleanup.log
"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
_lf = io.open(os.path.join(IPC, u"f02b_cleanup.log"), "w", encoding="utf-8")

POU = u"prg_Sf01VerifyUse"


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
            try:
                names = [unicode(x) for x in t.pous]
            except Exception:
                continue
            L(u"task %s: %r" % (unicode(t.get_name()), names))
            if POU in names:
                t.pous.replace(names.index(POU), u"")
                L(u"  cleared slot -> %r" % [unicode(x) for x in t.pous])

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
    L(u"=== done ===")
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

_lf.close()
print(u"done")
