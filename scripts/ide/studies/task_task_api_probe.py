# -*- coding: utf-8 -*-
# @ipy2
"""探测 Task Configuration 的调用列表 API（用于把验证 POU 挂进任务，强制参与编译）。"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
_lf = io.open(os.path.join(IPC, u"task_api_probe.log"), "w", encoding="utf-8")


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


try:
    proj = projects.primary
    app = proj.active_application
    tc = None
    for o in app.get_children():
        if unicode(o.get_name()) == u"Task Configuration":
            tc = o
            break
    L(u"Task Configuration found: %s" % (tc is not None))
    if tc is not None:
        L(u"tc type: %s" % unicode(type(tc)))
        for n in (u"get_tasks", u"tasks", u"get_children"):
            try:
                v = getattr(tc, n)
                L(u"tc.%s = %r" % (n, v))
            except Exception, e:
                L(u"tc.%s ERR %s" % (n, e))
        for t in tc.get_children():
            L(u"  task: %s  type=%s" % (unicode(t.get_name()), unicode(type(t))))
            for n in (u"pous", u"get_pous", u"add_pou", u"programs"):
                try:
                    v = getattr(t, n)
                    L(u"    %s.%s = %r" % (unicode(t.get_name()), n, v))
                except Exception, e:
                    L(u"    %s.%s ERR %s" % (unicode(t.get_name()), n, e))
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
