# -*- coding: utf-8 -*-
# @ipy2
"""在设备树里找轴组引用的 POU / 轴 的真实归属。

Application 树 584 个对象里找不到那 4 个 POU Guid 和 2 个 AxisGuid，
所以它们要么在 Device 层（PLC 设备下的 SoftMotion 轴），要么是轴组内部对象。

同时探测：
  - 设备树全貌（Application 之外还有哪些层）
  - 轴对象（SM_Drive_* / Axis）是否在树里可见
  - 轴组的 POU 是否以「子节点」形式藏在轴组对象内部

输出 ipc/f08_device.log
"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
LOG = os.path.join(IPC, u"f08_device.log")
_lf = io.open(LOG, "w", encoding="utf-8")

WANT = {
    u"13345d93-0620-48bf-8747-0b576ba0c9da": u"A1.ReadInputs",
    u"7a840816-d599-499d-8d1b-bc55ffb4269c": u"A1.WriteOutputs",
    u"746be94b-de86-4687-a8df-5c1e2e34bb26": u"A1.Init",
    u"fb146491-461b-4c9c-b717-ca986d3bdb32": u"A1.gvl",
    u"2b9e1a51-3d84-41f9-9187-c4b390e44702": u"A1.Axis1",
    u"39176bc8-8579-4e58-82de-64bf898d66fb": u"A1.Axis2",
    u"bc928f13-793b-4ca2-b761-58e907c53b35": u"C1.ReadInputs",
    u"d3c6ffb4-7446-4649-8b59-0049aac7c359": u"C1.WriteOutputs",
    u"dd7b459e-0cd4-4efb-bb4b-3d80167d66e0": u"C1.Init",
    u"ee199867-2025-4228-a1eb-fd7b67b56458": u"C1.gvl",
    u"abafabd0-00c4-4e76-8297-ec8962a0b629": u"C1.Axis1",
    u"d9285e5b-cb8f-4be6-92e7-2269a8304159": u"C1.Axis2",
}


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
        return unicode(o.guid).lower()
    except Exception:
        return u""


def walk_all(o, depth=0, acc=None, path=u""):
    if acc is None:
        acc = []
    p = (path + u"/" + nm(o)) if path else nm(o)
    acc.append((o, depth, p))
    for c in kids(o):
        walk_all(c, depth + 1, acc, p)
    return acc


try:
    proj = projects.primary
    L(u"工程路径 = %s" % proj.path)
    L(u"")

    # 1) 从工程根开始，看设备树全貌（前 4 层）
    L(u"=== 工程树前 4 层 ===")
    allobj = walk_all(proj)
    L(u"工程树对象总数 = %d" % len(allobj))
    for o, d, p in allobj:
        if d <= 3:
            L(u"  %s%s  (guid=%s)" % (u"  " * d, nm(o), gd(o)))
    L(u"")

    # 2) 全工程 guid 索引（含设备树）
    idx = {}
    for o, d, p in allobj:
        g = gd(o)
        if g:
            idx[g] = (nm(o), d, p)

    L(u"=== 引用解析（全工程树，不只 Application）===")
    for g, label in sorted(WANT.items(), key=lambda x: x[1]):
        hit = idx.get(g)
        L(u"  %-18s %s -> %s" % (
            label, g,
            (u"%s [depth=%d] %s" % hit) if hit else u"** 全工程树内都没有（内部对象）**"))

    L(u"")
    L(u"=== 设备树里的 Axis 类对象 ===")
    for o, d, p in allobj:
        n = nm(o)
        try:
            is_dev = o.is_device
        except Exception:
            is_dev = False
        if is_dev:
            L(u"  [device] %-40s depth=%d guid=%s  path=%s" % (n, d, gd(o), p))
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
print(u"done")
