# -*- coding: utf-8 -*-
# @ipy2
"""A/B 验证 F04 副本 FB：ST POU prg_F04VerifyUse 挂 MainTask 实例化副本 FB。

pos : fbCyl : FB_Cylinder_F04V(...);（引脚接 GVLVerify 变量）+ fbRGY : FB_RGYLamp_F04V(...)
neg : fbCyl.ZZZ_NotExist_Pin := TRUE;（引脚不存在必须报错）

用法：bridge.py eval_file {"path":".../task_f04_ab_test.py"}
模式文件 ipc/f04_ab_mode.txt：pos / neg
输出 ipc/f04_ab_test.log
"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
LOG = os.path.join(IPC, u"f04_ab_test.log")
MODE_FILE = os.path.join(IPC, u"f04_ab_mode.txt")
_lf = io.open(LOG, "w", encoding="utf-8")


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


mode = u"pos"
if os.path.exists(MODE_FILE):
    mode = io.open(MODE_FILE, u"r", encoding=u"utf-8").read().strip() or u"pos"
L(u"mode = %s" % mode)

POU = u"prg_F04VerifyUse"

# 引脚名从原件 FB_Cylinder 声明里确认过：i_stStationControl / io_stHMICylinder /
# o_xUsingTimesAlarm 等；GVL 引用 H_astAlarmRecord_GVLVerify 是真实存在的
DECL = (u"PROGRAM %s\n"
        u"VAR\n"
        u"    fbCyl  : FB_Cylinder_F04V;\n"
        u"    fbRGY  : FB_RGYLamp_F04V;\n"
        u"    stCtrl : Struct_StationControl;\n"
        u"    stCyl  : Struct0_Cylinder_F04V;\n"
        u"    stHMI  : Struct1_HMI_Cylinder_F04V;\n"
        u"    stHMIRe: Struct2_HMI_Persistent_Cylinder_F04V;\n"
        u"    xOut   : BOOL;\n"
        u"END_VAR" % POU)

if mode == u"pos":
    IMPL = (u"fbCyl(i_stStationControl:=stCtrl, io_stCylinder:=stCyl, "
            u"io_stHMICylinder:=stHMI, io_stHMICylinderRe:=stHMIRe);\n"
            u"fbRGY();\n"
            u"xOut := fbCyl.o_xUsingTimesAlarm;")
else:
    IMPL = (u"fbCyl.ZZZ_NotExist_Pin := TRUE;\n"
            u"xOut := fbCyl.ZZZ_NotExist_Pin;")

try:
    proj = projects.primary
    app = proj.active_application

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

    pou.textual_declaration.replace(DECL)
    pou.textual_implementation.replace(IMPL)
    L(u"mode=%s  decl/impl set" % mode)

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
