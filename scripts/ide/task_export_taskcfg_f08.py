# -*- coding: utf-8 -*-
"""把 prg_F08VerifyUse 从指定任务里彻底摘掉（绕开 pous.remove 无效的问题）。

背景（2026-11-26 实测）：
  ScriptPouObjectList.remove("名字") 报成功、日志也打印了，
  但回读 pous 列表里名字仍在 —— 与铁律 25 同源（remove 摘不掉）。

所以这里改用「导出 TaskConfig native → 主机侧删 <Single> 块 → 同名覆盖导入」。

本脚本只做导出（IDE 内），改与导入在主机侧 + 另一个脚本完成。

输出 ipc/f08_taskcfg.native
"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[0])))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
LOG = os.path.join(IPC, u"f08_taskcfg.log")
OUT = os.path.join(IPC, u"f08_taskcfg.native")
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

    # 顺便打印每个任务当前的 pous
    for k in kids(tc):
        try:
            L(u"[%s] pous = %s" % (nm(k), [unicode(x) for x in k.pous]))
        except Exception, e:
            L(u"[%s] pous !! %s" % (nm(k), e))
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
print(u"done")
