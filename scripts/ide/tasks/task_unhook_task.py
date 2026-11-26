# -*- coding: utf-8 -*-
# @ipy2
"""彻底把 prg_GvlVerifyUse 从 MainTask 调用列表摘掉（remove 传名字无效，改试索引/其它方式）。"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
_lf = io.open(os.path.join(IPC, u"unhook_task.log"), "w", encoding="utf-8")

POU = u"prg_GvlVerifyUse"


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


def snapshot(t):
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
    L(u"before: %s" % u", ".join(snapshot(mt)))

    # 方式 1：按索引 remove
    names = snapshot(mt)
    if POU in names:
        idx = names.index(POU)
        try:
            mt.pous.remove(idx)
            L(u"remove(idx=%d) ok -> %s" % (idx, u", ".join(snapshot(mt))))
        except Exception, e:
            L(u"remove(idx) ERR %s" % unicode(e)[:160])

    # 方式 2：remove 传对象名（若还残留）
    if POU in snapshot(mt):
        try:
            mt.pous.remove(POU)
            L(u"remove(name) ok -> %s" % u", ".join(snapshot(mt)))
        except Exception, e:
            L(u"remove(name) ERR %s" % unicode(e)[:160])

    # 方式 3：Item 索引赋值 / replace
    if POU in snapshot(mt):
        try:
            names = snapshot(mt)
            idx = names.index(POU)
            L(u"still present, idx=%d; try replace(idx, '')" % idx)
            mt.pous.replace(idx, u"")
            L(u"replace ok -> %s" % u", ".join(snapshot(mt)))
        except Exception, e:
            L(u"replace ERR %s" % unicode(e)[:160])

    L(u"after: %s" % u", ".join(snapshot(mt)))
    proj.save()
    L(u"saved")
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
