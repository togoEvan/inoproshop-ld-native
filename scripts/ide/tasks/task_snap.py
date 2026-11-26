# -*- coding: utf-8 -*-
"""双快照多重集差分验收（lead 方案）：before/import/after 三拍，delta 判定。

解决 baseline 截断问题：模板工程自带 101 条 warning，POU 名 grep 不可靠。
只看本次导入【新增】的消息，baseline 自动归零，无需白名单。

用法（主机侧串三拍，等待放主机侧）：
  1. bridge eval_file task_snap.py            （before 快照 -> ipc/snap_before.json）
  2. 导入（do_replace.py / task_silent_import.py）
  3. bridge eval_file task_snap.py             （after 快照 -> ipc/snap_after.json）
  4. 主机侧 delta.py 算差分（本文件自带 delta 函数，主机侧 import 调用）

差分规则（IP2 内不依赖 json 差集运算）：
  - 消息归一化：数字段与 {8-4-4-4-12} GUID 替换为 # 再哈希（防行号/GUID 漂移）
  - 多重集减法：after - before；同文本多条按条数记
  - before 已截断（total>=100）的分类：文本不可信，只比 total 差 -> 记 UNKNOWN
  - 结论：delta.error==0 且无 UNKNOWN -> PASS；否则 FAIL/UNKNOWN

输出：ipc/snap_before.json / snap_after.json（{"meta":{"which",..}, "cats":{..}}）/ delta.log
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
    for c in list(system.get_message_categories()):
        guid = unicode(c)
        objs = list(system.get_message_objects(c))
        items = []
        for m in objs:
            v = prop(m, u"severity")
            sev = unicode(v).rsplit(u".", 1)[-1].lower() if v is not None else u"?"
            txt = norm(prop(m, u"text"))
            items.append([sev, txt])
        snap[guid] = {"total": len(objs),
                      "truncated": len(objs) >= TRUNC_AT,
                      "items": items}
    # meta 自证：delta 侧校验 before/after 拍子，两次拍成同一个立刻 UNKNOWN
    meta = {"which": which, "ts": time.strftime(u"%H:%M:%S"),
            "argv0": unicode(sys.argv[0])}
    out = os.path.join(IPC, u"snap_%s.json" % which)
    # 必须显式 close（不能裸 io.open().write()）——IDE 进程持有句柄不释放，
    # 主机侧 delta_snap.py 读会 PermissionError（实测）。
    _of = io.open(out, "w", encoding="utf-8")
    try:
        _of.write(unicode(json.dumps({"meta": meta, "cats": snap}, ensure_ascii=False)))
    finally:
        _of.close()
    L(u"=== snap %s : %d 分类 -> %s ===" % (which, len(snap), out))
    for g in sorted(snap.keys()):
        d = snap[g]
        L(u"  %s total=%d%s" % (g, d["total"], u" [TRUNCATED]" if d["truncated"] else u""))
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))
finally:
    _lf.close()
