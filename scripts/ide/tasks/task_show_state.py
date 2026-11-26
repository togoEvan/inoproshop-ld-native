# -*- coding: utf-8 -*-
# @ipy2
"""显示 MainTask 调用列表 + prg_NoTaskTest 是否存在。"""
import io, os, sys, traceback
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base
BASE = _base.resolve_base(); IPC = _base.ensure_ipc(BASE)
_lf = io.open(os.path.join(IPC, u"show_state.log"), "w", encoding="utf-8")
def L(m):
    _lf.write(u"%s\n" % unicode(m)); _lf.flush()
try:
    app = projects.primary.active_application
    tc = None
    for o in app.get_children():
        if unicode(o.get_name()) == u"Task Configuration":
            tc = o; break
    for t in tc.get_children():
        L(u"task %s : %r" % (unicode(t.get_name()), [unicode(x) for x in t.pous]))
    L(u"prg_NoTaskTest exists: %s" % any(unicode(o.get_name()) == u"prg_NoTaskTest"
                                        for o in app.get_children()))
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))
L(u"=== done ==="); _lf.close()
