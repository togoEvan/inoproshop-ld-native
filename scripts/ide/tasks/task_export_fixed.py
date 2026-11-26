# -*- coding: utf-8 -*-
"""导出当前工程里的 prg_StartStop（用户手改后版本），供学习其结构。"""
import io, os, sys, traceback
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base
BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
_lf = io.open(os.path.join(IPC, "export_now.log"), "w", encoding="utf-8")
def L(m):
    _lf.write(u"%s\n" % unicode(m)); _lf.flush()
L(u"BASE = %s (source: %s)" % (BASE, _base.SOURCE))
try:
    proj = projects.primary
    app = proj.active_application
    target = None
    for c in app.get_children():
        try:
            if unicode(c.get_name()) == u"prg_StartStop":
                target = c; break
        except Exception: pass
    if target is None:
        L(u"prg_StartStop NOT FOUND")
    else:
        out = os.path.join(IPC, "user_fixed.native")
        target.export_native(out)
        L(u"exported -> %s (%d bytes)" % (out, os.path.getsize(out)))
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))
finally:
    _lf.close()
