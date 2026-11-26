# -*- coding: utf-8 -*-
# @ipy2
"""导出 prg_ReproStudy 到指定路径（供往返比对）。"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
OUT = os.path.join(IPC, u"repro_export.native")
if os.path.exists(OUT):
    try:
        os.remove(OUT)
    except Exception:
        pass

proj = projects.primary
app = proj.active_application
target = None
for o in app.get_children():
    if unicode(o.get_name()) == u"prg_ReproStudy":
        target = o
        break
if target is None:
    raise RuntimeError(u"prg_ReproStudy not found")

target.export_native(OUT)
print(u"exported -> %s (%d bytes)" % (OUT, os.path.getsize(OUT)))
