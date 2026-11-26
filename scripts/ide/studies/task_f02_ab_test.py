# -*- coding: utf-8 -*-
"""A/B 验证副本 Struct：建 ST POU prg_StructVerifyUse 挂进 MainTask，两种实现切换。

模式（exp_args.json 不用，直接参数化文件 f02_ab_mode.txt：pos / neg）：
  pos : stClock : Struct_Clock_StructVerify;  xOut := stClock.xBlink_1Hz_StructVerify;
        stUWB : UN_WORD_BYTE_StructVerify; stUWB.w字_StructVerify := 16#00FF;
  neg : xOut := stClock.ZZZ_NotExist_Member;（成员不存在，必须报错）

用法：bridge.py eval_file {"path":".../task_f02_ab_test.py"}
输出：ipc/f02_ab_test.log
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
LOG = os.path.join(IPC, u"f02_ab_test.log")
MODE_FILE = os.path.join(IPC, u"f02_ab_mode.txt")
_lf = io.open(LOG, u"w", encoding=u"utf-8")


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


mode = u"pos"
if os.path.exists(MODE_FILE):
    mode = io.open(MODE_FILE, u"r", encoding=u"utf-8").read().strip() or u"pos"
L(u"mode = %s" % mode)

POU = u"prg_StructVerifyUse"

DECL = (u"PROGRAM %s\n"
        u"VAR\n"
        u"    stClock : Struct_Clock_StructVerify;\n"
        u"    stUWB   : UN_WORD_BYTE_StructVerify;\n"
        u"    xOut    : BOOL;\n"
        u"    wOut    : WORD;\n"
        u"END_VAR" % POU)

if mode == u"pos":
    IMPL = (u"stClock.xBlink_1Hz_StructVerify := TRUE;\n"
            u"xOut := stClock.xBlink_1Hz_StructVerify;\n"
            u"stUWB.w字_StructVerify := 16#00FF;\n"
            u"wOut := stUWB.w字_StructVerify;")
else:
    IMPL = (u"stClock.ZZZ_NotExist_Member := TRUE;\n"
            u"xOut := stClock.ZZZ_NotExist_Member;")

try:
    proj = projects.primary
    app = proj.active_application

    # 1) 建 / 更新 POU（已验证写法：app.create_pou + PouType.Program）
    pou = None
    for o in app.get_children():
        if unicode(o.get_name()) == POU:
            pou = o
            break
    if pou is None:
        import System
        ptype = None
        for a in System.AppDomain.CurrentDomain.GetAssemblies():
            try:
                for t in a.GetTypes():
                    if unicode(t.FullName) == u"_3S.CoDeSys.ScriptEngine.BasicFunctionality.PouType":
                        ptype = System.Enum.Parse(t, u"Program")
                        break
            except Exception:
                pass
            if ptype is not None:
                break
        if ptype is None:
            raise RuntimeError(u"PouType enum not found")
        pou = app.create_pou(POU, ptype, None, u"", u"", u"")
        L(u"created %s" % POU)
    else:
        L(u"reuse existing %s" % POU)

    # 2) 写声明 + 实现（已验证写法：.replace() 而非 .text 赋值）
    pou.textual_declaration.replace(DECL)
    pou.textual_implementation.replace(IMPL)
    L(u"mode=%s  decl/impl set" % mode)

    # 3) 挂进 MainTask
    tc = None
    for o in app.get_children():
        if unicode(o.get_name()) == u"Task Configuration":
            tc = o
            break
    if tc is None:
        raise RuntimeError(u"Task Configuration not found")
    main_task = None
    for k in tc.get_children():
        if unicode(k.get_name()) == u"MainTask":
            main_task = k
            break
    if main_task is None:
        raise RuntimeError(u"MainTask not found")
    pl = main_task.pous
    cur = [unicode(x) for x in pl]
    L(u"MainTask pous before: %s" % (cur,))
    if POU not in cur:
        pl.add(POU)
        L(u"added %s" % POU)
    L(u"MainTask pous after: %s" % [unicode(x) for x in pl])
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
print(u"done")
