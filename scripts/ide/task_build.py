# -*- coding: utf-8 -*-
"""只跑 app.build()，不读消息 —— 与 task_check.py 配对使用。

为什么必须拆成两个脚本（2026-11-26 实测）：

  `app.build()` **会先清空预编译分类，再异步重建**。
  实测：build 返回后立刻读预编译是 **0 条**，约 10s 后才回到 101 条。
  所以「build + 立刻读」必然得到「预编译 0 错误」——**假通过**。
  clear_messages 同理，清掉之后不会自行恢复（空闲 20s 仍是 0 条）。

正确姿势（等待放主机侧，IDE 脚本里绝不 sleep）：

    python bridge.py eval_file '{"path":".../task_build.py"}'
    sleep 12
    python bridge.py eval_file '{"path":".../task_check.py"}'
    cat ipc/check.log

输出 ipc/build.log
"""
import io
import os
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[0])))
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
