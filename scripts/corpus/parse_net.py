# -*- coding: utf-8 -*-
"""按网络拆解 LD POU，统计网络形状（顶层元素 + 框组合）。"""
import io, json, os, collections, re
import xml.etree.ElementTree as ET

# --- 语料目录（可用环境变量覆盖，默认当前工作目录下的 ld_study）---
import os
LD_BASE = os.environ.get('LD_BASE') or os.path.join(os.getcwd(), 'ld_study')
RAW = os.environ.get('LD_RAW') or os.path.join(LD_BASE, 'raw')
PROJ = os.environ.get('LD_PROJ') or os.path.join(LD_BASE, 'proj', 'study_lead.project')
INDEX = os.environ.get('LD_INDEX') or os.path.join(LD_BASE, 'index.json')
OUT_SHAPES = os.environ.get('LD_SHAPES') or os.path.join(LD_BASE, 'net_shapes.json')
LOG = os.environ.get('LD_EXPORT_LOG') or os.path.join(LD_BASE, 'export_all.log')

G = {
 "branch": "827b9ec2", "box": "acfc6f68", "contact": "9de7f100",
 "operand": "c9b2f165", "connector": "5f9848d3", "outconn": "505bff94",
 "netitem": "9873c309", "network": "d9a99d73",
}

def kids(node):
    """返回直接子元素列表中属于 LD 图形的节点"""
    out = []
    for c in list(node):
        out.append(c)
    return out

def typeguid(el):
    t = (el.get("Type") or "").strip("{}").lower()
    return t

def kind_of(el):
    t = typeguid(el)
    for k, g in G.items():
        if t.startswith(g):
            return k
    return "?"

def box_type(el):
    for s in el.iter("Single"):
        if s.get("Name") == "BoxType":
            return (s.text or "").strip()
    return "?"

def walk_kind(el, acc, depth=0):
    """递归收集子树里所有图形节点的 kind 与 box 类型"""
    k = kind_of(el)
    if k != "?":
        acc.append((k, box_type(el) if k == "box" else None))
    for c in list(el):
        walk_kind(c, acc, depth+1)

rows = json.loads(io.open(INDEX, "r", encoding="utf-8").read())
best = {}
for r in rows:
    n = r.get("name")
    if not n: continue
    if n not in best or r["bytes"] > best[n]["bytes"]:
        best[n] = r
TEST = re.compile(r"(prg_Stn|prg_Cyl|prg_Repro|prg_.*Test|prg_.*Verify|fb_.*Test|fb_.*Verify|prg_PackML|prg_FbCall|prg_LdLearn|prg_AxisCall|fb_AxisSkel|prg_SrCoil|prg_FuncRet|prg_GvlVerify|prg_Jump|prg_ValPin|prg_Edge|prg_MsgFlood|prg_ErrFlood|prg_NoTask)")
ld = [r for r in best.values() if r.get("lang") == "LD" and not TEST.search(r.get("name") or "")]

shape_counter = collections.Counter()
shape_examples = {}
pou_profiles = {}

for r in ld:
    p = os.path.join(RAW, r["file"])
    try:
        root = ET.parse(p).getroot()
    except Exception as e:
        continue
    nets = [n for n in root.iter() if "d9a99d73" in (n.get("Type") or "")]
    prof = {"nets": len(nets), "shapes": collections.Counter(), "box_per_net": []}
    for ni, net in enumerate(nets):
        # 取网络下的 NetworkItems（直接子 List2）
        items = None
        for lst in net.iter("List2"):
            if lst.get("Name") == "NetworkItems":
                items = lst
        if items is None:
            continue
        acc = []
        tops = []
        for top in list(items):
            k = kind_of(top)
            tops.append(k)
            walk_kind(top, acc)
        boxes = [b for (k, b) in acc if k == "box" and b]
        bc = collections.Counter(boxes)
        # 形状 = 顶层元素计数 + 框类型计数
        sig = "|".join("%s:%d" % (k, tops.count(k)) for k in sorted(set(tops))) + " || " + \
              "+".join("%s:%d" % (b, c) for b, c in sorted(bc.items())) if bc else "".join(
              "%s:%d" % (k, tops.count(k)) for k in sorted(set(tops)))
        shape_counter[sig] += 1
        if sig not in shape_examples:
            shape_examples[sig] = "%s#%d" % (r["name"], ni+1)
        prof["shapes"][sig] += 1
        prof["box_per_net"].append(sum(bc.values()))
    pou_profiles[r["name"]] = {
        "nets": prof["nets"],
        "shape_kinds": len(prof["shapes"]),
        "top_shapes": [[s, c] for s, c in prof["shapes"].most_common(5)],
        "box_per_net_avg": round(sum(prof["box_per_net"])/max(1,len(prof["box_per_net"])), 2),
    }

io.open(OUT_SHAPES, "w", encoding="utf-8").write(json.dumps({
    "shapes": [[s, c, shape_examples.get(s)] for s, c in shape_counter.most_common(200)],
    "pou": pou_profiles,
}, ensure_ascii=False, indent=1))

L = []
def w(s=""): L.append(s)
w("# LD 网络形状统计（模板 58 个 LD POU，共 %d 个网络）" % sum(v["nets"] for v in pou_profiles.values()))
w("")
w("## 1. 最常见的网络形状 Top 25")
w("")
w("| # | 次数 | 形状（顶层元素 || 框类型） | 例 |")
w("|---|---|---|---|")
for i, (s, c) in enumerate(shape_counter.most_common(25), 1):
    w("| %d | %d | %s | %s |" % (i, c, s.replace("|", "\\|"), shape_examples[s]))
w("")
w("形状种类总数 = %d" % len(shape_counter))
w("")
w("## 2. 各 POU 画像（网络数 / 出现几种形状 / 平均框数）")
w("")
w("| POU | 网络 | 形状种类 | 平均框/网络 |")
w("|---|---|---|---|")
for n, v in sorted(pou_profiles.items(), key=lambda x: -x[1]["nets"]):
    w("| %s | %d | %d | %s |" % (n, v["nets"], v["shape_kinds"], v["box_per_net_avg"]))
io.open(r"D:\plc_mcp\ld_study\report_02.md","w",encoding="utf-8").write("\n".join(L))
print("ok shapes=%d pou=%d" % (len(shape_counter), len(pou_profiles)))
