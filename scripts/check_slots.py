# -*- coding: utf-8 -*-
# @py3
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

# Instance.Operand 三态规律（2026-11-25 实测确认）：
#   FunctionBlock -> <Single Name="Operand">实例名</Single>
#   Action / Function / Program        -> <Null Name="Operand" />
# 写错形态 IDE 不报错，但会在框上方多画一个可填参数的小方框
# （用户两次截图反馈证实），且往返 diff 查不出来，只能靠这里断言。
_OP_NULL_CT = {"Action", "Function", "Program"}


def check_operand(el, bt, ct):
    """校验 Instance.Operand 形态与 CallType 匹配。"""
    inst = child(el, "Instance")
    if inst is None:
        return None
    op = child(inst, "Operand")
    if op is None:
        return None
    is_null = (op.tag == "Null")
    if ct in _OP_NULL_CT and not is_null:
        return ("CallType=%s 的 Instance.Operand 必须是 <Null/>，"
                "实际是 <%s>（空 <Single> 会让 IDE 多画可填参数小方框）"
                % (ct, op.tag))
    if ct == "FunctionBlock" and is_null:
        return ("CallType=FunctionBlock 的 Instance.Operand 必须是"
                "<Single>实例名</Single>，实际是 <Null/>")
    return None


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

    ⚠ 2026-11-25 全工程 126 POU 实测容器不对称（557 框无一例外）：
       InputItems  = <List2 Name="InputItems"> 直接挂在框下
       OutputItems = <Single Name="OutputItems"> 内包一层 <List2 Name="OutputItems">
       用同一段代码取两者会把 MOVE 的输入槽数成 0（踩过）。
    """
    holder = child(el, items_name)
    if holder is None:
        return 0
    if holder.tag == "List2":          # InputItems：直接挂 List2
        return len(list(holder))
    # OutputItems：Single 包一层 List2（内层与外层同名）
    lst = child(holder, "OutputItems")
    if lst is None:
        lst = child(holder, "InputItems")
    if lst is None:
        lst = holder
    return len(list(lst))


G_NESTED_BOX = "acfc6f68-8e3a-4af5-bf81-3dd512095a46"   # 功能框（含嵌套框）
G_CONTACT = "9de7f100-1b87-424c-a62e-45b0cfc85ed2"        # 触点/值引脚


def _input_exempt(el, bt):
    """IDE 原生形态豁免：这些框「输入槽数 != InputParam 名数」是正常的。

    2026-11-25 真实产线工程全量实测（详见 native-structure.md「全量结构普查」）：
      ① MOVE 嵌套框接 EN：槽0 是功能框，前框 ENO 链式供 EN，InputParam 只有 [EN]
      ② MOVE 多槽触点链：槽0 是触点且槽 > 2（末槽为 IN 常量），EN 直接串联
      ③ 比较框（EQ/NE/GT/LT/GE/LE）：InputParam 只有 ['EN'] 一个名字，
         但 InputItems 恒为 3 槽（槽0=EN 触点、槽1/2=左右操作数）。
         实测 EQ 725 / GT 67 / LT 53 / GE 47 / LE 17 / NE 2 处，无一例外。
         **不能按 len(InputItems)==len(InputParam) 校验比较框**，
         否则模板原生 POU 会被全部误报（本轮 `prg_ReproStudy` 即被误报 3 处）。
      ④ ADD / LE 等「EN + 多操作数」框同理：InputParam=['EN'] 但槽数 = 操作数+1。
    """
    lst = child(el, "InputItems")
    if lst is None or lst.tag != "List2" or len(lst) == 0:
        return False
    kind = (lst[0].get("Type") or "").strip("{}")
    n = len(lst)

    # ③ 比较框：InputParam 恒为 ['EN']，槽数恒为 3
    if bt in ("EQ", "NE", "GT", "LT", "GE", "LE"):
        return True

    # ④ 算术/选择框：InputParam 只有 EN，槽数 = 操作数 + 1
    if bt in ("ADD", "SUB", "MUL", "DIV", "MOD", "SEL", "MUX", "LIMIT"):
        return True

    # ⑤ MOVE：InputParam 只有 ['EN']，InputItems 恒 2 槽（EN 电源流 + IN 源值）。
    #    模板实测槽0 形态：CONN 806 / PIN 326 / BOX:AND 155 / BRANCH 40 —— 全部 2 槽。
    #    「槽数 == InputParam 数」对 MOVE 完全不成立，一律豁免。
    if bt == "MOVE":
        return True

    # ① 嵌套框接 EN ② 多槽触点链
    return kind == G_NESTED_BOX or (kind == G_CONTACT and n > 2)


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
        # 实测依据（2026-11-25 prg_SlotTest）：1 槽 AND → 预编译报
        #   [Error] 'AND'需要至少'2' 个操作数
        #   [Error] 检测到不一致元素 (不正确的输入序列)
        # ⚠ 单条件 rung 不要建 AND 框，触点直挂 NETITEM.RValue（见 native-structure.md）
        if bt == "AND":
            if n_in < 2:
                rows.append((bt, ct, "AND 只有 %d 个输入槽（必须 >=2）；"
                                      "单条件请让触点直挂 RValue" % n_in))
            continue

        # Instance.Operand 三态断言（IDE/编译/往返 diff 都查不出来）
        msg = check_operand(el, bt, ct)
        if msg:
            rows.append((bt, ct, msg))

        # IDE 原生形态豁免（MOVE 嵌套/多槽触点链、比较框 3 槽、算术框多操作数）
        if n_in != len(in_names) and not _input_exempt(el, bt):
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
