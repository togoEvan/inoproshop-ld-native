# -*- coding: utf-8 -*-
"""读回 prg_GvlVerifyUse 的声明/实现原文，确认 replace 是否真的写进工程。"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
_lf = io.open(os.path.join(IPC, u"readback_pou.log"), "w", encoding="utf-8")


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


proj = projects.primary
app = proj.active_application
pou = None
for o in app.get_children():
    if unicode(o.get_name()) == u"prg_GvlVerifyUse":
        pou = o
        break
L(u"found: %s" % (pou is not None))
if pou is not None:
    try:
        L(u"--- decl ---")
        for ln in unicode(pou.textual_declaration.text).splitlines():
            L(u"  | %s" % ln)
    except Exception, e:
        L(u"decl err %s" % e)
    try:
        L(u"--- impl ---")
        for ln in unicode(pou.textual_implementation.text).splitlines():
            L(u"  | %s" % ln)
    except Exception, e:
        L(u"impl err %s" % e)
    try:
        L(u"is_modified: %r" % pou.is_modified)
    except Exception, e:
        L(u"is_modified err %s" % e)
L(u"=== done ===")
_lf.close()
