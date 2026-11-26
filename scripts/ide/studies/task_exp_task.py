# -*- coding: utf-8 -*-
# @ipy2
"""把 POU 挂进 / 摘出 MainTask 的调用列表。

参数 ipc/exp_args.json: {"op": "add"|"remove", "task": "MainTask", "pou": "..."}
输出 ipc/exp/<op>_<pou>.task.log
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
ARGS = json.loads(io.open(os.path.join(IPC, u"exp_args.json"), "r",
                          encoding="utf-8").read())
OP = unicode(ARGS[u"op"])
TASK = unicode(ARGS.get(u"task") or u"MainTask")
POU = unicode(ARGS[u"pou"])
LOG = os.path.join(IPC, u"exp", u"%s_%s.task.log" % (OP, POU))
_lf = io.open(LOG, "w", encoding="utf-8")


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


try:
    app = projects.primary.active_application
    taskcfg = None
    for ch in app.get_children():
        if ch.get_name() == u"Task Configuration":
            taskcfg = ch
            break
    L(u"taskcfg = %s" % (taskcfg.get_name() if taskcfg else u"NONE"))
    task = None
    for t in taskcfg.get_children():
        if t.get_name() == TASK:
            task = t
            break
    L(u"task = %s" % (task.get_name() if task else u"NONE"))
    L(u"before pous = %s" % unicode(list(task.pous)))

    if OP == u"add":
        task.pous.add(POU)
        L(u"added %s" % POU)
    else:
        # remove 会留空槽，这里只用于实验，稍后用导出 Task Config 修复
        try:
            task.pous.remove(POU)
            L(u"remove(name) 调用返回")
        except Exception, e:
            L(u"remove(name) 异常: %s" % e)

    L(u"after pous = %s" % unicode(list(task.pous)))
    projects.primary.save()
    L(u"saved")
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
