# -*- coding: utf-8 -*-
"""全量消息转储：build 之后把所有分类里的每条消息（不论级别）都写出来，
用于排查「错误为什么没被报告」。

输出 ipc/allmsg_dump.log
"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
_lf = io.open(os.path.join(IPC, u"allmsg_dump.log"), "w", encoding="utf-8")


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


try:
    proj = projects.primary
    app = proj.active_application

    L(u"=== build ===")
    app.build()
    L(u"=== build done ===")
    system.process_messageloop()

    cats = list(system.get_message_categories())
    L(u"categories: %d" % len(cats))
    for c in cats:
        try:
            desc = unicode(system.get_message_category_description(c))
        except Exception:
            desc = u"?"
        objs = list(system.get_message_objects(c))
        L(u"--- %s  %s : %d ---" % (unicode(c), desc, len(objs)))
        for m in objs:
            try:
                sev = unicode(getattr(m, u"severity", u""))
            except Exception:
                sev = u"?"
            try:
                txt = unicode(getattr(m, u"text", u""))
            except Exception:
                txt = u"?"
            try:
                objn = unicode(m.object.get_name())
            except Exception:
                objn = u"-"
            L(u"  [%s] %s | %s" % (sev, objn, txt))
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
