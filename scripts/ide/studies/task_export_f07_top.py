# -*- coding: utf-8 -*-
import io, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base
BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
OUT = os.path.join(IPC, u"f07_top_backup.native")
if os.path.exists(OUT):
    os.remove(OUT)
app = projects.primary.active_application
top = None
for o in app.get_children():
    if unicode(o.get_name()) == u"F07_CAM_Verify":
        top = o
        break
if top is None:
    raise RuntimeError(u"F07_CAM_Verify not found")
top.export_native(OUT)
print(u"exported %d bytes" % os.path.getsize(OUT))
