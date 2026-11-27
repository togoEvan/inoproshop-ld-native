# -*- coding: utf-8 -*-
# @ipy2
"""只读转储当前消息（不 build）：逐分类统计 severity，并把 Error 级全部列出。

用途：预编译/编译条数 ≥100 时验证消息池是否被截断、Error 是否真的为 0。
输出 ipc/msgdump_now.log
"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
_lf = io.open(os.path.join(IPC, u"msgdump_now.log"), "w", encoding="utf-8")

CAT_PRE = u"217bc73e-759b-4a3c-bfa1-991c938a6541"
CAT_BUILD = u"97f48d64-a2a3-4856-b640-75c046e37ea9"


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


try:
    cats = list(system.get_message_categories())
    for c in cats:
        cid = unicode(c)
        try:
            desc = unicode(system.get_message_category_description(c))
        except Exception:
            desc = u"?"
        objs = list(system.get_message_objects(c))
        sev_count = {}
        errs = []
        for m in objs:
            try:
                sev = unicode(getattr(m, u"severity", u""))
            except Exception:
                sev = u"?"
            sev_count[sev] = sev_count.get(sev, 0) + 1
            if sev.lower().find(u"error") >= 0:
                try:
                    txt = unicode(getattr(m, u"text", u""))
                except Exception:
                    txt = u"?"
                try:
                    objn = unicode(m.object.get_name())
                except Exception:
                    objn = u"-"
                errs.append(u"    [%s] %s | %s" % (sev, objn, txt))
        L(u"--- %s  %s : total=%d %r" % (cid, desc, len(objs), sev_count))
        for e in errs:
            L(e)

    # 精确复查：只用分类 guid 再取一次，确认条数稳定（非异步窗口抖动）
    L(u"\n=== re-read (stability) ===")
    for guid in (CAT_PRE, CAT_BUILD):
        for c in cats:
            if unicode(c) == guid:
                n1 = len(list(system.get_message_objects(c)))
                system.process_messageloop()
                n2 = len(list(system.get_message_objects(c)))
                L(u"  %s : %d -> %d" % (guid, n1, n2))
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
print(u"done")
