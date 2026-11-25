# -*- coding: utf-8 -*-
"""结构自检：检查一个 native 里所有功能框的「项数 vs 参数数」是否一致。

为什么需要它（2026-11-25 教训）：
  这类错误**预编译 0 错误、编译 0 错误、往返 diff 也 PASS**，IDE 静默接受。
  唯一能发现的办法就是数一遍：OutputItems/List2 的项数必须 == OutputParam/Names 项数。
  典型翻车：把「第 0 项恒为 <Null/> 对应 ENO」当死规矩，给 TON 少写一个输出项
  （TON 的 EN/ENO=False，OutputParam=['Q','ET'] 不含 ENO，要两项）。

用法：
    python check_slots.py <a.native> [b.native ...]
    python check_slots.py ipc/*.native

退出码：0 = 全部一致；1 = 有不一致（可直接当 CI 断言用）
"""
import glob
import io
import os
import sys
import xml.etree.ElementTree as ET

G_BOX = "{acfc6f68-8e3a-4af5-bf81-3dd512095a46}"


def child(el, name):
    for c in el:
        if (c.get("Name") or "") == name:
            return c
    return None


def names_of(el, pname):
    """取 InputParam/OutputParam 的 Names 列表。"""
    p = child(el, pname)
    if p is None:
        return []
    n = child(p, "Names")
    if n is None:
        return []
    return [(c.text or "").strip() for c in n]


def slots_of(el, items_name):
    """数 InputItems/OutputItems 的槽数。

    ⚠ 这两者都是 Single 包一层 List2，必须数 List2 的子节点。
       直接数外层恒得 1，会把「TON 少写一项」误判成一致。
    """
    holder = child(el, items_name)
    if holder is None:
        return 0
    if holder.tag == "List2":          # AND 框是直接挂 List2
        return len(list(holder))
    # 注意：不能用 `a or b`，ElementTree 元素在 Python 3.12 起真值判断会告警
    lst = child(holder, "OutputItems")
    if lst is None:
        lst = child(holder, "InputItems")
    if lst is None:
        lst = holder
    return len(list(lst))


def check(path):
    root = ET.parse(path).getroot()
    rows = []
    for el in root.iter():
        if el.get("Type") != G_BOX:
            continue
        bt = child(el, "BoxType")
        ct = child(el, "CallType")
        bt = (bt.text or "").strip() if bt is not None else "?"
        ct = (ct.text or "").strip() if ct is not None else "?"

        in_names = names_of(el, "InputParam")
        out_names = names_of(el, "OutputParam")
        n_in = slots_of(el, "InputItems")
        n_out = slots_of(el, "OutputItems")

        # AND 框没有参数名，豁免「槽位 == 参数数」规则（但它至少 2 槽）
        if bt == "AND":
            if n_in < 2:
                rows.append((bt, ct, "AND 只有 %d 个输入槽（必须 >=2）" % n_in))
            continue

        if n_in != len(in_names):
            rows.append((bt, ct, "输入槽 %d != InputParam %d %s"
                         % (n_in, len(in_names), in_names)))
        if n_out != len(out_names):
            rows.append((bt, ct, "输出槽 %d != OutputParam %d %s"
                         % (n_out, len(out_names), out_names)))
    return rows


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 2
    files = []
    for a in args:
        if any(ch in a for ch in "*?["):
            files.extend(sorted(glob.glob(a)))
        else:
            files.append(a)

    bad_total = 0
    for f in files:
        if not os.path.exists(f):
            print("MISSING %s" % f)
            bad_total += 1
            continue
        try:
            rows = check(f)
        except Exception as e:
            print("PARSE FAIL %s : %s" % (os.path.basename(f), e))
            bad_total += 1
            continue
        if rows:
            print("FAIL %s" % os.path.basename(f))
            for bt, ct, msg in rows:
                print("   %-18s %-14s %s" % (bt, ct, msg))
            bad_total += len(rows)
        else:
            print("OK   %s" % os.path.basename(f))

    print()
    print("RESULT: %s (%d 处不一致)" %
          ("PASS" if bad_total == 0 else "FAIL", bad_total))
    return 0 if bad_total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
