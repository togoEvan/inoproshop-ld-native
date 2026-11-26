# -*- coding: utf-8 -*-
"""只跑 app.build()，不读消息 —— 与 task_check.py 配对使用。

app.build() 会先清空预编译分类再异步重建（build 后立刻读是 0 条，约 10s
后恢复），所以「build + 立刻读」是假通过；等待必须放主机侧：
    task_build.py → 主机侧 sleep 12 → task_check.py → 看 ipc/check.log
输出 ipc/build.log
"""
import io
import os
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
_lf = io.open(os.path.join(IPC, "build.log"), "w", encoding="utf-8")


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


try:
    app = projects.primary.active_application
    L(u"=== app.build() at %s ===" % time.strftime(u"%H:%M:%S"))
    t0 = time.time()
    r = app.build()
    L(u"build() -> %r in %.2fs" % (r, time.time() - t0))
    L(u"⚠ 预编译分类已被清空并异步重建，请主机侧等 ≥10s 后再跑 task_check.py")
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
