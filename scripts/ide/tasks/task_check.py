# -*- coding: utf-8 -*-
"""验收：只读两个分类的消息并统计 Error / Warning，单次快照，绝不阻塞 IDE。

- 不编译、不清消息、不 sleep、不轮询（IDE 脚本跑主线程，sleep 冻死界面）
- severity 是 .NET 枚举：getattr 读不到，必须反射
  `m.GetType().GetProperty('severity').GetValue(m, None)`
- 两个分类作用域不同，缺一不可：预编译 217bc73e 覆盖 Application 全部 POU；
  编译 97f48d64 只含挂进任务调用列表的 POU
- 读不到分类/消息必须抛错，绝不返回空列表当 0 错误（假通过）

用法（等待放主机侧）：task_build.py → 主机侧 sleep 12 → 本脚本 → 看 ipc/check.log
"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
_lf = io.open(os.path.join(IPC, "check.log"), "w", encoding="utf-8")


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


CAT_PRE = u"217bc73e-759b-4a3c-bfa1-991c938a6541"
CAT_BUILD = u"97f48d64-a2a3-4856-b640-75c046e37ea9"


def prop(obj, name):
    """反射读 .NET 属性（getattr 对 ScriptMessage 不可靠）。"""
    try:
        p = obj.GetType().GetProperty(name)
        if p is not None:
            return p.GetValue(obj, None)
    except Exception:
        pass
    try:
        return getattr(obj, name)
    except Exception:
        return None


try:
    proj = projects.primary
    app = proj.active_application
    L(u"BASE = %s (source: %s)" % (BASE, _base.SOURCE))
    L(u"app  = %r" % unicode(app.get_name()))

    # 只处理一次待办消息，绝不循环、绝不 sleep
    system.process_messageloop()

    # ═══ 动态枚举全部消息分类 ═══
    # GUID 集合因版本/配置而异，枚举运行时暴露的每一个分类；
    # 名称用 get_message_category_description() 动态取，名称才是稳定语义。
    cats = {}
    for c in list(system.get_message_categories()):
        cats[unicode(c)] = c
    if not cats:
        raise RuntimeError(u"get_message_categories() 返回空，不得当作 0 错误")

    def cat_name(c):
        try:
            d = unicode(system.get_message_category_description(c))
            if d:
                return d
        except Exception:
            pass
        return u"?"

    L(u"=== 消息分类清单（共 %d 个）===" % len(cats))
    cat_desc = {}
    for guid in sorted(cats.keys()):
        nm = cat_name(cats[guid])
        cat_desc[guid] = nm
        L(u"  %s  %s" % (guid, nm))

    def sev_of(m):
        """取 severity 枚举名（Text / Error / Warning ...）。"""
        v = prop(m, u"severity")
        if v is None:
            return u""
        s = unicode(v)
        if u"." in s:
            s = s.rsplit(u".", 1)[-1]
        return s

    def dump(guid, label):
        c = cats.get(guid)
        if c is None:
            raise RuntimeError(u"消息分类 %s(%s) 不存在，不得当作 0 错误" % (label, guid))
        objs = list(system.get_message_objects(c))
        ne = nw = 0
        shown_err = shown_warn = 0
        for m in objs:
            sev = sev_of(m)
            low = sev.lower()
            txt = prop(m, u"text")
            txt = unicode(txt) if txt is not None else u""
            if low == u"error":
                ne += 1
                # Error 全打印（这是验收要看的）
                L(u"  [Error] %s" % txt)
            elif low == u"warning":
                nw += 1
                # Warning 只打前 10 条，避免刷屏
                if shown_warn < 10:
                    L(u"  [Warning] %s" % txt)
                    shown_warn += 1
        if nw > shown_warn:
            L(u"  ... 另有 %d 条 Warning 未列出（模板自带，非本次新增）" % (nw - shown_warn))
        # ⚠ IDE 消息池有 100 条上限（lead 交叉验证发现）：溢出时会在分类里
        #   塞「多于100个消息发生：跳过更多的消息信息」占位条目 ——
        #   total≥100 即视为可能被截断，Error 计数可能低估，绝不静默通过。
        truncated = len(objs) >= 100
        if truncated:
            L(u"  ⚠ total=%d ≥100，消息池可能被截断，Error 计数可能低估 —— 不可单独作为通过依据" % len(objs))
        L(u"=== %s : total=%d errors=%d warnings=%d%s ===" % (
            label, len(objs), ne, nw, u" [TRUNCATED]" if truncated else u""))
        return len(objs), ne, nw

    pre_total, pre_err, pre_warn = dump(CAT_PRE, cat_desc.get(CAT_PRE) or u"预编译")
    bld_total, bld_err, bld_warn = dump(CAT_BUILD, cat_desc.get(CAT_BUILD) or u"编译")

    # 其余分类：存在才读，只报 Error
    other_err = 0
    for guid in sorted(cats.keys()):
        if guid in (CAT_PRE, CAT_BUILD):
            continue
        label = cat_desc.get(guid) or u"?"
        try:
            objs = list(system.get_message_objects(cats[guid]))
        except Exception, e:
            L(u"=== %s %s : 读取失败 %s（忽略） ===" % (label, guid, e))
            continue
        ne = 0
        for m in objs:
            if sev_of(m).lower() == u"error":
                ne += 1
                txt = prop(m, u"text")
                L(u"  [Error] %s | %s" % (label, unicode(txt) if txt else u""))
        if ne:
            L(u"=== %s : errors=%d ===" % (label, ne))
        other_err += ne

    total_err = pre_err + bld_err + other_err
    total_warn = pre_warn + bld_warn
    # 任一分类 total≥100 即整体标记：Error 可能被 100 条上限截断而低估
    truncated = (pre_total >= 100) or (bld_total >= 100)

    L(u"=== 验收结论 : %s (预编译 %d + 编译 %d + 其它 %d = 合计 %d 错误, %d 警告)%s ===" % (
        u"通过" if total_err == 0 else u"不通过",
        pre_err, bld_err, other_err, total_err, total_warn,
        u" ⚠ 消息池≥100 可能截断，结果存疑" if truncated else u""))

    if pre_total == 0 and bld_total > 0:
        L(u"⚠ 预编译 0 条而编译有消息，疑似撞上 build 后的异步重建窗口，请等 10s 后重跑本脚本")
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))
finally:
    _lf.close()
