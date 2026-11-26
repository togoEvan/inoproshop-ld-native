# -*- coding: utf-8 -*-
"""探测消息接口的严重级别能力：能不能区分 Error / Warning。

输出 ipc/exp/probe_sev.log
"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
LOG = os.path.join(IPC, u"exp", u"probe_sev.log")
_lf = io.open(LOG, "w", encoding="utf-8")


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


CAT_BUILD = u"97f48d64-a2a3-4856-b640-75c046e37ea9"

try:
    c = None
    for x in system.get_message_categories():
        if unicode(x).lower() == CAT_BUILD:
            c = x
            break
    L(u"category = %r" % (c,))

    # 1) get_messages 返回的元素类型
    msgs = list(system.get_messages(c))
    L(u"get_messages -> %d 项, 首项 type=%s repr=%r"
      % (len(msgs), type(msgs[0]).__name__ if msgs else u"-", msgs[0] if msgs else u"-"))
    if msgs:
        t = msgs[0].GetType()
        L(u"  类型全名 = %s" % t.FullName)
        ps = [u"%s:%s" % (unicode(p.Name), unicode(p.PropertyType.Name))
              for p in t.GetProperties()]
        L(u"  props = %s" % u", ".join(ps))
        ms = []
        for m in t.GetMethods():
            n = unicode(m.Name)
            if n not in ms and not n.startswith(u"get_") and not n.startswith(u"set_"):
                ms.append(n)
        L(u"  methods = %s" % u", ".join(ms))

    # 2) get_message_objects 的元素类型与属性实值
    objs = list(system.get_message_objects(c))
    L(u"get_message_objects -> %d 项" % len(objs))
    if objs:
        o = objs[0]
        t = o.GetType()
        L(u"  类型全名 = %s" % t.FullName)
        for p in t.GetProperties():
            try:
                v = p.GetValue(o, None)
                L(u"  %s = %r" % (unicode(p.Name), v))
            except Exception, e:
                L(u"  %s -> ERR %s" % (unicode(p.Name), e))

    # 3) 找 summary 行
    L(u"=== 含「错误」的行 ===")
    for i, m in enumerate(msgs):
        s = unicode(m)
        if u"错误" in s:
            L(u"  [%d] %s" % (i, s))
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
