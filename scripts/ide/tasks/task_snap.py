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
TRUNC_AT = 100


def norm(text):
    """归一化消息文本：数字与 GUID 替换为 #，防行号/GUID 漂移导致差分误判。"""
    t = unicode(text or u"")
    t = _GUID.sub(u"#", t)
    t = _NUM.sub(u"#", t)
    return t


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

    system.process_messageloop()
    snap = {}
    n_msg = 0
    n_sev_ok = 0
    n_txt_miss = 0
    for c in list(system.get_message_categories()):
        guid = unicode(c)
        objs = list(system.get_message_objects(c))
        items = []
        err_addrs = set()
        n_err = 0
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
            txt = norm(raw)
            items.append([sev, txt])
            if sev == u"error":
                n_err += 1
                for a in _ADDR.findall(unicode(raw or u"")):
                    err_addrs.add(a.upper())
        snap[guid] = {"total": len(objs),
                      "truncated": len(objs) >= TRUNC_AT,
                      "items": items,
                      # 对象级兜底：归一化会把「地址重复」这类错误全撞成一条，
                      # 靠 err_total + 地址集合才能看出「换了一批地址照样全错」。
                      "err_total": n_err,
                      "err_addrs": sorted(err_addrs)}
    if n_txt_miss:
        L(u"WARN text 读不到 %d/%d 条（归一化后为空串，不影响 severity 判定）"
          % (n_txt_miss, n_msg))
    # meta 自证：delta 侧校验 before/after 拍子，两次拍成同一个立刻 UNKNOWN
    meta = {"which": which, "ts": time.strftime(u"%H:%M:%S"),
            "argv0": unicode(sys.argv[0]),
            "n_msg": n_msg, "n_sev_ok": n_sev_ok, "n_txt_miss": n_txt_miss}
    out = os.path.join(IPC, u"snap_%s.json" % which)
    # 必须显式 close（不能裸 io.open().write()）——IDE 进程持有句柄不释放，
    # 主机侧 delta_snap.py 读会 PermissionError（实测）。
    _of = io.open(out, "w", encoding="utf-8")
    try:
        _of.write(unicode(json.dumps({"meta": meta, "cats": snap}, ensure_ascii=False)))
    finally:
        _of.close()
    L(u"=== snap %s : %d 分类 / %d 消息 / severity %d OK -> %s ==="
      % (which, len(snap), n_msg, n_sev_ok, out))
    for g in sorted(snap.keys()):
        d = snap[g]
        L(u"  %s total=%d err=%d addr=%d%s" % (
            g, d["total"], d["err_total"], len(d["err_addrs"]),
            u" [TRUNCATED]" if d["truncated"] else u""))
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))
finally:
    _lf.close()
