# -*- coding: utf-8 -*-
"""F05_FC 全量翻译管线：58 个对象「改名 + 跨引用改写 + GVL 引用改写」。

改名规则：
  对象名     old        -> old + "_F05V"          （MetaObject.Name + 声明首行 + 全部引用）
  GVL 引用   Gv_xxx     -> Gv_xxx + "_GVLVerify"  （FB 体内引用的全局变量改到副本 GVL）

改写范围（单遍正则替换，防链式替换/子串误伤）：
  1. 所有 `Single Name="Text"` 节点（声明区 + ST 实现 + 注释）
  2. LD 的 Operand 内 `Single Type="string"` 节点（触点/线圈/实例名）

envelope 不动（沿用 make_f02_copy 实测结论：import_native 到目标父对象时
ParentSVNodeGuid/Path 由 IDE 按导入目标修正，native 内的旧值无害）。

用法：python examples/make_f05_translate.py <src_dir> <out_dir>
输出 <out_dir>/<子文件夹>/<名>_F05V.native + _report.txt
"""
import io
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

SRC = sys.argv[1] if len(sys.argv) > 1 else u"ipc/f05"
OUT = sys.argv[2] if len(sys.argv) > 2 else u"ipc/f05_out"
SUFFIX = u"_F05V"
HERE = os.path.dirname(os.path.abspath(__file__))


def U(s):
    try:
        return unicode(s)  # noqa: F821 (IronPython 2.7)
    except NameError:
        return str(s)


# ---------- 1) 载入映射表 ----------
analysis = json.load(io.open(
    os.path.join(HERE, u"..", u"ipc", u"f05_analysis.json"), encoding=u"utf-8"))
obj_names = set(r[u"name"] for r in analysis)          # 58 个内部对象名
gvl_orig2ver = json.load(io.open(
    os.path.join(HERE, u"..", u"ipc", u"f05_gvl_orig2ver.json"), encoding=u"utf-8"))

# 合并改写表：内部对象名 + GVL 原件变量名（长名优先，防前缀误伤）
rename_map = {}
for n in obj_names:
    rename_map[n] = n + SUFFIX
for k, v in gvl_orig2ver.items():
    if k not in rename_map:            # 内部名优先，冲突极小概率
        rename_map[k] = v

# ⚠ 枚举字面量进全局命名空间：副本枚举的值必须也加后缀，否则与原件
#   全局符号重名（实测 277 条「符号'xxx'存在重名」+ 裸引用变未知类型）。
#   枚举值行：`	A1_上料移栽R轴:=1,` —— 从 DUT 声明文本提取。
ENUM_VAL_RE = re.compile(
    u"^\\s*([A-Za-z_\\u4e00-\\u9fff][A-Za-z0-9_\\u4e00-\\u9fff]*)\\s*:=\\s*-?[0-9]+\\s*,?\\s*(//.*)?$")


def collect_enum_values():
    vals = set()
    for sfn in sorted(os.listdir(SRC)):
        sdp = os.path.join(SRC, sfn)
        if not os.path.isdir(sdp):
            continue
        for f in sorted(os.listdir(sdp)):
            if not f.endswith(u".native"):
                continue
            t = ET.parse(os.path.join(sdp, f))
            for arr in t.getroot().findall(u".//Array[@Name='TextLines']"):
                in_enum = False
                for c in arr:
                    te = c.find(u"Single[@Name='Text']")
                    if te is None or te.text is None:
                        continue
                    s = te.text.strip()
                    if s.startswith(u"TYPE") and u"(" not in s:
                        continue
                    if s == u"(":
                        in_enum = True
                        continue
                    if in_enum:
                        if s == u")":
                            in_enum = False
                            continue
                        m = ENUM_VAL_RE.match(s)
                        if m:
                            vals.add(m.group(1))
    return vals


enum_vals = collect_enum_values()
for v in enum_vals:
    if v not in rename_map:
        rename_map[v] = v + SUFFIX
sys.stderr.write(u"enum values to suffix: %d\n" % len(enum_vals))

# 单遍交替正则：(?<![A-Za-z0-9_])name(?![A-Za-z0-9_])
# 中文不属于 [A-Za-z0-9_]，所以中文名边界天然成立。
keys = sorted(rename_map, key=len, reverse=True)
BIG_RE = re.compile(
    u"(?<![A-Za-z0-9_])(%s)(?![A-Za-z0-9_])" % u"|".join(
        re.escape(k) for k in keys))


def rewrite(text):
    """单遍替换；返回 (新文本, 命中次数)。"""
    cnt = [0]

    def sub(m):
        cnt[0] += 1
        return rename_map[m.group(1)]

    return BIG_RE.sub(sub, text), cnt[0]


# ---------- 2) 逐对象翻译 ----------
def translate_file(path, out_path):
    t = ET.parse(path)
    root = t.getroot()
    hits = 0
    name_hits = 0

    # 2a) MetaObject.Name
    for mo in root.iter(u"Single"):
        if mo.get(u"Name") == u"MetaObject":
            for c in mo:
                if c.get(u"Name") == u"Name" and c.text:
                    old = c.text.strip()
                    if old in rename_map:
                        c.text = rename_map[old]
                        name_hits += 1
                    break
            break

    # 2b) 全部 Text 节点
    for el in root.iter(u"Single"):
        if el.get(u"Name") == u"Text" and el.text:
            el.text, n = rewrite(el.text)
            hits += n

    # 2c) LD Operand 里的字符串
    for op in root.iter(u"Single"):
        if op.get(u"Name") == u"Operand":
            for c in op:
                if c.tag == u"Single" and c.get(u"Type") == u"string" and c.text:
                    c.text, n = rewrite(c.text)
                    hits += n

    t.write(out_path, encoding=u"utf-8", xml_declaration=False)
    return hits, name_hits


def main():
    if not os.path.isdir(OUT):
        os.makedirs(OUT)
    report = []
    total_hits = 0
    for sfn in sorted(os.listdir(SRC)):
        sdp = os.path.join(SRC, sfn)
        if not os.path.isdir(sdp):
            continue
        odir = os.path.join(OUT, sfn)
        if not os.path.isdir(odir):
            os.makedirs(odir)
        for f in sorted(os.listdir(sdp)):
            if not f.endswith(u".native"):
                continue
            name = f[:-7]
            src = os.path.join(sdp, f)
            dst = os.path.join(odir, u"%s%s.native" % (name, SUFFIX))
            hits, nh = translate_file(src, dst)
            total_hits += hits
            report.append(u"%s/%s: %d refs rewritten (name=%d)"
                          % (sfn, name, hits, nh))

    # ---- F05 特有：F05_FC 根下直接 POU（导出名为 <名>_folder.native，实为 FC）----
    for f in sorted(os.listdir(SRC)):
        if not f.endswith(u"_folder.native"):
            continue
        src = os.path.join(SRC, f)
        # 只处理实为 POU 的（TypeGuid = FB 类），真正的 Folder 跳过
        t = ET.parse(src)
        tg = None
        for el in t.getroot().iter(u"Single"):
            if el.get(u"Name") == u"TypeGuid" and el.text:
                tg = el.text.strip()
                break
        if tg != u"6f9dac99-8de1-4efc-8465-68ac443b7d08":
            continue
        name = f[:-len(u"_folder.native")]
        dst = os.path.join(OUT, u"%s%s.native" % (name, SUFFIX))
        hits, nh = translate_file(src, dst)
        total_hits += hits
        report.append(u"(root)/%s: %d refs rewritten (name=%d)"
                      % (name, hits, nh))
    rpt = u"\n".join(report)
    io.open(os.path.join(OUT, u"_report.txt"), u"w", encoding=u"utf-8").write(
        rpt + u"\ntotal refs rewritten: %d\n" % total_hits)
    print(rpt)
    print(u"total refs rewritten: %d" % total_hits)


if __name__ == u"__main__":
    main()
