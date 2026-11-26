# -*- coding: utf-8 -*-
# @ipy2
"""交叉验证：新建一个 ST POU，代码里直接引用 GVL 里的全局变量。

若 GVL 真的全局生效，编译不会报「没有定义标识符」；否则必报未定义。
PouType 是 CLR 枚举，必须用反射拿真值（传字符串/数字都不行）。

输出 ipc/gvl_cross_check.log
"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
_lf = io.open(os.path.join(IPC, u"gvl_cross_check.log"), "w", encoding="utf-8")

POU = u"prg_GvlVerifyUse"

DECL = u"""PROGRAM %s
VAR
\txOut\t: BOOL;
\tiOut\t: INT;
\tuiOut\t: UINT;
\trOut\t: REAL;
END_VAR
""" % POU

BODY = u"""// 交叉验证：全部来自 F99_GVLVerify 里的 GVL
xOut  := Gv_xEnable;
iOut  := Gv_iCount + 1;
uiOut := Gv_uiSpeed + Gc_uiVerifyNum;
rOut  := Gv_rTemp;
"""


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


def pou_type(name):
    import System
    for a in System.AppDomain.CurrentDomain.GetAssemblies():
        try:
            for t in a.GetTypes():
                if unicode(t.FullName) == u"_3S.CoDeSys.ScriptEngine.BasicFunctionality.PouType":
                    return System.Enum.Parse(t, name)
        except Exception:
            pass
    raise RuntimeError(u"PouType enum not found")


try:
    proj = projects.primary
    app = proj.active_application

    for o in app.get_children():
        if unicode(o.get_name()) == POU:
            o.remove()
            L(u"removed existing %s" % POU)
            break

    pt = pou_type(u"Program")
    L(u"PouType.Program = %r" % pt)

    pou = app.create_pou(POU, pt, None, u"", u"", u"")
    L(u"created: %r" % unicode(pou.get_name()))
    pou.textual_declaration.replace(DECL)
    pou.textual_implementation.replace(BODY)
    L(u"decl %d chars, body %d chars" % (len(DECL), len(BODY)))

    try:
        L(u"readback body has Gv_xEnable: %s"
          % (u"Gv_xEnable" in unicode(pou.textual_implementation.text)))
    except Exception, e:
        L(u"readback err %s" % e)

    proj.save()
    L(u"saved")
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
