# -*- coding: utf-8 -*-
"""LD 逻辑层验收：把 native 的图形拓扑还原成布尔表达式并规范化比对。

第四层验收（双分类/往返 diff/check_slots 都证明不了「画的是想要的逻辑」）：
图形还原成布尔表达式后与期望比对，XML 文本/Id/节点顺序变了只要逻辑等价即通过。
（思路学自 Wayan123/multi-plc-agent：The verification compares logic, not XML）

节点结构（实测）：
  串联条件 = AND 框 {acfc6f68}；并联分支 = 分支组 {827b9ec2}（Trees ≥2，否则 IDE 崩）
  触点 = {9de7f100}，Flags=1 即常闭；线圈 = {c9b2f165} 且 IsCoil=True

用法：
    python ld_logic.py <a.native>                    # 打印每个网络的逻辑签名
    python ld_logic.py <a.native> <b.native>         # 逻辑等价性比对
    python ld_logic.py <a.native> --expect exp.json  # 与期望表达式比对

退出码：0 = 全部等价/匹配；1 = 有差异
"""
import io
import json
import os
import sys
import xml.etree.ElementTree as ET

# 节点类型 GUID（去掉花括号，本模块统一用不带括号的形式比对）
G_BOX = "acfc6f68-8e3a-4af5-bf81-3dd512095a46"      # 功能框（含 AND）
G_BRANCH = "827b9ec2-2032-40da-9f4e-7670ca2d55a8"   # 并联分支组
G_CONTACT = "9de7f100-1b87-424c-a62e-45b0cfc85ed2"  # 触点 / 值引脚
G_OPERAND = "c9b2f165-48a2-4a45-8326-3952d8a3d708"  # 操作数
G_NETITEM = "9873c309-1f09-4ebf-9078-42d8057ef11b"  # 网络项
G_CONNECTOR = "5f9848d3-568d-4cc5-9e31-8e28e9607ff1"  # 连接器（电源流入口）
G_NETWORK = "d9a99d73-b633-47db-b876-a752acb25871"   # 网络


def _g(t):
    """把 {xxx-...} 归一成不带花括号的小写 GUID。"""
    if not t:
        return ""
    return t.strip().strip("{}").lower()


def child(el, name):
    for c in el:
        if (c.get("Name") or "") == name:
            return c
    return None


def children(el, name):
    return [c for c in el if (c.get("Name") or "") == name]


def text_of(el, name, default=""):
    c = child(el, name)
    if c is None or c.text is None:
        return default
    return c.text.strip()


def flag_of(el, *path):
    """取嵌套的 Flags 整数值，如 flag_of(contact,'Operand','Flags','Flags')。"""
    cur = el
    for p in path:
        cur = child(cur, p)
        if cur is None:
            return None
    try:
        return int((cur.text or "0").strip())
    except Exception:
        return None


def operand_name(el):
    """取变量名。

    ⚠ 两种形态都要处理（本机实测 2026-11-25）：
      · 触点/引脚：el 是 {9de7f100}，其子节点 Operand 是 {c9b2f165} 容器，
        变量名在容器的 **Operand 子节点** 里（容器自身 .text 是 None）。
      · 直接传入 {c9b2f165} 容器：同样取内部 Operand 子节点。
    """
    op = child(el, "Operand")
    if op is None:
        op = el
    inner = child(op, "Operand")
    if inner is not None:
        return (inner.text or "").strip()
    return (op.text or "").strip()


# ═══════════════════════════════════════════════════════════════════
# 表达式：字符串 = 单个字面量；("NOT", x)；("AND", ...)；("OR", ...)
# ═══════════════════════════════════════════════════════════════════

def flat(op, items):
    """合并同运算符、去掉 AND 里的恒真项。"""
    out = []
    for it in items:
        if it == "TRUE" and op == "AND":
            continue
        if isinstance(it, tuple) and it[0] == op:
            out.extend(it[1:])
        else:
            out.append(it)
    if not out:
        return "TRUE" if op == "AND" else "FALSE"
    return out[0] if len(out) == 1 else tuple([op] + out)


def dnf(e):
    """化成「和之积」的集合形式；梯形图没有取反组，所以这是精确的。"""
    if isinstance(e, str):
        return frozenset({frozenset()}) if e == "TRUE" else frozenset({frozenset({e})})
    if e[0] == "NOT":
        return frozenset({frozenset({"NOT " + str(e[1])})})
    if e[0] == "OR":
        out = frozenset()
        for x in e[1:]:
            out = out | dnf(x)
        return out
    # AND
    out = frozenset({frozenset()})
    for x in e[1:]:
        out = frozenset(a | b for a in out for b in dnf(x))
    return out


def render(e):
    """规范文本：OR 的 AND 项、每项内字面量都排序 → 逻辑等价则文本相等。"""
    terms = sorted((" AND ".join(sorted(t)) or "TRUE") for t in dnf(e))
    out = []
    for t in terms:
        if " AND " in t and len(terms) > 1:
            out.append("(%s)" % t)
        else:
            out.append(t)
    return " OR ".join(out)


# ═══════════════════════════════════════════════════════════════════
# 拓扑解析
# ═══════════════════════════════════════════════════════════════════

def node_expr(el):
    """把一个图形节点还原成布尔表达式。"""
    g = _g(el.get("Type"))
    if g == G_BRANCH:
        # 并联分支组：Trees 下每条支路是串联条件
        trees = child(el, "Trees")
        legs = []
        if trees is not None:
            for leg in trees:
                legs.append(series_expr([leg]))
        return flat("OR", legs)
    if g == G_BOX:
        ct = text_of(el, "CallType")
        if ct == "And":
            items = child(el, "InputItems")
            subs = [node_expr(x) for x in (items if items is not None else [])]
            return flat("AND", subs)
        # 其它功能框：作为不透明块，用 BoxType(实例) 表示其输出条件
        bt = text_of(el, "BoxType") or "?"
        inst_el = child(el, "Instance")
        inst = text_of(el, "Instance", "") or operand_name(inst_el if inst_el is not None else el)
        return "BLOCK:%s(%s)" % (bt, inst)
    if g == G_CONTACT:
        name = operand_name(el)
        fl = flag_of(el, "Operand", "Flags", "Flags") or 0
        isc = text_of(el, "IsContact", "True")
        if isc == "False":
            # 值引脚（常量/表达式输入），不是条件
            return name or "?"
        return ("NOT " + name) if (fl & 1) else name
    if g == G_CONNECTOR:
        inp = child(el, "Input")
        if inp is None:
            return "TRUE"
        return node_expr(inp)
    return "UNKNOWN:%s" % (g[:8] or el.tag)


def series_expr(nodes):
    """一组串联节点 → AND 表达式。"""
    return flat("AND", [node_expr(n) for n in nodes])


def parse_network(net):
    """解析一个 Network → {comment, outputs:[...], logic:str}。"""
    comment = text_of(net, "Comment")
    items = child(net, "NetworkItems")
    outputs = []
    logic = "TRUE"
    if items is None:
        return {"comment": comment, "outputs": outputs, "logic": logic}
    for item in items:
        if _g(item.get("Type")) != G_NETITEM:
            continue
        rv = child(item, "RValue")
        if rv is not None:
            logic = render(node_expr(rv))
        outs = child(item, "OutputItems")
        if outs is None:
            continue
        # ⚠ OutputItems 是 Single 包一层 List2（与 check_slots 同一个坑）：
        #   直接数外层恒得 1 项，必须取内层 List2 的子节点。
        inner = child(outs, "OutputItems")
        holder = inner if inner is not None else outs
        for o in holder:
            og = _g(o.get("Type"))
            if og == G_OPERAND:
                iscoil = text_of(o, "IsCoil", "False")
                nm = operand_name(o)
                if iscoil == "True":
                    # S/R 线圈区分（lead 交叉验证发现漏洞：只判 IsCoil 时
                    # Flags 2(S)→3(R) 负样本能通过——置位改复位，状态机永不进 IDLE）
                    # 实测：0=普通线圈，2=Set，3=Reset。Flags 在线圈节点直接下面。
                    fl = flag_of(o, "Flags", "Flags") or 0
                    kind = {0: "COIL", 2: "COIL_S", 3: "COIL_R"}.get(fl, "COIL_F%s" % fl)
                else:
                    kind = "OPERAND"
                outputs.append({"kind": kind, "target": nm})
            elif og == G_BOX:
                outputs.append({"kind": "BLOCK",
                                "target": text_of(o, "BoxType") or "?"})
    return {"comment": comment, "outputs": outputs, "logic": logic}


def find_networks(root):
    """取第一个 NetworkList 下的所有 Network。"""
    for el in root.iter():
        if (el.get("Name") or "") == "NetworkList":
            return [n for n in el if _g(n.get("Type")) == G_NETWORK]
    return []


def logic_signature(path):
    """返回 [ {comment, outputs, logic}, ... ]，每个网络一条。"""
    root = ET.parse(path).getroot()
    return [parse_network(n) for n in find_networks(root)]


def key_of(net):
    """可比对的关键签名：输出列表 + 规范化逻辑。"""
    outs = "|".join("%s:%s" % (o["kind"], o["target"]) for o in net["outputs"])
    return "%s  <=  %s" % (outs, net["logic"])


# ═══════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__)
        return 2

    if len(args) == 1:
        sig = logic_signature(args[0])
        print("=== %s : %d 个网络 ===" % (os.path.basename(args[0]), len(sig)))
        for i, n in enumerate(sig):
            c = ("  // " + n["comment"][:40]) if n["comment"] else ""
            print("  [%02d] %s%s" % (i + 1, key_of(n), c))
        return 0

    a, b = args[0], args[1]
    sa, sb = logic_signature(a), logic_signature(b)
    print("=== 逻辑比对 ===")
    print("  A: %s (%d 网络)" % (os.path.basename(a), len(sa)))
    print("  B: %s (%d 网络)" % (os.path.basename(b), len(sb)))
    bad = 0
    if len(sa) != len(sb):
        print("!! 网络数不同：%d vs %d" % (len(sa), len(sb)))
        bad += 1
    for i in range(min(len(sa), len(sb))):
        ka, kb = key_of(sa[i]), key_of(sb[i])
        if ka != kb:
            bad += 1
            print("  [%02d] 逻辑不同" % (i + 1))
            print("     A: %s" % ka)
            print("     B: %s" % kb)
        else:
            print("  [%02d] 等价  %s" % (i + 1, ka))
    print()
    print("RESULT: %s (%d 处不同)" % ("PASS" if bad == 0 else "FAIL", bad))
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
