# -*- coding: utf-8 -*-
"""把某个文件夹下的子对象（GVL）批量改名，统一加后缀。

参数 ipc/rename_children_args.json:
    {"parent": "F01_Variable_GVLVerify", "suffix": "_GVLVerify", "map": {"旧名": "新名", ...}}

map 可选：给了就按 map 精确改；没给就一律 名字+suffix。
输出 ipc/rename_children.log
"""
import io
import json
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
_lf = io.open(os.path.join(IPC, u"rename_children.log"), "w", encoding="utf-8")
ARGS = json.loads(io.open(os.path.join(IPC, u"rename_children_args.json"), "r",
                          encoding="utf-8").read())

PARENT = unicode(ARGS.get(u"parent"))
SUFFIX = unicode(ARGS.get(u"suffix") or u"")
MAP = ARGS.get(u"map") or {}


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


try:
    proj = projects.primary
    app = proj.active_application
    L(u"parent=%s  suffix=%r  map=%r" % (PARENT, SUFFIX, MAP))

    folder = None
    for o in app.get_children():
        if unicode(o.get_name()) == PARENT:
            folder = o
            break
    if folder is None:
        raise RuntimeError(u"%s not found under Application" % PARENT)

    L(u"children before: %s"
      % u", ".join([unicode(k.get_name()) for k in folder.get_children()]))

    # 两阶段改名：先改成临时名，避免 A->B 与 B 已存在冲突
    plan = []
    for k in folder.get_children():
        old = unicode(k.get_name())
        if old in MAP:
            new = unicode(MAP[old])
        elif SUFFIX and not old.endswith(SUFFIX):
            new = old + SUFFIX
        else:
            new = old
        plan.append((k, old, new))

    for k, old, new in plan:
        if old != new:
            tmp = u"__tmp__%s" % old
            k.rename(tmp)
            L(u"stage1 %s -> %s" % (old, tmp))
    for k, old, new in plan:
        if old != new:
            tmp = u"__tmp__%s" % old
            k.rename(new)
            L(u"stage2 %s -> %s" % (tmp, new))

    L(u"children after: %s"
      % u", ".join([unicode(k.get_name()) for k in folder.get_children()]))

    proj.save()
    L(u"saved")
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
