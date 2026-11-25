# -*- coding: utf-8 -*-
"""验收：动态枚举全部消息分类并全量扫描，单次快照，绝不阻塞 IDE。

已知四分类：预编译(217bc73e) + 编译(97f48d64) + 格式检查(0986c5dd)
+ 附加代码检查(220493a1)。大工程里编译错误还可能落到其它分类
（Library Manager、POU 专属、工程树等），所以其余分类也全量扫描
（学自 inoproshop-mcp 的 compile_project.py，2026-11-25）。

═══════════════════════════════════════════════════════════════════════
为什么这个脚本「不编译、不清消息、不 sleep、不轮询」（2026-11-25 最终定论）
═══════════════════════════════════════════════════════════════════════
前几轮踩了一串坑，全部记在这里，别再重犯：

【坑 1】在 IDE 脚本里 sleep + 轮询 → 界面卡死
  IDE 脚本跑在 InoProShop 主线程上，time.sleep() 和 process_messageloop()
  循环会把界面冻住，用户直接反馈「你在等待的时候软件卡死了」「还是卡死」。
  → 铁律：IDE 侧脚本只做「读一次、写文件、立刻返回」，单次耗时控制在 1s 内。
    计时/重试全部放主机侧（Python 主进程），IDE 毫不知情。

【坑 2】clear_messages 之后再也读不到错误
  实测：导入 prg_AxisCallTest（actAbs 的 ST 体引用了不存在的 xPtpCond）后，
  直接读快照 → 预编译分类里有
      [Error] actAbs | 没有定义标识符'xPtpCond'
  但如果先 clear_messages 再跑「重新编译」，预编译分类恒为 0 条，
  编译分类只回一句「此应用程序是最新的」。
  → 铁律：**不要 clear_messages**。错误消息是导入动作触发的自动检查产生的，
    清掉就没了，而且后续任何编译命令都不会重算（走缓存）。

【坑 3】「重新编译 / 清理+重新编译 / 检查程序 / 运行静态分析 / 生成代码」
        全部走缓存，报 0 错误
  逐个实测（工程里放一个必然报错的 BoxType=actAbs_NOPE）：
      清理            → 预编译 0，编译「此应用程序是最新的」
      重新编译        → 预编译 0，编译「此应用程序是最新的」
      （旧）重新编译  → 预编译 0，编译「开始构建 / 代码典型化 / 编译完成 0 错误」
      （旧）编译      → 预编译 0，编译「此应用程序是最新的」
      检查所有对象    → 预编译 0
      运行静态分析    → 预编译 0
      生成代码        → 预编译 0
      生成二进制文件  → 预编译 0
      编译            → 预编译 0
  → 结论：**没有任何一条编译命令能替代导入触发的自动检查**。
    验收的正确时机 = 导入刚结束时立刻读一次。

【坑 4】负样本本身写错了，导致「以为验收链路坏了」
  用 s.replace('>actAbs<', '>actAbs_ZZZ<') 造负样本，结果把
  BoxType **和** action Entry 的 Name 一起改了 —— 于是 actAbs_ZZZ 变成一个
  真实存在的合法 action，编译 0 错误是**正确结果**，不是假通过。
  → 造负样本必须精确替换目标字段，只改 BoxType，Entry 名保持不动。
    改完先 grep 自查两处（BoxType 1 处、Entry Name 1 处）。

═══════════════════════════════════════════════════════════════════════
正确用法
═══════════════════════════════════════════════════════════════════════
  1. 导入 native（do_replace.py，导入瞬间会自动跑一次检查并落消息）
  2. 等 1~2 秒（主机侧 time.sleep，不在 IDE 里）
  3. 调本脚本读一次快照，看 check.log

⚠ 铁律：读不到分类 / 取不到消息必须抛错，绝不能静默返回空列表当 0 错误。
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
CAT_FMT = u"0986c5dd-ca06-40a7-94e5-bf42de3dfd91"
CAT_CHECKS = u"220493a1-f49b-4416-9a3f-a545db707cbe"

try:
    proj = projects.primary
    app = proj.active_application
    L(u"BASE = %s (source: %s)" % (BASE, _base.SOURCE))
    L(u"app  = %r" % unicode(app.get_name()))

    # 只处理一次待办消息，绝不循环、绝不 sleep
    system.process_messageloop()

    # ═══ 动态枚举全部消息分类（学自 inoproshop-mcp / multi-plc-agent）═══
    # 硬编码 GUID 只覆盖常见分类；大工程里编译错误会落到其它分类
    # （Library Manager、POU 专属、工程树等）。这里枚举运行时暴露的
    # 每一个分类，全部扫描，防止漏读。
    # 分类名称用 system.get_message_category_description() 动态取（实测可用），
    # 不再硬编码中文标签——GUID 集合因版本/配置而异，名称才是稳定语义。
    cats = {}
    for c in list(system.get_message_categories()):
        cats[unicode(c)] = c
    if not cats:
        raise RuntimeError(u"get_message_categories() 返回空，不得当作 0 错误")

    def cat_name(c):
        """取分类可读名（实测本机 SP11 返回中文：编译/预编译/格式检查/导出导入/脚本消息）。"""
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

    def read_cat(guid, label):
        """读一个分类；分类不存在直接抛错（不得当作 0 错误）。"""
        c = cats.get(guid)
        if c is None:
            raise RuntimeError(u"消息分类 %s(%s) 不存在，不得当作 0 错误" % (label, guid))
        return list(system.get_message_objects(c))

    def msg_text(m):
        for a in ("text", "message"):
            try:
                v = getattr(m, a)
                if v:
                    return unicode(v)
            except Exception:
                pass
        return u""

    def msg_sev(m):
        try:
            return unicode(getattr(m, 'severity', u''))
        except Exception:
            return u""

    def msg_obj(m):
        try:
            return unicode(m.object.get_name())
        except Exception:
            return u""

    def dump_cat(label, objs):
        ne = 0
        nw = 0
        for m in objs:
            sev = msg_sev(m)
            low = sev.lower()
            if 'err' in low:
                ne += 1
            elif 'warn' in low:
                nw += 1
            L(u"  [%s] %s | %s" % (sev, msg_obj(m), msg_text(m)))
        return ne, nw

    # ① 三个基础分类：缺一个就抛错（本机 SP11 实测必存在）
    # ② 其余分类（含已知的 220493a1 附加代码检查）存在才读。
    #    实测（2026-11-25 本机 SP11）：运行时只暴露 5 个分类，没有 220493a1——
    #    外部项目记录的分类集合与本机不同，GUID 因版本/配置而异，
    #    所以非基础分类不能设为「缺了就 raise」，否则验收永远过不去。
    total_err = 0
    total_warn = 0
    for guid in (CAT_PRE, CAT_BUILD, CAT_FMT):
        label = cat_desc.get(guid) or u"?"
        objs = read_cat(guid, label)
        L(u"=== %s : total=%d ===" % (label, len(objs)))
        ne, nw = dump_cat(label, objs)
        total_err += ne
        total_warn += nw
        L(u"  -> %s errors=%d warnings=%d" % (label, ne, nw))

    # 可选分类：其余全部分类，存在就读、计入合计
    for guid in sorted(cats.keys()):
        if guid in (CAT_PRE, CAT_BUILD, CAT_FMT):
            continue
        label = cat_desc.get(guid) or u"?"
        try:
            objs = list(system.get_message_objects(cats[guid]))
        except Exception, e:
            L(u"=== %s %s : 读取失败 %s（忽略） ===" % (label, guid, e))
            continue
        ne, nw = 0, 0
        for m in objs:
            sev = msg_sev(m)
            low = sev.lower()
            if 'err' in low:
                ne += 1
                L(u"  [%s] %s | %s" % (sev, msg_obj(m), msg_text(m)))
            elif 'warn' in low:
                nw += 1
        if ne or nw:
            L(u"=== %s %s : errors=%d warnings=%d ===" % (label, guid, ne, nw))
        else:
            L(u"=== %s %s : total=%d（无错误警告） ===" % (label, guid, len(objs)))
        total_err += ne
        total_warn += nw

    L(u"=== 结论 : %s (合计 %d 错误, %d 警告，覆盖全部分类) ===" % (
        u"通过" if total_err == 0 else u"不通过", total_err, total_warn))
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))
finally:
    _lf.close()
