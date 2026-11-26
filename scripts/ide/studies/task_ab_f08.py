# -*- coding: utf-8 -*-
# @ipy2
"""F08 轴组 A/B 验证。

轴组在 ST 里通过 PAXES_GROUP_REF 引用（实测 M010_插补控制 的写法）：
    io_stAxesGroup : PAXES_GROUP_REF;
    io_stAxesGroup := AxesGroup_A1;

pos : stGroup := AxesGroup_A1_F08V;        （副本轴组名可见）
neg : stGroup := ZZZ_NoSuchGroup_F08V;     （不存在必须报错）

模式文件 ipc/f08_ab_mode.txt：pos / neg / clean
输出 ipc/f08_ab.log
"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
LOG = os.path.join(IPC, u"f08_ab.log")
MODE_FILE = os.path.join(IPC, u"f08_ab_mode.txt")
_lf = io.open(LOG, "w", encoding="utf-8")


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


mode = u"pos"
if os.path.exists(MODE_FILE):
    mode = io.open(MODE_FILE, u"r", encoding=u"utf-8").read().strip() or u"pos"
L(u"mode = %s" % mode)

POU = u"prg_F08VerifyUse"

DECL = (u"PROGRAM %s\n"
        u"VAR\n"
        u"    stGroup : PAXES_GROUP_REF;\n"
        u"    xUsed   : BOOL;\n"
        u"END_VAR" % POU)

if mode == u"pos":
    IMPL = (u"stGroup := AxesGroup_A1_F08V;\n"
            u"xUsed := TRUE;")
elif mode == u"neg":
    IMPL = (u"stGroup := ZZZ_NoSuchGroup_F08V;\n"
            u"xUsed := TRUE;")
else:
    IMPL = u"xUsed := FALSE;"


def get_task_plist(app, task_name=u"MainTask"):
    tc = None
    for o in app.get_children():
        if unicode(o.get_name()) == u"Task Configuration":
            tc = o
            break
    if tc is None:
        return None
    for k in tc.get_children():
        if unicode(k.get_name()) == task_name:
            return k.pous
    return None


# ⚠ 轴组必须在「轴所在的那个任务」里被引用，否则报
#   「轴组 xxx 与所选轴所在任务不同: 不能再在任务 yyy 中被引用」
#   本工程的轴挂在 EthercatTask 下（F10_POU_EthercatTask），所以挂这里
TASK_NAME = u"ETHERCAT"


try:
    proj = projects.primary
    app = proj.active_application

    pou = None
    for o in app.get_children():
        if unicode(o.get_name()) == POU:
            pou = o
            break

    if mode == u"clean":
        for tn in (u"MainTask", u"ETHERCAT"):
            _p = get_task_plist(app, tn)
            if _p is not None:
                _cur = [unicode(x) for x in _p]
                if POU in _cur:
                    try:
                        _p.remove(POU)
                        L(u"removed from %s" % tn)
                    except Exception, _e:
                        L(u"task %s remove failed: %s" % (tn, _e))
                L(u"%s pous: %s" % (tn, [unicode(x) for x in _p]))
        pl = None
        if pl is not None:
            cur = [unicode(x) for x in pl]
            if POU in cur:
                try:
                    pl.remove(POU)
                    L(u"removed from task")
                except Exception, e:
                    L(u"task remove failed: %s" % e)
            L(u"%s pous: %s" % (TASK_NAME, [unicode(x) for x in pl]))
        if pou is not None:
            try:
                pou.remove()
                L(u"removed %s" % POU)
            except Exception, e:
                L(u"remove failed: %s" % e)
        else:
            L(u"%s not found" % POU)
    else:
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
        L(u"decl/impl set")

        # 先确保只挂在目标任务上（同一 POU 挂两个任务会冲突）
        for tn in (u"MainTask", u"ETHERCAT"):
            _p = get_task_plist(app, tn)
            if _p is None:
                continue
            _cur = [unicode(x) for x in _p]
            if tn != TASK_NAME and POU in _cur:
                try:
                    _p.remove(POU)
                    L(u"removed from %s (keep only %s)" % (tn, TASK_NAME))
                except Exception, _e:
                    L(u"%s remove failed: %s" % (tn, _e))

        pl = get_task_plist(app, TASK_NAME)
        if pl is not None:
            cur = [unicode(x) for x in pl]
            L(u"%s pous before: %s" % (TASK_NAME, cur))
            if POU not in cur:
                pl.add(POU)
                L(u"added %s" % POU)
            L(u"%s pous after: %s" % (TASK_NAME, [unicode(x) for x in pl]))

        proj.save()
        L(u"saved")
        L(u"--- IMPL ---")
        L(IMPL)
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
print(u"done")
