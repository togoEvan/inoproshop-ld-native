# -*- coding: utf-8 -*-
"""F07 CAM A/B 验证。

CAM 对象在 ST 里通过「类型化引用」使用：`MC_CamIn` 的 CamTable 引脚类型是
`MC_CAM_REF`（或直接写 CAM 名做初始化）。最稳的正样本是**用 CAM 名做赋值/
类型引用**，负样本用不存在的 CAM 名。

pos : xRef := Cam0_F07V;               （CAM 名可见）
neg : xRef := ZZZ_NoSuchCam_F07V;      （不存在必须报错）

模式文件 ipc/f07_ab_mode.txt：pos / neg
输出 ipc/f07_ab_test.log
"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[0])))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
LOG = os.path.join(IPC, u"f07_ab_test.log")
MODE_FILE = os.path.join(IPC, u"f07_ab_mode.txt")
_lf = io.open(LOG, "w", encoding="utf-8")


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


mode = u"pos"
if os.path.exists(MODE_FILE):
    mode = io.open(MODE_FILE, u"r", encoding=u"utf-8").read().strip() or u"pos"
L(u"mode = %s" % mode)

POU = u"prg_F07VerifyUse"

DECL = (u"PROGRAM %s\n"
        u"VAR\n"
        u"    refCam : MC_CAM_REF;\n"
        u"END_VAR" % POU)

if mode == u"pos":
    # 把 CAM 名赋给 MC_CAM_REF 变量：能通过即证明副本 CAM 名可见且类型正确
    IMPL = (u"refCam := Cam0_F07V;")
else:
    IMPL = (u"refCam := ZZZ_NoSuchCam_F07V;")

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
    L(u"mode=%s decl/impl set" % mode)

    tc = None
    for o in app.get_children():
        if unicode(o.get_name()) == u"Task Configuration":
            tc = o
            break
    main_task = None
    for k in tc.get_children():
        if unicode(k.get_name()) == u"MainTask":
            main_task = k
            break
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
