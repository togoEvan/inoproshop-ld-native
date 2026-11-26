# -*- coding: utf-8 -*-
"""递归列出 Application 下全部对象：名称 / 子对象数 / 是否疑似 Folder（空壳）。"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[0])))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
_lf = io.open(os.path.join(IPC, u"dump_tree.log"), "w", encoding="utf-8")


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


def kids(o):
    try:
        return list(o.get_children())
    except Exception:
        return []


def has_impl(o):
    try:
        ti = o.textual_implementation
        return ti is not None
    except Exception:
        return False


def has_decl(o):
    try:
        td = o.textual_declaration
        return td is not None
    except Exception:
        return False


def walk(o, depth, maxdepth):
    if depth > maxdepth:
        return
    for k in kids(o):
        n = unicode(k.get_name())
        ch = kids(k)
        tags = []
        if not has_impl(k) and not has_decl(k):
            tags.append(u"NO-CODE")     # 无实现无声明 = 纯容器/Folder
        if len(ch) == 0:
            tags.append(u"EMPTY")
        L(u"%s- %-40s kids=%d %s"
          % (u"  " * depth, n, len(ch), u" ".join(tags)))
        walk(k, depth + 1, maxdepth)


try:
    app = projects.primary.active_application
    L(u"### Application 顶层 ###")
    for o in app.get_children():
        ch = kids(o)
        tags = []
        if not has_impl(o) and not has_decl(o):
            tags.append(u"NO-CODE")
        if len(ch) == 0:
            tags.append(u"EMPTY")
        L(u"- %-40s kids=%d %s" % (unicode(o.get_name()), len(ch), u" ".join(tags)))

    L(u"")
    L(u"### F05_FC_Verify 全展开 ###")
    for o in app.get_children():
        if unicode(o.get_name()) == u"F05_FC_Verify":
            walk(o, 1, 3)
            break

    L(u"")
    L(u"### F04_FB_Verify 一层 ###")
    for o in app.get_children():
        if unicode(o.get_name()) == u"F04_FB_Verify":
            walk(o, 1, 1)
            break
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
print(u"done")
