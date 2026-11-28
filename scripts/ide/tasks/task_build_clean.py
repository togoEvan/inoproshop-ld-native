# -*- coding: utf-8 -*-
# @ipy2
"""干净验收：先 clear_messages(预编译/编译/导出导入) → build() → 退出，让主机侧等待后读。

为什么必须清：
  `app.build()` 是**增量**编译。第二次 build 时若无改动，预编译分类
  不会产生新消息，而编译分类还留着上一轮的条目 —— 直接读会看到
  「预编译 0 / 编译 104」，把**陈旧消息当成本轮结果**（假通过）。
  2026-11-27 F20 实测踩到：连跑三次都是 预编译 0 + 编译 104。
  另外静默导入会往「导出/导入」分类里加消息，分类总数变多后
  task_check 会因消息池截断判 UNKNOWN（trunc-msg=1），所以这一类也要清。

安全闸门（不打扰用户）：
  只有隐藏实例（PLC_MCP_HIDDEN=1，hidden_launch.py 自动设置）或显式
  PLC_MCP_ALLOW_CLEAR=1 才清。在用户正开着的 IDE 里清消息会抹掉他的
  消息面板，属于打扰 —— 那种情况只做 build，不清。

⚠ clear_messages 必须传分类参数（无参报 takes exactly 1 argument）。
⚠ 不在 IDE 里 sleep —— 等待放主机侧。

输出 ipc/build_clean.log
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
_lf = io.open(os.path.join(IPC, u"build_clean.log"), "w", encoding="utf-8")

CAT_PRE = u"217bc73e-759b-4a3c-bfa1-991c938a6541"
CAT_BUILD = u"97f48d64-a2a3-4856-b640-75c046e37ea9"
CAT_IO = u"2af7707f-6167-4a76-a40e-430967be0f18"   # 导出/导入


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


try:
    proj = projects.primary
    app = proj.active_application
    cats = {}
    for c in list(system.get_message_categories()):
        cats[unicode(c)] = c

    hidden = os.environ.get("PLC_MCP_HIDDEN") == "1"
    allow = os.environ.get("PLC_MCP_ALLOW_CLEAR") == "1"
    L(u"hidden=%s allow_clear=%s" % (hidden, allow))
    if hidden or allow:
        L(u"=== clear categories ===")
        for guid in (CAT_PRE, CAT_BUILD, CAT_IO):
            c = cats.get(guid)
            if c is None:
                L(u"  %s missing" % guid)
                continue
            try:
                system.clear_messages(c)
                L(u"  cleared %s" % guid)
            except Exception, e:
                L(u"  clear FAIL %s: %s" % (guid, e))
    else:
        L(u"SKIP clear: 不是隐藏实例（会抹掉用户消息面板）。"
          u"要强制清请设 PLC_MCP_ALLOW_CLEAR=1")

    L(u"=== build at %s ===" % time.strftime(u"%H:%M:%S"))
    t0 = time.time()
    r = app.build()
    L(u"build() -> %r in %.2fs" % (r, time.time() - t0))
    L(u"主机侧等 10s 后跑 task_check.py")
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
print(u"done")
