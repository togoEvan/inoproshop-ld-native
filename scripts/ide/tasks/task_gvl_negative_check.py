# -*- coding: utf-8 -*-
"""负样本对照：把 prg_GvlVerifyUse 的 body 改成一个必然未定义的标识符，
用来证明「预编译 0 错误」不是假通过（链路真的会报未定义）。

跑完立刻 task_check.py 读快照，预期出现
    [Error] prg_GvlVerifyUse | 没有定义标识符'Gv_NotExist_ZZZ'
然后再跑 task_gvl_cross_check.py 恢复正样本。
"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
_lf = io.open(os.path.join(IPC, u"gvl_negative_check.log"), "w", encoding="utf-8")

POU = u"prg_GvlVerifyUse"

BODY = u"""// 负样本：故意引用不存在的标识符
xOut := Gv_NotExist_ZZZ;
iOut := 0;
uiOut := 0;
rOut := 0.0;
"""


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


try:
    proj = projects.primary
    app = proj.active_application
    pou = None
    for o in app.get_children():
        if unicode(o.get_name()) == POU:
            pou = o
            break
    if pou is None:
        raise RuntimeError(u"%s not found" % POU)
    pou.textual_implementation.replace(BODY)
    L(u"body replaced with negative sample (%d chars)" % len(BODY))
    proj.save()
    L(u"saved")
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
