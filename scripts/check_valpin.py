# -*- coding: utf-8 -*-
"""值引脚 IsContact 校验：框的输入引脚被画成触点 = 编译器完全不报错。

为什么需要它（2026-11-26，lead 隐藏实例实证）：
  MOVE/算术/比较/FB 的输入引脚是「值槽」，IsContact 必须 False。
  写成 True（触点形态）时，**预编译 0 错误、编译 0 错误、往返 diff PASS**，
  check_symbols / check_slots / ld_logic 三层也全 PASS——编译器不校验这个语义。
  实测（lead_valpin_neg_c3d81f47.native，MOVE.IN 的 INT 引脚改 True）：
    编译 97f48d64 err=0，唯一差异是导入分类多一条 Text，逻辑层把常量当成了条件。

判据（不看父框类型，看引脚自己声明的类型）：
  {9de7f100} 节点 Operand.Type 非 BOOL 且 IsContact=True  -> 违规。
  · 触点只可能是布尔量，非 BOOL 却被画成触点，必然是值槽写错了形态。
  · 不看 InputParam 对齐：比较框 InputParam 只有 ['EN'] 而 InputItems 恒 3 槽
    （README 铁律 22），按索引对齐会静默跳过 = 漏检。
  · BOOL 引脚不反向判：实测 FB 的 BOOL 输入合法地存在 IsContact=False（值槽
    形态），反向断言会误报（fb_call_test / prg_EM01_Logic 共 20 处）。

用法：
    python check_valpin.py <a.native> [b.native ...]
    python check_valpin.py ipc/*.native

退出码：0 = 全部合规；1 = 有违规
"""
import glob
import os
import sys
import xml.etree.ElementTree as ET

G_PIN = "{9de7f100-1b87-424c-a62e-45b0cfc85ed2}"


def child(el, name):
    for c in el:
        if (c.get("Name") or "") == name:
            return c
    return None


def text_of(el, name, default=""):
    c = child(el, name)
    if c is None or c.text is None:
        return default
    return c.text.strip()


def seq(el, name):
    """取 List2 的直接子项文本列表。"""
    holder = child(el, name)
    if holder is None:
        return []
    return [(c.text or "").strip() for c in holder]


def operand_name(pin):
    """{9de7f100} -> Operand{c9b2f165}.Operand 的变量名/常量文本。"""
    op = child(pin, "Operand")
    if op is None:
        return ""
    inner = child(op, "Operand")
    return ((inner.text if inner is not None else op.text) or "").strip()


def operand_type(pin):
    op = child(pin, "Operand")
    if op is None:
        return ""
    return text_of(op, "Type")


def check(path):
    """返回 [(box, ptype, opnd), ...] 违规行。"""
    root = ET.parse(path).getroot()
    rows = []

    def walk(el, box):
        # 记录最近的祖先框类型，仅用于报错时定位，不参与判定
        b = child(el, "BoxType")
        if b is not None:
            box = (b.text or "").strip()
        if el.tag == "Single" and el.get("Type") == G_PIN:
            ic = text_of(el, "IsContact", "True")
            op = child(el, "Operand")
            otype = text_of(op, "Type") if op is not None else ""
            # 空 Type = 无类型信息（如未接线的空槽），不判
            if ic == "True" and otype and otype.upper() != "BOOL":
                rows.append((box or "?", otype, operand_name(el)))
        for c in el:
            walk(c, box)

    walk(root, None)
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
            for box, otype, opnd in rows:
                print("   %-18s 类型=%-14s 操作数=%-16s -> 值槽 IsContact 应为 False"
                      % (box, otype, opnd or "<空>"))
            bad_total += len(rows)
        else:
            print("OK   %s" % os.path.basename(f))

    print()
    print("RESULT: %s (%d 处值引脚被画成触点)"
          % ("PASS" if bad_total == 0 else "FAIL", bad_total))
    return 0 if bad_total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
