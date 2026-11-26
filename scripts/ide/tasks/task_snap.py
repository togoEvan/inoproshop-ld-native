# -*- coding: utf-8 -*-
"""双快照多重集差分验收：before/import/after 三拍，delta 判定。

解决 baseline 截断问题：模板工程自带 101 条 warning，POU 名 grep 不可靠。
只看本次导入【新增】的消息，baseline 自动归零，无需白名单。

用法（主机侧串三拍，等待放主机侧）：
  1. bridge eval_file task_snap.py            （before 快照 -> ipc/snap_before.json）
  2. 导入（do_replace.py / task_silent_import.py）
  3. bridge eval_file task_snap.py             （after 快照 -> ipc/snap_after.json）
  4. 主机侧 delta_snap.py 算差分

采集原则：宁缺毋滥。severity 读不到就 raise（快照失败），不产出坏快照——
坏快照会被下游当成真结果，把「我不知道」伪装成「没问题」。

关键通道：get_message_objects(cat, Severity.Error) 是【按完整池过滤】，不是从
被截断的 100 条里筛。实测 97f48d64 all=104 / Warning=101 + Text=3 = 104 可证。
所以 Error 池独立且不受 100 条上限影响 —— 这是 baseline 高截断工程的唯一可靠判据。
"""
import io
import json
import os
import re
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
_lf = io.open(os.path.join(IPC, "snap.log"), "w", encoding="utf-8")


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


def prop(m, name):
    try:
        return m.GetType().GetProperty(name).GetValue(m, None)
    except Exception:
        return None


_NUM = re.compile(u"\\d+")
_GUID = re.compile(u"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
# PLC 地址：%MB131076 / %MW100 / %MX1.2 / %IW0 等，取原始（未归一化）文本里的
_ADDR = re.compile(u"%[IQM][BWDX]\\d+(?:\\.\\d+)?", re.IGNORECASE)
# 截断的【本质判据】：IDE 截断时会注入一条「多于N个消息/警告/错误发生：跳过更多的…」。
# 不能用条数阈值代替 —— 实测 lead 的损坏工程 编译分类 all=540
# （Error 502 + Warning 35 + Text 3）完整返回、无任何截断提示；
# 而我的模板工程 all=104（Warning 101 + Text 3）就带提示。
# 即：100 条上限只作用于警告，不作用于错误。条数阈值会把 502 条误判为截断。
#
# 两种提示必须区分（都实测到过）：
#   「多于N个【警告】发生」→ 只有 warning 被截，error 池仍完整可信
#   「多于N个【消息】发生」→ 所有消息都可能被截，error 池也可能缺条
_TRUNC_WARN = re.compile(u"多于\\s*\\d+\\s*个警告发生")
_TRUNC_ALL = re.compile(u"多于\\s*\\d+\\s*个(?:消息|错误)发生")


def norm(text):
    """归一化消息文本：数字与 GUID 替换为 #，防行号/GUID 漂移导致差分误判。"""
    t = unicode(text or u"")
    t = _GUID.sub(u"#", t)
    t = _NUM.sub(u"#", t)
    return t


def _severity_filter():
    """取 get_message_objects(cat, Severity) 重载与 Error 枚举值。取不到返回 None。

    IronPython 下不能 import _3S，只能反射拿重载；Invoke 参数必须是 Array[object]。
    """
    try:
        import System
        from System import Array, Object
        target = None
        sev_type = None
        for m in system.GetType().GetMethods():
            if unicode(m.Name) != u"get_message_objects":
                continue
            ps = m.GetParameters()
            if len(ps) == 2 and u"Severity" in unicode(ps[1].ParameterType):
                target = m
                sev_type = ps[1].ParameterType
        if target is None:
            return None
        err_v = System.Enum.Parse(sev_type, u"Error")
        return (target, Array, Object, err_v)
    except Exception, e:
        L(u"WARN severity 过滤通道不可用：%s" % e)
        return None


def err_pool(cat_guid, filt):
    """按 severity=Error 过滤取池。返回 {"total","truncated","items","addrs"} 或 None。

    None = 通道不可用（老版本 IDE / 反射失败），delta 侧回退到文本差分。
    """
    if filt is None:
        return None
    target, Array, Object, err_v = filt
    try:
        objs = list(target.Invoke(system, Array[Object]([cat_guid, err_v])))
    except Exception, e:
        L(u"WARN 分类 %s 的 Error 池取不到：%s" % (cat_guid, e))
        return None
    items = []
    addrs = set()
    all_trunc = False
    for m in objs:
        raw = prop(m, u"text")
        txt = norm(raw)
        items.append(txt)
        # 只有「多于N个消息/错误」才意味着 error 池本身可能缺条；
        # 「多于N个警告」只截 warning，error 池仍完整可信。
        if _TRUNC_ALL.search(unicode(raw or u"")):
            all_trunc = True
        for a in _ADDR.findall(unicode(raw or u"")):
            addrs.add(a.upper())
    return {"total": len(objs),
            "truncated": all_trunc,
            "items": items,
            "addrs": sorted(addrs)}


try:
    # 哪个拍子：默认 after；before 由 args 指定（{"which": "before"}）
    which = u"after"
    args_p = os.path.join(IPC, "snap_args.json")
    if os.path.isfile(args_p):
        # 读也显式 close，句柄滞留会堵主机侧下次写（实测）
        _af = io.open(args_p, "r", encoding="utf-8")
        try:
            which = json.load(_af).get(u"which") or u"after"
        finally:
            _af.close()

    filt = _severity_filter()
    system.process_messageloop()
    snap = {}
    n_msg = 0
    n_sev_ok = 0
    n_txt_miss = 0
    n_pool_ok = 0
    for c in list(system.get_message_categories()):
        guid = unicode(c)
        objs = list(system.get_message_objects(c))
        items = []
        err_addrs = set()
        n_err = 0
        cat_trunc = False       # 有任意截断提示
        cat_trunc_all = False   # 提示是「消息/错误」级（error 池可能缺条）
        for m in objs:
            n_msg += 1
            v = prop(m, u"severity")
            if v is None:
                # severity 取不到 = 采集器坏了。若静默降级成 "?"，delta 侧只认
                # "error"，新增 error 会被判成 PASS（lead 实验 2 实证）。
                raise RuntimeError(
                    u"消息 severity 反射取不到（第 %d 条，分类 %s）：采集器不可信，"
                    u"拒绝产出坏快照" % (n_msg, guid))
            sev = unicode(v).rsplit(u".", 1)[-1].lower()
            n_sev_ok += 1
            raw = prop(m, u"text")
            if raw is None:
                n_txt_miss += 1
            sraw = unicode(raw or u"")
            if _TRUNC_WARN.search(sraw) or _TRUNC_ALL.search(sraw):
                cat_trunc = True
            if _TRUNC_ALL.search(sraw):
                cat_trunc_all = True
            txt = norm(raw)
            items.append([sev, txt])
            if sev == u"error":
                n_err += 1
                for a in _ADDR.findall(sraw):
                    err_addrs.add(a.upper())
        pool = err_pool(c, filt)
        if pool is not None:
            n_pool_ok += 1
        snap[guid] = {"total": len(objs),
                      "truncated": cat_trunc,
                      # 截断到「消息/错误」级 = error 池可能缺条，必须存疑
                      "truncated_all": cat_trunc_all,
                      "items": items,
                      # 对象级兜底：归一化会把「地址重复」这类错误全撞成一条，
                      # 靠 err_total + 地址集合才能看出「换了一批地址照样全错」。
                      "err_total": n_err,
                      "err_addrs": sorted(err_addrs),
                      # 主判据通道：独立 Error 池，不受 100 条截断影响
                      "err_pool": pool}
    if n_txt_miss:
        L(u"WARN text 读不到 %d/%d 条（归一化后为空串，不影响 severity 判定）"
          % (n_txt_miss, n_msg))
    # meta 自证：delta 侧校验 before/after 拍子，两次拍成同一个立刻 UNKNOWN
    meta = {"which": which, "ts": time.strftime(u"%H:%M:%S"),
            "argv0": unicode(sys.argv[0]),
            "schema": 2,
            "n_msg": n_msg, "n_sev_ok": n_sev_ok, "n_txt_miss": n_txt_miss,
            "n_pool_ok": n_pool_ok}
    out = os.path.join(IPC, u"snap_%s.json" % which)
    # 必须显式 close（不能裸 io.open().write()）——IDE 进程持有句柄不释放，
    # 主机侧 delta_snap.py 读会 PermissionError（实测）。
    _of = io.open(out, "w", encoding="utf-8")
    try:
        _of.write(unicode(json.dumps({"meta": meta, "cats": snap}, ensure_ascii=False)))
    finally:
        _of.close()
    L(u"=== snap %s : %d 分类 / %d 消息 / severity %d OK / err_pool %d 分类 -> %s ==="
      % (which, len(snap), n_msg, n_sev_ok, n_pool_ok, out))
    for g in sorted(snap.keys()):
        d = snap[g]
        p = d.get("err_pool")
        pstr = (u"pool=%d%s" % (p["total"], u"[T]" if p["truncated"] else u"")) \
            if p is not None else u"pool=N/A"
        L(u"  %s total=%d err=%d addr=%d %s%s" % (
            g, d["total"], d["err_total"], len(d["err_addrs"]), pstr,
            u" [TRUNCATED]" if d["truncated"] else u""))
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))
finally:
    _lf.close()
