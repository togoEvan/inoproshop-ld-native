# -*- coding: utf-8 -*-
# @ipy2
"""只调用 app.build()，不读消息。

输出 ipc/exp/<note>.build.log
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
NOTE = unicode(ARGS.get(u"note") or u"build")
LOG = os.path.join(IPC, u"exp", NOTE + u".build.log")
_lf = io.open(LOG, "w", encoding="utf-8")


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


try:
    L(u"=== app.build() at %s ===" % time.strftime(u"%H:%M:%S"))
    t0 = time.time()
    r = projects.primary.active_application.build()
    L(u"build() -> %r in %.2fs" % (r, time.time() - t0))
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
