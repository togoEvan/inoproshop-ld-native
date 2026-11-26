# -*- coding: utf-8 -*-
"""探测：如何在脚本里创建一个 POU（用于写一段引用 GVL 变量的代码做交叉验证）。"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
_lf = io.open(os.path.join(IPC, u"pou_api_probe.log"), "w", encoding="utf-8")


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


proj = projects.primary
app = proj.active_application
L(u"app dir: %s" % u", ".join(sorted([n for n in dir(app) if not n.startswith(u"_")])))
L(u"proj dir: %s" % u", ".join(sorted([n for n in dir(proj) if not n.startswith(u"_")])))
for n in (u"create_pou", u"create_program", u"create_gvl"):
    try:
        L(u"app.%s = %r" % (n, getattr(app, n)))
    except Exception, e:
        L(u"app.%s ERR %s" % (n, e))
# 看一个已有 PRG 的 API
for o in app.get_children():
    nm = unicode(o.get_name())
    if nm.startswith(u"prg_"):
        L(u"sample %s dir: %s" % (nm, u", ".join(sorted([x for x in dir(o) if not x.startswith(u"_")]))))
        break
L(u"=== done ===")
_lf.close()
