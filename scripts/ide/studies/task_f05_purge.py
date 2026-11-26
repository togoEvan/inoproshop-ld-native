# -*- coding: utf-8 -*-
"""删除 F05_FC_Verify 整个顶层文件夹（含全部子对象）+ 删除 prg_F05VerifyUse。
输出 ipc/f05_purge.log
"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
_lf = io.open(os.path.join(IPC, u"f05_purge.log"), "w", encoding="utf-8")


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


try:
    proj = projects.primary
    app = proj.active_application

    # 1) 摘任务槽里的测试 POU
    POU = u"prg_F05VerifyUse"
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
            if POU in names:
                t.pous.replace(names.index(POU), u"")
                L(u"cleared task slot of %s" % POU)

    # 2) 删测试 POU
    for o in app.get_children():
        if unicode(o.get_name()) == POU:
            o.remove()
            L(u"deleted %s" % POU)
            break

    # 3) 删 F05_FC_Verify 整文件夹
    for o in app.get_children():
        if unicode(o.get_name()) == u"F05_FC_Verify":
            o.remove()
            L(u"deleted F05_FC_Verify")
            break

    proj.save()
    L(u"saved")
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
print(u"done")
