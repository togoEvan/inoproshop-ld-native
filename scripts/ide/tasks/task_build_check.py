# -*- coding: utf-8 -*-
"""构建一次（不 clear_messages），让编译分类出现；然后读双分类。

⚠ 不在 IDE 里 sleep/轮询（会冻死界面）。只做一次 build + 一次读快照。
"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
_lf = io.open(os.path.join(IPC, "build_check.log"), "w", encoding="utf-8")


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


CAT_PRE = u"217bc73e-759b-4a3c-bfa1-991c938a6541"
CAT_BUILD = u"97f48d64-a2a3-4856-b640-75c046e37ea9"

try:
    proj = projects.primary
    app = proj.active_application
    L(u"app = %r" % unicode(app.get_name()))

    L(u"=== build start ===")
    app.build()
    L(u"=== build done ===")

    system.process_messageloop()

    cats = {}
    for c in list(system.get_message_categories()):
        cats[unicode(c)] = c
    L(u"=== categories (%d) ===" % len(cats))
    for guid in sorted(cats.keys()):
        try:
            d = unicode(system.get_message_category_description(cats[guid]))
        except Exception:
            d = u"?"
        L(u"  %s  %s" % (guid, d))

    def read(guid):
        c = cats.get(guid)
        if c is None:
            return None
        return list(system.get_message_objects(c))

    for guid, label in ((CAT_PRE, u"预编译"), (CAT_BUILD, u"编译")):
        objs = read(guid)
        if objs is None:
            L(u"=== %s(%s) : 分类不存在 ===" % (label, guid))
            continue
        ne = nw = 0
        L(u"=== %s : total=%d ===" % (label, len(objs)))
        for m in objs:
            sev = u""
            txt = u""
            obj = u""
            try:
                sev = unicode(getattr(m, "severity", u""))
            except Exception:
                pass
            for a in ("text", "message"):
                try:
                    v = getattr(m, a)
                    if v:
                        txt = unicode(v)
                        break
                except Exception:
                    pass
            try:
                obj = unicode(m.object.get_name())
            except Exception:
                pass
            low = sev.lower()
            if "err" in low:
                ne += 1
                L(u"  [%s] %s | %s" % (sev, obj, txt))
            elif "warn" in low:
                nw += 1
        L(u"  -> %s errors=%d warnings=%d" % (label, ne, nw))
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))
finally:
    _lf.close()
