# -*- coding: utf-8 -*-
"""把 f08_out_alt 的副本同名覆盖导入 F08_AxisGroup_Verify（对照实验）。

输出 ipc/f08_alt_import.log
"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[0])))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
SRC = os.path.join(IPC, u"f08_out_alt")
TOPNAME = u"F08_AxisGroup_Verify"
LOG = os.path.join(IPC, u"f08_alt_import.log")
_lf = io.open(LOG, "w", encoding="utf-8")


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


def kids(o):
    try:
        return list(o.get_children())
    except Exception:
        return []


def nm(o):
    try:
        return unicode(o.get_name())
    except Exception:
        return u"?"


try:
    app = projects.primary.active_application
    top = None
    for o in kids(app):
        if nm(o) == TOPNAME:
            top = o
            break
    if top is None:
        raise RuntimeError(u"%s not found" % TOPNAME)

    for f in sorted(os.listdir(SRC)):
        if not f.endswith(u".native") or f.startswith(u"_"):
            continue
        try:
            r = top.import_native(unicode(os.path.join(SRC, f)))
            L(u"[ok] %s -> %r" % (f, r))
        except Exception, e:
            L(u"[FAIL] %s: %s" % (f, e))

    L(u"--- tree ---")
    for k in kids(top):
        try:
            g = unicode(k.guid)
        except Exception:
            g = u"?"
        L(u"  - %s guid=%s" % (nm(k), g))
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
print(u"done")
