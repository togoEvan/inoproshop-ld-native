# -*- coding: utf-8 -*-
# @py3
"""F20 主机侧引用分析：提取 7 个 ST PROGRAM 的全部标识符，比对 GVL 映射表找缺口。

输出 ipc/f20_analysis.json + 控制台报告：
  - gvl_mapped: 在 f04_gvl_orig2ver.json 中有映射的全局引用（可改写到 _GVLVerify）
  - unmapped:   无映射的标识符（设备对象/跨文件夹 POU/持久变量/库类型——需逐个判定）
  - locals:     各 POU 的局部变量（不改写）
"""
import io
import json
import os
import re
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, u"..", u"ipc", u"f20")
OUT = os.path.join(HERE, u"..", u"ipc", u"f20_analysis.json")
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

# F20 内部互相调用的 7 个 POU（改名后要改写）
F20_NAMES = [
    u"STN0_00_Main", u"STN0_01_Initialize", u"STN0_02_Auto", u"STN0_03_Manual",
    u"STN0_04_Alarm", u"STN0_05_Parameter", u"STN0_06_ProductStateSetting",
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


def decl_texts(texts):
    """取出声明区。

    ⚠ 声明区每行是**独立 Text 节点**，所以不能按「含 VAR/PROGRAM 的节点」筛
    （那样只剩 `PROGRAM xxx` / `VAR` / `END_VAR` 三行，变量行全丢，locals 恒为 0）。
    正确做法：定位 `PROGRAM/FUNCTION_BLOCK/FUNCTION xxx` 起始行，取其后全部节点。
    顺序上实现区在前、声明区在后，因此从起始行到末尾即为声明区。
    """
    for i, t in enumerate(texts):
        head = t.strip()
        if re.match(u"^(PROGRAM|FUNCTION_BLOCK|FUNCTION)\\s", head):
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


def main():
    gvl_map = json.load(io.open(GVL_MAP, encoding=u"utf-8"))
    analysis = []
    for f in sorted(os.listdir(SRC)):
        if not f.endswith(u".native"):
            continue
        name = f[:-7]
        texts = texts_of(os.path.join(SRC, f))
        locs = local_vars_of(texts)
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
                          and i not in F20_NAMES)
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
