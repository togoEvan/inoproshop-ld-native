# -*- coding: utf-8 -*-
"""删除 F05_FC_Verify 下误建的空文件夹（无子对象、无代码的纯容器）。

判定：kids==0 且 textual_declaration 与 textual_implementation 都取不到。
只删名字以 _F05V 结尾且满足上述条件的直接子项。
"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[0])))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
_lf = io.open(os.path.join(IPC, u"f05_rm_empty.log"), "w", encoding="utf-8")


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


def kids(o):
    try:
        return list(o.get_children())
    except Exception:
        return []


def has_code(o):
    for attr in (u"textual_declaration", u"textual_implementation"):
        try:
            v = getattr(o, attr)
            if v is not None:
                return True
        except Exception:
            pass
    return False


try:
    proj = projects.primary
    app = proj.active_application
    top = None
    for o in app.get_children():
        if unicode(o.get_name()) == u"F05_FC_Verify":
            top = o
            break
    if top is None:
        raise RuntimeError(u"F05_FC_Verify not found")

    targets = []
    for k in kids(top):
        n = unicode(k.get_name())
        if len(kids(k)) == 0 and not has_code(k):
            targets.append((n, k))
    L(u"empty folders found: %d -> %s" % (len(targets), [t[0] for t in targets]))

    for n, k in targets:
        try:
            k.remove()
            L(u"removed empty folder: %s" % n)
        except Exception, e:
            L(u"FAIL remove %s: %s" % (n, e))

    proj.save()
    L(u"saved")

    L(u"--- after ---")
    for k in kids(top):
        L(u"  - %-40s kids=%d code=%s"
          % (unicode(k.get_name()), len(kids(k)), has_code(k)))
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
print(u"done")
