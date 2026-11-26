# -*- coding: utf-8 -*-
# @py3
"""F11 主机侧引用分析：提取 15 个 ST PROGRAM 的全部标识符，比对 GVL 映射表找缺口。

输出 ipc/f11_analysis.json + 控制台报告：
  - gvl_mapped: 在 f04_gvl_orig2ver.json 中有映射的全局引用（可改写到 _GVLVerify）
  - unmapped:   无映射的标识符（设备对象/跨文件夹 POU/持久变量/库类型——需逐个判定）
  - locals:     各 POU 的局部变量（不改写）
"""
import io
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, u"..", u"ipc", u"f11")
OUT = os.path.join(HERE, u"..", u"ipc", u"f11_analysis.json")
GVL_MAP = os.path.join(HERE, u"..", u"ipc", u"f04_gvl_orig2ver.json")

# 库/系统类型与关键字（不改写）
LIB_TYPES = set(u"""
TON TOF TP CTU CTD CTUD R_TRIG F_TRIG RS SR SEMA BLINK
SMC3_ReinitDrive RTS_IEC_RESULT SysTimeRtc SysTimeRtcGet SysTimeRtcConvertUtcToDate
MC_Power MC_Home MC_Stop MC_Reset MC_MoveAbsolute MC_MoveRelative MC_MoveVelocity
MC_MoveJog MC_Jog MC_TouchProbe MC_GearIn MC_CamIn MC_CamTableSelect MC_SetPosition
MC_SetOverride MC_Phasing MC_GearInPos MC_CamOut MC_GearOut MC_WriteParameter
MC_ReadParameter MC_ReadAxisError MC_ReadActualPosition MC_ReadActualVelocity
MC_SetControllerMode MC_DigitalCamSwitch MC_Direction MC_CAMSwitch MC_LimitSwitch
AXIS_REF_SM3 MC_GROUP_REF
INT DINT UDINT UINT SINT USINT BYTE WORD DWORD LREAL REAL TIME BOOL STRING WSTRING
DATE TOD DT STRUCT END_STRUCT ARRAY OF VAR END_VAR PROGRAM FUNCTION FUNCTION_BLOCK
TYPE END_TYPE CONSTANT RETAIN PERSISTENT
IF THEN ELSE ELSIF END_FOR FOR TO BY DO WHILE REPEAT UNTIL CASE OF RETURN EXIT
TRUE FALSE AND OR NOT XOR MOD
""".split())

IDENT_RE = re.compile(u"[A-Za-z_\u4e00-\u9fff][A-Za-z0-9_\u4e00-\u9fff]*")

# F11 内部互相调用的 15 个 POU（改名后要改写）
F11_NAMES = [
    u"M000_MAIN", u"M001_气缸程序", u"M002_真空程序", u"M003_轴程序", u"M004_IO",
    u"M005_压力控制", u"M006_风速仪", u"M007_FFU", u"M008_酒精",
    u"M009_无尘布放料卷张力控制", u"M010_插补控制", u"M012_上下游交互",
    u"M100_模组调用", u"M995_配方", u"M999_产量统计",
]


def texts_of(path):
    t = ET.parse(path)
    out = []
    for el in t.getroot().iter(u"Single"):
        if el.get(u"Name") == u"Text" and el.text:
            out.append(el.text)
        elif el.get(u"Name") == u"Operand":
            for c in el:
                if c.tag == u"Single" and c.get(u"Type") == u"string" and c.text:
                    out.append(c.text)
    return out


def local_vars_of(decl_texts):
    locs = set()
    joined = u"\n".join(decl_texts)
    for m in re.finditer(u"VAR\\b(.*?)END_VAR", joined, re.S):
        for line in m.group(1).split(u"\n"):
            mm = re.match(u"\\s*([A-Za-z_\u4e00-\u9fff][A-Za-z0-9_\u4e00-\u9fff]*)\\s*(:|$)", line)
            if mm:
                locs.add(mm.group(1))
    return locs


def main():
    gvl_map = json.load(io.open(GVL_MAP, encoding=u"utf-8"))
    analysis = []
    for f in sorted(os.listdir(SRC)):
        if not f.endswith(u".native"):
            continue
        name = f[:-7]
        texts = texts_of(os.path.join(SRC, f))
        decl = [t for t in texts if u"VAR" in t or u"PROGRAM" in t]
        locs = local_vars_of(decl)
        idents = set()
        for t in texts:
            idents.update(IDENT_RE.findall(t))
        refs = {}
        for i in sorted(idents):
            if i in LIB_TYPES or i in locs:
                continue
            if i in gvl_map:
                refs[i] = gvl_map[i]
        unmapped = sorted(i for i in idents
                          if i not in LIB_TYPES and i not in locs and i not in refs
                          and i not in F11_NAMES)
        analysis.append({u"name": name, u"locals": sorted(locs),
                         u"gvl_mapped": refs, u"unmapped": unmapped})

    io.open(OUT, u"w", encoding=u"utf-8").write(
        json.dumps(analysis, ensure_ascii=False, indent=1))

    for a in analysis:
        print(u"### %s: locals=%d mapped=%d unmapped=%d"
              % (a[u"name"], len(a[u"locals"]), len(a[u"gvl_mapped"]), len(a[u"unmapped"])))
    all_unmapped = set()
    for a in analysis:
        all_unmapped.update(a[u"unmapped"])
    print(u"\n=== unmapped 全集 (%d) ===" % len(all_unmapped))
    for x in sorted(all_unmapped):
        print(u"  %s" % x)


if __name__ == u"__main__":
    main()
