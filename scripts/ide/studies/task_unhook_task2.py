# -*- coding: utf-8 -*-
# @ipy2
"""彻底摘掉 MainTask 里的空槽项：试 Item(i) 后 remove(obj)，并检查最终列表。"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
_lf = io.open(os.path.join(IPC, u"unhook_task2.log"), "w", encoding="utf-8")


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


def snap(t):
    return [unicode(x) for x in t.pous]


try:
    proj = projects.primary
    app = proj.active_application
    tc = None
    for o in app.get_children():
        if unicode(o.get_name()) == u"Task Configuration":
            tc = o
            break
    mt = None
    for t in tc.get_children():
        if unicode(t.get_name()) == u"MainTask":
            mt = t
            break
    L(u"before: %r" % (snap(mt),))

    pl = mt.pous
    # 倒序删空项
    n = len(pl)
    for i in range(n - 1, -1, -1):
        try:
            item = pl.Item[i]
            nm = unicode(item)
        except Exception, e:
            L(u"Item(%d) ERR %s" % (i, unicode(e)[:120]))
            continue
        if not nm.strip():
            L(u"index %d is empty -> removing" % i)
            try:
                pl.remove(item)
                L(u"  remove(item) ok -> %r" % (snap(mt),))
            except Exception, e:
                L(u"  remove(item) ERR %s" % unicode(e)[:160])
                try:
                    pl.remove(i)
                    L(u"  remove(i) ok -> %r" % (snap(mt),))
                except Exception, e2:
                    L(u"  remove(i) ERR %s" % unicode(e2)[:160])

    L(u"after: %r" % (snap(mt),))
    proj.save()
    L(u"saved")
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
