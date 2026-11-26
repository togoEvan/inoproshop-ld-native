# -*- coding: utf-8 -*-
"""F10 第一步：导出 4 个 POU 的 native + 建 F10_POU_EthercatTask_Verify 顶层文件夹。

分两步（与 task_import_f07.py 同模式）：
  1) 无 ipc/f10_top_guid.txt 时：只建顶层 Folder，然后退出
  2) 有 guid 后：导出 4 个 POU native 到 ipc/f10/（供主机侧翻译）

输出 ipc/f10_export.log
"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
SRC = os.path.join(IPC, u"f10")
LOG = os.path.join(IPC, u"f10_export.log")
_lf = io.open(LOG, "w", encoding="utf-8")

TOPNAME = u"F10_POU_EthercatTask_Verify"


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


def ug():
    import uuid as _uuid
    try:
        return unicode(_uuid.uuid4())
    except NameError:
        return str(_uuid.uuid4())


try:
    sys.path.insert(0, os.path.join(
        u"D:\\小艺Work工作空间\\20261123160323\\inoproshop-ld-native", u"scripts", u"examples"))
    import make_gvl

    proj = projects.primary
    app = proj.active_application

    # ---- 1) 找/建顶层 Verify 文件夹 ----
    top = None
    for o in kids(app):
        if nm(o) == TOPNAME:
            top = o
            break

    if top is None:
        sv_root = ug()
        entry = make_gvl.folder_entry(
            name=TOPNAME,
            guid=ug(),
            own_sv_guid=sv_root,
            parent_container_guid=make_gvl.APP_SV_NODE,
            path_parts=[u"Device", u"PLC 逻辑", u"Application"],
            sv_root_guid=sv_root,
            parent_guid=None,
            is_root=True)
        tmp = os.path.join(IPC, u"f10_top.native")
        make_gvl.build_export([entry], tmp, sv_root)
        res = app.import_native(unicode(tmp))
        L(u"top folder import: %r" % (res,))
        for o in kids(app):
            if nm(o) == TOPNAME:
                top = o
                break
    if top is None:
        raise RuntimeError(u"%s create failed" % TOPNAME)

    gf = os.path.join(IPC, u"f10_top_guid.txt")
    if not os.path.exists(gf):
        L(u"STEP1 done: top folder created, need host-side guid parse")
        L(u"=== done ===")
        _lf.close()
        print(u"done")
        sys.exit(0)

    L(u"top guid = %s" % io.open(gf, u"r", encoding=u"utf-8").read().strip())

    # ---- 2) 导出 F10 四个 POU ----
    f10 = None
    for o in kids(app):
        if nm(o).upper().startswith(u"F10_POU"):
            f10 = o
            break
    if f10 is None:
        raise RuntimeError(u"F10_POU_EthercatTask not found")

    if not os.path.isdir(SRC):
        os.makedirs(SRC)

    names = [nm(c) for c in kids(f10)]
    L(u"F10 children = %r" % names)

    ok = 0
    for c in kids(f10):
        n = nm(c)
        dst = os.path.join(SRC, u"%s.native" % n)
        try:
            c.export_native(unicode(dst))
            L(u"  [ok] %s -> %s (%d bytes)" % (n, dst, os.path.getsize(dst)))
            ok += 1
        except Exception, e:
            L(u"  [FAIL] %s: %s" % (n, e))
    L(u"exported %d/%d" % (ok, len(names)))

    L(u"--- Verify tree ---")
    for k in kids(top):
        L(u"  - %s" % nm(k))
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
print(u"done")
