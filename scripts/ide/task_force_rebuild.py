# -*- coding: utf-8 -*-
"""强制重编译：app.clean() + app.rebuild()，然后全量 dump 消息。
⚠ 不 clear_messages 之前的分类？这里必须 clear 才能区分「本次重编译」的结果，
   但已知 clear 后预编译分类不会再重算 —— 本轮目的是验证「坏类型会不会被报」，
   所以先 dump 旧消息到 old，再 clear，再 clean+rebuild，再 dump 新消息。
"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[0])))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
_lf = io.open(os.path.join(IPC, u"force_rebuild.log"), "w", encoding="utf-8")


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


def dump_all(tag):
    cats = list(system.get_message_categories())
    L(u"### %s : categories=%d" % (tag, len(cats)))
    for c in cats:
        try:
            desc = unicode(system.get_message_category_description(c))
        except Exception:
            desc = u"?"
        objs = list(system.get_message_objects(c))
        L(u"--- %s %s : %d" % (unicode(c), desc, len(objs)))
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


try:
    proj = projects.primary
    app = proj.active_application

    try:
        system.clear_messages(None)
        L(u"messages cleared")
    except Exception, e:
        L(u"clear err %s" % e)

    try:
        app.clean()
        L(u"clean ok")
    except Exception, e:
        L(u"clean ERR %s" % unicode(e)[:200])

    try:
        app.rebuild()
        L(u"rebuild ok")
    except Exception, e:
        L(u"rebuild ERR %s" % unicode(e)[:200])

    system.process_messageloop()
    dump_all(u"after clean+rebuild")
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
