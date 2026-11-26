# -*- coding: utf-8 -*-
# @ipy2
"""把 prg_F11VerifyUse 从 MainTask 调用列表彻底摘掉。

实测：对象删除后任务槽里仍残留名字（编译报「没有定义标识符 'prg_F11VerifyUse'」），
`pl.remove(name)` 会返回成功但槽位不变，必须再按索引 remove。

输出 ipc/unhook_f11.log
"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
_lf = io.open(os.path.join(IPC, u"unhook_f11.log"), "w", encoding="utf-8")

POU = u"prg_F11VerifyUse"


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
    L(u"before: %s" % u", ".join(snap(mt)))

    for attempt in range(4):
        names = snap(mt)
        if POU not in names:
            break
        idx = names.index(POU)
        try:
            mt.pous.remove(idx)
            L(u"round%d remove(idx=%d) -> %s" % (attempt, idx, u", ".join(snap(mt))))
            continue
        except Exception, e:
            L(u"round%d remove(idx) ERR %s" % (attempt, unicode(e)[:160]))
        try:
            mt.pous.remove(POU)
            L(u"round%d remove(name) -> %s" % (attempt, u", ".join(snap(mt))))
        except Exception, e:
            L(u"round%d remove(name) ERR %s" % (attempt, unicode(e)[:160]))
            break

    L(u"after: %s" % u", ".join(snap(mt)))
    proj.save()
    L(u"saved")
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
print(u"done")
