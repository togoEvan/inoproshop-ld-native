# -*- coding: utf-8 -*-
# @py3
"""F10_POU_EthercatTask 翻译管线：4 个 ST PROGRAM「改名 + 跨引用改写 + GVL 引用改写」。

改名规则（与 F04 同）：
  对象名   E0_EtherCAT_MainC 等       -> 加后缀 "_F10V"（MetaObject.Name + 声明首行 + 相互调用）
  GVL 引用 G_xMasterETCOK 等 36 个     -> 改到 F01_Variable_GVLVerify 副本（_GVLVerify 后缀）

不改写（实测 F04 轮已确认共享即可）：
  - 设备对象 Servo*/Axis*/EtherCAT_C/GL20*
  - 共享全局 Gc_ui4PMEAxisNum / Gc_uiPAxisNum / Hr_astAxisData / g_xVirtual（原件无副本）
  - A 开头轴枚举值（DUT 是原件的，未复制枚举定义，无需加后缀）
  - FB 引脚名、库类型、局部变量、注释中文

F10 与 F04 的差别：无枚举定义复制（无 DUT），故无「枚举值加后缀」步骤。

用法：python examples/make_f10_translate.py <src_dir> <out_dir>
输出 <out_dir>/<名>_F10V.native + _report.txt
"""
import io
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

SRC = sys.argv[1] if len(sys.argv) > 1 else u"ipc/f10"
OUT = sys.argv[2] if len(sys.argv) > 2 else u"ipc/f10_out"
SUFFIX = u"_F10V"
HERE = os.path.dirname(os.path.abspath(__file__))


def U(s):
    try:
        return unicode(s)  # noqa: F821 (IronPython 2.7)
    except NameError:
        return str(s)


# ---------- 1) 载入映射表 ----------
# 对象名（4 个 POU 互相调用也要改写）
obj_names = [u"E0_EtherCAT_MainC", u"E1_M8000与EtherCAT通讯检测",
             u"E2_轴控调用", u"E3_SystemTime"]

gvl_orig2ver = json.load(io.open(
    os.path.join(HERE, u"..", u"ipc", u"f04_gvl_orig2ver.json"), encoding=u"utf-8"))

rename_map = {}
for n in obj_names:
    rename_map[n] = n + SUFFIX
for k, v in gvl_orig2ver.items():
    if k not in rename_map:            # 内部名优先
        rename_map[k] = v

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

    # 2b) 全部 Text 节点（声明 + ST 实现 + 注释）
    for el in root.iter(u"Single"):
        if el.get(u"Name") == u"Text" and el.text:
            el.text, n = rewrite(el.text)
            hits += n

    # 2c) LD Operand 里的字符串（F10 是纯 ST，保险起见保留）
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
    for f in sorted(os.listdir(SRC)):
        if not f.endswith(u".native"):
            continue
        name = f[:-7]
        dst = os.path.join(OUT, u"%s%s.native" % (name, SUFFIX))
        hits, nh = translate_file(os.path.join(SRC, f), dst)
        total_hits += hits
        report.append(u"%s: %d refs rewritten (name=%d)" % (name, hits, nh))
    rpt = u"\n".join(report)
    io.open(os.path.join(OUT, u"_report.txt"), u"w", encoding=u"utf-8").write(
        rpt + u"\ntotal refs rewritten: %d\n" % total_hits)
    print(rpt)
    print(u"total refs rewritten: %d" % total_hits)


if __name__ == u"__main__":
    main()
