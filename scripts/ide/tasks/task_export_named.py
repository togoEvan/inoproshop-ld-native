# -*- coding: utf-8 -*-
"""通用：导出 Application 下指定名字的对象（含子对象）为 native，供往返比对。

用法：python bridge.py eval_file {"path":".../task_export_named.py"}
      对象名从 ipc/export_name.txt 读取（UTF-8），输出到 ipc/<name>_after.native
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)

NAME_FILE = os.path.join(IPC, u"export_name.txt")
NAME = io.open(NAME_FILE, "r", encoding="utf-8").read().strip()
OUT = os.path.join(IPC, u"%s_after.native" % NAME)
if os.path.exists(OUT):
    try:
        os.remove(OUT)
    except Exception:
        pass

proj = projects.primary
app = proj.active_application
target = None
for o in app.get_children():
    if unicode(o.get_name()) == unicode(NAME):
        target = o
        break
if target is None:
    raise RuntimeError(u"%s not found under Application" % NAME)

try:
    kids = [unicode(k.get_name()) for k in target.get_children()]
    print(u"children = %s" % u", ".join(kids))
except Exception:
    pass

target.export_native(OUT)
print(u"exported -> %s (%d bytes)" % (OUT, os.path.getsize(OUT)))
