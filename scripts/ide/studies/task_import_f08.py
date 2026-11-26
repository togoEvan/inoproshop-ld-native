# -*- coding: utf-8 -*-
"""建 F08_AxisGroup_Verify 顶层文件夹并导入轴组副本。

分两步（顶层 Folder 的 SV guid 必须在主机侧解析）：
  1) 无 ipc/f08_top_guid.txt 时：只建顶层 Folder，然后退出
  2) 有 guid 后：导入 ipc/f08_out 下的全部 native

⚠ AxesGroup 导入后 IDE 会重建内部 4 个 POU（ReadInputs/WriteOutputs/Init/gvl），
   guid 被改写为新值 —— 这是预期行为，不是错误。

输出 ipc/f08_import.log
"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
SRC = os.path.join(IPC, u"f08_out")
TOPNAME = u"F08_AxisGroup_Verify"
LOG = os.path.join(IPC, u"f08_import.log")
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


def ug():
    import uuid as _uuid
    try:
        return unicode(_uuid.uuid4())
    except NameError:
        return str(_uuid.uuid4())


try:
    sys.path.insert(0, os.path.join(BASE, u"scripts", u"examples"))
    import make_gvl

    proj = projects.primary
    app = proj.active_application

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
        tmp = os.path.join(IPC, u"f08_top.native")
        make_gvl.build_export([entry], tmp, sv_root)
        res = app.import_native(unicode(tmp))
        L(u"top folder import: %r" % (res,))
        for o in kids(app):
            if nm(o) == TOPNAME:
                top = o
                break
    if top is None:
        raise RuntimeError(u"%s create failed" % TOPNAME)

    gf = os.path.join(IPC, u"f08_top_guid.txt")
    if not os.path.exists(gf):
        L(u"STEP1 done: top folder created, need host-side guid parse")
        L(u"=== done ===")
        _lf.close()
        print(u"done")
        sys.exit(0)

    L(u"top guid = %s" % io.open(gf, u"r", encoding=u"utf-8").read().strip())

    total = 0
    ok = 0
    if os.path.isdir(SRC):
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

    L(u"--- tree ---")
    for k in kids(top):
        try:
            g = unicode(k.guid)
        except Exception:
            g = u"?"
        L(u"  - %s (guid=%s)" % (nm(k), g))
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
print(u"done")
