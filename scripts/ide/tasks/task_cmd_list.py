# -*- coding: utf-8 -*-
"""枚举 system.commands（GetEnumerator 返回 ScriptCommand 对象），反射取 guid/name/description。

输出 ipc/cmd_list.log
"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
_lf = io.open(os.path.join(IPC, u"cmd_list.log"), "w", encoding="utf-8")

KEYS = (u"build", u"compile", u"generate", u"check", u"rebuild", u"clean",
        u"analy", u"verify", u"\u4e0b\u8f7d", u"\u7f16\u8bd1", u"\u751f\u6210",
        u"\u68c0\u67e5", u"\u91cd\u5efa", u"\u6e05\u7406", u"\u91cd\u7f6e")


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


def attr(obj, name):
    try:
        v = getattr(obj, name)
        return unicode(v)
    except Exception:
        pass
    try:
        p = obj.GetType().GetProperty(name)
        if p is not None:
            return unicode(p.GetValue(obj, None))
    except Exception:
        pass
    return u""


try:
    cmds = system.commands
    L(u"命令总数 = %d" % len(cmds))
    hits = []
    n = 0
    for c in cmds:
        n += 1
        g = attr(c, u"guid")
        nm = attr(c, u"name")
        desc = attr(c, u"description")
        line = u"[%d] %s | %s | %s" % (n, g, nm, desc)
        L(line)
        blob = nm + desc
        low = blob.lower()
        if any(k in low for k in KEYS) or any(k in blob for k in KEYS):
            hits.append(line)
    L(u"")
    L(u"=== 编译/构建类命令 (%d / %d) ===" % (len(hits), n))
    for h in hits:
        L(u"  %s" % h)
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
