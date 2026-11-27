# -*- coding: utf-8 -*-
# @py3
"""F21_POU_Station1_工站1_搬运移栽 翻译管线：ST + LD 混合结构。

7 个 PROGRAM：
  纯 ST：STN1_00_Main / 01_Initialize / 04_Alarm / 05_Parameter / 06_ProductStateSetting
  LD  ：STN1_02_Auto(20 网络) / STN1_03_Manual(2 网络)

改名规则（与 F20 同，但载体更宽）：
  对象名   STN1_xx -> 加后缀 "_F21V"（MetaObject.Name + 声明首行 + 相互调用 + Path 末元素）
  GVL 引用 687 条映射 -> 改到 F01_Variable_GVLVerify 副本

⚠ 比 F20 多出来的关键点（LD 才有）：
  LD 的标识符**不在 Text 节点**，而在：
    - <Single Name="Operand" Type="string">   触点/线圈操作数（如 STNControl[1].xAutoing）
    - <Single Name="Instance">...Operand...   功能框实例操作数
    - <Single Name="BoxType">                 功能框类型（FC_CylinderExe / AND / MOVE …）
  只改 Text 会让 LD 部分**一个符号都没改**，而双分类仍 0 错误 —— 副本悄悄引用
  原件全局量，是最难发现的假通过。所以四类载体全部过一遍。

不改写：设备名(A0_上料移栽…)、跨文件夹共享 FB/FC、库类型、注释中文、FB 引脚名。

用法：python examples/make_f21_translate.py [src_dir] [out_dir]
输出 <out_dir>/<名>_F21V.native + _report.txt
"""
import io
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, u"..", u"ipc", u"f21")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, u"..", u"ipc", u"f21_out")
SUFFIX = u"_F21V"
GVL_MAP = os.path.join(HERE, u"..", u"ipc", u"f04_gvl_orig2ver.json")

OBJ_NAMES = [
    u"STN1_00_Main", u"STN1_01_Initialize", u"STN1_02_Auto", u"STN1_03_Manual",
    u"STN1_04_Alarm", u"STN1_05_Parameter", u"STN1_06_ProductStateSetting",
]

# 标识符字符集（含中文）——前后出现任一字符即不算独立标识符（铁律：F11 的坑）
IDC = u"A-Za-z0-9_\u4e00-\u9fff"

AT_RE = re.compile(u"\\s*AT\\s*%M[BDWX]?\\d+")


def texts_of(root):
    out = []
    for el in root.iter(u"Single"):
        if el.get(u"Name") == u"Text" and el.text:
            out.append(el.text)
    return out


def decl_texts(texts):
    """声明区 = 从 `PROGRAM/FUNCTION_BLOCK/FUNCTION xxx` 起到末尾（铁律 42）。"""
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

    # 局部变量遮蔽全局：从映射里剔除同名项
    eff = dict((k, v) for k, v in MAP.items() if k not in locs)
    shadowed = sorted(set(MAP) & locs)
    big = make_re(eff)

    stats = {"Text": 0, "Operand": 0, "BoxType": 0, "Instance": 0,
             "Name": 0, "Path": 0, "AT": 0}

    def sub_factory(kind):
        def sub(mo):
            stats[kind] += 1
            return eff[mo.group(1)]
        return sub

    sub_text = sub_factory("Text")
    sub_op = sub_factory("Operand")
    sub_bt = sub_factory("BoxType")
    sub_inst = sub_factory("Instance")

    # 1) MetaObject.Name
    for mo in root.iter(u"Single"):
        if mo.get(u"Name") == u"MetaObject":
            for c in mo:
                if c.tag == u"Single" and c.get(u"Name") == u"Name" and c.text:
                    old = c.text.strip()
                    if old in MAP:
                        c.text = MAP[old]
                        stats["Name"] += 1
                    break
            break

    # 2) Text 节点（ST 代码 + 声明行 + 网络注释）
    for el in root.iter(u"Single"):
        if el.get(u"Name") == u"Text" and el.text:
            el.text = big.sub(sub_text, el.text)

    # 3) LD 载体：Operand(string) / BoxType / Instance 里的 Operand(string)
    for el in root.iter(u"Single"):
        nm = el.get(u"Name")
        if nm == u"Operand" and el.get(u"Type") == u"string" and el.text:
            el.text = big.sub(sub_op, el.text)
        elif nm == u"BoxType" and el.text:
            el.text = big.sub(sub_bt, el.text)

    # Instance 是结构节点，其内部 Operand(string) 已被上面第 3 步覆盖；
    # 这里再兜一遍，防止 Instance 直接以字符串形式出现。
    for el in root.iter(u"Single"):
        if el.get(u"Name") == u"Instance" and el.get(u"Type") == u"string" and el.text:
            el.text = big.sub(sub_inst, el.text)

    # 4) Path 数组末元素 = 对象自身名，必须跟着改（F11 的坑）
    for arr in root.iter(u"Array"):
        if arr.get(u"Name") != u"Path":
            continue
        for c in arr:
            if c.tag == u"Single" and c.text and c.text.strip() in MAP:
                c.text = MAP[c.text.strip()]
                stats["Path"] += 1

    # 5) 剥掉 AT 绝对地址（F21 实测 0 处，机制留着）
    for el in root.iter(u"Single"):
        if el.get(u"Name") == u"Text" and el.text and u"AT" in el.text:
            new = AT_RE.sub(u"", el.text)
            if new != el.text:
                stats["AT"] += el.text.count(u"AT %")
                el.text = new

    t.write(out_path, encoding=u"utf-8", xml_declaration=False)
    return stats, shadowed, eff


def verify(path, eff):
    """自检：改写后不应再有裸原名（按词边界计数）。"""
    t = ET.parse(path)
    bad = {}
    # 只看改名后的原名（不含 GVL，GVL 量大且已由映射覆盖）
    for n in OBJ_NAMES:
        cnt = 0
        for el in t.getroot().iter(u"Single"):
            nm = el.get(u"Name")
            if nm in (u"Text", u"Operand", u"BoxType", u"Instance") and el.text:
                pat = re.compile(u"(?<![%s])%s(?![%s])" % (IDC, re.escape(n), IDC))
                cnt += len(pat.findall(el.text))
        if cnt:
            bad[n] = cnt
    return bad


def main():
    if not os.path.isdir(OUT):
        os.makedirs(OUT)
    report = []
    totals = {"Text": 0, "Operand": 0, "BoxType": 0, "Instance": 0,
              "Name": 0, "Path": 0, "AT": 0}
    all_bad = {}
    for f in sorted(os.listdir(SRC)):
        if not f.endswith(u".native"):
            continue
        name = f[:-7]
        dst = os.path.join(OUT, u"%s%s.native" % (name, SUFFIX))
        stats, shadowed, eff = translate_file(os.path.join(SRC, f), dst)
        for k in totals:
            totals[k] += stats[k]
        bad = verify(dst, eff)
        if bad:
            all_bad[name] = bad
        n = sum(stats.values())
        extra = (u"  [shadowed: %s]" % u",".join(shadowed)) if shadowed else u""
        bads = (u"  [!! 残留裸原名: %s]" % bad) if bad else u""
        report.append(u"%-30s %5d refs  (Text=%d Operand=%d Box=%d Inst=%d Name=%d Path=%d AT=%d)%s%s"
                      % (name, n, stats["Text"], stats["Operand"], stats["BoxType"],
                         stats["Instance"], stats["Name"], stats["Path"], stats["AT"],
                         extra, bads))
    rpt = u"\n".join(report)
    tail = (u"\ntotal refs: %d\n  Text=%d Operand=%d BoxType=%d Instance=%d Name=%d Path=%d\n"
            u"total AT stripped: %d\n"
            % (sum(totals.values()), totals["Text"], totals["Operand"], totals["BoxType"],
               totals["Instance"], totals["Name"], totals["Path"], totals["AT"]))
    io.open(os.path.join(OUT, u"_report.txt"), u"w", encoding=u"utf-8").write(rpt + tail)
    print(rpt)
    print(tail)
    if all_bad:
        print(u"!!! 自检失败，仍有裸原名残留：")
        for k, v in all_bad.items():
            print(u"   %s : %s" % (k, v))
    else:
        print(u"自检通过：0 处裸原名残留")


if __name__ == u"__main__":
    main()
