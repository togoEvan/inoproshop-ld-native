# -*- coding: utf-8 -*-
# @ipy2
"""扫描 F10 文件夹：递归列出全部子项，标注类型与实现语言。

F10 预期是 F10_POU_EthercatTask（EtherCAT 任务相关的 POU 集合）。
沿用 task_scan_f08.py 的判定逻辑（靠行为判定类别，比 TypeGuid 更可靠）。

输出 ipc/f10_scan.log
"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
LOG = os.path.join(IPC, u"f10_scan.log")
_lf = io.open(LOG, "w", encoding="utf-8")

TARGET = u"F10"


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


def classify(o):
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
            return u"POU-LD(%d)" % len(t)
        if u"IMPLEMENTATION" in t:
            return u"POU-ST(%d)" % len(t)
        return u"POU(?)(%d)" % len(t)
    if decl is not None:
        d = unicode(getattr(decl, u"text", decl) or u"")
        head = u" / ".join([x.strip() for x in d.split(u"\n") if x.strip()][:2])
        if u"STRUCT" in d or u"UNION" in d:
            return u"DUT-struct  %s" % head[:70]
        if u"TYPE" in d:
            return u"DUT-other   %s" % head[:70]
        return u"decl-only(%d) %s" % (len(d), head[:60])
    return u"opaque"


def walk(o, depth):
    pad = u"    " * depth
    for c in kids(o):
        k = classify(c)
        L(u"%s%-44s %s" % (pad, nm(c), k))
        if k == u"Folder":
            walk(c, depth + 1)


try:
    app = projects.primary.active_application
    L(u"BASE=%s" % BASE)
    L(u"")
    L(u"=== Application 直属对象 ===")
    tops = kids(app)
    for c in tops:
        L(u"  %-46s %s" % (nm(c), classify(c)))

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
