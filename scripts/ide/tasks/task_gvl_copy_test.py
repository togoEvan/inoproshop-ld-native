# -*- coding: utf-8 -*-
"""验证副本 GVL 的「带后缀全局变量」是否真的可用（挂 MainTask 才参与编译）。

正样本引用 PLC_Constant_GVLVerify / HMI_Alarm_GVLVerify 里的变量；
负样本引用不存在的后缀变量，用来证明链路不是假通过。

参数 ipc/gvl_copy_args.json: {"mode": "positive"|"negative"}
输出 ipc/gvl_copy_test.log
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
_lf = io.open(os.path.join(IPC, u"gvl_copy_test.log"), "w", encoding="utf-8")
ARGS = json.loads(io.open(os.path.join(IPC, u"gvl_copy_args.json"), "r",
                          encoding="utf-8").read())
MODE = unicode(ARGS.get(u"mode") or u"positive")

POU = u"prg_GvlCopyUse"

DECL = u"""PROGRAM %s
VAR
\tuiOut\t: UINT;
\tuiOut2\t: UINT;
\trOut\t: REAL;
END_VAR
""" % POU

BODY_OK = u"""// 正样本：引用 F01_Variable_GVLVerify 里带后缀的全局变量
uiOut  := Gc_uiETCAxisNum_GVLVerify;
uiOut2 := Gc_uiCylinderNum_GVLVerify;
rOut   := 1.0 * Gc_uiStationNum_GVLVerify + Gc_uiVirAxisNum_GVLVerify;
"""

BODY_BAD = u"""// 负样本：引用一个不存在的带后缀变量
uiOut  := Gc_uiETCAxisNum_NOTEXIST;
uiOut2 := 0;
rOut   := 0.0;
"""


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


def dump_all(tag):
    cats = list(system.get_message_categories())
    L(u"### %s" % tag)
    total = 0
    for c in cats:
        try:
            desc = unicode(system.get_message_category_description(c))
        except Exception:
            desc = u"?"
        objs = list(system.get_message_objects(c))
        errs = []
        for m in objs:
            try:
                sev = unicode(getattr(m, u"severity", u""))
            except Exception:
                sev = u"?"
            if u"err" in sev.lower():
                try:
                    objn = unicode(m.object.get_name())
                except Exception:
                    objn = u"-"
                errs.append(u"  [%s] %s | %s"
                            % (sev, objn, unicode(getattr(m, u"text", u""))))
        total += len(errs)
        L(u"--- %s : total=%d errors=%d" % (desc, len(objs), len(errs)))
        for e in errs:
            L(e)
    L(u"### TOTAL ERRORS = %d" % total)
    return total


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

    pou = None
    for o in app.get_children():
        if unicode(o.get_name()) == POU:
            pou = o
            break
    if pou is None:
        pou = app.create_pou(POU, pou_type(u"Program"), None, u"", u"", u"")
        L(u"created %s" % POU)
    pou.textual_declaration.replace(DECL)
    pou.textual_implementation.replace(BODY_OK if MODE == u"positive" else BODY_BAD)
    L(u"mode=%s body set" % MODE)

    tc = None
    for o in app.get_children():
        if unicode(o.get_name()) == u"Task Configuration":
            tc = o
            break
    mt = None
    for t in tc.get_children():
        if unicode(t.get_name()) == u"MainTask":
            mt = t
            break
    cur = [unicode(x) for x in mt.pous]
    L(u"MainTask before: %r" % (cur,))
    if POU not in cur:
        mt.pous.add(POU)
        L(u"added to MainTask")
    L(u"MainTask after: %r" % ([unicode(x) for x in mt.pous],))

    proj.save()
    L(u"saved")
    L(u"=== build ===")
    app.build()
    system.process_messageloop()
    dump_all(u"after build")
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
