# -*- coding: utf-8 -*-
# @ipy2
"""F21 A/B 验证：证明 F21_POU_Station0_总控_Verify 下的副本确实在预编译/编译作用域内。

pos : 调用 STN1_00_Main_F21V()，应 0 错误
neg : 故意写未定义 POU ZZZ_NoSuchPou_F21V()，必须报错
      否则说明该文件夹根本没被编译，0 错误是假通过

模式文件 ipc/f21_ab_mode.txt：pos / neg / cleanup
输出 ipc/f21_ab_test.log
"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
LOG = os.path.join(IPC, u"f21_ab_test.log")
MODE_FILE = os.path.join(IPC, u"f21_ab_mode.txt")
_lf = io.open(LOG, "w", encoding="utf-8")

POU = u"prg_F21VerifyUse"


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


mode = u"pos"
if os.path.exists(MODE_FILE):
    mode = io.open(MODE_FILE, u"r", encoding=u"utf-8").read().strip() or u"pos"
L(u"mode = %s" % mode)

DECL = (u"PROGRAM %s\n"
        u"VAR\n"
        u"    xOut : BOOL;\n"
        u"END_VAR" % POU)

if mode == u"pos":
    IMPL = u"STN1_00_Main_F21V();\nxOut := TRUE;"
elif mode == u"neg":
    IMPL = u"ZZZ_NoSuchPou_F21V();\nxOut := TRUE;"
else:
    IMPL = u"xOut := FALSE;"

try:
    app = projects.primary.active_application

    if mode == u"cleanup":
        tc = None
        for o in app.get_children():
            if unicode(o.get_name()) == u"Task Configuration":
                tc = o
                break
        if tc is not None:
            for t in tc.get_children():
                pl = t.pous
                if POU in [unicode(x) for x in pl]:
                    pl.remove(POU)
                    L(u"removed %s from task %s" % (POU, unicode(t.get_name())))
                L(u"task %s pous: %s" % (unicode(t.get_name()),
                                         u", ".join([unicode(x) for x in pl])))
        victim = None
        for o in app.get_children():
            if unicode(o.get_name()) == POU:
                victim = o
                break
        if victim is not None:
            victim.remove()
            L(u"removed %s" % POU)
        else:
            L(u"%s not present" % POU)
    else:
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
