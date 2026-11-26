# -*- coding: utf-8 -*-
# @ipy2
"""覆盖式导入：不改名让位，直接 import_native，遇到同名覆盖弹框由主机侧点「全部」。
适用对象：不允许改名的系统对象（如 Task Configuration）。

参数 ipc/import_args.json: {"path": "...", "parent": "Application", "expect": [...]}
"""
import io, os, sys, time, traceback
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base
BASE = _base.resolve_base(); IPC = _base.ensure_ipc(BASE)
LOG = os.path.join(IPC, "import_overwrite.log")
ARGS = os.path.join(IPC, "import_args.json")
_lf = io.open(LOG, "w", encoding="utf-8")
def L(m):
    _lf.write(u"[%s] %s\n" % (time.strftime("%H:%M:%S"), unicode(m))); _lf.flush()

import json
args = json.loads(io.open(ARGS, "r", encoding="utf-8").read())
src = args.get(u"path")
L(u"=== overwrite import ===")
L(u"src = %s" % src)
proj = projects.primary
app = proj.active_application
parent = app
L(u"parent = %s" % parent.get_name())
t0 = time.time()
r = parent.import_native(src)
L(u"import_native -> %r (%.2fs)" % (r, time.time() - t0))
proj.save()
L(u"saved")
L(u"=== done ===")
_lf.close()
