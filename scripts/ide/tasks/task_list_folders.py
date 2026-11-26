# -*- coding: utf-8 -*-
# @ipy2
"""列出 Application 下所有 F0x 开头的 Folder / GVL 及成员，用于确认 F02 内容。

输出 ipc/exp/list_f02.log
"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
LOG = os.path.join(IPC, u"list_f02.log")
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
    app = projects.primary.active_application
    L(u"=== Application 直属对象 ===")
    for c in kids(app):
        L(u"  %s" % nm(c))

    L(u"")
    L(u"=== 递归展开 F 开头的 Folder ===")
    for c in kids(app):
        n = nm(c)
        if not n.startswith(u"F"):
            continue
        L(u"[Folder] %s" % n)
        for g in kids(c):
            gn = nm(g)
            L(u"    %s" % gn)
            try:
                t = g.textual_declaration
                if t:
                    lines = [l for l in unicode(t).split(u"\n") if l.strip()]
                    L(u"      (declaration %d 行)" % len(lines))
            except Exception, e:
                L(u"      (无文本声明: %s)" % e)
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
