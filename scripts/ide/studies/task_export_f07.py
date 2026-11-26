# -*- coding: utf-8 -*-
"""整树导出 F07_CAM：每个子文件夹单独 native + 每个对象单独 native + 整包备份。

输出：
  ipc/f07/<子文件夹>/<对象名>.native   每个对象单独导出
  ipc/f07/<子文件夹>_folder.native     每个子文件夹整包
  ipc/f07/F07_CAM_backup.native         整个 F07_CAM
  ipc/f07_export.log
"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
OUT = os.path.join(IPC, u"f07")
if not os.path.isdir(OUT):
    os.makedirs(OUT)
LOG = os.path.join(IPC, u"f07_export.log")
_lf = io.open(LOG, "w", encoding="utf-8")


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


def kids(o):
    try:
        return list(o.get_children())
    except Exception:
        return []


def safe_name(n):
    for ch in (u"/", u"\\", u":", u"*", u"?", u"\"", u"<", u">", u"|"):
        n = n.replace(ch, u"_")
    return n


def export_one(o, dirpath):
    n = safe_name(unicode(o.get_name()))
    p = os.path.join(dirpath, u"%s.native" % n)
    if os.path.exists(p):
        os.remove(p)
    o.export_native(p)
    return p


try:
    app = projects.primary.active_application
    f07 = None
    for o in app.get_children():
        if unicode(o.get_name()) == u"F07_CAM":
            f07 = o
            break
    if f07 is None:
        raise RuntimeError(u"F07_CAM not found")

    # 0) 整包备份
    p = os.path.join(OUT, u"F07_CAM_backup.native")
    if os.path.exists(p):
        os.remove(p)
    f07.export_native(p)
    L(u"[backup] F07_CAM -> %d bytes" % os.path.getsize(p))

    # 1) 每个子文件夹
    total = 0
    for sf in kids(f07):
        sfn = safe_name(unicode(sf.get_name()))
        sdir = os.path.join(OUT, sfn)
        if not os.path.isdir(sdir):
            os.makedirs(sdir)
        pf = os.path.join(OUT, u"%s_folder.native" % sfn)
        if os.path.exists(pf):
            os.remove(pf)
        sf.export_native(pf)
        L(u"[SF] %s (folder %d bytes)" % (sfn, os.path.getsize(pf)))
        # 2) 子文件夹下每个对象
        for obj in kids(sf):
            n = safe_name(unicode(obj.get_name()))
            op = export_one(obj, sdir)
            L(u"    %-44s %d bytes" % (n, os.path.getsize(op)))
            total += 1
    L(u"total objects exported: %d" % total)
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
print(u"done")
