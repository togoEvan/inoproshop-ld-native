# -*- coding: utf-8 -*-
"""GVL 全局变量验证（正确版）：建 POU + 挂进 MainTask 调用列表 + build + dump。

⚠ 关键教训：**没挂到任务调用列表的 POU 不参与编译**，build 恒 0 错误，
  前面的验证全是假通过。必须 task.pous.add() 之后才真的被编译。

参数从 ipc/gvl_task_args.json 读：
    {"mode": "positive"|"negative", "pou": "prg_GvlVerifyUse"}

输出 ipc/gvl_task_test.log
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
_lf = io.open(os.path.join(IPC, u"gvl_task_test.log"), "w", encoding="utf-8")
ARGS = json.loads(io.open(os.path.join(IPC, u"gvl_task_args.json"), "r",
                          encoding="utf-8").read())

POU = unicode(ARGS.get(u"pou") or u"prg_GvlVerifyUse")
MODE = unicode(ARGS.get(u"mode") or u"positive")

DECL = u"""PROGRAM %s
VAR
\txOut\t: BOOL;
\tiOut\t: INT;
\tuiOut\t: UINT;
\trOut\t: REAL;
END_VAR
""" % POU

BODY_OK = u"""// 正样本：全部引用 F99_GVLVerify 里的全局变量
xOut  := Gv_xEnable;
iOut  := Gv_iCount + 1;
uiOut := Gv_uiSpeed + Gc_uiVerifyNum;
rOut  := Gv_rTemp;
"""

BODY_BAD = u"""// 负样本：故意引用不存在的标识符
xOut := Gv_NotExist_ZZZ;
iOut := 0;
uiOut := 0;
rOut := 0.0;
"""


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


def dump_all(tag):
    cats = list(system.get_message_categories())
    L(u"### %s : categories=%d" % (tag, len(cats)))
    ne = 0
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
                try:
                    txt = unicode(getattr(m, u"text", u""))
                except Exception:
                    txt = u"?"
                errs.append(u"  [%s] %s | %s" % (sev, objn, txt))
        ne += len(errs)
        L(u"--- %s %s : total=%d errors=%d" % (unicode(c), desc, len(objs), len(errs)))
        for e in errs:
            L(e)
    return ne


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

    # 1) 建 / 更新 POU
    pou = None
    for o in app.get_children():
        if unicode(o.get_name()) == POU:
            pou = o
            break
    if pou is None:
        pou = app.create_pou(POU, pou_type(u"Program"), None, u"", u"", u"")
        L(u"created %s" % POU)
    else:
        L(u"reuse existing %s" % POU)
    pou.textual_declaration.replace(DECL)
    pou.textual_implementation.replace(BODY_OK if MODE == u"positive" else BODY_BAD)
    L(u"mode=%s  body set" % MODE)

    # 2) 挂进 MainTask 调用列表（关键！否则不参与编译）
    tc = None
    for o in app.get_children():
        if unicode(o.get_name()) == u"Task Configuration":
            tc = o
            break
    main_task = None
    for t in tc.get_children():
        if unicode(t.get_name()) == u"MainTask":
            main_task = t
            break
    existing = [unicode(x) for x in main_task.pous]
    L(u"MainTask pous before: %s" % u", ".join(existing))
    if POU not in existing:
        main_task.pous.add(POU)
        L(u"added %s to MainTask" % POU)
    else:
        L(u"%s already in MainTask" % POU)
    L(u"MainTask pous after: %s" % u", ".join([unicode(x) for x in main_task.pous]))

    proj.save()
    L(u"saved")

    # 3) build + dump（一次，不 sleep）
    L(u"=== build ===")
    app.build()
    system.process_messageloop()
    ne = dump_all(u"after build")
    L(u"### TOTAL ERRORS = %d" % ne)
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
