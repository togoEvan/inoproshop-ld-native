# -*- coding: utf-8 -*-
# @ipy2
"""F21 第三步：把 ipc/f21_out 下的 7 个翻译副本导入 F21_POU_Station1_工站1_搬运移栽_Verify 顶层文件夹。

前置：task_export_f21.py 已建顶层文件夹 + f21_top_guid.txt 已写入。

输出 ipc/f21_import.log
"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
SRC = os.path.join(IPC, u"f21_out")
LOG = os.path.join(IPC, u"f21_import.log")
_lf = io.open(LOG, "w", encoding="utf-8")

TOPNAME = u"F21_POU_Station1_工站1_搬运移栽_Verify"


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
    top = None
    for o in kids(app):
        if nm(o) == TOPNAME:
            top = o
            break
    if top is None:
        raise RuntimeError(u"%s not found" % TOPNAME)

    gf = os.path.join(IPC, u"f21_top_guid.txt")
    if not os.path.exists(gf):
        raise RuntimeError(u"f21_top_guid.txt missing")
    L(u"top guid = %s" % io.open(gf, u"r", encoding=u"utf-8").read().strip())
    L(u"children before: %s" % u", ".join(nm(k) for k in kids(top)))

    total = 0
    ok = 0
    for f in sorted(os.listdir(SRC)):
        if not f.endswith(u".native") or f.startswith(u"_"):
            continue
        total += 1
        try:
            r = top.import_native(unicode(os.path.join(SRC, f)))
            L(u"  [ok] %s -> %r" % (f, r))
            ok += 1
        except Exception, e:
            L(u"  [FAIL] %s: %s" % (f, e))
    L(u"imported %d/%d" % (ok, total))

    L(u"--- Verify tree ---")
    for k in kids(top):
        L(u"  - %s" % nm(k))

    projects.primary.save()
    L(u"saved")
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
print(u"done")
