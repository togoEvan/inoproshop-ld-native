# -*- coding: utf-8 -*-
"""按名字删除 Application 下的对象（清理验证用负样本 POU）。

参数：ipc/import_args.json 里的 "names" 列表。
日志：ipc/delete_objects.log
"""
import json
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[0])))
from _base import resolve_base

BASE = resolve_base()
IPC = os.path.join(BASE, "ipc")
ARGS = os.path.join(IPC, "import_args.json")
LOG = os.path.join(IPC, "delete_objects.log")


def L(msg):
    f = open(LOG, "a")
    try:
        f.write(msg + "\n")
    finally:
        f.close()


def main():
    f = open(ARGS)
    try:
        args = json.load(f)
    finally:
        f.close()
    names = args.get("names") or []
    app = projects.primary.active_application  # noqa: F821
    L(u"=== delete objects ===")
    L(u"app = %s" % app.get_name())
    for name in names:
        obj = None
        for ch in app.get_children():
            if ch.get_name() == name:
                obj = ch
                break
        if obj is None:
            L(u"  NOT FOUND: %s" % name)
            continue
        try:
            obj.remove()
            L(u"  removed: %s" % name)
        except Exception, e:
            L(u"  FAILED: %s -> %s" % (name, e))
    L(u"children after: %s" % u", ".join([k.get_name() for k in app.get_children()]))
    projects.primary.save()  # noqa: F821
    L(u"=== done ===")


try:
    main()
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))
