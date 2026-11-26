# -*- coding: utf-8 -*-
# @ipy2
"""把 F99_GVLVerify 重命名为 F01_Variable_GVLVerify（在软件工程里直接改名）。

rename 只改名字，guid 不变，其它 POU 对其中 GVL 变量的引用不受影响。

参数 ipc/rename_args.json: {"old": "...", "new": "..."}
输出 ipc/rename_folder.log
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
_lf = io.open(os.path.join(IPC, u"rename_folder.log"), "w", encoding="utf-8")
ARGS = json.loads(io.open(os.path.join(IPC, u"rename_args.json"), "r",
                          encoding="utf-8").read())

OLD = unicode(ARGS.get(u"old"))
NEW = unicode(ARGS.get(u"new"))


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


try:
    proj = projects.primary
    app = proj.active_application
    L(u"old=%s  new=%s" % (OLD, NEW))

    target = None
    for o in app.get_children():
        if unicode(o.get_name()) == OLD:
            target = o
            break
    if target is None:
        # 也许已经改过了
        for o in app.get_children():
            if unicode(o.get_name()) == NEW:
                L(u"already renamed: %s exists" % NEW)
                L(u"=== done ===")
                _lf.close()
                sys.exit(0)
        raise RuntimeError(u"%s not found under Application" % OLD)

    L(u"children of %s before: %s"
      % (OLD, u", ".join([unicode(k.get_name()) for k in target.get_children()])))
    target.rename(NEW)
    L(u"renamed -> %s" % unicode(target.get_name()))

    L(u"children after: %s"
      % u", ".join([unicode(k.get_name()) for k in target.get_children()]))

    proj.save()
    L(u"saved")
    L(u"Application children: %s"
      % u", ".join([unicode(k.get_name()) for k in app.get_children()]))
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
