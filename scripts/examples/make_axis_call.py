# -*- coding: utf-8 -*-
"""轴控生成器：复现 InoPack 模板的轴控写法（LD 调用 + FB/action 骨架）。

覆盖的新结构（实测导出见 references/native-structure.md「轴控指令」节）：
  ① 轴控 FB 在 LD 里的调用框
     - CallType=FunctionBlock，BoxType=HC_MovePtpV
     - InputParam.Types 里 REF 形参带 `[REF]` 后缀（HC_sPtpInfo[REF] / AXIS_REF_SM3[REF]）
     - AXIS_REF_SM3 引脚的操作数直接写轴名（Master），引脚 Type 去掉 [REF]
  ② CallType=Action（全新取值）
     - Instance.Operand 是 **<Null/>**（不是空字符串 Single，那会多画一个可填小方框）
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
    """[REF] 形参引脚。

    ⚠ 关键规律（2026-11-25 实测，模板 axis_act0_Ptp_0 为证）：
    `InputParam.Types` 写**形参声明类型**（`AXIS_REF_SM3[REF]`），
    但引脚的 `Operand.Type` 要写**轴变量的实际完整类型**——
    虚轴是 `SM3_Basic.AXIS_REF_VIRTUAL_SM3`，不是 `AXIS_REF_SM3`。

    写错时：预编译 0 错误、编译 0 错误、消息窗口 0 条——IDE 导入时
    **静默把它改正**，只有往返 diff 能发现（差 1 处 Type 字段）。
    """
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

    关键差异（实测 axis_prg_EM00_ETC / prg_UN00 / prg_EM01_Logic）：
      - CallType 写 "Action"
      - Instance.Operand 必须是 **`<Null Name="Operand" />`**
      - Instance.Type 是空字符串 `<Single Name="Type" Type="string" />`
      - 只有 EN 一个参数、1 个连接器槽；OutputParam=['ENO']、1 项 <Null/>
      - 框级 Flags.Fixed 写 True（Action 框全量样本无一例外是 True）

    ⚠⚠ 血泪教训（2026-11-25，用户第二次指出「actAbs_NOPE 上面还是有小方框」）：
      `Instance.Operand` 写成空 `<Single Name="Operand" Type="string" />`
      会被 IDE 渲染成一个**可填写的操作数小方框**，挂在框上方。
      当初的「Action 的 Operand 是空字符串，不是 Null」结论，是从**自己导入后
      再导出的文件**里反推出来的——自己验证自己，属于循环论证，是错的。
      全量对照真实模板（16 个 Action 框）**全部是 `<Null/>`**。

      规律总结（Operand 三态，看 CallType 决定）：
        FunctionBlock → <Single Type="string">实例名</Single>
        Action / Function / Program / And / Move → <Null/>
      只有 FB 才需要实例名，其余一律 Null；写空 Single 就会多画小方框。
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
            u'    <Null Name="Operand" />\n'
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
            u'</Single>' % (M.G_BOX, M.flags_block(0, True), slot,
                            M.G_CALLTYPE, M.G_OPERAND, M.flags_block(0),
                            M.conn_flags_block(), M.nid(), M.G_OUTPUTS,
                            M.param_block(u"InputParam", [u"EN"], [u"BOOL"]),
                            M.param_block(u"OutputParam", [u"ENO"], [u"BOOL"]),
                            action_name, M.nid()))


def build_networks_prg():
    """PROGRAM 版网络：演示轴控 FB 调用 + Action 调用。

    变量全部来自 DECL_PRG（stAxisPtpInfo / fbPtpV / xAxisSafety / xAxisCalling / xAxisActAbs）。
    """
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
            ref_pin(u"Master", u"SM3_Basic.AXIS_REF_VIRTUAL_SM3"),             # VirtualAxis ([REF])
        ],
        in_names=[u"EN", u"xCondition", u"stInfo", u"VirtualAxis"],
        in_types=[u"BOOL", u"BOOL", u"HC_sPtpInfo[REF]", u"AXIS_REF_SM3[REF]"])
    nets.append(M.network(
        [M.netitem_box_rvalue(box, [M.coil(u"xAxisCalling")])],
        u"// 网络1：轴控 FB 调用 —— AXIS_REF_SM3[REF] 引脚直接写轴名 Master"))

    # 网络2：Action 调用（Instance.Operand 必须是 <Null/>）
    nets.append(M.network(
        [M.netitem_box_rvalue(action_box(u"actAbs", M.connector_slot()),
                              [M.coil(u"xAxisActAbs")])],
        u"// 网络2：CallType=Action —— Instance.Operand 是 Null，不是空串"))

    return nets


def build_networks_fb():
    """FUNCTION_BLOCK 版网络：只演示「在 FB 内部调用轴控 FB」。

    ⚠ 教训（2026-11-25）：不能让 PROGRAM 和 FUNCTION_BLOCK 共用同一套网络。
    FB 的声明区里没有 PROGRAM 的变量（fbPtpV / stAxisPtpInfo / xAxisSafety…），
    共用后 FB 打开全是红波浪线——而**预编译/编译/消息窗口都是 0 错误**，
    只有静态符号检查才能发现。

    这里全部用 FB 自己的接口变量：xCondition(IN) / stInfo、VirtualAxis(IN_OUT)，
    实例 fbPtpV 声明在 FB 的 VAR 里。
    """
    box = axis_fb_box(
        box_type=u"HC_MovePtpV",
        instance=u"fbPtpV[0]",
        in_items=[
            M.connector_slot(),                              # EN
            M.contact(u"xCondition"),                        # xCondition (BOOL)
            ref_pin(u"stInfo", u"HC_sPtpInfo"),              # stInfo ([REF])
            ref_pin(u"VirtualAxis", u"SM3_Basic.AXIS_REF_VIRTUAL_SM3"),        # VirtualAxis ([REF])
        ],
        in_names=[u"EN", u"xCondition", u"stInfo", u"VirtualAxis"],
        in_types=[u"BOOL", u"BOOL", u"HC_sPtpInfo[REF]", u"AXIS_REF_SM3[REF]"])
    return [M.network(
        [M.netitem_box_rvalue(box, [M.coil(u"xAxisCalling")])],
        u"// 在 FB 内部调用轴控 FB —— 全部用 FB 自己的接口变量")]


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
    u"    (* ~~~~ 被调用的轴控 FB 实例 ~~~~~~~~~~~~~~ *)",
    u"    fbPtpV        : ARRAY[0..0] OF HC_MovePtpV;  // 轴控 FB 实例",
    u"    xAxisCalling  : BOOL;          // FB 调用中",
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


# actAbs 这个 action 的 ST 实现。
#
# ⚠⚠ 铁律（2026-11-25 实测）：action 的 ST 体**只能引用宿主 POU 声明区里的变量**。
#   action 属于 prg_AxisCallTest，就只认 prg_AxisCallTest 的 VAR——
#   不能引用 fb_AxisSkelTest 的 xPtpCond / fbAbsolute 之类。
#
#   踩坑记录：这里原本写 `xPtpCond := xAxisSafety AND xAxisCalling;`，
#   xPtpCond 只在 fb_AxisSkelTest 里声明，于是预编译报：
#       [Error] actAbs | 没有定义标识符'xPtpCond'
#   注意这类错误的三个特征：
#     ① 消息归属对象是 **action 名（actAbs）**，不是 POU 名；
#     ② 「预编译」分类里，不在「编译」分类里；
#     ③ 编译分类照样报「0 错误,0 警告」——只看编译分类必漏。
#
#   生成器层面：build_pou(actions=[(name, ST行列表)]) 不会做符号校验，
#   必须靠 check_symbols.py 或本文件的变量对照自查。
ACT_ABS_ST = [
    u"// 轴绝对定位 —— action 骨架",
    u"// ⚠ 只能引用本 PROGRAM 声明区的变量：xAxisSafety / xAxisCalling / xAxisActAbs",
    u"//   真正的运动指令实例（fbAbsolute 等）在 fb_AxisSkelTest 的声明区里，",
    u"//   这里不能直接引用，否则预编译报「没有定义标识符」。",
    u"xAxisActAbs := xAxisSafety AND xAxisCalling;",
]


def main():
    os.makedirs(M.OUT_DIR, exist_ok=True)
    M._id[0] = 6000
    # ⚠ 铁律（2026-11-25 实测）：网络2 里画了 CallType=Action 的 actAbs 调用框，
    #    就必须在本 POU 的 EntryList 里真实建一个 actAbs 的 action Entry。
    #    只写 BoxType 不建 Entry -> 预编译报「没有定义标识符'actAbs'」，
    #    而且**只有全量「重新编译」才报得出来**（增量「检查程序」0 条消息）。
    M.build_pou(u"prg_AxisCallTest", DECL_PRG, build_networks_prg(),
                os.path.join(M.OUT_DIR, "prg_AxisCallTest.native"),
                actions=[(u"actAbs", ACT_ABS_ST)])

    M._id[0] = 7000
    M.build_pou(u"fb_AxisSkelTest", DECL_FB, build_networks_fb(),
                os.path.join(M.OUT_DIR, "fb_AxisSkelTest.native"))


if __name__ == u"__main__":
    main()
