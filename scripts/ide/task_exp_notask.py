# -*- coding: utf-8 -*-
"""实验：未挂任务的 POU 到底被哪些操作检查？

阶段由 ipc/exp_args.json 的 "stage" 决定：
  del_check   : 删除 prg_NoTaskTest -> 执行「检查程序」-> dump 消息
  add_check   : 重新导入 prg_NoTaskTest（不挂任务）-> 执行「检查程序」-> dump 消息
  add_build   : （不删不改）直接 app.build() -> dump 消息

输出 ipc/exp/<stage>.log
"""
import io
import json
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[0])))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
ARGS = json.loads(io.open(os.path.join(IPC, u"exp_args.json"), "r",
                          encoding="utf-8").read())
STAGE = unicode(ARGS[u"stage"])
POU = unicode(ARGS.get(u"pou") or u"prg_NoTaskTest")
SRC = ARGS.get(u"src")

LOG = os.path.join(IPC, u"exp", STAGE + u".log")
_lf = io.open(LOG, "w", encoding="utf-8")


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


def attr(obj, name):
    try:
        return unicode(getattr(obj, name))
    except Exception:
        pass
    try:
        p = obj.GetType().GetProperty(name)
        if p is not None:
            return unicode(p.GetValue(obj, None))
    except Exception:
        pass
    return u""


def dump_msgs(tag):
    for c in system.get_message_categories():
        try:
            desc = unicode(system.get_message_category_description(c))
        except Exception:
            desc = unicode(c)
        msgs = list(system.get_messages(c))
        L(u"--- [%s] %s : %d 条 ---" % (tag, desc, len(msgs)))
        zzz = 0
        for m in msgs:
            s = unicode(m)
            if u"ZZZ" in s:
                zzz += 1
                L(u"    ZZZ> %s" % s)
        L(u"    (ZZZ 命中 %d)" % zzz)


def run_cmd(guid):
    for c in system.commands:
        if attr(c, u"guid").strip().lower() == guid:
            L(u"execute %s (%s)" % (attr(c, u"name"), guid))
            c.execute()
            return True
    L(u"command not found: %s" % guid)
    return False


CHECK_PROGRAM = u"ab02b3c3-a0b0-405c-9841-987504c7088d"


def find_child(parent, name):
    for ch in parent.get_children():
        if ch.get_name() == name:
            return ch
    return None


try:
    proj = projects.primary
    app = proj.active_application
    L(u"=== stage %s ===" % STAGE)
    L(u"app = %s" % app.get_name())

    if STAGE == u"del_check":
        obj = find_child(app, POU)
        if obj is None:
            L(u"NOT FOUND: %s" % POU)
        else:
            obj.remove()
            L(u"removed %s" % POU)
        proj.save()
        L(u"saved; exists now = %s" % (find_child(app, POU) is not None))
        run_cmd(CHECK_PROGRAM)
        dump_msgs(u"after check (POU 已删除)")

    elif STAGE == u"add_check":
        L(u"before import exists = %s" % (find_child(app, POU) is not None))
        r = app.import_native(SRC)
        L(u"import_native -> %r" % (r,))
        proj.save()
        L(u"after import exists = %s" % (find_child(app, POU) is not None))
        run_cmd(CHECK_PROGRAM)
        dump_msgs(u"after check (POU 已导入未挂任务)")

    elif STAGE == u"add_build":
        L(u"exists = %s" % (find_child(app, POU) is not None))
        t0 = __import__(u"time").time()
        app.build()
        L(u"build() done in %.2fs" % (__import__(u"time").time() - t0))
        dump_msgs(u"after app.build()")

    else:
        L(u"unknown stage")

except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
