# -*- coding: utf-8 -*-
"""建 F05_FC_Verify 顶层文件夹 + 9 个 SF 子文件夹，导入 58 个副本对象。

导入顺序：子文件夹依赖（引用其他副本对象的）最后导？不需要——IDE 符号表在
build 时才解析，导入顺序无所谓。逐个 import_native 到对应子文件夹。

用法：bridge.py eval_file {"path":".../task_import_f04.py"}
输出 ipc/f05_import.log
"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
SRC = os.path.join(IPC, u"f05_out")
LOG = os.path.join(IPC, u"f05_import.log")
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
        path_parts=[u"Device", u"PLC 逻辑", u"Application", u"F05_FC_Verify"],
        sv_root_guid=sv_root,
        parent_guid=parent_sv_guid,
        is_root=True)
    tmp = os.path.join(IPC, u"f05_tmp_folder.native")
    make_gvl.build_export([entry], tmp, sv_root)
    res = parent.import_native(unicode(tmp))
    L(u"  folder %s import: %r" % (name, res))
    for k in kids(parent):
        if unicode(k.get_name()) == name:
            return k
    return None


try:
    app = projects.primary.active_application

    # 1) 顶层 F05_FC_Verify
    top = None
    for o in app.get_children():
        if unicode(o.get_name()) == u"F05_FC_Verify":
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
            name=u"F05_FC_Verify",
            guid=_ug(),
            own_sv_guid=sv_root,
            parent_container_guid=make_gvl.APP_SV_NODE,
            path_parts=[u"Device", u"PLC 逻辑", u"Application"],
            sv_root_guid=sv_root,
            parent_guid=None,
            is_root=True)
        tmp = os.path.join(IPC, u"f05_top.native")
        make_gvl.build_export([entry], tmp, sv_root)
        res = app.import_native(unicode(tmp))
        L(u"top folder import: %r" % (res,))
        for o in app.get_children():
            if unicode(o.get_name()) == u"F05_FC_Verify":
                top = o
                break
    if top is None:
        raise RuntimeError(u"F05_FC_Verify not found")
    # top 的 SV guid（主机侧从导出 native 解析后写进这个文件）
    gf = os.path.join(IPC, u"f05_top_guid.txt")
    if not os.path.exists(gf):
        raise RuntimeError(u"f05_top_guid.txt missing - run task_export_f05_top.py + host-side parse first")
    top_guid = io.open(gf, u"r", encoding=u"utf-8").read().strip()
    L(u"top F05_FC_Verify sv guid = %s" % top_guid)

    # 2) 每个子文件夹 + 其下对象
    total_ok = 0
    total = 0
    for sfn in sorted(os.listdir(SRC)):
        sdp = os.path.join(SRC, sfn)
        if not os.path.isdir(sdp):
            continue
        # ⚠ 只对真正含 .native 的目录建子文件夹。
        # 根下直接 POU 在导出阶段会生成同名空目录，误建会产生空文件夹。
        natives = [x for x in sorted(os.listdir(sdp))
                   if x.endswith(u".native") and not x.startswith(u"_")]
        if not natives:
            L(u"[SKIP] empty dir (no .native): %s" % sfn)
            continue
        L(u"[SF] %s (%d objects)" % (sfn, len(natives)))
        sub = mk_folder(top, sfn + u"_F05V" if not sfn.endswith(u"_F05V") else sfn, top_guid)
        if sub is None:
            L(u"  FATAL: subfolder %s create failed" % sfn)
            continue
        for f in natives:
            p = os.path.join(sdp, f)
            total += 1
            try:
                r = sub.import_native(unicode(p))
                L(u"  [ok] %s" % f)
                total_ok += 1
            except Exception, e:
                L(u"  [FAIL] %s: %s" % (f, e))
    # ---- F05 特有：根下直接 POU（清单由主机侧预生成，IDE 内不解析 XML）----
    rp = os.path.join(IPC, u"f05_root_pous.txt")
    if os.path.exists(rp):
        for ln in io.open(rp, u"r", encoding=u"utf-8").read().splitlines():
            ln = ln.strip()
            if not ln:
                continue
            p = os.path.join(SRC, ln)
            if not os.path.exists(p):
                L(u"  [MISS] (root) %s" % ln)
                continue
            total += 1
            try:
                r = top.import_native(unicode(p))
                L(u"  [ok] (root) %s" % ln)
                total_ok += 1
            except Exception, e:
                L(u"  [FAIL] (root) %s: %s" % (ln, e))
    else:
        L(u"  WARN: f05_root_pous.txt missing")

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
