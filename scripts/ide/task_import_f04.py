# -*- coding: utf-8 -*-
"""建 F04_FB_Verify 顶层文件夹 + 9 个 SF 子文件夹，导入 58 个副本对象。

导入顺序：子文件夹依赖（引用其他副本对象的）最后导？不需要——IDE 符号表在
build 时才解析，导入顺序无所谓。逐个 import_native 到对应子文件夹。

用法：bridge.py eval_file {"path":".../task_import_f04.py"}
输出 ipc/f04_import.log
"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[0])))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
SRC = os.path.join(IPC, u"f04_out")
LOG = os.path.join(IPC, u"f04_import.log")
_lf = io.open(LOG, "w", encoding="utf-8")


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


def kids(o):
    try:
        return list(o.get_children())
    except Exception:
        return []


def mk_folder(parent, name, parent_sv_guid):
    """在 parent 下建名为 name 的 Folder，返回对象。parent_sv_guid = parent 的 SV guid。"""
    for k in kids(parent):
        if unicode(k.get_name()) == name:
            return k
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
        name=name,
        guid=_ug(),
        own_sv_guid=sv_root,
        parent_container_guid=parent_sv_guid,
        path_parts=[u"Device", u"PLC 逻辑", u"Application", u"F04_FB_Verify"],
        sv_root_guid=sv_root,
        parent_guid=parent_sv_guid,
        is_root=True)
    tmp = os.path.join(IPC, u"f04_tmp_folder.native")
    make_gvl.build_export([entry], tmp, sv_root)
    res = parent.import_native(unicode(tmp))
    L(u"  folder %s import: %r" % (name, res))
    for k in kids(parent):
        if unicode(k.get_name()) == name:
            return k
    return None


try:
    app = projects.primary.active_application

    # 1) 顶层 F04_FB_Verify
    top = None
    for o in app.get_children():
        if unicode(o.get_name()) == u"F04_FB_Verify":
            top = o
            break
    if top is None:
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
            name=u"F04_FB_Verify",
            guid=_ug(),
            own_sv_guid=sv_root,
            parent_container_guid=make_gvl.APP_SV_NODE,
            path_parts=[u"Device", u"PLC 逻辑", u"Application"],
            sv_root_guid=sv_root,
            parent_guid=None,
            is_root=True)
        tmp = os.path.join(IPC, u"f04_top.native")
        make_gvl.build_export([entry], tmp, sv_root)
        res = app.import_native(unicode(tmp))
        L(u"top folder import: %r" % (res,))
        for o in app.get_children():
            if unicode(o.get_name()) == u"F04_FB_Verify":
                top = o
                break
    if top is None:
        raise RuntimeError(u"F04_FB_Verify not found")
    # top 的 SV guid（主机侧从导出 native 解析后写进这个文件）
    gf = os.path.join(IPC, u"f04_top_guid.txt")
    if not os.path.exists(gf):
        raise RuntimeError(u"f04_top_guid.txt missing - run task_export_f04_top.py + host-side parse first")
    top_guid = io.open(gf, u"r", encoding=u"utf-8").read().strip()
    L(u"top F04_FB_Verify sv guid = %s" % top_guid)

    # 2) 每个子文件夹 + 其下对象
    total_ok = 0
    total = 0
    for sfn in sorted(os.listdir(SRC)):
        sdp = os.path.join(SRC, sfn)
        if not os.path.isdir(sdp):
            continue
        L(u"[SF] %s" % sfn)
        sub = mk_folder(top, sfn + u"_F04V" if not sfn.endswith(u"_F04V") else sfn, top_guid)
        if sub is None:
            L(u"  FATAL: subfolder %s create failed" % sfn)
            continue
        # 取 sub 的 sv guid（子对象导入不需要——import_native 到 sub 即可）
        for f in sorted(os.listdir(sdp)):
            if not f.endswith(u".native") or f.startswith(u"_"):
                continue
            p = os.path.join(sdp, f)
            total += 1
            try:
                r = sub.import_native(unicode(p))
                L(u"  [ok] %s" % f)
                total_ok += 1
            except Exception, e:
                L(u"  [FAIL] %s: %s" % (f, e))
    L(u"imported %d/%d" % (total_ok, total))

    # 3) 复核树
    def dump(o, ind):
        for k in kids(o):
            L(u"%s- %s" % (ind, unicode(k.get_name())))
            dump(k, ind + u"  ")
    dump(top, u"")
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
print(u"done")
