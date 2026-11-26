# -*- coding: utf-8 -*-
"""导出 F01_Variable 文件夹（含全部子 GVL）作为备份。

用法：python bridge.py eval_file {"path":".../task_export_f01.py"}
输出：ipc/F01_Variable_backup.native
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
OUT = os.path.join(IPC, u"F01_Variable_backup.native")
if os.path.exists(OUT):
    try:
        os.remove(OUT)
    except Exception:
        pass

proj = projects.primary
app = proj.active_application
target = None
for o in app.get_children():
    if unicode(o.get_name()) == u"F01_Variable":
        target = o
        break
if target is None:
    raise RuntimeError(u"F01_Variable not found")

kids = [unicode(k.get_name()) for k in target.get_children()]
print(u"children = %s" % u", ".join(kids))

target.export_native(OUT)
print(u"exported -> %s (%d bytes)" % (OUT, os.path.getsize(OUT)))
