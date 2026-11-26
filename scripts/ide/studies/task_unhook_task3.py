# -*- coding: utf-8 -*-
"""再试几种摘除空槽项的办法。"""
import io, os, sys, traceback
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base
BASE = _base.resolve_base(); IPC = _base.ensure_ipc(BASE)
_lf = io.open(os.path.join(IPC, u"unhook_task3.log"), "w", encoding="utf-8")
def L(m):
    _lf.write(u"%s\n" % unicode(m)); _lf.flush()
def snap(t):
    return [unicode(x) for x in t.pous]
try:
    proj = projects.primary; app = proj.active_application
    tc = None
    for o in app.get_children():
        if unicode(o.get_name()) == u"Task Configuration":
            tc = o; break
    mt = None
    for t in tc.get_children():
        if unicode(t.get_name()) == u"MainTask":
            mt = t; break
    L(u"before: %r" % (snap(mt),))
    pl = mt.pous
    for attempt in (u'pl.remove(u"")', u'pl.remove(None)', u'del pl[len(pl)-1]'):
        try:
            exec(attempt)
            L(u"%s ok -> %r" % (attempt, snap(mt)))
        except Exception, e:
            L(u"%s ERR %s" % (attempt, unicode(e)[:140]))
        if len(snap(mt)) == 1:
            break
    L(u"after: %r" % (snap(mt),))
    proj.save(); L(u"saved")
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))
L(u"=== done ===")
_lf.close()
