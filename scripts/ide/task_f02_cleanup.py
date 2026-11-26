# -*- coding: utf-8 -*-
"""收尾：删除 prg_StructVerifyUse（任务列表已通过覆盖导入复位，不再动 pous）。

输出 ipc/f02_cleanup.log
"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[0])))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
_lf = io.open(os.path.join(IPC, u"f02_cleanup.log"), "w", encoding="utf-8")

POU = u"prg_StructVerifyUse"


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


try:
    proj = projects.primary
    app = proj.active_application

    # 1) 保险：若任务列表里还有，先清掉（replace 置空即可，随后覆盖导入已复位过）
    tc = None
    for o in app.get_children():
        if unicode(o.get_name()) == u"Task Configuration":
            tc = o
            break
    if tc is not None:
        for t in tc.get_children():
            try:
                names = [unicode(x) for x in t.pous]
            except Exception:
                continue
            L(u"task %s: %r" % (unicode(t.get_name()), names))
            if POU in names:
                t.pous.replace(names.index(POU), u"")
                L(u"  cleared slot -> %r" % [unicode(x) for x in t.pous])

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
        L(u"%s not found (already removed)" % POU)

    # 3) 保存工程
    proj.save()
    L(u"saved")

    # 4) 复核
    for o in app.get_children():
        if unicode(o.get_name()) == POU:
            L(u"WARN: %s still exists!" % POU)
    L(u"=== done ===")
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

_lf.close()
print(u"done")
