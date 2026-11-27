# -*- coding: utf-8 -*-
# @py3
"""F21 主机侧引用分析：ST + LD 混合结构的标识符提取与 GVL 缺口比对。

与 F20（纯 ST）的关键差异：
  F21 里 STN1_02_Auto(20 网络) / STN1_03_Manual(2 网络) 是 **LD**，
  标识符不在 Text 节点，而在：
    - <Single Name="Operand" Type="string">  ← 触点的操作数（如 STNControl[1].xAutoing）
    - <Single Name="BoxType">                ← 功能框类型（如 TON / MOVE / 自定义 FB）
    - <Single Name="Instance">               ← 功能框实例名
    - <Single Name="Text">                   ← ST 代码行（纯 ST POU 全部走这里）
  漏掉前三类 → 改名漏改 → 副本引用了原件全局量，双分类仍 0 错误（假通过）。

输出 ipc/f21_analysis.json
"""
import io
import json
import os
import re
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, u"..", u"ipc", u"f21")
OUT = os.path.join(HERE, u"..", u"ipc", u"f21_analysis.json")
GVL_MAP = os.path.join(HERE, u"..", u"ipc", u"f04_gvl_orig2ver.json")

LIB_TYPES = set(u"""
TON TOF TP CTU CTD CTUD R_TRIG F_TRIG RS SR SEMA BLINK
SMC3_ReinitDrive RTS_IEC_RESULT SysTimeRtc SysTimeRtcGet SysTimeRtcConvertUtcToDate
MC_Power MC_Home MC_Stop MC_Reset MC_MoveAbsolute MC_MoveRelative MC_MoveVelocity
MC_MoveJog MC_Jog MC_TouchProbe MC_GearIn MC_CamIn MC_CamTableSelect MC_SetPosition
MC_SetOverride MC_Phasing MC_GearInPos MC_CamOut MC_GearOut MC_WriteParameter
MC_ReadParameter MC_ReadAxisError MC_ReadActualPosition MC_ReadActualVelocity
MC_SetControllerMode MC_DigitalCamSwitch MC_Direction MC_CAMSwitch MC_LimitSwitch
AXIS_REF_SM3 MC_GROUP_REF
MOVE SEL ADD SUB MUL DIV EQ NE LT LE GT GE AND OR XOR NOT LIMIT MAX MIN
MEMUtils ADR SIZEOF MEMCmp
INT DINT UDINT UINT SINT USINT BYTE WORD DWORD LREAL REAL TIME BOOL STRING WSTRING
DATE TOD DT STRUCT END_STRUCT ARRAY OF VAR END_VAR PROGRAM FUNCTION FUNCTION_BLOCK
TYPE END_TYPE CONSTANT RETAIN PERSISTENT
IF THEN ELSE ELSIF END_FOR FOR TO BY DO WHILE REPEAT UNTIL CASE OF RETURN EXIT
TRUE FALSE AND OR NOT XOR MOD
""".split())

IDENT_RE = re.compile(u"[A-Za-z_\u4e00-\u9fff][A-Za-z0-9_\u4e00-\u9fff]*")

# F21 内部 7 个 POU（改名后要改写引用）
F21_NAMES = [
    u"STN1_00_Main", u"STN1_01_Initialize", u"STN1_02_Auto", u"STN1_03_Manual",
    u"STN1_04_Alarm", u"STN1_05_Parameter", u"STN1_06_ProductStateSetting",
]


def carrier_texts(path):
    """取出所有可能承载标识符的文本，按来源分类返回 dict。"""
    t = ET.parse(path)
    out = {"Text": [], "Operand": [], "BoxType": [], "Instance": []}
    for el in t.getroot().iter(u"Single"):
        nm = el.get(u"Name")
        if nm == u"Text" and el.text:
            out["Text"].append(el.text)
        elif nm == u"Operand":
            # Operand 有两种：Type="string" 直接带文本；或嵌套结构
            if el.get(u"Type") == u"string" and el.text:
                out["Operand"].append(el.text)
            else:
                for c in el:
                    if c.tag == u"Single" and c.get(u"Name") == u"Operand" and c.text:
                        out["Operand"].append(c.text)
        elif nm == u"BoxType" and el.text:
            out["BoxType"].append(el.text)
        elif nm == u"Instance":
            for c in el:
                if c.tag == u"Single" and c.get(u"Name") == u"Operand" and c.text:
                    out["Instance"].append(c.text)
    return out


def decl_texts(texts):
    """声明区：从 `PROGRAM/FUNCTION_BLOCK/FUNCTION xxx` 起的所有后续 Text 节点。

    ⚠ 铁律 42：声明区每行是独立 Text 节点，不能按 VAR 关键字筛节点。
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


def main():
    gvl_map = json.load(io.open(GVL_MAP, encoding=u"utf-8"))
    analysis = []
    for f in sorted(os.listdir(SRC)):
        if not f.endswith(u".native"):
            continue
        name = f[:-7]
        carriers = carrier_texts(os.path.join(SRC, f))
        locs = local_vars_of(carriers["Text"])

        idents = set()
        for kind in ("Text", "Operand", "BoxType", "Instance"):
            for t in carriers[kind]:
                idents.update(IDENT_RE.findall(t))

        refs = {}
        for i in sorted(idents):
            if i in LIB_TYPES or i in locs:
                continue
            if i in gvl_map:
                refs[i] = gvl_map[i]

        unmapped = sorted(i for i in idents
                          if i not in LIB_TYPES and i not in locs and i not in refs
                          and i not in F21_NAMES)

        # 记录每个 POU 的载体统计，便于发现「漏掉某一类载体」的情况
        analysis.append({
            u"name": name,
            u"carrier_counts": {k: len(v) for k, v in carriers.items()},
            u"locals": sorted(locs),
            u"gvl_mapped": refs,
            u"unmapped": unmapped,
        })

    io.open(OUT, u"w", encoding=u"utf-8").write(
        json.dumps(analysis, ensure_ascii=False, indent=1))

    for a in analysis:
        cc = a[u"carrier_counts"]
        print(u"### %-30s Text=%-4d Operand=%-5d Box=%-5d Inst=%-4d | locals=%-3d mapped=%-3d unmapped=%d"
              % (a[u"name"], cc[u"Text"], cc[u"Operand"], cc[u"BoxType"], cc[u"Instance"],
                 len(a[u"locals"]), len(a[u"gvl_mapped"]), len(a[u"unmapped"])))

    all_unmapped = set()
    for a in analysis:
        all_unmapped.update(a[u"unmapped"])
    print(u"\n=== unmapped 全集 (%d) ===" % len(all_unmapped))
    for x in sorted(all_unmapped):
        print(u"  %s" % x)


if __name__ == u"__main__":
    main()
