# -*- coding: utf-8 -*-
# @ipy2
"""导出当前 Task Configuration native（供主机侧删除残留的 prg_F20VerifyUse）。

背景：ScriptPouObjectList.remove("名字") 报成功但回读仍在（铁律 25/38），
所以必须「导出 → 主机侧删 <Single> 块 → 同名覆盖导入」。

输出 ipc/f20_taskcfg.native / ipc/f20_taskcfg.log
"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
LOG = os.path.join(IPC, u"f20_taskcfg.log")
OUT = os.path.join(IPC, u"f20_taskcfg.native")
_lf = io.open(LOG, "w", encoding="utf-8")


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
    proj = projects.primary
    app = proj.active_application
    tc = None
    for o in kids(app):
        if nm(o) == u"Task Configuration":
            tc = o
            break
    if tc is None:
        raise RuntimeError(u"Task Configuration not found")

    L(u"导出 Task Configuration -> %s" % OUT)
    projects.primary.export_native([tc], OUT, True)
    L(u"文件存在 = %s, 大小 = %s" % (
        os.path.isfile(OUT),
        os.path.getsize(OUT) if os.path.isfile(OUT) else u"-"))

    for k in kids(tc):
        try:
            L(u"[%s] pous = %s" % (nm(k), [unicode(x) for x in k.pous]))
        except Exception, e:
            L(u"[%s] pous read err: %s" % (nm(k), e))
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
print(u"done")
