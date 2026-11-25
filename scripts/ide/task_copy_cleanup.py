# -*- coding: utf-8 -*-
"""收尾：删除验证 POU 并把 MainTask 调用列表恢复成只剩 M000_MAIN。

ScriptPouObjectList.remove(name) 会留下 Name="" 的空槽项（编译报「期望标识符」），
所以这里用 replace(idx, "") 置空后，再整体导出 Task Configuration 交给主机侧清理。
本脚本只负责「删 POU + 把列表项清空」。
"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[0])))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
_lf = io.open(os.path.join(IPC, u"copy_cleanup.log"), "w", encoding="utf-8")

POU = u"prg_GvlCopyUse"


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


try:
    proj = projects.primary
    app = proj.active_application

    # 1) 先把 MainTask 里指向它的项清空
    tc = None
    for o in app.get_children():
        if unicode(o.get_name()) == u"Task Configuration":
            tc = o
            break
    for t in tc.get_children():
        names = [unicode(x) for x in t.pous]
        if POU in names:
            idx = names.index(POU)
            t.pous.replace(idx, u"")
            L(u"task %s: cleared index %d -> %r"
              % (unicode(t.get_name()), idx, [unicode(x) for x in t.pous]))
        else:
            L(u"task %s: %r" % (unicode(t.get_name()), names))

    # 2) 删除 POU 对象
    hit = None
    for o in app.get_children():
        if unicode(o.get_name()) == POU:
            hit = o
            break
    if hit is not None:
        hit.remove()
        L(u"deleted %s" % POU)
    else:
        L(u"%s not found" % POU)

    proj.save()
    L(u"saved")
    L(u"children: %s" % u", ".join([unicode(k.get_name()) for k in app.get_children()]))
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
