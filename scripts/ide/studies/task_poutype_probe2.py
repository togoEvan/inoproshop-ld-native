# -*- coding: utf-8 -*-
# @ipy2
"""探测 PouType 枚举的可用值（只接受 0？）+ 尝试 create_pou(name, 0)。"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
_lf = io.open(os.path.join(IPC, u"poutype_probe2.log"), "w", encoding="utf-8")


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


proj = projects.primary
app = proj.active_application

for v in (0, -1, 5, 6, 7, 8):
    try:
        p = app.create_pou(u"prg_PouTypeProbeX", v)
        L(u"create_pou(%d) OK -> %r  dir=%s"
          % (v, unicode(p.get_name()),
             u",".join(sorted([n for n in dir(p) if not n.startswith(u"_")]))))
        p.remove()
        break
    except Exception, e:
        L(u"create_pou(%d) ERR %s" % (v, unicode(e)[:160]))

L(u"=== done ===")
_lf.close()
