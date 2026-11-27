# -*- coding: utf-8 -*-
"""扫描所有 LD 框节点：BoxType vs CallType 的编码方式。"""
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
rows = json.loads(io.open(INDEX,"r",encoding="utf-8").read())
best = {}
for r in rows:
    n = r.get("name")
    if not n: continue
    if n not in best or r["bytes"] > best[n]["bytes"]:
        best[n] = r
TEST = re.compile(r"(prg_Stn|prg_Cyl|prg_Repro|prg_.*Test|prg_.*Verify|fb_.*Test|fb_.*Verify|prg_PackML|prg_FbCall|prg_LdLearn|prg_AxisCall|fb_AxisSkel|prg_SrCoil|prg_FuncRet|prg_GvlVerify|prg_Jump|prg_ValPin|prg_Edge|prg_MsgFlood|prg_ErrFlood|prg_NoTask)")
ld = [r for r in best.values() if r.get("lang") == "LD" and not TEST.search(r.get("name") or "")]

BOX = "acfc6f68"
combo = collections.Counter()      # (BoxType, CallType)
by_pou = collections.defaultdict(collections.Counter)
slot_info = collections.Counter()  # (calltype_or_boxtype, n_inputitems)
edge_info = collections.Counter()  # (name, has_inputflags, first_flag)

for r in ld:
    p = os.path.join(RAW, r["file"])
    try:
        root = ET.parse(p).getroot()
    except Exception:
        continue
    for el in root.iter():
        if not (el.get("Type") or "").startswith("{" + BOX):
            continue
        bt = ct = None
        ii = None; iflags = None
        for c in el:
            nm = c.get("Name")
            if nm == "BoxType":
                bt = (c.text or "").strip()
            elif nm == "CallType":
                ct = (c.text or "").strip()
            elif nm == "InputItems":
                ii = c
            elif nm == "InputFlags":
                iflags = c
        key = (bt or "", ct or "")
        combo[key] += 1
        by_pou[r["name"]][key] += 1
        n_slots = len(list(ii)) if ii is not None else 0
        slot_info[(ct or bt or "?", n_slots)] += 1
        if iflags is not None:
            first = None
            for s in iflags.iter("Single"):
                if s.get("Name") == "Flags":
                    first = (s.text or "").strip(); break
            edge_info[((ct or bt or "?"), first)] += 1

L = []
def w(s=""): L.append(s)
w("# LD 框编码扫描：BoxType vs CallType（模板 %d 个 LD POU）" % len(ld))
w("")
w("## 1. (BoxType, CallType) 组合分布  Top 40")
w("")
w("| BoxType | CallType | 次数 | 出现在几个 POU |")
w("|---|---|---|---|")
pou_per = collections.Counter()
for n, c in by_pou.items():
    for k in c: pou_per[k] += 1
for (bt, ct), v in combo.most_common(40):
    w("| %s | %s | %d | %d |" % (bt or "(空)", ct or "(空)", v, pou_per[(bt,ct)]))
w("")
w("组合种类 = %d；其中只有 BoxType 的 = %d，只有 CallType 的 = %d，两者都有 = %d" % (
    len(combo),
    sum(1 for (b,c) in combo if b and not c),
    sum(1 for (b,c) in combo if c and not b),
    sum(1 for (b,c) in combo if b and c)))
w("")
w("## 2. 每种框的 InputItems 槽数")
w("")
w("| 框 | 槽数 | 次数 |")
w("|---|---|---|")
for (k, n), v in sorted(slot_info.items(), key=lambda x: -x[1])[:40]:
    w("| %s | %d | %d |" % (k, n, v))
w("")
w("## 3. InputFlags 非空情况（边沿）")
w("")
w("| 框 | 第0项 Flags | 次数 |")
w("|---|---|---|")
for (k, f), v in sorted(edge_info.items(), key=lambda x: -x[1])[:30]:
    w("| %s | %s | %d |" % (k, f, v))
w("")
io.open(r"D:\plc_mcp\ld_study\report_03.md","w",encoding="utf-8").write("\n".join(L))
print("ok combos=%d" % len(combo))
