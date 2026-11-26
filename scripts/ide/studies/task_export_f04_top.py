# -*- coding: utf-8 -*-
# @ipy2
"""导出 F04_FB_Verify 顶层文件夹 native（主机侧解析其 SV guid 后再供子文件夹用）。"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
OUT = os.path.join(IPC, u"f04_top_backup.native")
if os.path.exists(OUT):
    os.remove(OUT)

app = projects.primary.active_application
top = None
for o in app.get_children():
    if unicode(o.get_name()) == u"F04_FB_Verify":
        top = o
        break
if top is None:
    raise RuntimeError(u"F04_FB_Verify not found")
top.export_native(OUT)
print(u"exported %d bytes" % os.path.getsize(OUT))
