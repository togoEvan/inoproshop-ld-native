# -*- coding: utf-8 -*-
# @ipy2
"""清掉「导出/导入」分类里的残留消息。

场景：导出 native 时因目标文件已存在、主机侧点了「否」，
会在 2af7707f 分类留下一条 "文件...已经存在" 的 Error 记录。
它不是 PLC 代码错误，但会污染验收报告，需清除。

输出 ipc/clear_io_cat.log
"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
_lf = io.open(os.path.join(IPC, u"clear_io_cat.log"), "w", encoding="utf-8")

CAT_IO = u"2af7707f-6167-4a76-a40e-430967be0f18"


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


try:
    for c in list(system.get_message_categories()):
        if unicode(c) == CAT_IO:
            before = len(list(system.get_message_objects(c)))
            system.clear_messages(c)
            after = len(list(system.get_message_objects(c)))
            L(u"导出/导入 分类: %d -> %d" % (before, after))
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
print(u"done")
