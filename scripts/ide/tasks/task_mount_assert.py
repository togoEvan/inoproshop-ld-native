# -*- coding: utf-8 -*-
# @ipy2
"""验收前置断言：给定对象名必须已挂进某个任务的 POU 调用列表。

防「任务未挂载」类假通过（lead 交叉验证配方）：
  POU 不挂任务 = 不进编译单元 → build 后双分类 0 错误，但代码可能是坏的。
  （实测：prg_NoTaskTest 含未定义标识符，不挂任务 build 是 0 错误。）

参数从 ipc/task_mount_args.json 读：{"names": ["prg_A", "prg_B"]}
输出：
  ipc/task_mount.log        ：每个名字挂了哪个任务
  ipc/task_mount_result.json：{"ok":bool,"total":n,"unmounted":[..],"mounted":{..}}
本脚本被 eval_file 在守护进程里 exec，进程退出码不由它决定——
主机侧必须读 result.json 的 ok 字段判定，不能看退出码（恒 0 → 假通过）。
判挂载只读 Task Configuration，不需要编译，秒级。
"""
import io
import json
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
LOG = os.path.join(IPC, "task_mount.log")
ARGS = os.path.join(IPC, "task_mount_args.json")
RESULT = os.path.join(IPC, "task_mount_result.json")
_lf = io.open(LOG, "w", encoding="utf-8")


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


def dump_result(res):
    # 显式 close：裸 io.open().write() 会滞留句柄，主机侧读会 PermissionError
    _rf = io.open(RESULT, "w", encoding="utf-8")
    try:
        _rf.write(unicode(json.dumps(res, ensure_ascii=False)))
    finally:
        _rf.close()


try:
    names = []
    if os.path.isfile(ARGS):
        # 读也要显式 close：裸 io.open 被宿主 GC 前句柄滞留 IDE 进程，
        # 主机侧下次写 args 会 PermissionError（实测）
        _af = io.open(ARGS, "r", encoding="utf-8")
        try:
            names = json.load(_af).get("names") or []
        finally:
            _af.close()
    if not names:
        raise RuntimeError(u"task_mount_args.json 里没有 names，空名单无意义")

    app = projects.primary.active_application
    # 枚举所有任务的全部挂载表：{pou_name: [task1, task2]}
    mounted = {}
    n_tasks = 0
    for o in app.get_children():
        if unicode(o.get_name()) != u"Task Configuration":
            continue
        for t in o.get_children():
            n_tasks += 1
            for p in t.pous:
                mounted.setdefault(unicode(p), []).append(unicode(t.get_name()))
    if n_tasks == 0:
        raise RuntimeError(u"Task Configuration 下没有任务，无法判挂载")

    unmounted = []
    for n in names:
        ts = mounted.get(n) or []
        if ts:
            L(u"OK   %s -> %s" % (n, u",".join(ts)))
        else:
            L(u"MISS %s -> 未挂进任何任务（不进编译单元，双分类 0 错误是假通过）" % n)
            unmounted.append(n)

    if unmounted:
        L(u"=== FAIL : %d/%d 未挂载 (%s) ===" % (len(unmounted), len(names), u",".join(unmounted)))
    else:
        L(u"=== PASS : %d/%d 全部已挂载 ===" % (len(names), len(names)))
    dump_result({"ok": not unmounted, "total": len(names),
                 "unmounted": unmounted, "mounted": mounted})
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))
    dump_result({"ok": False, "total": 0, "unmounted": [], "mounted": {},
                 "fatal": unicode(e)})
finally:
    _lf.close()
