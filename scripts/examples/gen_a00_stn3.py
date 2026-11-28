# @py3
# -*- coding: utf-8 -*-
"""按 A00_上料移栽 的**完整骨架**生成工站子程序（样本 prg_Stn3LoadSeq）。

用法：
    python gen_a00_stn3.py
    LDSKEL=<任意 PROGRAM 的 native 骨架> LDOUT=<输出路径> python gen_a00_stn3.py
依赖 assets/natives/a00-fragments/ 里的 5 个片段（3 个网络 + 2 个功能框模板），
它们是从 InoPack 模板导出的 A00 原样结构，只改操作数文本即可复用。

A00 的骨架（不是只有步序网络）：
  NET1  步序号记录器      FB_StepLogger（原样克隆 A00 net01）
  NET2  步序号缓存处理    单步/单站/总控启动三种放行（原样克隆 A00 net02）
  NET3  流程开始          10000 -> 10
  NET4-7 安全自检         10/15/20/30：C1 复位、C2 复位、A1 安全位、A0 安全位 -> 100
  NET8  工位判断跳转      100：产品状态 0/1 -> 1000 取料 / 2000 放料，异常置多料/少料报警（克隆 A00 net08）
  NET9+ 取料段 1000-1120 / 放料段 2000-2060
变量容器用 STNControl[3]（0=总控、1=上料移栽、2=擦拭已占用）。
"""
import io, os, sys

HERE = os.path.dirname(os.path.abspath(sys.argv[0]))
sys.path.insert(0, HERE)
import ldgen as L
import xml.etree.ElementTree as ET

# 仓库布局：本脚本在 scripts/examples/，骨架片段在 assets/natives/a00-fragments/
ROOT = os.path.dirname(os.path.dirname(HERE))
FRAG = os.path.join(ROOT, "assets", "natives", "a00-fragments")
TPL_CYL = os.path.join(FRAG, "fc_cylinderexe.xml")
TPL_AXIS = os.path.join(FRAG, "fc_axisabsgo.xml")


def fc_box(tpl_path, operands):
    """克隆 A00 导出的功能框结构，只替换操作数文本。"""
    root = ET.fromstring(io.open(tpl_path, "r", encoding="utf-8").read().strip())
    els = [e for e in root.iter()
           if e.tag == "Single" and e.get("Name") == "Operand" and e.get("Type") == "string"]
    if len(els) < len(operands):
        raise RuntimeError("template %s operands=%d < %d" % (tpl_path, len(els), len(operands)))
    for el, val in zip(els, operands):
        el.text = val
    return ET.tostring(root, encoding="unicode")


def cyl(name, val):
    return fc_box(TPL_CYL, [name, val])


def axis(name, pos):
    return fc_box(TPL_AXIS, [name, pos, u"0"])


def cdone(c):
    return L.contact(u"G_astCylinder[%s].xDone" % c)


def adone(a):
    return L.contact(u"G_astAxis[%s].o_xAbsDone" % a)

TPL = FRAG
SKEL = os.environ.get("LDSKEL") or os.path.join(ROOT, "assets", "natives", "user_fixed.native")
OUT = os.environ.get("LDOUT") or os.path.join(HERE, "prg_Stn3LoadSeq.native")

STN = u"STNControl[3]."
AX0 = u"A0_上料移栽直线电机轴"
AX1 = u"A1_上料移栽R轴"
C0 = u"C0_上料移载夹紧气缸"
C1 = u"C1_上料移载升降气缸"
C2 = u"C2_上料移载伸出气缸"

# 让 ldgen 的语义构件全部指向 STNControl[3]
L.AUTOING = STN + u"xAutoing"
L.STEP = STN + u"aiAutoStep[0]"
L.BUF = STN + u"aiAutoStepBuffer[0]"
L.DESC = STN + u"awstrAutoDescription[0]"


def read_tpl(name):
    return io.open(os.path.join(TPL, name), "r", encoding="utf-8").read().strip()


def sub(xml, pairs):
    s = xml
    for a, b in pairs:
        if a not in s:
            raise RuntimeError(u"替换未命中: %s" % a)
        s = s.replace(a, b)
    return s


# ── NET1 / NET2：原样克隆 A00，只换工站位号 ────────────────────────────
net01 = sub(read_tpl("net01_step_logger.xml"), [(u"STNControl[1].", STN)])
net02 = sub(read_tpl("net02_step_buffer.xml"), [(u"STNControl[1].", STN)])

# ── NET8：工位判断跳转，换掉上料移栽专有的三个符号 ──────────────────────
net08 = sub(read_tpl("net08_station_dispatch.xml"), [
    (u"STNControl[1].", STN),
    (u"Gr_stS1上料移栽工位状态.ui产品状态", u"iStationProductState"),
    (u"G_xS1上料移载有无料检测感应", u"xMaterialAtStation"),
    (u"HAL_stStation1Alarm.x上料移栽异常多料报警", u"xAlarmOver"),
    (u"HAL_stStation1Alarm.x上料移栽异常少料报警", u"xAlarmShort"),
])

nets = [net01, net02]

# ── 流程开始 ────────────────────────────────────────────────────────
nets.append(L.step_net2(10000, u"流程开始", [], 10, unconditional=True))

# ── 安全自检 10/15/20/30 ────────────────────────────────────────────
nets.append(L.step_net(10, u"安全自检--C1_上料移载升降气缸复位",
                       [cyl(C1, u"0")], 15, cdone(C1)))
nets.append(L.step_net(15, u"安全自检--C2_上料移载伸出气缸复位",
                       [cyl(C2, u"0")], 20, cdone(C2)))
nets.append(L.step_net(20, u"安全自检--A1_上料移栽R轴去安全位",
                       [axis(AX1, u"A1P_安全位")], 30, adone(AX1)))
nets.append(L.step_net(30, u"安全自检--A0_上料移栽直线电机轴去安全位",
                       [axis(AX0, u"A0P_安全位")], 100, adone(AX0)))

# ── 工位判断跳转（克隆 A00 net08）────────────────────────────────────
nets.append(net08)

# ── 取料段 ──────────────────────────────────────────────────────────
nets.append(L.note_net(u"*无料，取料流程*"))
nets.append(L.step_net(1000, u"C0_上料移载夹紧气缸复位、A0_上料移栽直线电机轴去取料位",
                       [cyl(C0, u"0"), axis(AX0, u"A0P_上料机取料位")], 1010,
                       L.and_box([cdone(C0), adone(AX0)])))
nets.append(L.step_net(1010, u"A1_上料移栽R轴去A1P_上料机取料位",
                       [axis(AX1, u"A1P_上料机取料位")], 1020, adone(AX1)))
nets.append(L.step_net(1020, u"等待上料机请求取料", [], 1025,
                       done_contact=L.contact(u"xPickRequest")))
nets.append(L.step_net(1025, u"C2_上料移载伸出气缸伸出", [cyl(C2, u"1")], 1030, cdone(C2)))
nets.append(L.step_net(1030, u"C1_上料移载升降气缸伸出", [cyl(C1, u"1")], 1040, cdone(C1)))
nets.append(L.step_net(1040, u"C0_上料移载夹紧气缸伸出（夹紧抓料）",
                       [cyl(C0, u"1")], 1050, cdone(C0)))
nets.append(L.step_net(1050, u"C1_上料移载升降气缸复位", [cyl(C1, u"0")], 1060, cdone(C1)))
# 1060：夹爪物料检测 —— 有料去缩回，无料判取料失败
nets.append(L.judge_net(1060, u"判断夹爪物料检测感应", [
    (L.contact(u"xMaterialAtGrip"), 1090),
    (L.contact(u"xMaterialAtGrip", neg=True), 1070),
]))
nets.append(L.step_net(1070, u"取料失败--C0_上料移载夹紧气缸复位后重夹",
                       [cyl(C0, u"0")], 1030, cdone(C0)))
nets.append(L.step_net(1090, u"C2_上料移载伸出气缸缩回", [cyl(C2, u"0")], 1095, cdone(C2)))
# 1095：置产品状态=1，回复取料完成（BOOL 用线圈，INT 用 MOVE）
nets.append(L.network([L.branch(L.step_gate(1095), [
    L.desc_tree(u"置工位产品状态=1，回复取料完成"),
    L.act_tree(L.move_box(L.value_pin(u"1", u"INT"), u"iStationProductState", u"INT")),
    L.coil_tree([L.set_coil(u"xPickDone")]),
    L.jump_tree(1100, unconditional=True),
])], u"置工位产品状态=1，回复取料完成"))
nets.append(L.step_net(1100, u"等待上料机请求信号复位", [], 1110,
                       done_contact=L.contact(u"xPickRequest", neg=True)))
nets.append(L.network([L.branch(L.step_gate(1110), [
    L.desc_tree(u"复位取料完成回复"),
    L.coil_tree([L.reset_coil(u"xPickDone")]),
    L.jump_tree(1120),
])], u"复位取料完成回复"))
nets.append(L.step_net2(1120, u"跳回工位判断", [], 100, unconditional=True))

# ── 放料段 ──────────────────────────────────────────────────────────
nets.append(L.note_net(u"*有料，放料流程*"))
nets.append(L.step_net(2000, u"A0_上料移栽直线电机轴、A1_上料移栽R轴去擦拭A1放料位",
                       [axis(AX0, u"A0P_擦拭A1放料位"), axis(AX1, u"A1P_擦拭A1放料位")],
                       2010, L.and_box([adone(AX0), adone(AX1)])))
nets.append(L.step_net(2010, u"C2_上料移载伸出气缸伸出", [cyl(C2, u"1")], 2020, cdone(C2)))
nets.append(L.step_net(2020, u"C1_上料移载升降气缸伸出", [cyl(C1, u"1")], 2030, cdone(C1)))
nets.append(L.step_net(2030, u"C0_上料移载夹紧气缸复位（放料）",
                       [cyl(C0, u"0")], 2040, cdone(C0)))
nets.append(L.step_net(2040, u"C1_上料移载升降气缸复位", [cyl(C1, u"0")], 2050, cdone(C1)))
nets.append(L.step_net(2050, u"C2_上料移载伸出气缸缩回", [cyl(C2, u"0")], 2060, cdone(C2)))
nets.append(L.network([L.branch(L.step_gate(2060), [
    L.desc_tree(u"置工位产品状态=0，跳回工位判断"),
    L.act_tree(L.move_box(L.value_pin(u"0", u"INT"), u"iStationProductState", u"INT")),
    L.jump_tree(100, unconditional=True),
])], u"置工位产品状态=0，跳回工位判断"))

DECL = [
    u"PROGRAM prg_Stn3LoadSeq",
    u"VAR",
    u"    v_aFBStepLogger : ARRAY[0..0] OF FB_StepLogger; // 步序号记录器实例（A00 里声明在父 POU）",
    u"    iStationProductState : INT; // 本工位产品状态：0=无料 / 1=有料",
    u"    xMaterialAtStation : BOOL; // 工位有无料检测感应",
    u"    xPickRequest : BOOL; // 上料机请求取料",
    u"    xPickDone : BOOL; // 回复上料机取料完成",
    u"    xMaterialAtGrip : BOOL; // 夹爪有无料检测感应",
    u"    xAlarmOver : BOOL; // 异常多料报警",
    u"    xAlarmShort : BOOL; // 异常少料报警",
    u"END_VAR",
]

f = io.open(SKEL, "r", encoding="utf-8")
try:
    SK = f.read()
finally:
    f.close()

r = L.build_doc(SK, u"prg_Stn3LoadSeq", DECL, nets, OUT)
for k in sorted(r.keys()):
    print("%-10s %s" % (k, r[k]))
