# -*- coding: utf-8 -*-
# @ipy2
"""验收快照 v4：双通道计数 + 按 severity 分档的截断判定。

为什么要有两个通道（2026-11-28，lead 在 1.10 上实测 + 对照 inoproshop-mcp）：

  通道 1（可见通道）：get_message_objects(cat) 全量，按 severity 字符串在 Python 侧计数。
    缺点：单个分类最多回传 100 条，截断后计数低估（错误池另有 500 上限）。
  通道 2（过滤通道）：get_message_objects(cat, Severity.Error / FatalError)。
    本机 1.10 实测它按「完整池」过滤（all=540，Error=502，各项相加等于 all），
    所以即使全量被截断到 100 条，Error 池的条数依然精确（错误池封顶 500 + 1 条提示行）。
    但 inoproshop-mcp 在 CODESYS SP19 上实测过相反行为（2 错误只回 1 条 warning、0 错误），
    所以两个通道要交叉校验，不能只信一个。

交叉校验与判定：
  - 未截断的分类：两通道错误数必须相等，不等记 mismatch。
  - 已截断的分类：只做单向校验（过滤通道不得少于可见错误数），并标 cross=GE。
  - 计数取两通道较大值：过滤通道坏（少报）不能把已有错误洗成 0；可见通道被截断时由过滤补充。
  - 判定顺序：无编译分类 → UNKNOWN；未知 severity → UNKNOWN；错误 > 0 → FAIL；
    通道冲突 → UNKNOWN；通用消息截断且无过滤通道 → UNKNOWN；否则 PASS。
  - 错误池截断标记（「多于500个错误」）本身是错误证据（会计入 trunc_err 并进入错误明细判断）。
  - 警告池 100 条截断是模板工程常态，用过滤通道取精确警告数（warn_exact），不影响判定。

仍然遵守三条铁律：单次读、零 sleep、零轮询、绝不清空。
输出：<BASE>/ipc/check.log，末行 VERDICT: PASS|FAIL|UNKNOWN (...)。
"""
import io
import os
import sys
import traceback

# 本脚本在 scripts/ide/tasks/ 下，上溯两级才是 scripts/ide（_base.py 所在）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

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

KNOWN = {CAT_PRE: u"预编译", CAT_BUILD: u"编译", CAT_FMT: u"格式检查",
         u"194b48a9-ab51-43ae-b9a9-51d3edaaddf3": u"脚本消息",
         u"2af7707f-6167-4a76-a40e-430967be0f18": u"导入导出",
         u"220493a1-f49b-4416-9a3f-a545db707cbe": u"附加代码检查",
         u"0b4f7286-39b6-4849-833c-da14b0252650": u"未知(0b4f7286)"}

TRUNC_MARKS = (u"多于100", u"多于500", u"跳过更多", u"多于 100", u"多于 500")


def cat_name(c):
    """分类名优先取 IDE 的动态描述（跨版本稳定），取不到才退回硬编码表。"""
    try:
        d = system.get_message_category_description(c)
        if d:
            return unicode(d)
    except Exception:
        pass
    return KNOWN.get(unicode(c), u"未知分类")

SEV_KNOWN = frozenset([u"fatalerror", u"error", u"warning", u"information", u"text"])
SEV_NUM = {u"1": u"fatalerror", u"2": u"error", u"4": u"warning",
           u"8": u"information", u"16": u"text"}

_SEV_TYPE = [None]


def _txt(m, attr):
    try:
        v = getattr(m, attr)
        return unicode(v) if v is not None else u""
    except Exception:
        return u""


def _trunc_kind(t):
    """命中截断提示行时返回 err / warn / msg，否则 None"""
    hit = False
    for mk in TRUNC_MARKS:
        if mk in t:
            hit = True
            break
    if not hit:
        return None
    if u"错误" in t:
        return u"err"
    if u"警告" in t:
        return u"warn"
    return u"msg"


def _sev_name(m):
    s = _txt(m, "severity")
    if not s:
        return u""
    low = s.lower()
    if low in SEV_KNOWN:
        return low
    if s in SEV_NUM:
        return SEV_NUM[s]
    if u"." in s:
        tail = s.split(u".")[-1].lower()
        if tail in SEV_KNOWN:
            return tail
    return low


def _find_sev_type():
    if _SEV_TYPE[0] is not None:
        return _SEV_TYPE[0]
    t = None
    for n in (u"_3S.CoDeSys.ScriptEngine.BasicFunctionality.Severity, ScriptEngine",
              u"_3S.CoDeSys.ScriptEngine.BasicFunctionality.Severity"):
        try:
            t = System.Type.GetType(n)
        except Exception:
            t = None
        if t is not None:
            break
    if t is None:
        try:
            asms = list(System.AppDomain.CurrentDomain.GetAssemblies())
        except Exception:
            asms = []
        for phase in (1, 2):
            for a in asms:
                try:
                    an = unicode(a.GetName().Name)
                except Exception:
                    continue
                if phase == 1 and u"scriptengine" not in an.lower():
                    continue
                try:
                    types = a.GetTypes()
                except Exception:
                    continue
                for tt in types:
                    try:
                        if tt.Name == u"Severity" and tt.IsEnum:
                            t = tt
                            L(u"  [chan] Severity 枚举取自程序集 %s (phase=%d)" % (an, phase))
                            break
                    except Exception:
                        pass
                if t is not None:
                    break
            if t is not None:
                break
    _SEV_TYPE[0] = t
    if t is None:
        L(u"  [chan] 找不到 Severity 枚举，过滤通道不可用")
    return t


def _sev_value(name):
    t = _find_sev_type()
    if t is None:
        return None
    try:
        return System.Enum.Parse(t, name)
    except Exception, e:
        L(u"  [chan] Enum.Parse(%s) 失败：%s" % (name, e))
        return None


def _filter_pool(cat_obj, sev_name, label):
    """返回过滤通道的条数（已剔除截断提示行）；不可用返回 None"""
    sv = _sev_value(sev_name)
    if sv is None:
        return None
    try:
        lst = list(system.get_message_objects(cat_obj, sv))
    except Exception, e:
        L(u"  [chan] %s filter=%s 调用失败：%s" % (label, sev_name, e))
        return None
    n = 0
    for m in lst:
        if _trunc_kind(_txt(m, "text")) is None:
            n += 1
    return (len(lst), n)


def classify(objs):
    d = {u"fatal": 0, u"error": 0, u"warning": 0, u"information": 0, u"text": 0,
         u"unknown": 0, u"trunc_err": 0, u"trunc_warn": 0, u"trunc_msg": 0}
    for m in objs:
        t = _txt(m, "text")
        k = _trunc_kind(t)
        if k == u"err":
            d[u"trunc_err"] += 1
            continue
        if k == u"warn":
            d[u"trunc_warn"] += 1
            continue
        if k == u"msg":
            d[u"trunc_msg"] += 1
            continue
        n = _sev_name(m)
        if n == u"fatalerror":
            d[u"fatal"] += 1
        elif n == u"error":
            d[u"error"] += 1
        elif n == u"warning":
            d[u"warning"] += 1
        elif n == u"information":
            d[u"information"] += 1
        elif n == u"text":
            d[u"text"] += 1
        else:
            d[u"unknown"] += 1
    d[u"err"] = d[u"fatal"] + d[u"error"]
    return d


def enumerate_cats():
    cats = {}
    for c in list(system.get_message_categories()):
        cats[unicode(c)] = c
    return cats


try:
    proj = projects.primary
    app = proj.active_application
    L(u"BASE = %s (source: %s)" % (BASE, _base.SOURCE))
    L(u"PROJECT = %s" % unicode(proj.path))
    L(u"APP = %s" % unicode(app.get_name()))
    L(u"VERSION = v4.1 dual-channel (rev2)")

    try:
        system.process_messageloop()
    except Exception, e:
        L(u"process_messageloop 单次调用异常（忽略）：%s" % e)

    cats = enumerate_cats()
    built = False

    # 坑 4 加强版：刚打开的工程可能一个分类都没有（从没 build 过），
    # 此时不能直接 FATAL，必须先 build 一次让分类注册、让消息产生。
    if (not cats) or (CAT_BUILD not in cats):
        L(u"--- 消息分类为空或编译分类缺失，触发一次 app.build() 让分类注册 ---")
        try:
            app.build()
            built = True
            L(u"app.build() 返回（单次调用，不等待）")
        except Exception, e:
            L(u"app.build() 异常：%s" % e)
        try:
            system.process_messageloop()
        except Exception, e:
            L(u"pump 异常：%s" % e)
        cats = enumerate_cats()
        L(u"=== build 后消息分类（共 %d 个）===" % len(cats))

    if not cats:
        raise RuntimeError(u"get_message_categories() 返回空，不得当作 0 错误")

    L(u"=== 消息分类（共 %d 个）===" % len(cats))
    for guid in sorted(cats.keys()):
        L(u"  %s %s" % (guid, cat_name(cats[guid])))

    total_err = 0
    total_warn = 0
    sev_unknown = 0
    trunc_err = 0
    trunc_warn = 0
    trunc_msg = 0
    seen = 0
    ok_cats = set()
    chan_tested = 0
    chan_bad = []
    exact = 0          # 用过滤通道精确计数过的分类数
    visible_only = 0   # 只能用可见通道计数的分类数

    for guid in sorted(cats.keys()):
        label = cat_name(cats[guid])
        try:
            objs = list(system.get_message_objects(cats[guid]))
        except Exception, e:
            L(u"=== %s %s 读取失败：%s ===" % (label, guid, e))
            continue
        seen += 1
        ok_cats.add(guid)
        d = classify(objs)
        sev_unknown += d[u"unknown"]
        trunc_err += d[u"trunc_err"]
        trunc_warn += d[u"trunc_warn"]
        trunc_msg += d[u"trunc_msg"]

        fe = _filter_pool(cats[guid], u"Error", label)
        ff = _filter_pool(cats[guid], u"FatalError", label)
        f_err = None
        if fe is not None and ff is not None:
            f_err = fe[1] + ff[1]

        f_warn = None
        if d[u"trunc_warn"] > 0:
            fw = _filter_pool(cats[guid], u"Warning", label)
            if fw is not None:
                f_warn = fw[1]

        truncated = (d[u"trunc_err"] > 0) or (d[u"trunc_warn"] > 0) or (d[u"trunc_msg"] > 0)

        note = u""
        if f_err is None:
            eff = d[u"err"]
            if d[u"err"] > 0 or guid in (CAT_BUILD, CAT_PRE):
                visible_only += 1
            note = u" filter=NA"
        else:
            exact += 1
            # 取两通道的较大值：过滤通道坏了（少报）也不能把已有错误洗成 0；
            # 可见通道被截断（少报）时由过滤通道补上。
            eff = f_err if f_err >= d[u"err"] else d[u"err"]
            if truncated:
                # 全量被截断时只能做单向校验：过滤通道绝不能少于可见错误数
                if f_err < d[u"err"]:
                    chan_bad.append((guid, d[u"err"], f_err))
                    note = u" filter=%d cross=BAD(%d<%d)" % (f_err, f_err, d[u"err"])
                else:
                    note = u" filter=%d cross=GE(vis=%d,trunc)" % (f_err, d[u"err"])
            else:
                chan_tested += 1
                if f_err != d[u"err"]:
                    chan_bad.append((guid, d[u"err"], f_err))
                    note = u" filter=%d cross=BAD(%d!=%d)" % (f_err, f_err, d[u"err"])
                else:
                    note = u" filter=%d cross=OK" % f_err
        if f_warn is not None:
            total_warn += f_warn
            note += u" warn_exact=%d" % f_warn
        else:
            total_warn += d[u"warning"]
        total_err += eff
        L(u"=== %s : total=%d errors=%d warnings=%d%s ===" % (
            label, len(objs), eff, (f_warn if f_warn is not None else d[u"warning"]), note))
        if d[u"trunc_err"] or d[u"trunc_warn"] or d[u"trunc_msg"]:
            L(u"  [TRUNCATED] err=%d warn=%d msg=%d（单分类上限，见分类池过滤计数）" % (
                d[u"trunc_err"], d[u"trunc_warn"], d[u"trunc_msg"]))
        for m in objs:
            t = _txt(m, "text")
            if _trunc_kind(t) is not None:
                continue
            s = _sev_name(m)
            if s not in SEV_KNOWN:
                L(u"  [?? %s] %s | %s" % (_txt(m, "severity"), _txt(m, "object"), t))
            elif s in (u"error", u"fatalerror"):
                L(u"  [%s] %s | %s" % (_txt(m, "severity"), _txt(m, "object"), t))
        if d[u"warning"] > 0:
            shown = 0
            for m in objs:
                t = _txt(m, "text")
                if _trunc_kind(t) is not None:
                    continue
                if _sev_name(m) != u"warning":
                    continue
                L(u"  [warn] %s | %s" % (_txt(m, "object"), t))
                shown += 1
                if shown >= 5:
                    L(u"  [warn] ... 其余 %d 条省略" % (d[u"warning"] - shown))
                    break

    if seen == 0:
        raise RuntimeError(u"一个分类都没读到，不得当作 0 错误")

    has_build = CAT_BUILD in ok_cats

    if chan_bad:
        chan = u"mismatch"
    elif chan_tested > 0:
        chan = u"dual"
    elif exact > 0:
        chan = u"dual-unchecked"
    else:
        chan = u"all"

    L(u"=== 合计 : errors=%d warnings=%d trunc(err/warn/msg)=%d/%d/%d ===" % (
        total_err, total_warn, trunc_err, trunc_warn, trunc_msg))
    L(u"=== 通道 : %s tested=%d exact=%d visible=%d mismatch=%d ===" % (
        chan, chan_tested, exact, visible_only, len(chan_bad)))
    for (g, a, b) in chan_bad:
        L(u"  [CHAN-BAD] %s 可见=%d 过滤=%d" % (g, a, b))

    if not has_build:
        verdict = u"UNKNOWN"
        why = u"no-build-category"
    elif sev_unknown > 0:
        verdict = u"UNKNOWN"
        why = u"unknown-severity"
    elif total_err > 0:
        verdict = u"FAIL"
        why = u"errors"
    elif chan == u"mismatch":
        verdict = u"UNKNOWN"
        why = u"chan-mismatch"
    elif trunc_msg > 0 and exact == 0:
        verdict = u"UNKNOWN"
        why = u"trunc-msg-no-filter"
    else:
        verdict = u"PASS"
        why = u"clean"

    L(u"VERDICT: %s (errors=%d warnings=%d chan=%s why=%s sev_unknown=%d trunc=%d/%d/%d built=%s)" % (
        verdict, total_err, total_warn, chan, why, sev_unknown,
        trunc_err, trunc_warn, trunc_msg, built))
    L(u"注意：编译命令全部走缓存，本快照只能反映导入/编辑/build 那一刻触发的检查。")
except Exception, e:
    L(u"VERDICT: UNKNOWN (脚本异常)")
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))
finally:
    try:
        _lf.close()
    except Exception:
        pass
