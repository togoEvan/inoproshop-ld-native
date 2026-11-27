# -*- coding: utf-8 -*-
"""LD native 结构树打印器：python ld_dump.py <native> [起始网络] [结束网络]"""
import io, sys
import xml.etree.ElementTree as ET
# --- 语料目录（可用环境变量覆盖，默认当前工作目录下的 ld_study）---
import os
LD_BASE = os.environ.get('LD_BASE') or os.path.join(os.getcwd(), 'ld_study')
RAW = os.environ.get('LD_RAW') or os.path.join(LD_BASE, 'raw')
PROJ = os.environ.get('LD_PROJ') or os.path.join(LD_BASE, 'proj', 'study_lead.project')
INDEX = os.environ.get('LD_INDEX') or os.path.join(LD_BASE, 'index.json')
OUT_SHAPES = os.environ.get('LD_SHAPES') or os.path.join(LD_BASE, 'net_shapes.json')
LOG = os.environ.get('LD_EXPORT_LOG') or os.path.join(LD_BASE, 'export_all.log')

G = {"branch":"827b9ec2","box":"acfc6f68","pin":"9de7f100","conn":"5f9848d3",
     "outconn":"505bff94","netitem":"9873c309","network":"d9a99d73","operand":"c9b2f165"}

def T(el): return (el.get("Type") or "").strip("{}").lower()
def kind(el):
    t = T(el)
    for k, g in G.items():
        if t.startswith(g): return k
    return None
def child(el, name):
    if el is None: return None
    for c in el:
        if c.get("Name") == name: return c
    return None
def ctext(el, name):
    c = child(el, name)
    return (c.text or "").strip() if c is not None and c.text else ""
def descendants(el):
    return list(el.iter()) if el is not None else []

def operand_name(el):
    """从 Operand 容器里取变量名（可能多层嵌套）"""
    if el is None: return ""
    # 直接子 Operand
    nm = child(el, "Operand")
    if nm is not None and nm.text and nm.text.strip():
        return nm.text.strip()
    # 深一层
    for c in el:
        if c.get("Name") == "Operand":
            t = operand_name(c)
            if t: return t
    for d in descendants(el):
        if d.get("Name") == "Operand" and d.text and d.text.strip():
            return d.text.strip()
    return ""

def flags_of(el):
    """取 Operand 的 Flags.Flags 值"""
    for d in descendants(el):
        if d.get("Name") == "Flags":
            v = child(d, "Flags")
            if v is not None and v.text:
                try: return int(v.text.strip())
                except: return None
    return None

def pin_names(el):
    """框的 InputParam / OutputParam 名字列表"""
    res = {}
    for nm in ("InputParam", "OutputParam"):
        c = child(el, nm)
        if c is None: continue
        names = []
        for d in descendants(c):
            if d.get("Name") == "Names":
                for s in d:
                    names.append((s.text or "").strip())
        res[nm] = names
    return res

def input_flags_edge(el):
    """InputFlags 第 0 项是否带边沿（Flags=16）"""
    c = child(el, "InputFlags")
    if c is None: return None
    first = True
    for s in c.iter("Single"):
        if s.get("Name") == "Flags":
            try: return int((s.text or "0").strip())
            except: return None
    return None

def dump(el, depth, out):
    k = kind(el)
    ind = "  " * depth
    if k == "box":
        bt = ctext(el, "BoxType")
        if bt in ("AND", "OR") or not bt:
            out.append("%s[%s]" % (ind, bt or "AND?"))
            for c in el:
                dump(c, depth + 1, out)
            return
        pn = pin_names(el)
        of = input_flags_edge(el)
        out.append("%sBOX %s  pins_in=%s pins_out=%s%s" % (
            ind, bt, pn.get("InputParam"), pn.get("OutputParam"),
            ("  EDGE(in0 flags=%d)" % of) if of else ""))
        ii = child(el, "InputItems")
        if ii is not None:
            out.append(ind + "  IN:")
            for c in ii:
                dump(c, depth + 2, out)
        oi = child(el, "OutputItems")
        if oi is not None:
            out.append(ind + "  OUT:")
            for c in oi:
                dump(c, depth + 2, out)
        return
    if k == "pin":
        isc = ctext(el, "IsContact")
        op = child(el, "Operand")
        nm = operand_name(op)
        fl = flags_of(el)
        if isc == "True":
            tag = "CONTACT"
            if fl and fl & 1: tag += "~"
            if fl == 2: tag += "^"
        elif op is not None and ctext(op, "IsCoil") == "True":
            tag = "COIL"
            if fl == 2: tag += "_S"
            elif fl == 3: tag += "_R"
        else:
            tag = "OPERAND"
        out.append("%s%s %s%s" % (ind, tag, nm, ("  (flags=%d)" % fl) if fl not in (None, 0) else ""))
        return
    if k == "branch":
        out.append(ind + "BRANCH")
        inp = child(el, "Input")
        if inp is not None:
            out.append(ind + "  guard:")
            for c in inp:
                dump(c, depth + 2, out)
        tr = child(el, "Trees")
        if tr is not None:
            for i, t in enumerate(tr, 1):
                out.append(ind + "  T%d:" % i)
                for c in t:
                    dump(c, depth + 2, out)
        return
    if k == "operand":
        nm = operand_name(el)
        ic = ctext(el, "IsCoil")
        out.append("%sOPERAND %s%s" % (ind, nm, " (coil)" if ic == "True" else ""))
        return
    if k in ("conn", "outconn"):
        out.append(ind + ("CONN" if k == "conn" else "OUTCONN"))
        return
    if k == "netitem":
        for c in el:
            dump(c, depth, out)
        return
    # 未知容器
    for c in el:
        dump(c, depth, out)

path = sys.argv[1]
start = int(sys.argv[2]) if len(sys.argv) > 2 else 1
end   = int(sys.argv[3]) if len(sys.argv) > 3 else 9999
root = ET.parse(path).getroot()
nets = [e for e in root.iter() if "d9a99d73" in T(e)]
out = []
for i, net in enumerate(nets, 1):
    if i < start or i > end: continue
    out.append("")
    out.append("=== NET %d  %s ===" % (i, ctext(net, "Comment") or ctext(net, "NetworkName")))
    items = child(net, "NetworkItems")
    if items is None:
        out.append("  (no items)")
        continue
    for it in items:
        dump(it, 1, out)
txt = "\n".join(out)
dst = path + ".dump.txt"
io.open(dst, "w", encoding="utf-8").write(txt)
print("nets=%d written %s (%d lines)" % (len(nets), dst, len(out)))
