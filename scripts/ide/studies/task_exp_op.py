# -*- coding: utf-8 -*-
"""只删除 / 只导入一个对象，不做别的（避免异步命令与读消息互相干扰）。

参数 ipc/exp_args.json: {"op": "delete"|"import", "name": "...", "src": "..."}
输出 ipc/exp/<op>_<name>.op.log
"""
import io
import json
import os
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
ARGS = json.loads(io.open(os.path.join(IPC, u"exp_args.json"), "r",
                          encoding="utf-8").read())
OP = unicode(ARGS[u"op"])
NAME = unicode(ARGS.get(u"name") or u"")
SRC = ARGS.get(u"src")
LOG = os.path.join(IPC, u"exp", u"%s_%s.op.log" % (OP, NAME))
_lf = io.open(LOG, "w", encoding="utf-8")


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


def find_child(parent, name):
    for ch in parent.get_children():
        if ch.get_name() == name:
            return ch
    return None


try:
    proj = projects.primary
    app = proj.active_application
    L(u"=== %s %s ===" % (OP, NAME))
    if OP == u"delete":
        obj = find_child(app, NAME)
        if obj is None:
            L(u"NOT FOUND")
        else:
            obj.remove()
            L(u"removed")
    elif OP == u"import":
        r = app.import_native(SRC)
        L(u"import_native -> %r" % (r,))
    else:
        L(u"unknown op")
    proj.save()
    L(u"saved at %s; exists now = %s" % (time.strftime(u"%H:%M:%S"),
                                         find_child(app, NAME) is not None))
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
