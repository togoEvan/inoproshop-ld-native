# -*- coding: utf-8 -*-
# @ipy2
"""验收 F11 收尾：确认 MainTask 的 POU 列表已不含 prg_F11VerifyUse。"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
LOG = os.path.join(IPC, "verify_tc.log")
_lf = io.open(LOG, "w", encoding="utf-8")


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


app = projects.primary.active_application
tc = None
for o in app.get_children():
    if unicode(o.get_name()) == u"Task Configuration":
        tc = o
        break
L(u"tc = %r" % tc)
if tc is not None:
    for c in tc.get_children():
        L(u"  task: %s" % c.get_name())
        for p in c.get_children():
            L(u"    -> %s" % p.get_name())
L(u"=== done ===")
_lf.close()
