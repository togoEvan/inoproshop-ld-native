# -*- coding: utf-8 -*-
"""F08 轴组深入探测：导出 C1、解析 A1/C1 的 Guid 引用、查工程里这些 Guid 是谁。

关键疑问：
  轴组 Object 下有 4 个 POU Guid 引用
    ReadInputsPouGuid / WriteOutputsPouGuid / InitPouGuid / gvlPouGuid
  以及 AxisMappings 里每根轴的 AxisGuid。
  复制轴组时这些引用若不改，两个轴组会共用同一批 POU/轴 —— 必须搞清后果。

输出 ipc/f08_deep.log
"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
LOG = os.path.join(IPC, u"f08_deep.log")
_lf = io.open(LOG, "w", encoding="utf-8")
OUTDIR = os.path.join(IPC, u"f08")


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


def guid(o):
    try:
        return unicode(o.guid)
    except Exception:
        return u"?"


def walk_all(o, depth=0, acc=None):
    """递归收集 (对象, 深度)"""
    if acc is None:
        acc = []
    acc.append((o, depth))
    for c in kids(o):
        walk_all(c, depth + 1, acc)
    return acc


try:
    app = projects.primary.active_application
    if not os.path.isdir(OUTDIR):
        os.makedirs(OUTDIR)

    f08 = None
    for c in kids(app):
        if nm(c).upper().startswith(u"F08"):
            f08 = c
            break
    if f08 is None:
        raise RuntimeError(u"F08 not found")

    # 1) 导出两个轴组
    L(u"=== 导出 ===")
    for grp in kids(f08):
        gn = nm(grp)
        outp = os.path.join(OUTDIR, gn + u".native")
        try:
            projects.primary.export_native([grp], outp, True)
            L(u"  %s -> %s (%s bytes)" % (
                gn, os.path.basename(outp),
                os.path.getsize(outp) if os.path.isfile(outp) else u"-"))
        except Exception, e:
            L(u"  %s !! %s: %s" % (gn, type(e).__name__, e))
    L(u"")

    # 2) 建立全工程 guid -> 名字 索引
    L(u"=== 全工程对象索引（Application 下全部层级）===")
    allobj = walk_all(app)
    L(u"对象总数 = %d" % len(allobj))
    idx = {}
    for o, d in allobj:
        g = guid(o)
        if g and g != u"?":
            idx[g.lower()] = (nm(o), d)
    L(u"有 guid 的对象数 = %d" % len(idx))
    L(u"")

    # 3) 解出两个轴组 native 里的所有 Guid 引用
    import re
    L(u"=== 轴组 native 内的 Guid 引用解析 ===")
    for grp in kids(f08):
        gn = nm(grp)
        outp = os.path.join(OUTDIR, gn + u".native")
        if not os.path.isfile(outp):
            continue
        s = io.open(outp, "r", encoding="utf-8").read()
        L(u"")
        L(u"---- %s ----" % gn)
        # 抓 <Name>Guid</Name> 形式的引用：XML 里是 <X Type="System.Guid">值</X>
        refs = []
        for m in re.finditer(
                r'<([A-Za-z0-9_]*Guid)\s+Type="System\.Guid">([0-9a-fA-F\-]{36})</\1>', s):
            refs.append((m.group(1), m.group(2)))
        L(u"Guid 引用共 %d 处：" % len(refs))
        for fname, g in refs:
            hit = idx.get(g.lower())
            if g == u"00000000-0000-0000-0000-000000000000":
                desc = u"(空引用)"
            elif hit:
                desc = u"%s  [depth=%d]" % hit
            else:
                desc = u"** 工程内未找到 **"
            L(u"  %-24s %s  -> %s" % (fname, g, desc))

    L(u"")
    L(u"=== 工程内与轴组相关的对象（名字含 Axes/Axis/GVL 组）===")
    for o, d in allobj:
        n = nm(o)
        low = n.lower()
        if u"axesgroup" in low or u"axisgroup" in low:
            L(u"  %-50s depth=%d guid=%s" % (n, d, guid(o)))
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
print(u"done")
