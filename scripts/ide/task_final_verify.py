# -*- coding: utf-8 -*-
"""复核：MainTask 调用列表是否真的摘掉了验证 POU；再 build 一次看最终错误数。"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[0])))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
_lf = io.open(os.path.join(IPC, u"final_verify.log"), "w", encoding="utf-8")


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


try:
    proj = projects.primary
    app = proj.active_application

    tc = None
    for o in app.get_children():
        if unicode(o.get_name()) == u"Task Configuration":
            tc = o
            break
    for t in tc.get_children():
        L(u"task %s pous: %s" % (unicode(t.get_name()),
                                 u", ".join([unicode(x) for x in t.pous])))

    L(u"app children: %s" % u", ".join([unicode(k.get_name()) for k in app.get_children()]))

    L(u"=== build ===")
    app.build()
    system.process_messageloop()

    cats = list(system.get_message_categories())
    total_err = 0
    for c in cats:
        try:
            desc = unicode(system.get_message_category_description(c))
        except Exception:
            desc = u"?"
        objs = list(system.get_message_objects(c))
        errs = []
        for m in objs:
            try:
                sev = unicode(getattr(m, u"severity", u""))
            except Exception:
                sev = u"?"
            if u"err" in sev.lower():
                try:
                    objn = unicode(m.object.get_name())
                except Exception:
                    objn = u"-"
                errs.append(u"  [%s] %s | %s"
                            % (sev, objn, unicode(getattr(m, u"text", u""))))
        total_err += len(errs)
        L(u"--- %s : total=%d errors=%d" % (desc, len(objs), len(errs)))
        for e in errs:
            L(e)
    L(u"### TOTAL ERRORS = %d" % total_err)
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
