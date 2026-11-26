# -*- coding: utf-8 -*-
# @py3
"""修 45 个 C0046 + 去掉每支路多余的第二个 TRUE。

根因1：声明区只声明了起保停 3 个变量，状态机 8 个变量（iState/xAlarm/xAutoMode/
       xInitDone/xAutoRun/xIniting/xStopClear/xStepMode）根本没声明 -> 45 个 C0046。
根因2：分支组 Input 已有公共前缀 TRUE，每个支路条件链的开头又放了一个 TRUE，
       图形上就成了两个 TRUE 串联 -> 用户说的「第二个 TRUE 多余」。

做法：
  A. 在每个「MOVE 框的 EN 条件 AND 框」的 InputItems 里，删掉第一个 TRUE 引脚。
     注意：只删 EN 条件框里的，不删分支组 Input 的公共 TRUE。
  B. 在 VAR 区补上 8 个变量声明。
"""
import copy
import os
import xml.etree.ElementTree as ET

SRC = os.environ.get("PLC_SRC_NATIVE") or "user_fixed.native"
DST = os.environ.get("PLC_DST_NATIVE") or "startstop_fix45.native"

AND    = "{acfc6f68-8e3a-4af5-bf81-3dd512095a46}"
BRANCH = "{827b9ec2-2032-40da-9f4e-7670ca2d55a8}"
NET    = "{d9a99d73-b633-47db-b876-a752acb25871}"


def nm(e): return e.get("Name", "")
def ty(e): return e.get("Type", "")


def ch(e, n):
    for c in e:
        if nm(c) == n:
            return c
    return None


def boxtext(e, n):
    c = ch(e, n)
    return (c.text or "").strip() if c is not None else ""


def pin_text(pin_el):
    """返回 (操作数, 内部Flags)"""
    op = ""
    fl = ""
    o = ch(pin_el, "Operand")
    if o is not None:
        for d in o:
            if nm(d) == "Operand":
                op = (d.text or "").strip()
            if nm(d) == "Flags":
                f2 = ch(d, "Flags")
                if f2 is not None:
                    fl = (f2.text or "").strip()
    return op, fl


tree = ET.parse(SRC)
root = tree.getroot()

# ---------- Id 分配器 ----------
ids = []
for e in root.iter("Single"):
    if nm(e) == "Id":
        try:
            ids.append(int(e.text))
        except Exception:
            pass
_nid = [max(ids) + 1]


def new_id():
    v = _nid[0]
    _nid[0] += 1
    return v


def set_id(el, v):
    c = ch(el, "Id")
    if c is not None:
        c.text = str(v)
        return True
    return False


# ---------- A. 删除 EN 条件框里多余的 TRUE ----------
removed = 0


def strip_true(box):
    """box 是 AND 框；若 InputItems 第一个是 TRUE 触点，删掉它。"""
    global removed
    ii = ch(box, "InputItems")
    if ii is None or len(ii) < 2:
        return False
    first = ii[0]
    if ty(first) != "{9de7f100-1b87-424c-a62e-45b0cfc85ed2}":
        return False
    op, fl = pin_text(first)
    if op != "TRUE" or fl != "0":
        return False
    ii.remove(first)
    removed += 1
    return True


# 遍历所有 MOVE 框：找 InputItems[0] 是 AND 框（EN 条件框），对它 strip_true
move_count = 0
for el in root.iter("Single"):
    if ty(el) != AND:
        continue
    if boxtext(el, "BoxType") != "MOVE":
        continue
    move_count += 1
    ii = ch(el, "InputItems")
    en = ii[0] if ii is not None and len(ii) > 0 else None
    if en is not None and ty(en) == AND:
        ok = strip_true(en)
        print("MOVE#%d  EN条件框 删TRUE: %s  (剩余 %d 个输入)"
              % (move_count, ok, len(ch(en, "InputItems"))))

print("共 MOVE 框 %d 个，删除多余 TRUE %d 个" % (move_count, removed))

# ---------- B. 补声明 ----------
DECL = [
    "    (* 状态机 *)",
    "    iState     : INT;    // 当前状态字（0=Init 2=Ready 3=Running 4=Paused 5=Done 6..9 其他）",
    "    xAlarm     : BOOL;   // 报警（TRUE 时禁止状态迁移）",
    "    xAutoMode  : BOOL;   // 自动模式",
    "    xInitDone  : BOOL;   // 初始化完成",
    "    xIniting   : BOOL;   // 初始化中",
    "    xAutoRun   : BOOL;   // 自动运行中",
    "    xStopClear : BOOL;   // 停止/清除",
    "    xStepMode  : BOOL;   // 单步模式",
]

td = None
for el in root.iter("Single"):
    if nm(el) == "TextDocument":
        td = el
        break
arr = ch(td, "TextLines")

# 找到 END_VAR 那一行，在它之前插入
end_idx = None
for i, s in enumerate(arr):
    t = ch(s, "Text")
    if t is not None and (t.text or "").strip() == "END_VAR":
        end_idx = i
        break

if end_idx is None:
    raise SystemExit("没找到 END_VAR")

# 模板行（克隆 Id/Tag 结构）
tpl = arr[end_idx - 1]
line_id = 907
for k, text in enumerate(DECL):
    line = copy.deepcopy(tpl)
    set_id(line, line_id)
    line_id += 1
    tt = ch(line, "Text")
    tt.text = text
    arr.insert(end_idx + k, line)

print("已插入 %d 行声明，END_VAR 现在位于 index %d" % (len(DECL), end_idx + len(DECL)))

# ---------- UniqueIdGenerator 抬高 ----------
for e in root.iter("Single"):
    if nm(e) == "UniqueIdGenerator":
        e.text = str(_nid[0] + 500)
        break

tree.write(DST, encoding="utf-8", xml_declaration=True)
print("written:", DST)
