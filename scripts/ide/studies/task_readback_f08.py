# -*- coding: utf-8 -*-
# @ipy2
"""F08 回读验证：导出导入后的轴组，比对 13 个关键字段，并检查内部 POU Guid 是否被重建。

关注点：
  1) MetaObject.Name / Guid / Object.Id 是否保留我们写入的值
  2) AxisGuid 是否仍指向原设备轴（保留 = 副本共用轴）
  3) 4 个内部 POU Guid（ReadInputs/WriteOutputs/Init/gvl）是否被 IDE 改写
     —— 若改写 = IDE 为副本重建了自己的 POU，完全独立
     —— 若不变 = 两个轴组共用同一批 POU，可能冲突
  4) WorkspaceConfig 数值是否保留

输出 ipc/f08_readback.log
"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
TOPNAME = u"F08_AxisGroup_Verify"
OUTDIR = os.path.join(IPC, u"f08_readback")
LOG = os.path.join(IPC, u"f08_readback.log")
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


def gd(o):
    try:
        return unicode(o.guid)
    except Exception:
        return u"?"


try:
    app = projects.primary.active_application
    if not os.path.isdir(OUTDIR):
        os.makedirs(OUTDIR)

    top = None
    for o in kids(app):
        if nm(o) == TOPNAME:
            top = o
            break
    if top is None:
        raise RuntimeError(u"%s not found" % TOPNAME)

    L(u"=== 回读导出 ===")
    for k in kids(top):
        outp = os.path.join(OUTDIR, nm(k) + u".native")
        try:
            projects.primary.export_native([k], outp, True)
            L(u"  %s -> %s (%d bytes)" % (
                nm(k), os.path.basename(outp),
                os.path.getsize(outp) if os.path.isfile(outp) else -1))
        except Exception, e:
            L(u"  %s !! %s: %s" % (nm(k), type(e).__name__, e))

    # 顶层文件夹的子对象（看 IDE 是否给轴组加了内部 POU 作为兄弟节点）
    L(u"")
    L(u"=== Verify 文件夹成员 ===")
    for k in kids(top):
        L(u"  %-30s guid=%s" % (nm(k), gd(k)))
        for c in kids(k):
            L(u"      child: %-26s guid=%s" % (nm(c), gd(c)))
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
print(u"done")
