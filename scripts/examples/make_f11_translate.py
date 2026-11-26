# -*- coding: utf-8 -*-
# @py3
"""F11_POU_MainTask 翻译管线：15 个 ST PROGRAM「改名 + 跨引用改写 + GVL 引用改写」。

改名规则（与 F04/F10 同）：
  对象名   M000_MAIN 等 15 个          -> 加后缀 "_F11V"（MetaObject.Name + 声明首行 + 相互调用）
  GVL 引用 687 条映射（f04_gvl_orig2ver.json）-> 改到 F01_Variable_GVLVerify 副本

不改写（F04/F10 轮已确认共享即可）：
  - 设备对象 Servo*/Axis*/EtherCAT_C/GL20*/AxesGroup_*
  - 跨文件夹调用 STN*_00_Main / E3_SystemTime / FB_* / FC_AlarmRecord（原件存在即可）
  - 无副本的共享全局 Hr_astAxisData / Hr_axStationEnable 等
  - FB 引脚名、库类型、局部变量、注释中文

⚠ 边界判定比 F10 更严：前后不能是 [A-Za-z0-9_] **或中文**。
  F10 只排除 ASCII，中文名互相为前缀时会误替换（F11 有 15 个中文对象名）。

用法：python examples/make_f11_translate.py [src_dir] [out_dir]
输出 <out_dir>/<名>_F11V.native + _report.txt
"""
import io
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, u"..", u"ipc", u"f11")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, u"..", u"ipc", u"f11_out")
SUFFIX = u"_F11V"
GVL_MAP = os.path.join(HERE, u"..", u"ipc", u"f04_gvl_orig2ver.json")

OBJ_NAMES = [
    u"M000_MAIN", u"M001_气缸程序", u"M002_真空程序", u"M003_轴程序", u"M004_IO",
    u"M005_压力控制", u"M006_风速仪", u"M007_FFU", u"M008_酒精",
    u"M009_无尘布放料卷张力控制", u"M010_插补控制", u"M012_上下游交互",
    u"M100_模组调用", u"M995_配方", u"M999_产量统计",
]

# 标识符字符集（含中文）——前后出现任一字符即不算独立标识符
IDC = u"A-Za-z0-9_\u4e00-\u9fff"

# AT 绝对地址：`AT %MB131072` / `AT%MW1000` 两种写法都要吃（README 铁律 27）
AT_RE = re.compile(u"\\s*AT\\s*%M[BDWX]?\\d+")


def build_map():
    m = {}
    for n in OBJ_NAMES:
        m[n] = n + SUFFIX
    gvl = json.load(io.open(GVL_MAP, encoding=u"utf-8"))
    for k, v in gvl.items():
        if k not in m:
            m[k] = v
    keys = sorted(m, key=len, reverse=True)
    big = re.compile(u"(?<![%s])(%s)(?![%s])" % (IDC, u"|".join(re.escape(k) for k in keys), IDC))
    return m, big


MAP, BIG_RE = build_map()


def rewrite(text):
    cnt = [0]

    def sub(mo):
        cnt[0] += 1
        return MAP[mo.group(1)]

    return BIG_RE.sub(sub, text), cnt[0]


def translate_file(path, out_path):
    t = ET.parse(path)
    root = t.getroot()
    hits = 0
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

    # 2) 全部 Text 节点（声明 + 实现 + 注释）
    for el in root.iter(u"Single"):
        if el.get(u"Name") == u"Text" and el.text:
            el.text, n = rewrite(el.text)
            hits += n

    # 3) Path 数组最后一项是对象自身名，必须跟着改（否则导入后路径与实际名不一致）
    for arr in root.iter(u"Array"):
        if arr.get(u"Name") != u"Path":
            continue
        for c in arr:
            if c.tag == u"Single" and c.text and c.text.strip() in MAP:
                c.text = MAP[c.text.strip()]
                hits += 1

    # 3.5) 剥掉 AT 绝对地址（README 铁律 27）
    #      副本沿用原件 %MB 地址必然与原件撞「地址重复」，改由 IDE 自动分配。
    #      F11 实测 2 处：M003_轴程序 的 v_uiAxisIndexOld / v_uiHMICurrentPageOld。
    at_hits = 0
    for el in root.iter(u"Single"):
        if el.get(u"Name") == u"Text" and el.text and u"AT" in el.text:
            new = AT_RE.sub(u"", el.text)
            if new != el.text:
                at_hits += el.text.count(u"AT %")
                el.text = new

    # 4) Operand 里的字符串（LD 用；F11 全 ST，保险起见保留）
    for op in root.iter(u"Single"):
        if op.get(u"Name") == u"Operand":
            for c in op:
                if c.tag == u"Single" and c.get(u"Type") == u"string" and c.text:
                    c.text, n = rewrite(c.text)
                    hits += n

    t.write(out_path, encoding=u"utf-8", xml_declaration=False)
    return hits, name_hits, at_hits


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
        hits, nh, ah = translate_file(os.path.join(SRC, f), dst)
        total += hits
        total_at += ah
        report.append(u"%s: %d refs rewritten (name=%d, AT stripped=%d)" % (name, hits, nh, ah))
    rpt = u"\n".join(report)
    io.open(os.path.join(OUT, u"_report.txt"), u"w", encoding=u"utf-8").write(
        rpt + u"\ntotal refs rewritten: %d\n" % total)
    print(rpt)
    print(u"total refs rewritten: %d" % total)


if __name__ == u"__main__":
    main()
