# -*- coding: utf-8 -*-
"""双快照差分（主机侧）：after - before 多重集减法，只判新增的 error。

与 ide/tasks/task_snap.py 配对（先 before 快照，导入后 after 快照）。
用法：
    python delta_snap.py [ipc目录]
默认 ipc 目录取 bridge 的 IPC。

结论（四态）：
  PASS       : delta error == 0 且无不可信分类
  FAIL       : delta 里出现新增 error（确定的工程事实）
  UNKNOWN    : 截断 / 拍子不对 / severity 未知 / 存量 error 或地址集合变化，交人工
  TOOL_ERROR : 快照缺失或损坏，工具链故障——不是工程结论

主判据：err_pool（独立 Error 池，不受 100 条截断影响）。
  get_message_objects(cat, Severity.Error) 按完整池过滤，实测可证：
  97f48d64 all=104 = Warning 101 + Text 3。所以 Error 池条数是真值。
  快照无 err_pool（旧版）时回退文本差分，此时截断即 UNKNOWN。

退出码：0=PASS，1=FAIL，2=UNKNOWN，3=TOOL_ERROR
  工具崩了必须与「工程有错」分码，否则主机侧会把链路故障误报成质量事故。

固定局限：文本差分按归一化文本计数，回答的是「错误数净增了吗」；
若一消一增两条同文本 error 抵消，delta=0。err_pool 通道给条数真值，
地址集合给定位，两者互补。仍不回答「这次导入引入错误了吗」——
那需比对具体对象 GUID/路径。

输出：ipc/delta.log（UTF-8，中文细节全在这）；stdout 只打 ASCII 摘要
（GBK 控制台会把中文打成乱码，判定请读 delta.log 或退出码）。
"""
import io
import json
import os
import sys

EXIT_PASS = 0
EXIT_FAIL = 1
EXIT_UNKNOWN = 2
EXIT_TOOL = 3

EMPTY = {"total": 0, "truncated": False, "items": [], "err_total": 0, "err_addrs": []}


class ToolError(Exception):
    pass


def load(ipc, which):
    p = os.path.join(ipc, "snap_%s.json" % which)
    if not os.path.isfile(p):
        raise ToolError(u"snapshot-missing: %s" % p)
    try:
        f = io.open(p, "r", encoding="utf-8")
        try:
            return json.load(f)
        finally:
            f.close()
    except Exception as e:
        raise ToolError(u"snapshot-corrupt: %s (%s)" % (p, e))


def split(doc):
    """兼容新旧快照格式：新 {"meta":{..},"cats":{..}}，旧直接是分类 dict。"""
    if isinstance(doc, dict) and "cats" in doc:
        return doc.get("meta") or {}, doc["cats"]
    return {}, doc


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

    log = io.open(os.path.join(ipc, "delta.log"), "w", encoding="utf-8")

    def W(s):
        log.write(u"%s\n" % s)
        log.flush()

    def finish(verdict, code, summary):
        W(u"=== delta : %s === %s" % (verdict, summary))
        log.close()
        # stdout 只打 ASCII：GBK 控制台打中文会变乱码，判定别 grep stdout
        print(u"=== delta : %s === %s" % (verdict, summary))
        return code

    # ---- 工具链自检：快照读不到 = 工具故障，不是工程结论 ----
    try:
        before_doc = load(ipc, "before")
        after_doc = load(ipc, "after")
    except ToolError as e:
        return finish(u"TOOL_ERROR", EXIT_TOOL, u"%s" % e)

    bmeta, before = split(before_doc)
    ameta, after = split(after_doc)

    # 拍子自证：两次拍成同一个（如都拍成 after）差分必然全零 -> 假 PASS。
    # 旧格式快照无 meta，同样不可证。不满足直接 UNKNOWN，绝不判 PASS。
    if bmeta.get("which") != u"before" or ameta.get("which") != u"after":
        return finish(u"UNKNOWN", EXIT_UNKNOWN,
                      u"snapshot-which-mismatch before=%s after=%s"
                      % (bmeta.get("which"), ameta.get("which")))

    # severity 采集完整性：task_snap 现在读不到就 raise，这里再兜一层——
    # 旧版/外部快照若把 sev 写成 "?"，绝不能当「非 error」放过去。
    bad_sev = 0
    for cats in (before, after):
        for d in cats.values():
            for it in d.get("items") or []:
                if len(it) > 0 and it[0] == u"?":
                    bad_sev += 1
    unknown = bad_sev > 0
    if bad_sev:
        W(u"发现 %d 条 severity 未知（'?'）的消息：采集器降级，新增 error 可能被漏判"
          % bad_sev)

    delta_err = 0
    pool_used = 0
    for guid in sorted(after.keys()):
        a = after[guid]
        b = before.get(guid) or dict(EMPTY)

        # ---- 主判据：独立 Error 池（不受 100 条截断影响）----
        # get_message_objects(cat, Severity.Error) 按完整池过滤，实测可证：
        # 97f48d64 all=104 = Warning 101 + Text 3。所以 Error 池的条数是真值，
        # 与 warning 池是否截断无关 —— 这条通道能让高 baseline 工程正常判 PASS。
        pa, pb = a.get("err_pool"), b.get("err_pool")
        if pa is not None and pb is not None:
            pool_used += 1
            pe = pa["total"] - pb["total"]
            if pe > 0:
                W(u"%s : Error 池 %d -> %d（独立通道，不受截断影响）= %+d"
                  % (guid, pb["total"], pa["total"], pe))
                delta_err += pe
            elif pa["total"] != pb["total"]:
                W(u"%s : Error 池 %d -> %d（减少，不算新增）"
                  % (guid, pb["total"], pa["total"]))
            # 池自身也被截断：文本/地址不可全信
            if pa.get("truncated"):
                W(u"%s : Error 池自身已截断(total=%d)，地址集合不完整 -> 存疑"
                  % (guid, pa["total"]))
                unknown = True
            # 地址集合变化（同类错误换地址，条数可能不变）
            aa, ab = set(pa.get("addrs") or []), set(pb.get("addrs") or [])
            if aa != ab and not pa.get("truncated"):
                W(u"%s : Error 池地址集合变化 +%d/-%d（%s）"
                  % (guid, len(aa - ab), len(ab - aa),
                     u",".join(sorted(aa - ab)[:5])))
                unknown = True
            # 池通道可用时，该分类的文本差分结论不再需要——避免被截断误伤
            continue

        if b.get("truncated"):
            # 无 Error 池通道（旧快照/老 IDE）：只能退回文本差分。
            # before 已截断 = 文本不可信，total 无增不代表没藏 error（可能一消一增），
            # 所以截断本身就该降 UNKNOWN。
            dn = a["total"] - b["total"]
            W(u"%s : before 已截断(total=%d)，只比 total 差 = %+d -> 文本不可信"
              % (guid, b["total"], dn))
            unknown = True
            continue

        mb, ma = multiset(b.get("items") or []), multiset(a.get("items") or [])
        for key, n in sorted(ma.items()):
            new = n - mb.get(key, 0)
            if new > 0:
                sev, txt = key
                W(u"%s [+%d] %s : %s" % (guid, new, sev.upper(), txt[:120]))
                if sev == u"error":
                    delta_err += new

        # after 截断且有净增量：可见新增只是前 100 条里的部分，
        # 被截掉部分可能有 error。可见 error 已计进 delta_err（确定的 FAIL 事实），
        # 无可见新增 error 时也不能判 PASS，降 UNKNOWN。
        if a.get("truncated") and a["total"] - b["total"] > 0:
            W(u"%s : after 已截断(total=%d)且有净增量，被截部分不可见 -> 文本不完全可信"
              % (guid, a["total"]))
            unknown = True

        # ---- 对象级兜底（不走文本归一化）----
        # 归一化会把「%MB131076 地址重复」这类错误全撞成同一条 key：
        # before 13 条 / after 13 条（地址全换但仍全错）-> 文本 delta=0 -> 假 PASS。
        # 用 err_total（error 条数）+ err_addrs（地址集合）兜住。
        if "err_total" in a or "err_total" in b:
            ea, eb = a.get("err_total", 0), b.get("err_total", 0)
            aa, ab = set(a.get("err_addrs") or []), set(b.get("err_addrs") or [])
            if ea != eb:
                W(u"%s : error 条数 %d -> %d（对象级计数，不依赖文本归一化）"
                  % (guid, eb, ea))
            if aa != ab:
                W(u"%s : error 地址集合变化 +%d/-%d（%s）"
                  % (guid, len(aa - ab), len(ab - aa),
                     u",".join(sorted(aa - ab)[:5])))
                unknown = True
            # after 仍有存量 error 而文本差分看不见：一消一增抵消，不可判干净
            if ea > 0 and delta_err == 0:
                W(u"%s : after 仍有 %d 条存量 error，文本差分未体现 -> 不可判 PASS"
                  % (guid, ea))
                unknown = True

    # 判定优先级：新增 error > 0 是确定的 FAIL（截断/降级不影响这个事实）；
    # 否则有不可信因素才 UNKNOWN；都干净才 PASS。
    chan = u"errpool" if pool_used else u"text"
    if delta_err > 0:
        return finish(u"FAIL", EXIT_FAIL, u"new_err=%d chan=%s" % (delta_err, chan))
    if unknown:
        return finish(u"UNKNOWN", EXIT_UNKNOWN, u"new_err=0 chan=%s need_manual" % chan)
    return finish(u"PASS", EXIT_PASS, u"new_err=0 chan=%s" % chan)


if __name__ == "__main__":
    sys.exit(main())
