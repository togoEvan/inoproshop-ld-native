# -*- coding: utf-8 -*-
"""执行「检查程序」(预编译)，读取预编译分类的真实错误。"""
import io, os, time, traceback
import os
BASE = os.environ.get("PLC_MCP_BASE") or "D:/plc_mcp"
_lf = io.open(os.path.join(BASE,"ipc","check.log"), "w", encoding="utf-8")
def L(m):
    _lf.write(u"%s\n" % unicode(m)); _lf.flush()
CAT_PRE = u"217bc73e-759b-4a3c-bfa1-991c938a6541"
CAT_BUILD = u"97f48d64-a2a3-4856-b640-75c046e37ea9"
try:
    proj = projects.primary
    app = proj.active_application
    try:
        import System
        system.clear_messages(System.Guid.Empty)
    except Exception, e:
        L(u"clear FAIL %s" % e)

    cmds = list(system.commands)
    chk = None
    for c in cmds:
        try:
            if unicode(c.name) == u"检查程序":
                chk = c; break
        except Exception: pass
    L(u"found 检查程序: %r" % chk)
    t0=time.time()
    chk.execute()
    system.process_messageloop()
    time.sleep(0.8)
    system.process_messageloop()
    L(u"check %.2fs" % (time.time()-t0))

    for label, cat in ((u"预编译", CAT_PRE), (u"编译", CAT_BUILD)):
        objs = list(system.get_message_objects(cat))
        nerr = sum(1 for m in objs if 'err' in unicode(getattr(m,'severity',u'')).lower())
        L(u"=== %s : total=%d errors=%d ===" % (label, len(objs), nerr))
        for m in objs:
            sev = unicode(getattr(m, 'severity', u''))
            txt = u""
            for a in ("text","message"):
                try:
                    v=getattr(m,a)
                    if v: txt=unicode(v); break
                except Exception: pass
            L(u"  [%s] %s" % (sev, txt))
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))
finally:
    _lf.close()
