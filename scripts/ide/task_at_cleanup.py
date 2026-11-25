# -*- coding: utf-8 -*-
"""收尾：删除 prg_AtVerifyUse + 把 MainTask 调用列表恢复成只剩 M000_MAIN。

输出 ipc/at_cleanup.log
"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[0])))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
_lf = io.open(os.path.join(IPC, u"at_cleanup.log"), "w", encoding="utf-8")

POU = u"prg_AtVerifyUse"


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
    for t in tc.get_children():
        names = [unicode(x) for x in t.pous]
        L(u"task %s before: %r" % (unicode(t.get_name()), names))
        if POU in names:
            idx = names.index(POU)
            t.pous.replace(idx, u"")
            L(u"  cleared index %d -> %r"
              % (idx, [unicode(x) for x in t.pous]))

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
