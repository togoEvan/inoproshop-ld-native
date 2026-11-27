# -*- coding: utf-8 -*-
# @py3
"""F20_POU_Station0_总控 翻译管线：7 个 ST PROGRAM「改名 + 跨引用改写 + GVL 引用改写」。

改名规则（与 F04/F10/F11 同）：
  对象名   STN0_00_Main 等 7 个        -> 加后缀 "_F20V"（MetaObject.Name + 声明首行 + 相互调用）
  GVL 引用 687 条映射（f04_gvl_orig2ver.json）-> 改到 F01_Variable_GVLVerify 副本

不改写：
  - 设备对象 / 轴名（A0_贴装Y轴 等）
  - 跨文件夹调用 FB_MachineState / FB_RGYLamp / FC_AlarmRecord / Struct_HMI_Station00Alarm（原件存在即可）
  - 无副本的共享全局 Hr_astAxisData / Hr_astCylinderData / G_tS2酒精喷射时间 等
  - FB 引脚名（i_/o_/io_/v_ 前缀）、库类型、注释中文

⚠ 三处比 F11 更严的边界：
  1. 标识符边界含中文（F11 的坑）
  2. Path 数组末元素必须改名（F11 的坑）
  3. **逐文件排除该 POU 自己的局部变量**——局部变量与 GVL 全局同名时，
     裸替换会把局部变量也改成 _GVLVerify 名，编译报「未定义」。
     F20 实测 0 撞名，但机制必须留着，否则下次换工程就炸。

用法：python examples/make_f20_translate.py [src_dir] [out_dir]
输出 <out_dir>/<名>_F20V.native + _report.txt
"""
import io
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, u"..", u"ipc", u"f20")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, u"..", u"ipc", u"f20_out")
SUFFIX = u"_F20V"
GVL_MAP = os.path.join(HERE, u"..", u"ipc", u"f04_gvl_orig2ver.json")

OBJ_NAMES = [
    u"STN0_00_Main", u"STN0_01_Initialize", u"STN0_02_Auto", u"STN0_03_Manual",
    u"STN0_04_Alarm", u"STN0_05_Parameter", u"STN0_06_ProductStateSetting",
]

# 标识符字符集（含中文）——前后出现任一字符即不算独立标识符
IDC = u"A-Za-z0-9_\u4e00-\u9fff"

# AT 绝对地址：`AT %MB131072` / `AT%MW1000` 两种写法都要吃（README 铁律 27）
AT_RE = re.compile(u"\\s*AT\\s*%M[BDWX]?\\d+")


def texts_of(root):
    out = []
    for el in root.iter(u"Single"):
        if el.get(u"Name") == u"Text" and el.text:
            out.append(el.text)
    return out


def decl_texts(texts):
    """声明区 = 从 `PROGRAM/FUNCTION_BLOCK/FUNCTION xxx` 起到末尾。

    ⚠ 声明区每行是独立 Text 节点，不能按「含 VAR 的节点」筛（会丢变量行）。
    """
    for i, t in enumerate(texts):
        if re.match(u"^(PROGRAM|FUNCTION_BLOCK|FUNCTION)\\s", t.strip()):
            return texts[i:]
    return texts


def local_vars_of(texts):
    locs = set()
    joined = u"\n".join(decl_texts(texts))
    for m in re.finditer(u"\\bVAR\\b(.*?)\\bEND_VAR\\b", joined, re.S):
        for line in m.group(1).split(u"\n"):
            line = re.sub(u"//.*$", u"", line)
            mm = re.match(u"\\s*([A-Za-z_\u4e00-\u9fff][A-Za-z0-9_\u4e00-\u9fff]*)\\s*(:|$)", line)
            if mm:
                locs.add(mm.group(1))
    return locs


def build_map():
    m = {}
    for n in OBJ_NAMES:
        m[n] = n + SUFFIX
    gvl = json.load(io.open(GVL_MAP, encoding=u"utf-8"))
    for k, v in gvl.items():
        if k not in m:
            m[k] = v
    return m


MAP = build_map()
GVL_KEYS = set(MAP) - set(OBJ_NAMES)


def make_re(mapping):
    keys = sorted(mapping, key=len, reverse=True)
    return re.compile(u"(?<![%s])(%s)(?![%s])"
                      % (IDC, u"|".join(re.escape(k) for k in keys), IDC))


def translate_file(path, out_path):
    t = ET.parse(path)
    root = t.getroot()

    texts = texts_of(root)
    locs = local_vars_of(texts)

    # 局部变量优先：从映射里剔除同名项（局部遮蔽全局）
    eff = dict((k, v) for k, v in MAP.items() if k not in locs)
    shadowed = sorted(set(MAP) & locs)
    big = make_re(eff)

    hits = [0]

    def sub(mo):
        hits[0] += 1
        return eff[mo.group(1)]

    name_hits = 0
    # 1) MetaObject.Name
    for mo in root.iter(u"Single"):
        if mo.get(u"Name") == u"MetaObject":
            for c in mo:
                if c.tag == u"Single" and c.get(u"Name") == u"Name" and c.text:
                    old = c.text.strip()
                    if old in MAP:
                        c.text = MAP[old]
                        name_hits += 1
                    break
            break

    # 2) 全部 Text 节点（实现区 + 声明区）
    for el in root.iter(u"Single"):
        if el.get(u"Name") == u"Text" and el.text:
            el.text = big.sub(sub, el.text)

    # 3) Path 数组最后一项是对象自身名，必须跟着改
    for arr in root.iter(u"Array"):
        if arr.get(u"Name") != u"Path":
            continue
        for c in arr:
            if c.tag == u"Single" and c.text and c.text.strip() in MAP:
                c.text = MAP[c.text.strip()]
                hits[0] += 1

    # 4) 剥掉 AT 绝对地址（副本沿用原件 %MB 必撞「地址重复」）
    at_hits = 0
    for el in root.iter(u"Single"):
        if el.get(u"Name") == u"Text" and el.text and u"AT" in el.text:
            new = AT_RE.sub(u"", el.text)
            if new != el.text:
                at_hits += el.text.count(u"AT %")
                el.text = new

    # 5) Operand 字符串（LD 用，保险）
    for op in root.iter(u"Single"):
        if op.get(u"Name") == u"Operand":
            for c in op:
                if c.tag == u"Single" and c.get(u"Type") == u"string" and c.text:
                    c.text = big.sub(sub, c.text)

    t.write(out_path, encoding=u"utf-8", xml_declaration=False)
    return hits[0], name_hits, at_hits, shadowed


def main():
    if not os.path.isdir(OUT):
        os.makedirs(OUT)
    report = []
    total = 0
    total_at = 0
    for f in sorted(os.listdir(SRC)):
        if not f.endswith(u".native"):
            continue
        name = f[:-7]
        dst = os.path.join(OUT, u"%s%s.native" % (name, SUFFIX))
        hits, nh, ah, shadowed = translate_file(os.path.join(SRC, f), dst)
        total += hits
        total_at += ah
        extra = (u"  [shadowed locals: %s]" % u",".join(shadowed)) if shadowed else u""
        report.append(u"%s: %d refs (name=%d, AT=%d)%s" % (name, hits, nh, ah, extra))
    rpt = u"\n".join(report)
    io.open(os.path.join(OUT, u"_report.txt"), u"w", encoding=u"utf-8").write(
        rpt + u"\ntotal refs rewritten: %d\ntotal AT stripped: %d\n" % (total, total_at))
    print(rpt)
    print(u"total refs rewritten: %d, AT stripped: %d" % (total, total_at))


if __name__ == u"__main__":
    main()
