# -*- coding: utf-8 -*-
"""把段2 内层 6 个裸 MOVE 支路包成「外层 AND 框 + 连接器」的完整支路。

用户要求：7 和 2 已经是完整的（AND[MOVE, CONN]），其余 6 个（6/8/9/4/3/5）也补齐。

做法：
  1. 从 tree0（值7 的完整支路）克隆外层 AND 框作为模板
  2. 对每个内层裸 MOVE 支路：
     - 新建外层 AND 框（清空 EN/ENO，Flags Fixed=False）
     - InputItems = [原 MOVE 框, 新连接器 {505bff94}]
     - 用新 AND 框替换该支路在 Trees 中的位置
  3. Id 全部重新分配，UniqueIdGenerator 抬高
"""
import copy
import io
import os
import xml.etree.ElementTree as ET

SRC = os.environ.get("PLC_SRC_NATIVE") or "user_manual_full.native"
DST = os.environ.get("PLC_DST_NATIVE") or "startstop_full8.native"

BG   = "{827b9ec2-2032-40da-9f4e-7670ca2d55a8}"
BOX  = "{acfc6f68-8e3a-4af5-bf81-3dd512095a46}"
CONN = "{505bff94-4c90-4e17-ac28-b8ac69d1b9e2}"
NET  = "{d9a99d73-b633-47db-b876-a752acb25871}"

tree = ET.parse(SRC)
root = tree.getroot()

# ---- Id 分配器 ----
ids = []
for e in root.iter("Single"):
    if e.get("Name") == "Id":
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
    for c in el:
        if c.tag == "Single" and c.get("Name") == "Id":
            c.text = str(v)
            return True
    return False


def get_single(el, name):
    return el.find("Single[@Name='%s']" % name)


# ---- 定位 ----
nets = [e for e in root.iter("Single") if e.get("Type") == NET]
top_bg = [c for c in nets[1].find("List2[@Name='NetworkItems']") if c.get("Type") == BG][0]
top_trees = top_bg.find("List2[@Name='Trees']")
top_list = list(top_trees)
print("top trees: %d" % len(top_list))

tree0 = top_list[0]           # 值 7 的完整支路，作为模板
tree2 = top_list[2]           # 含嵌套分支组
tree2_items = tree2.find("List2[@Name='InputItems']")
inner_bg = [c for c in tree2_items if c.get("Type") == BG][0]
inner_trees = inner_bg.find("List2[@Name='Trees']")
inner_list = list(inner_trees)
print("inner trees: %d" % len(inner_list))

# 记录每个内层 MOVE 的目标常量值，用于日志
def move_const(mv):
    ii = mv.find("List2[@Name='InputItems']")
    if ii is None:
        return None
    for slot in ii:
        if (slot.get("Type") or "") != BOX:
            continue
        if get_single(slot, "BoxType") is not None and get_single(slot, "BoxType").text == "AND":
            continue
        for cc in slot.find("List2[@Name='InputItems']"):
            if (cc.get("Type") or "").startswith("{9de7f100"):
                if get_single(cc, "IsContact") is not None and get_single(cc, "IsContact").text == "False":
                    o = cc.find("Single[@Name='Operand']")
                    if o is not None:
                        return o.findtext("Single[@Name='Operand']")
    return None


print("inner MOVE consts:", [move_const(m) for m in inner_list])

# ---- 构造包装器 ----
# 模板：tree0 = AND 框，InputItems = [MOVE框, CONN]
def make_wrapper(move_el):
    """用 tree0 克隆一个外层 AND 框，把 move_el 和新建连接器放进去。"""
    wrapper = copy.deepcopy(tree0)
    # 清空外层 AND 的 EN/ENO（tree0 里是 Null）
    for nm in ("EN", "ENO"):
        e = wrapper.find("Null[@Name='%s']" % nm)
        if e is None:
            # 若模板是 Single，改成 Null
            s = get_single(wrapper, nm)
            if s is not None:
                wrapper.remove(s)
                n = ET.SubElement(wrapper, "Null")
                n.set("Name", nm)
    # Flags: Fixed=False
    fl = get_single(wrapper, "Flags")
    if fl is not None:
        f = fl.find("Single[@Name='Fixed']")
        if f is not None:
            f.text = "False"
    # 重建 InputItems
    old_ii = wrapper.find("List2[@Name='InputItems']")
    if old_ii is not None:
        wrapper.remove(old_ii)
    new_ii = ET.SubElement(wrapper, "List2")
    new_ii.set("Name", "InputItems")
    new_ii.append(move_el)          # [0] MOVE 框
    conn = ET.SubElement(new_ii, "Single")
    conn.set("Type", CONN)
    conn.set("Method", "IArchivable")
    cid = ET.SubElement(conn, "Single")
    cid.set("Name", "Id")
    cid.set("Type", "long")
    cid.text = str(new_id())        # [1] 连接器
    # 外层 AND 新 Id
    set_id(wrapper, new_id())
    return wrapper


# ---- 逐个替换 ----
for i, mv in enumerate(inner_list):
    const = move_const(mv)
    wrapper = make_wrapper(mv)
    inner_trees.remove(mv)
    inner_trees.insert(i, wrapper)
    print("  wrapped inner[%d] const=%s -> AND[MOVE, CONN]" % (i, const))

# 内层分支组本身也重分配 Id
set_id(inner_bg, new_id())
# tree2 外层 AND 也重分配
set_id(tree2, new_id())
set_id(top_bg, new_id())

# ---- UniqueIdGenerator 抬高 ----
for e in root.iter("Single"):
    if e.get("Name") == "UniqueIdGenerator":
        e.text = str(_nid[0] + 200)
        print("UniqueIdGenerator -> %s" % e.text)
        break

tree.write(DST, encoding="utf-8", xml_declaration=True)
print("written:", DST)
