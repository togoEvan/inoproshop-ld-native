# -*- coding: utf-8 -*-
# @ipy2
"""查 F08 轴组引用的 4 个 POU Guid + 2 个 AxisGuid 在工程里对应哪个对象。

A1: ReadInputs 13345d93 / WriteOutputs 7a840816 / Init 746be94b / gvl fb146491
    Axis 2b9e1a51 / 39176bc8
C1: ReadInputs bc928f13 / WriteOutputs d3c6ffb4 / Init dd7b459e / gvl ee199867
    Axis abafabd0 / d9285e5b

如果这些 Guid 在 Application 树里找不到，说明是轴组「内部自动生成的 POU」，
不出现在树上 —— 这对复制策略是决定性的。

输出 ipc/f08_guidref.log
"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
LOG = os.path.join(IPC, u"f08_guidref.log")
_lf = io.open(LOG, "w", encoding="utf-8")

WANT = [
    (u"A1.ReadInputs", u"13345d93-0620-48bf-8747-0b576ba0c9da"),
    (u"A1.WriteOutputs", u"7a840816-d599-499d-8d1b-bc55ffb4269c"),
    (u"A1.Init", u"746be94b-de86-4687-a8df-5c1e2e34bb26"),
    (u"A1.gvl", u"fb146491-461b-4c9c-b717-ca986d3bdb32"),
    (u"A1.Axis1", u"2b9e1a51-3d84-41f9-9187-c4b390e44702"),
    (u"A1.Axis2", u"39176bc8-8579-4e58-82de-64bf898d66fb"),
    (u"C1.ReadInputs", u"bc928f13-793b-4ca2-b761-58e907c53b35"),
    (u"C1.WriteOutputs", u"d3c6ffb4-7446-4649-8b59-0049aac7c359"),
    (u"C1.Init", u"dd7b459e-0cd4-4efb-bb4b-3d80167d66e0"),
    (u"C1.gvl", u"ee199867-2025-4228-a1eb-fd7b67b56458"),
    (u"C1.Axis1", u"abafabd0-00c4-4e76-8297-ec8962a0b629"),
    (u"C1.Axis2", u"d9285e5b-cb8f-4be6-92e7-2269a8304159"),
]


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


def walk_all(o, depth=0, acc=None):
    if acc is None:
        acc = []
    acc.append((o, depth))
    for c in kids(o):
        walk_all(c, depth + 1, acc)
    return acc


try:
    app = projects.primary.active_application
    allobj = walk_all(app)
    L(u"对象总数 = %d" % len(allobj))

    idx = {}
    for o, d in allobj:
        g = gd(o)
        if g:
            idx[g] = (nm(o), d)

    L(u"")
    L(u"=== 引用解析 ===")
    for label, g in WANT:
        hit = idx.get(g.lower())
        L(u"  %-18s %s -> %s" % (
            label, g, (u"%s [depth=%d]" % hit) if hit else u"** 树内未找到（内部对象）**"))

    L(u"")
    L(u"=== 名字里含 Axis / A1 / C1 的对象 ===")
    for o, d in allobj:
        n = nm(o)
        low = n.lower()
        if (u"axis" in low or u"_a1" in low or u"_c1" in low
                or low.startswith(u"a1") or low.startswith(u"c1")):
            L(u"  %-50s depth=%d guid=%s" % (n, d, gd(o)))
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
print(u"done")
