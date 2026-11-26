# -*- coding: utf-8 -*-
"""探测：当前 IDE 打开了哪些编辑器/文档，以及「检查程序」的作用域。

输出 ipc/exp/probe_editor.log
"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
LOG = os.path.join(IPC, u"exp", u"probe_editor.log")
_lf = io.open(LOG, "w", encoding="utf-8")


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


def dump_methods(obj, tag):
    try:
        t = obj.GetType()
        L(u"[%s] type = %s" % (tag, t.FullName))
        names = []
        for m in t.GetMethods():
            n = unicode(m.Name)
            if n not in names:
                names.append(n)
        L(u"  methods: %s" % u", ".join(names))
        pnames = []
        for p in t.GetProperties():
            pnames.append(u"%s:%s" % (unicode(p.Name), unicode(p.PropertyType.Name)))
        L(u"  props: %s" % u", ".join(pnames))
    except Exception, e:
        L(u"[%s] reflect failed: %s" % (tag, e))


try:
    L(u"=== system members ===")
    dump_methods(system, u"system")

    L(u"")
    L(u"=== try open editors ===")
    for expr in (u"system.get_editors()", u"system.editors",
                 u"projects.primary.active_application.get_children()"):
        try:
            v = eval(expr)
            L(u"%s -> %r" % (expr, v))
        except Exception, e:
            L(u"%s -> ERR %s" % (expr, e))

    L(u"")
    L(u"=== active_application children names ===")
    app = projects.primary.active_application
    for ch in app.get_children():
        L(u"  child: %s" % ch.get_name())

except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
