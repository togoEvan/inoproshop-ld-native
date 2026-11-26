# -*- coding: utf-8 -*-
"""在 F02_Struct_Verify 下建 SF01_Alarm_StructVerify 子文件夹，导入 14 个报警结构体副本。

关键：子文件夹的 parent_container_guid = 父文件夹 F02_Struct_Verify 的 SV 节点 guid
（从 ipc/f02b_verify_sv.txt 读，主机侧解析好），path 含 F02_Struct_Verify。

用法：bridge.py eval_file {"path":".../task_import_sf01.py"}
"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[0])))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
SRC = os.path.join(IPC, u"f02b_verify")
SVF = os.path.join(IPC, u"f02b_verify_sv.txt")
LOG = os.path.join(IPC, u"f02b_import.log")
_lf = io.open(LOG, u"w", encoding=u"utf-8")


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


try:
    lines = io.open(SVF, u"r", encoding=u"utf-8").read().split(u"\n")
    parent_sv_guid = lines[1].strip()   # F02_Struct_Verify 的 SV 节点 guid
    L(u"parent (F02_Struct_Verify) sv guid = %s" % parent_sv_guid)

    app = projects.primary.active_application

    # 1) 找父文件夹
    parent = None
    for o in app.get_children():
        if unicode(o.get_name()) == u"F02_Struct_Verify":
            parent = o
            break
    if parent is None:
        raise RuntimeError(u"F02_Struct_Verify not found")

    folder_name = u"SF01_Alarm_StructVerify"
    # 2) 已存在则复用，否则用 make_gvl.folder_entry 新建
    sub = None
    for k in parent.get_children():
        if unicode(k.get_name()) == folder_name:
            sub = k
            break
    if sub is None:
        sys.path.insert(0, u"D:\\小艺Work工作空间\\20261123160323\\inoproshop-ld-native\\scripts\\examples")
        import make_gvl
        import uuid as _uuid

        def _ug():
            try:
                return unicode(_uuid.uuid4())
            except NameError:
                return str(_uuid.uuid4())

        sv_root = _ug()
        entry = make_gvl.folder_entry(
            name=folder_name,
            guid=_ug(),
            own_sv_guid=sv_root,
            parent_container_guid=parent_sv_guid,
            path_parts=[u"Device", u"PLC 逻辑", u"Application", u"F02_Struct_Verify"],
            sv_root_guid=sv_root,
            # Folder 的子对象：ParentGuid = 父容器（F02_Struct_Verify）的 SV 节点 guid
            parent_guid=parent_sv_guid,
            is_root=True)
        tmp = os.path.join(IPC, u"f02b_folder.native")
        make_gvl.build_export([entry], tmp, sv_root)
        res = parent.import_native(unicode(tmp))
        L(u"subfolder import: %r" % (res,))
        for k in parent.get_children():
            if unicode(k.get_name()) == folder_name:
                sub = k
                break
    if sub is None:
        raise RuntimeError(u"subfolder create failed")

    kids_before = [unicode(k.get_name()) for k in sub.get_children()]
    L(u"subfolder children before: %s" % (kids_before,))

    # 3) 逐个导入 14 个副本
    names = sorted(f for f in os.listdir(SRC) if f.endswith(u".native"))
    ok = 0
    for n in names:
        p = os.path.join(SRC, n)
        try:
            r = sub.import_native(unicode(p))
            L(u"[ok] %s" % n)
            ok += 1
        except Exception, e:
            L(u"[FAIL] %s: %s" % (n, e))
    L(u"imported %d/%d" % (ok, len(names)))

    kids_after = [unicode(k.get_name()) for k in sub.get_children()]
    L(u"subfolder children after (%d): %s" % (len(kids_after), kids_after))
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
print(u"done")
