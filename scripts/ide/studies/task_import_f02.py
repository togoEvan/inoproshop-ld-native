# -*- coding: utf-8 -*-
# @ipy2
"""在 Application 下新建 F02_Struct_Verify 文件夹（复用 make_gvl 的 folder_entry），
然后逐个导入 17 个 Struct 副本 native（import_native 到该文件夹，此时无同名冲突不弹窗）。

用法：bridge.py eval_file {"path":".../task_import_f02.py"}
"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
SRC = os.path.join(IPC, u"f02_verify")
LOG = os.path.join(IPC, u"f02_import.log")
_lf = io.open(LOG, u"w", encoding=u"utf-8")


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


def import_folder_mod():
    p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))), u"..")
    sys.path.insert(0, os.path.abspath(p))
    import make_gvl
    return make_gvl


try:
    app = projects.primary.active_application
    folder_name = u"F02_Struct_Verify"

    parent = None
    for o in app.get_children():
        if unicode(o.get_name()) == folder_name:
            parent = o
            break

    if parent is None:
        sys.path.insert(0, u"D:\\小艺Work工作空间\\20261123160323\\inoproshop-ld-native\\scripts\\examples")
        import make_gvl
        import uuid as _uuid

        def _ug():
            try:
                return unicode(_uuid.uuid4())
            except NameError:
                return str(_uuid.uuid4())

        sv_root = _ug()
        folder_guid = _ug()
        entry = make_gvl.folder_entry(
            name=folder_name,
            guid=folder_guid,
            own_sv_guid=sv_root,
            parent_container_guid=make_gvl.APP_SV_NODE,
            path_parts=[u"Device", u"PLC 逻辑", u"Application"],
            sv_root_guid=sv_root,
            parent_guid=None,      # 直属 Application -> 全零
            is_root=True)
        tmp = os.path.join(IPC, u"f02_folder.native")
        make_gvl.build_export([entry], tmp, sv_root)
        res = app.import_native(unicode(tmp))
        L(u"folder import: %r" % (res,))
        for o in app.get_children():
            if unicode(o.get_name()) == folder_name:
                parent = o
                break
    if parent is None:
        raise RuntimeError(u"folder create failed")

    kids_before = [unicode(k.get_name()) for k in parent.get_children()]
    L(u"folder children before: %s" % (kids_before,))

    # 2) 逐个导入 17 个副本
    names = sorted(f for f in os.listdir(SRC) if f.endswith(u".native"))
    ok = 0
    for n in names:
        p = os.path.join(SRC, n)
        try:
            r = parent.import_native(unicode(p))
            L(u"[ok] %s -> %r" % (n, r))
            ok += 1
        except Exception, e:
            L(u"[FAIL] %s: %s" % (n, e))
    L(u"imported %d/%d" % (ok, len(names)))

    # 3) 导入后清单
    kids_after = [unicode(k.get_name()) for k in parent.get_children()]
    L(u"folder children after: %s" % (kids_after,))
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
print(u"done")
