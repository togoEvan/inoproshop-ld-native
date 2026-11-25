# -*- coding: utf-8 -*-
"""不清空，直接读当前 5 个分类的所有消息。"""
import io, os, sys, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[0])))
import _base
BASE = _base.resolve_base()
_lf = io.open(os.path.join(_base.ensure_ipc(BASE), "readnow.log"), "w", encoding="utf-8")
def L(m):
    _lf.write(u"%s\n" % unicode(m)); _lf.flush()
L(u"BASE = %s (source: %s)" % (BASE, _base.SOURCE))
try:
    system.process_messageloop()
    for ci, c in enumerate(list(system.get_message_categories())):
        try:
            desc = unicode(system.get_message_category_description(c))
        except Exception:
            desc = u"?"
        objs = list(system.get_message_objects(c))
        L(u"=== [%d] %s (%s) count=%d ===" % (ci, desc, unicode(c), len(objs)))
        for m in objs:
            sev = unicode(getattr(m,'severity',u''))
            txt=u""
            for a in ("text","message"):
                try:
                    v=getattr(m,a)
                    if v: txt=unicode(v); break
                except Exception: pass
            objn=u""
            try: objn=unicode(m.object.get_name())
            except Exception: pass
            pos=u""
            try: pos=unicode(m.position)
            except Exception: pass
            L(u"   [%s] %s | obj=%s pos=%s" % (sev, txt, objn, pos))
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))
finally:
    _lf.close()
