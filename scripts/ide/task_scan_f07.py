# -*- coding: utf-8 -*-
"""扫描 F07_CAM：列出全部子项（含直接 POU），标注实现语言（ST/LD）与对象大小。
输出 ipc/f07_scan.log
"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[0])))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
LOG = os.path.join(IPC, u"f07_scan.log")
_lf = io.open(LOG, "w", encoding="utf-8")


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


def kids(o):
    try:
        return list(o.get_children())
    except Exception:
        return []


try:
    app = projects.primary.active_application
    f07 = None
    for o in app.get_children():
        if unicode(o.get_name()) == u"F07_CAM":
            f07 = o
            break
    if f07 is None:
        raise RuntimeError(u"F07_CAM not found")

    for sf in kids(f07):
        sfn = unicode(sf.get_name())
        L(u"[SF] %s" % sfn)
        for fb in kids(sf):
            n = unicode(fb.get_name())
            impl = u"?"
            try:
                ti = fb.textual_implementation
                if ti is None:
                    impl = u"(no impl)"
                else:
                    t = unicode(getattr(ti, u"text", ti) or u"")
                    if u"NetworkList" in t or u"IMPLEMENTATION" not in t:
                        impl = u"maybe-LD/empty"
                    else:
                        impl = u"ST(%d chars)" % len(t)
            except Exception, e:
                impl = u"err:%s" % type(e).__name__
            L(u"    %-40s %s" % (n, impl))
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
print(u"done")
