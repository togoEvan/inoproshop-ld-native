# -*- coding: utf-8 -*-
"""验收检查：预编译(217bc73e) + 构建(97f48d64) 两个分类都要读。

为什么两个都要读（2026-11-25 实测教训）：
  预编译 0 错误 **不等于** 能构建。单条件 rung 的顶层 AND 只有 1 个输入槽时，
  预编译分类是 0 错误，构建分类却报 N 条 `'AND'需要至少'2' 个操作数`。
  只跑「检查程序」不调用 build() 的验收流程会漏掉这类错误。
"""
import io, os, sys, time, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[0])))
import _base
BASE = _base.resolve_base()
_lf = io.open(os.path.join(_base.ensure_ipc(BASE), "check.log"), "w", encoding="utf-8")


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


L(u"BASE = %s (source: %s)" % (BASE, _base.SOURCE))
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
                chk = c
                break
        except Exception:
            pass
    L(u"found 检查程序: %r" % chk)
    t0 = time.time()
    chk.execute()
    system.process_messageloop()
    time.sleep(0.8)
    system.process_messageloop()
    L(u"check %.2fs" % (time.time() - t0))

    # 再跑一次构建：预编译 0 不代表能构建（单条件 rung 的 AND 元数错误只在构建分类出现）
    t1 = time.time()
    try:
        app.build()
        system.process_messageloop()
        time.sleep(0.5)
        system.process_messageloop()
        L(u"build %.2fs" % (time.time() - t1))
    except Exception, e:
        L(u"build FAIL %s" % e)

    # get_message_objects 需要「分类对象」而不能传字符串/GUID。
    # 枚举所有分类，按 GUID 匹配到目标分类后再取消息对象。
    # ⚠ 铁律：匹配不到 / 取不到消息必须抛错，绝不能静默返回空列表。
    #   教训（2026-11-25）：旧版这里是 `except Exception: continue` + `return []`，
    #   预编译实际有 48 条 Error，脚本却输出 total=0 并判「验收通过」——假通过。
    #   验收脚本宁可崩，也不能把「读不到」当成「没错误」。
    cats = list(system.get_message_categories())
    L(u"categories: %d" % len(cats))
    for c in cats:
        L(u"  cat %s" % unicode(c))

    def _objs_by_guid(guid):
        for c in cats:
            if unicode(c) == guid:
                try:
                    return list(system.get_message_objects(c))
                except Exception, e:
                    raise RuntimeError(u"get_message_objects(%s) 失败: %s" % (guid, e))
        raise RuntimeError(u"消息分类 %s 未找到，不得当作 0 错误" % guid)

    total_err = 0
    for label, cat in ((u"预编译", CAT_PRE), (u"编译", CAT_BUILD)):
        objs = _objs_by_guid(cat)
        nerr = sum(1 for m in objs if 'err' in unicode(getattr(m, 'severity', u'')).lower())
        total_err += nerr
        L(u"=== %s : total=%d errors=%d ===" % (label, len(objs), nerr))
        for m in objs:
            sev = unicode(getattr(m, 'severity', u''))
            txt = u""
            for a in ("text", "message"):
                try:
                    v = getattr(m, a)
                    if v:
                        txt = unicode(v)
                        break
                except Exception:
                    pass
            L(u"  [%s] %s" % (sev, txt))

    L(u"=== 验收结论 : %s (预编译+编译合计 %d 错误) ===" % (
        u"通过" if total_err == 0 else u"不通过", total_err))
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))
finally:
    _lf.close()
