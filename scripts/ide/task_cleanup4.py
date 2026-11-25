# -*- coding: utf-8 -*-
import io, os, time, traceback
BASE = r"D:/小艺Work工作空间/20261123160323/plc_mcp"
_lf = io.open(os.path.join(BASE,"ipc","cleanup4.log"), "w", encoding="utf-8")
def L(m):
    _lf.write(u"[%s] %s\n" % (time.strftime("%H:%M:%S"), unicode(m))); _lf.flush()
KEEP = set([u"库管理器", u"PLC_PRG", u"Task Configuration", u"DifferentialMonitor", u"TaskEventPreStart", u"prg_StartStop"])
try:
    proj = projects.primary
    app = proj.active_application
    for k in app.get_children():
        nm = k.get_name()
        if nm not in KEEP:
            try:
                k.remove(); L(u"removed %s" % nm)
            except Exception, e:
                L(u"remove %s FAIL %s" % (nm, e))
    proj.save()
    L(u"after: %s" % u", ".join([k.get_name() for k in app.get_children()]))
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))
finally:
    _lf.close()
