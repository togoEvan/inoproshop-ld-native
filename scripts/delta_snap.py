# -*- coding: utf-8 -*-
"""双快照差分（主机侧）：after - before 多重集减法，只判新增的 error。

与 ide/tasks/task_snap.py 配对（先 before 快照，导入后 after 快照）。
用法：
    python delta_snap.py [ipc目录]
默认 ipc 目录取 bridge 的 IPC。

结论：
  PASS    : delta error == 0 且无截断不可信分类
  UNKNOWN : before 某分类已截断（total>=100），文本不可信只比 total 差
  FAIL    : delta 里出现 error
退出码：0=PASS，1=FAIL，2=UNKNOWN（交人工，绝不静默当通过）
"""
import io
import json
import os
import sys


def load(ipc, which):
    p = os.path.join(ipc, "snap_%s.json" % which)
    return json.load(io.open(p, "r", encoding="utf-8"))


def multiset(items):
    ms = {}
    for it in items:
        key = tuple(it)
        ms[key] = ms.get(key, 0) + 1
    return ms


def main():
    ipc = sys.argv[1] if len(sys.argv) > 1 else None
    if ipc is None:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import bridge
        ipc = bridge.IPC

    before = load(ipc, "before")
    after = load(ipc, "after")

    log = io.open(os.path.join(ipc, "delta.log"), "w", encoding="utf-8")
    def W(s):
        log.write(u"%s\n" % s)
        log.flush()

    delta_err = 0
    unknown = False
    for guid in sorted(after.keys()):
        a, b = after[guid], before.get(guid) or {"total": 0, "truncated": False, "items": []}
        if b.get("truncated"):
            # before 已截断：文本不可信，只能比 total 差
            dn = a["total"] - b["total"]
            W(u"%s : before 已截断(total=%d)，只比 total 差 = %+d -> 文本不可信" % (guid, b["total"], dn))
            if dn > 0:
                unknown = True
            continue
        mb, ma = multiset(b["items"]), multiset(a["items"])
        for key, n in sorted(ma.items()):
            new = n - mb.get(key, 0)
            if new > 0:
                sev, txt = key
                W(u"%s [+%d] %s : %s" % (guid, new, sev.upper(), txt[:120]))
                if sev == "error":
                    delta_err += new

    # 判定优先级：可靠分类的新增 error > 0 就是确定的 FAIL（截断分类不影响
    # 这个事实）；否则有截断不可信分类才 UNKNOWN；都干净才 PASS。
    if delta_err > 0:
        verdict = u"FAIL"
        code = 1
    elif unknown:
        verdict = u"UNKNOWN"
        code = 2
    else:
        verdict = u"PASS"
        code = 0
    W(u"=== delta : %s (新增 error %d)%s ===" % (
        verdict, delta_err, u" ⚠ 存在截断不可信分类，交人工" if unknown else u""))
    log.close()
    print(u"=== delta : %s (新增 error %d) ===" % (verdict, delta_err))
    return code


if __name__ == "__main__":
    sys.exit(main())
