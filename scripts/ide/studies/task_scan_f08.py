# -*- coding: utf-8 -*-
"""扫描 F08 文件夹：递归列出全部子项，标注类型 / TypeGuid / 实现语言。

先不假设 F08 内部结构（可能是 POU 集合、也可能是 DUT 集合或混合），
所以这里做完整递归 + TypeGuid 判定，输出后由主机侧决定复制策略。

输出 ipc/f08_scan.log
"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
LOG = os.path.join(IPC, u"f08_scan.log")
_lf = io.open(LOG, "w", encoding="utf-8")

TARGET = u"F08"

# TypeGuid 速查（与 references/native-structure.md 铁律 32/33 一致）
TG = {
    u"6f9dac99-8de1-4efc-8465-68ac443b7d08": u"POU(FB/FC)",
    u"2db5746d-d284-4425-9f7f-2663a34b0ebc": u"DUT",
    u"ffbfa93a-...": u"GVL",
    u"fea841a8-cb28-421c-8d22-c7226c528b66": u"CAM",
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


def tg(o):
    """取 TypeGuid。IDE 里没有直接属性，退化为行为判定。"""
    try:
        g = o.type_guid
        return unicode(g)
    except Exception:
        pass
    return u"?"


def classify(o):
    """靠行为判定对象类别（比 TypeGuid 更可靠，属性名因版本而异）"""
    is_folder = False
    try:
        is_folder = bool(o.is_folder)
    except Exception:
        pass

    has_impl = False
    try:
        has_impl = bool(o.has_textual_implementation)
    except Exception:
        pass

    decl = None
    try:
        decl = o.textual_declaration
    except Exception:
        decl = None

    impl = None
    try:
        impl = o.textual_implementation
    except Exception:
        impl = None

    if is_folder:
        return u"Folder"
    if has_impl and impl is not None:
        t = unicode(getattr(impl, u"text", impl) or u"")
        if u"NetworkList" in t or u"<LD>" in t:
            return u"POU-LD(%d chars)" % len(t)
        if u"IMPLEMENTATION" in t:
            return u"POU-ST(%d chars)" % len(t)
        return u"POU(?)(%d chars)" % len(t)
    if decl is not None:
        d = unicode(getattr(decl, u"text", decl) or u"")
        head = u" / ".join([x.strip() for x in d.split(u"\n") if x.strip()][:2])
        if u"STRUCT" in d or u"UNION" in d:
            return u"DUT-struct  head=%s" % head[:70]
        if u"TYPE" in d:
            return u"DUT-other   head=%s" % head[:70]
        return u"decl-only(%d chars) head=%s" % (len(d), head[:70])
    return u"opaque"


def walk(o, depth):
    pad = u"    " * depth
    for c in kids(o):
        cn = nm(c)
        kind = classify(c)
        L(u"%s%-44s %s" % (pad, cn, kind))
        # Folder 才递归；POU 的子节点是 Implementation 等，不展开
        if kind == u"Folder":
            walk(c, depth + 1)


try:
    app = projects.primary.active_application
    L(u"BASE=%s  SOURCE=%s" % (BASE, _base.SOURCE))
    L(u"")
    L(u"=== Application 直属对象 ===")
    tops = kids(app)
    for c in tops:
        L(u"  %-44s %s" % (nm(c), classify(c)))

    L(u"")
    target = None
    for c in tops:
        if nm(c).upper().startswith(TARGET):
            target = c
            break

    if target is None:
        L(u"")
        L(u"!! 未找到以 %s 开头的顶层对象" % TARGET)
    else:
        L(u"=== %s 递归展开 ===" % nm(target))
        walk(target, 0)
        L(u"")
        L(u"=== 统计 ===")
        cnt = {}
        def count(o):
            for c in kids(o):
                k = classify(c)
                key = k.split(u"(")[0].split(u"  ")[0]
                cnt[key] = cnt.get(key, 0) + 1
                if k == u"Folder":
                    count(c)
        count(target)
        for k in sorted(cnt):
            L(u"  %-16s %d" % (k, cnt[k]))
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
print(u"done")
