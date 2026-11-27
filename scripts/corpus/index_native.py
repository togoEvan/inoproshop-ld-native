# -*- coding: utf-8 -*-
import os, io, json, glob, collections
import xml.etree.ElementTree as ET

# --- 语料目录（可用环境变量覆盖，默认当前工作目录下的 ld_study）---
import os
LD_BASE = os.environ.get('LD_BASE') or os.path.join(os.getcwd(), 'ld_study')
RAW = os.environ.get('LD_RAW') or os.path.join(LD_BASE, 'raw')
PROJ = os.environ.get('LD_PROJ') or os.path.join(LD_BASE, 'proj', 'study_lead.project')
INDEX = os.environ.get('LD_INDEX') or os.path.join(LD_BASE, 'index.json')
OUT_SHAPES = os.environ.get('LD_SHAPES') or os.path.join(LD_BASE, 'net_shapes.json')
LOG = os.environ.get('LD_EXPORT_LOG') or os.path.join(LD_BASE, 'export_all.log')
LD = "25e509de"; ST = "3b83b776"
rows = []
for p in sorted(glob.glob(os.path.join(RAW, "*.native"))):
    rec = {"file": os.path.basename(p), "bytes": os.path.getsize(p)}
    try:
        txt = io.open(p, "r", encoding="utf-8", errors="replace").read()
    except Exception as e:
        rec["err"] = str(e); rows.append(rec); continue
    try:
        root = ET.fromstring(txt)
    except Exception as e:
        rec["err"] = "xml" + str(e)[:60]; rows.append(rec); continue
    # 根 EntryList 的第一个 Entry（IsRoot=True）
    ent = root.find(".//List2[@Name='EntryList']/Single")
    if ent is None:
        rec["err"] = "noentry"; rows.append(rec); continue
    mo = ent.find("./Single[@Name='MetaObject']")
    nm = mo.find("./Single[@Name='Name']") if mo is not None else None
    rec["name"] = (nm.text or "").strip() if nm is not None else None
    tg = mo.find("./Single[@Name='TypeGuid']") if mo is not None else None
    rec["typeguid"] = (tg.text or "").strip() if tg is not None else None
    path = []
    pa = ent.find("./Array[@Name='Path']")
    if pa is not None:
        for s in pa.findall("Single"):
            path.append((s.text or "").strip())
    rec["path"] = path
    rec["depth"] = len(path)
    # Implementation
    impl = None
    for s in root.iter("Single"):
        if s.get("Name") == "Implementation":
            impl = (s.get("Type") or "").strip("{}").lower(); break
    rec["impl"] = impl
    rec["lang"] = ("LD" if impl and impl.startswith(LD) else ("ST" if impl and impl.startswith(ST) else None))
    nets = sum(1 for n in root.iter() if "d9a99d73" in (n.get("Type") or ""))
    rec["networks"] = nets
    boxes = collections.Counter()
    for s in root.iter("Single"):
        if s.get("Name") == "BoxType":
            boxes[(s.text or "").strip()] += 1
    rec["n_boxes"] = sum(boxes.values())
    rec["boxes"] = dict(boxes)
    rows.append(rec)

io.open(INDEX, "w", encoding="utf-8").write(json.dumps(rows, ensure_ascii=False, indent=1))

# 去重：按 name 取字节最大的那份
best = {}
for r in rows:
    n = r.get("name")
    if not n: continue
    if n not in best or r["bytes"] > best[n]["bytes"]:
        best[n] = r
uniq = list(best.values())
ld = [r for r in uniq if r.get("lang") == "LD"]
st = [r for r in uniq if r.get("lang") == "ST"]
other = [r for r in uniq if r.get("lang") is None]
print("files=%d  uniq=%d  LD=%d  ST=%d  other=%d" % (len(rows), len(uniq), len(ld), len(st), len(other)))
print("")
print("=== LD POUs (by networks desc) ===")
for r in sorted(ld, key=lambda x: -(x.get("networks") or 0)):
    print("%3d nets %5d boxes %7dB  %-52s %s" % (r["networks"], r["n_boxes"], r["bytes"], r["name"], "/".join(r["path"][:3])))
print("")
print("=== other (no impl) top15 by bytes ===")
for r in sorted(other, key=lambda x: -x["bytes"])[:15]:
    print("%7dB %3d nets  %-45s path=%s" % (r["bytes"], r["networks"], r["name"], "/".join(r["path"])))
