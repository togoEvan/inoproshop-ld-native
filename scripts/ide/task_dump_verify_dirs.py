# -*- coding: utf-8 -*-
"""列出 F05_FC_Verify 与 F04_FB_Verify 下的完整结构（含子对象类型与数量）。"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[0])))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
_lf = io.open(os.path.join(IPC, u"dump_verify_dirs.log"), "w", encoding="utf-8")


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
    for topname in (u"F05_FC_Verify", u"F04_FB_Verify", u"F02_Struct_Verify"):
        top = None
        for o in app.get_children():
            if unicode(o.get_name()) == topname:
                top = o
                break
        L(u"=== %s ===" % topname)
        if top is None:
            L(u"  NOT FOUND")
            continue
        for k in kids(top):
            ch = kids(k)
            L(u"  - %-36s children=%d  type=%s"
              % (unicode(k.get_name()), len(ch),
                 type(k).__name__))
            for c in ch:
                L(u"      . %s" % unicode(c.get_name()))
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
print(u"done")
