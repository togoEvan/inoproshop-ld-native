# -*- coding: utf-8 -*-
# @py3
"""盘点 F04_FB 的 58 个对象：类型/实现语言/内部引用。

输出 ipc/f05_analysis.json：
  objects: [{name, sf, type_guid, impl_lang, refs_internal, refs_gvl}]
    refs_internal —— 引用了 F04 内部其他对象名（改名后需同步改写）
    refs_gvl      —— 引用了 F01_Variable 的 GVL 变量（需映射到 *_GVLVerify）

引用提取范围：全部 Text 节点文本（声明 + ST 实现）+ LD Operand 节点。
"""
import io
import json
import os
import re
import xml.etree.ElementTree as ET

SRC = u"ipc/f05"
TYPE_FB = u"6f9dac99-8de1-4efc-8465-68ac443b7d08"
TYPE_DUT = u"2db5746d-d284-4425-9f7f-2663a34b0ebc"
IMPL_ST = u"3b83b776-fb25-43b8-99f2-3c507c9143fc"
IMPL_LD = u"25e509de-33d4-4447-93f8-c9e4ea381c8b"

# ---------- 1) 全部对象名 ----------
objects = []
sf_dirs = []
for f in sorted(os.listdir(SRC)):
    p = os.path.join(SRC, f)
    if os.path.isdir(p):
        sf_dirs.append((f, p))

names = set()
for sfn, sdp in sf_dirs:
    for f in os.listdir(sdp):
        if f.endswith(u".native"):
            names.add(f[:-7])

# ---------- 2) GVL 变量名（原件 + GVLVerify 副本） ----------
# 从工程里的 F01_Variable_GVLVerify 目录归档拿？没归档变量清单——
# 从 study.project 里导出过 gvl 的 f01_lines.json 在 D:/plc_study。
# 简单可靠路线：扫 F01_Variable_GVLVerify 每个对象的声明文本——
# 但我们主机侧没有。改为从 ipc/f05 的引用里先提取候选，再人工核对。
# 更好：工程侧导出 GVL 变量名清单（见 task_export_gvl_names.py）。
gvl_orig2ver = {}   # 原件变量名 -> GVLVerify 名（后续从工程导出填充）

IDENT_RE = re.compile(u"[A-Za-z_\\u4e00-\\u9fff][A-Za-z0-9_\\u4e00-\\u9fff]*")


def extract_texts(root):
    """全部 Text 节点（声明+ST实现）+ LD Operand 文本。"""
    out = []
    for el in root.iter(u"Single"):
        nm = el.get(u"Name")
        if nm == u"Text":
            if el.text:
                out.append(el.text)
        elif nm == u"Operand":
            # LD 的 Operand 里的 Single Type=string
            for c in el:
                if c.tag == u"Single" and c.get(u"Type") == u"string" and c.text:
                    out.append(c.text)
    return out


result = []
for sfn, sdp in sf_dirs:
    for f in sorted(os.listdir(sdp)):
        if not f.endswith(u".native"):
            continue
        name = f[:-7]
        path = os.path.join(sdp, f)
        t = ET.parse(path)
        root = t.getroot()
        # TypeGuid + 实现语言
        tg = None
        for el in root.iter(u"Single"):
            if el.get(u"Name") == u"TypeGuid" and el.text:
                tg = el.text.strip()
                break
        impl = None
        for el in root.iter(u"Single"):
            if el.get(u"Name") == u"Implementation":
                impl = (el.get(u"Type") or u"").strip(u"{}")
                break
        impl_lang = (u"ST" if impl == IMPL_ST
                     else (u"LD" if impl == IMPL_LD else None))
        # 引用
        texts = extract_texts(root)
        joined = u"\n".join(texts)
        idents = set(IDENT_RE.findall(joined))
        refs_internal = sorted(i for i in idents if i in names and i != name)
        result.append({
            u"name": name, u"sf": sfn, u"type_guid": tg,
            u"impl_lang": impl_lang,
            u"size": os.path.getsize(path),
            u"refs_internal": refs_internal,
            u"n_texts": len(texts),
        })

# ---- 追加：F05_FC 根下直接 POU（导出为 <名>_folder.native，实为 FC 不是 Folder）----
root_objs = []
for f in sorted(os.listdir(SRC)):
    if not f.endswith(u"_folder.native"):
        continue
    path = os.path.join(SRC, f)
    t = ET.parse(path)
    r0 = t.getroot()
    tg = None
    for el in r0.iter(u"Single"):
        if el.get(u"Name") == u"TypeGuid" and el.text:
            tg = el.text.strip()
            break
    if tg != TYPE_FB:
        continue
    impl = None
    for el in r0.iter(u"Single"):
        if el.get(u"Name") == u"Implementation":
            impl = (el.get(u"Type") or u"").strip(u"{}")
            break
    impl_lang = (u"ST" if impl == IMPL_ST else (u"LD" if impl == IMPL_LD else None))
    name = f[:-len(u"_folder.native")]
    names.add(name)
    root_objs.append({
        u"name": name, u"sf": u"(root)", u"type_guid": tg,
        u"impl_lang": impl_lang, u"size": os.path.getsize(path),
        u"refs_internal": [], u"n_texts": len(extract_texts(r0)),
        u"_path": path,
    })

# names 已含全部对象，二次算 root 对象的内部引用
for r in root_objs:
    t2 = ET.parse(r[u"_path"])
    idents = set(IDENT_RE.findall(u"\n".join(extract_texts(t2.getroot()))))
    r[u"refs_internal"] = sorted(i for i in idents if i in names and i != r[u"name"])
    r.pop(u"_path")
result.extend(root_objs)

with io.open(u"ipc/f05_analysis.json", u"w", encoding=u"utf-8") as fp:
    json.dump(result, fp, ensure_ascii=False, indent=1)

# 摘要
print(u"objects: %d" % len(result))
by_lang = {}
for r in result:
    k = r[u"impl_lang"] or u"none"
    by_lang[k] = by_lang.get(k, 0) + 1
print(u"impl_lang:", by_lang)
nref = sum(1 for r in result if r[u"refs_internal"])
print(u"objects with internal refs: %d" % nref)
for r in result[:6]:
    print(u"%s [%s/%s] refs=%s" % (r[u"name"], r[u"sf"],
                                   r[u"impl_lang"], r[u"refs_internal"][:5]))
