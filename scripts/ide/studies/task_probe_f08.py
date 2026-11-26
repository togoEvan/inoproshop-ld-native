# -*- coding: utf-8 -*-
"""探测 F08_AxisGroup 下轴组对象的能力：属性、方法、能否导出 native。

轴组（AxesGroup）是 CODESYS 的运动控制对象，与 CAM 类似属于「结构化对象」，
可能没有 TextLines。先摸清再决定复制策略。

输出 ipc/f08_probe.log
"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
LOG = os.path.join(IPC, u"f08_probe.log")
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


def safe(label, fn):
    try:
        return u"%s = %r" % (label, fn())
    except Exception, e:
        return u"%s !! %s: %s" % (label, type(e).__name__, e)


def dir_public(o):
    out = []
    for a in dir(o):
        if a.startswith(u"_"):
            continue
        out.append(a)
    return out


try:
    app = projects.primary.active_application
    L(u"BASE=%s" % BASE)
    L(u"")

    f08 = None
    for c in kids(app):
        if nm(c).upper().startswith(u"F08"):
            f08 = c
            break
    if f08 is None:
        raise RuntimeError(u"F08 not found")

    L(u"=== F08 容器 ===")
    L(u"name = %s" % nm(f08))
    L(u"children = %s" % [nm(k) for k in kids(f08)])
    L(u"")

    for grp in kids(f08):
        gn = nm(grp)
        L(u"########## %s ##########" % gn)
        L(dir_public(grp))
        L(u"")
        L(safe(u"is_folder", lambda: grp.is_folder))
        L(safe(u"has_textual_implementation", lambda: grp.has_textual_implementation))
        L(safe(u"textual_declaration", lambda: unicode(grp.textual_declaration)[:200]))
        L(safe(u"textual_implementation", lambda: unicode(grp.textual_implementation)[:200]))
        L(safe(u"get_children()", lambda: [nm(k) for k in kids(grp)]))
        L(safe(u"type_guid", lambda: unicode(grp.type_guid)))
        L(safe(u"guid", lambda: unicode(grp.guid)))
        L(u"")

        # 逐个成员探测：找轴引用、类型信息
        for k in kids(grp):
            kn = nm(k)
            L(u"  --- child: %s ---" % kn)
            L(u"  " + unicode(dir_public(k))[:600])
            L(u"  " + safe(u"is_folder", lambda kk=k: kk.is_folder))
            L(u"  " + safe(u"has_textual_implementation", lambda kk=k: kk.has_textual_implementation))
            L(u"  " + safe(u"textual_declaration", lambda kk=k: unicode(kk.textual_declaration)[:300]))
            L(u"  " + safe(u"children", lambda kk=k: [nm(x) for x in kids(kk)]))
            L(u"")

    # 导出接口探测
    L(u"=== 导出接口 ===")
    L(safe(u"projects.primary.export_native", lambda: projects.primary.export_native))
    L(safe(u"app.export_native", lambda: app.export_native))
    L(safe(u"system.export_native", lambda: system.export_native))
    L(u"")

    # 尝试导出 AxesGroup_A1
    first = kids(f08)[0] if kids(f08) else None
    if first is not None:
        outdir = os.path.join(IPC, u"f08")
        if not os.path.isdir(outdir):
            os.makedirs(outdir)
        outp = os.path.join(outdir, u"AxesGroup_A1_probe.native")
        L(u"--- 尝试 export_native(%s -> %s) ---" % (nm(first), outp))
        try:
            r = projects.primary.export_native([first], outp, True)
            L(u"export_native ok = %r" % (r,))
            L(u"文件存在 = %s, 大小 = %s" % (
                os.path.isfile(outp),
                os.path.getsize(outp) if os.path.isfile(outp) else u"-"))
        except Exception, e:
            L(u"export_native !! %s: %s" % (type(e).__name__, e))
            L(traceback.format_exc())
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
print(u"done")
