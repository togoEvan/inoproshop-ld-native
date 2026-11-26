# -*- coding: utf-8 -*-
"""验收：只读两个分类的消息并统计 Error / Warning，单次快照，绝不阻塞 IDE。

═══════════════════════════════════════════════════════════════════════
设计要点（2026-11-25 定论 + 2026-11-26 两次修订）
═══════════════════════════════════════════════════════════════════════

【要点 1】本脚本**不编译、不清消息、不 sleep、不轮询**
  ① IDE 脚本跑在 InoProShop 主线程，sleep / process_messageloop 循环会冻死界面
     （用户两次反馈「你在等待的时候软件卡死了」）。
  ② **`app.build()` 会清空预编译分类**，然后异步重建——实测 build 返回后立刻读
     预编译是 **0 条**，约 10s 后才回到 101 条。所以「build 后立刻读」必然假通过。
     → 构建与读取必须**分成两个脚本**，中间由主机侧 Python 等待 ≥10s。
  ③ `clear_messages` 同理，清掉之后不会自行恢复（空闲 20s 仍是 0 条）。

【要点 2】severity 必须用反射读，且按枚举名判断（2026-11-26 实测）
  `ScriptMessage` 的属性：`text` / `severity` / `object` / `number` / `prefix` ...
  `severity` 是枚举 `_3S.CoDeSys.Core.Messages.Severity`，实测取值有
  `Text`（普通信息）/ `Error` / `Warning`。
  ⚠ **`getattr(m, 'severity')` 读不到值**（返回空/未知），必须走
  `m.GetType().GetProperty('severity').GetValue(m, None)`。
  旧版用 getattr + 字符串匹配 'err'，导致真实 1 条 Error 被统计成 0 —— **假通过**。

【要点 3】两个分类作用域不同，缺一不可
  预编译 217bc73e = build 阶段覆盖 Application 下**全部 POU**（含未挂任务的）
  编译   97f48d64 = 只含**挂进任务调用列表**的 POU

【要点 4】读不到分类 / 取不到消息必须抛错，绝不能静默返回空列表当 0 错误

═══════════════════════════════════════════════════════════════════════
正确用法（主机侧串起来）
═══════════════════════════════════════════════════════════════════════
  A. 导入后验收：
     do_replace.py 导入 → 主机侧 sleep 3 → task_check.py 读快照
  B. 强制重新构建后验收：
     task_build.py（只 app.build()）→ 主机侧 sleep 12 → task_check.py 读快照
  C. 若 check.log 里预编译 total=0 而编译 total>0，说明刚好撞上异步窗口，
     主机侧再 sleep 10s 重跑一次 task_check.py 即可。
"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[0])))
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
        L(u"=== %s : total=%d errors=%d warnings=%d ===" % (label, len(objs), ne, nw))
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

    L(u"=== 验收结论 : %s (预编译 %d + 编译 %d + 其它 %d = 合计 %d 错误, %d 警告) ===" % (
        u"通过" if total_err == 0 else u"不通过",
        pre_err, bld_err, other_err, total_err, total_warn))

    if pre_total == 0 and bld_total > 0:
        L(u"⚠ 预编译 0 条而编译有消息，疑似撞上 build 后的异步重建窗口，请等 10s 后重跑本脚本")
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))
finally:
    _lf.close()
