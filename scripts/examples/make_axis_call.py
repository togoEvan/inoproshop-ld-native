# -*- coding: utf-8 -*-
"""轴控生成器：复现 InoPack 模板的轴控写法（LD 调用 + FB/action 骨架）。

覆盖的新结构（实测导出见 references/native-structure.md「轴控指令」节）：
  ① 轴控 FB 在 LD 里的调用框
     - CallType=FunctionBlock，BoxType=HC_MovePtpV
     - InputParam.Types 里 REF 形参带 `[REF]` 后缀（HC_sPtpInfo[REF] / AXIS_REF_SM3[REF]）
     - AXIS_REF_SM3 引脚的操作数直接写轴名（Master），引脚 Type 去掉 [REF]
  ② CallType=Action（全新取值）
     - Instance.Operand 是**空字符串**，不是 <Null/>
     - 只有 EN/ENO 一对参数，InputItems 只有 1 个连接器槽

生成两个 POU：
  prg_AxisCallTest —— PROGRAM，验证 ①（调 HC_MovePtpV）
  fb_AxisSkelTest  —— FUNCTION_BLOCK，轴控 FB 的声明骨架（8 个指令实例 + 轴引用放 VAR_IN_OUT）
"""
import io
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

import make_ld_learn as M


def ref_pin(var, typ):
    """[REF] 形参引脚：操作数 Type 写去掉 [REF] 后的实际类型。"""
    return M.value_pin(var, typ)


def axis_fb_box(box_type, instance, in_items, in_names, in_types,
                out_names=None, out_types=None, out_vars=None):
    """轴控 FB 调用框：CallType=FunctionBlock，与普通 FB 同构。

    与 make_ld_learn.fb_box 的唯一区别是允许传入带 [REF] 后缀的类型名，
    并把 Instance.Type 写成去掉后缀的 FB 名。
    """
    out_names = out_names or [u"ENO"]
    out_types = out_types or [u"BOOL"]
    out_vars = out_vars or [u'   <Null/>']
    return M.fb_box(box_type=box_type, instance=instance,
                    in_items=in_items, in_names=in_names, in_types=in_types,
                    out_names=out_names, out_types=out_types,
                    out_vars=out_vars, en=True)


def action_box(action_name, slot):
    """CallType=Action 调用框。

    关键差异（实测 axis_prg_EM00_ETC）：
      - CallType 写 "Action"
      - Instance.Operand 是**空字符串** `<Single Name="Operand" Type="string"></Single>`
        （FB 调用是 <Null/> 或实例名，Action 是空串，这是三态里的第三种）
      - Instance.Type 也是空字符串
      - 只有 EN 一个参数、1 个连接器槽；OutputParam=['ENO']、1 项 <Null/>
    """
    return (u'<Single Type="%s" Method="IArchivable">\n'
            u'  <Single Name="ContainsExtensibleInputs" Type="bool">False</Single>\n'
            u'  <Single Name="EN" Type="bool">True</Single>\n'
            u'  <Single Name="ENO" Type="bool">True</Single>\n'
            u'  <Single Name="ProvidesSTSnippet" Type="bool">False</Single>\n'
            u'  %s\n'
            u'  <Null Name="InputFlags" />\n'
            u'  <List2 Name="InputItems">\n%s\n  </List2>\n'
            u'  <Single Name="CallType" Type="%s">Action</Single>\n'
            u'  <Single Name="Instance" Type="%s" Method="IArchivable">\n'
            u'    <Single Name="Boolean" Type="bool">False</Single>\n'
            u'    <Single Name="IsInstance" Type="bool">True</Single>\n'
            u'    <Single Name="LValue" Type="bool">False</Single>\n'
            u'    %s\n'
            u'    <Single Name="Address" Type="string"></Single>\n'
            u'    <Single Name="Comment" Type="string"></Single>\n'
            u'    <Single Name="Operand" Type="string"></Single>\n'
            u'    <Single Name="SymbolComment" Type="string"></Single>\n'
            u'    <Single Name="Type" Type="string"></Single>\n'
            u'    <Single Name="IsCoil" Type="bool">False</Single>\n'
            u'    <Single Name="IsSeriesCoil" Type="bool">False</Single>\n'
            u'    <Single Name="SeriesIndex" Type="int">-1</Single>\n'
            u'    %s\n'
            u'    <Single Name="Id" Type="long">%d</Single>\n'
            u'  </Single>\n'
            u'  <Single Name="OutputItems" Type="%s" Method="IArchivable">\n'
            u'    <List2 Name="OutputItems">\n     <Null/>\n    </List2>\n'
            u'  </Single>\n'
            u'  %s\n'
            u'  %s\n'
            u'  <Single Name="BoxType" Type="string">%s</Single>\n'
            u'  <Null Name="STSnippet" />\n'
            u'  <Single Name="IsBoxType" Type="bool">True</Single>\n'
            u'  <Single Name="Id" Type="long">%d</Single>\n'
            u'</Single>' % (M.G_BOX, M.flags_block(0), slot,
                            M.G_CALLTYPE, M.G_OPERAND, M.flags_block(0),
                            M.conn_flags_block(), M.nid(), M.G_OUTPUTS,
                            M.param_block(u"InputParam", [u"EN"], [u"BOOL"]),
                            M.param_block(u"OutputParam", [u"ENO"], [u"BOOL"]),
                            action_name, M.nid()))


def build_networks():
    nets = []

    # 网络1：轴控 FB 调用（虚轴 HC_MovePtpV）
    #   InputParam.Names = ['EN','xCondition','stInfo','VirtualAxis']
    #   槽位 4 个：连接器(EN) + 3 个引脚
    box = axis_fb_box(
        box_type=u"HC_MovePtpV",
        instance=u"fbPtpV[0]",
        in_items=[
            M.connector_slot(),                              # EN
            M.contact(u"xAxisSafety"),                       # xCondition (BOOL)
            ref_pin(u"stAxisPtpInfo", u"HC_sPtpInfo"),       # stInfo ([REF])
            ref_pin(u"Master", u"AXIS_REF_SM3"),             # VirtualAxis ([REF])
        ],
        in_names=[u"EN", u"xCondition", u"stInfo", u"VirtualAxis"],
        in_types=[u"BOOL", u"BOOL", u"HC_sPtpInfo[REF]", u"AXIS_REF_SM3[REF]"])
    nets.append(M.network(
        [M.netitem_box_rvalue(box, [M.coil(u"xAxisCalling")])],
        u"// 网络1：轴控 FB 调用 —— AXIS_REF_SM3[REF] 引脚直接写轴名 Master"))

    # 网络2：Action 调用（Instance.Operand 是空字符串）
    nets.append(M.network(
        [M.netitem_box_rvalue(action_box(u"actAbs", M.connector_slot()),
                              [M.coil(u"xAxisActAbs")])],
        u"// 网络2：CallType=Action —— Instance.Operand 是空串，不是 Null 节点"))

    return nets


DECL_PRG = [
    u"",
    u"PROGRAM prg_AxisCallTest",
    u"VAR",
    u"    (* ~~~~ 轴控 FB 调用测试 ~~~~~~~~~~~~~~ *)",
    u"    stAxisPtpInfo : HC_sPtpInfo;   // PLC 侧轴数据接口（[REF] 形参）",
    u"    fbPtpV        : ARRAY[0..0] OF HC_MovePtpV;  // 轴控 FB 实例",
    u"    xAxisSafety   : BOOL;          // 动作条件",
    u"    xAxisCalling  : BOOL;          // FB 调用中",
    u"    xAxisActAbs   : BOOL;          // Action 调用结果",
    u"END_VAR",
]

DECL_FB = [
    u"",
    u"FUNCTION_BLOCK fb_AxisSkelTest",
    u"VAR_INPUT",
    u"    xCondition : BOOL := TRUE;   // 动作条件满足",
    u"END_VAR",
    u"VAR_OUTPUT",
    u"END_VAR",
    u"VAR_IN_OUT",
    u"    // ⚠ 轴引用必须放 VAR_IN_OUT：AXIS_REF_SM3 是结构体，",
    u"    //    放 VAR_INPUT 会复制一份，运动指令不会作用到真实轴",
    u"    stInfo      : HC_sPtpInfo;   // PLC 数据接口",
    u"    VirtualAxis : AXIS_REF_SM3;  // 虚轴轴引用",
    u"END_VAR",
    u"VAR",
    u"    (* ~~~~ 8 个轴控指令，各一个独立实例，不能共用 ~~~~~~~~~~~~~~ *)",
    u"    fbPower       : MC_Power;",
    u"    fbStop        : MC_Stop;",
    u"    fbHalt        : MC_Halt;",
    u"    fbAbsolute    : MC_MoveAbsolute;",
    u"    fbRelative    : MC_MoveRelative;",
    u"    fbSetPosition : MC_SetPosition;",
    u"    fbReset       : MC_Reset;",
    u"    fbVelocity    : HMC_MoveVelocity;   // 汇川扩展：形参小写 xEnable/fVelocity",
    u"    fbJog         : HMC_MoveJog;        // 汇川扩展：xJogForward/xJogBackward",
    u"    (* ~~~~ 中间量 ~~~~~~~~~~~~~~ *)",
    u"    fSetVel     : LREAL;",
    u"    fSetAcc     : LREAL;",
    u"    fSetDec     : LREAL;",
    u"    fSetJerk    : LREAL;",
    u"    fSetMaxDec  : LREAL;",
    u"    fSetMaxJerk : LREAL;",
    u"    xPtpCond    : BOOL;          // 运动条件满足",
    u"END_VAR",
]


def main():
    os.makedirs(M.OUT_DIR, exist_ok=True)

    M._id[0] = 6000
    M.build_pou(u"prg_AxisCallTest", DECL_PRG, build_networks(),
                os.path.join(M.OUT_DIR, "prg_AxisCallTest.native"))

    M._id[0] = 7000
    M.build_pou(u"fb_AxisSkelTest", DECL_FB, build_networks(),
                os.path.join(M.OUT_DIR, "fb_AxisSkelTest.native"))


if __name__ == u"__main__":
    main()
