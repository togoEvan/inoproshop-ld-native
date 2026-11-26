# -*- coding: utf-8 -*-
# @ipy2
"""用 get_messages(cat) 直接 dump 每个分类的全部消息文本（返回的是字符串）。

输出 ipc/msg_text.log
"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
_lf = io.open(os.path.join(IPC, u"msg_text.log"), "w", encoding="utf-8")


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


try:
    for c in system.get_message_categories():
        try:
            desc = unicode(system.get_message_category_description(c))
        except Exception:
            desc = unicode(c)
        msgs = list(system.get_messages(c))
        L(u"=== %s (%s) : %d 条 ===" % (desc, unicode(c), len(msgs)))
        for i, m in enumerate(msgs):
            L(u"  [%d] %s" % (i, unicode(m)))
        L(u"")
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
