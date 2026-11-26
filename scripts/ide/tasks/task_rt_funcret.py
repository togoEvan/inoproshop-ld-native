# -*- coding: utf-8 -*-
# @ipy2
"""往返验证 prg_FuncRetTest：导出导入后的 POU，比对 Function 框结构是否保持。"""
import io
import os
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
_lf = io.open(os.path.join(IPC, "rt_funcret.log"), "w", encoding="utf-8")


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


try:
    proj = projects.primary
    app = proj.active_application
    by_name = {}
    for c in app.get_children():
        try:
            by_name[unicode(c.get_name())] = c
        except Exception:
            pass
    obj = by_name.get(u"prg_FuncRetTest")
    if obj is None:
        L(u"MISS prg_FuncRetTest")
    else:
        stamp = time.strftime("%H%M%S")
        out = os.path.join(IPC, u"rt_prg_FuncRetTest_%s.native" % stamp)
        obj.export_native(out)
        L(u"OK %s (%d bytes)" % (os.path.basename(out), os.path.getsize(out)))
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))
finally:
    _lf.close()
