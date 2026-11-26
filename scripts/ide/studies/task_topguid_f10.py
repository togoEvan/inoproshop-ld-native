# -*- coding: utf-8 -*-
# @ipy2
"""F10 补充步骤：读取 F10_POU_EthercatTask_Verify 顶层文件夹 guid，
写入 ipc/f10_top_guid.txt，并导出该文件夹 native 备查。

输出 ipc/f10_topguid.log
"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
LOG = os.path.join(IPC, u"f10_topguid.log")
_lf = io.open(LOG, "w", encoding="utf-8")

TOPNAME = u"F10_POU_EthercatTask_Verify"


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


def kids(o):
    try:
        return list(o.get_children())
    except Exception:
        return []


def nm(o):
    try:
        return unicode(o.get_name())
    except Exception:
        return u"?"


try:
    app = projects.primary.active_application
    top = None
    for o in kids(app):
        if nm(o) == TOPNAME:
            top = o
            break
    if top is None:
        raise RuntimeError(u"%s not found" % TOPNAME)

    g = None
    try:
        g = unicode(top.guid)
    except Exception, e:
        L(u"guid attr fail: %s" % e)

    if not g:
        # 回退：导出 native 由主机侧解析
        dst = os.path.join(IPC, u"f10_top_ide.native")
        top.export_native(unicode(dst))
        L(u"exported -> %s (%d bytes), parse host-side" % (dst, os.path.getsize(dst)))
    else:
        io.open(os.path.join(IPC, u"f10_top_guid.txt"), "w", encoding="utf-8").write(g + u"\n")
        L(u"guid = %s (written)" % g)
    L(u"name = %s, is_folder = %s" % (nm(top), getattr(top, u"is_folder", u"?")))
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
print(u"done")
