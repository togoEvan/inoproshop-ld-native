# -*- coding: utf-8 -*-
# @py3
"""按「除油倒盘-擦拭机-PLCV20261124」工程真实结构复现 LD 写法。

所有结构均取自该工程的全量导出（D:\\plc_study\\split\\*.export）逐字段核对，
不是猜的。覆盖 8 个网络，每个网络对应模板里的一种真实写法：

  网络1  并联分支组 BRANCH —— 模板最主流写法（679/940 个网络是纯 BRANCH）
         Trees = [ NETITEM(RValue=连接器, 输出 R 线圈), AND[ MOVE框, {505bff94}占位 ] ]
  网络2  裸触点直挂 NETITEM.RValue + 普通线圈（单条件，不建 AND 框）
  网络3  NETITEM.RValue 直挂 EQ 比较框（InputItems 3 槽：EN触点 + 2 值引脚）
  网络4  NETITEM.RValue 直挂 LT 比较框，槽0 再嵌 GE 比较框（比较框可嵌套）
  网络5  NETITEM.RValue 直挂 ADD 框（InputFlags 是 List2，逐引脚标志）
  网络6  BRANCH.Input 挂 TON 实例框，两条 Trees 各带一个线圈（模板典型）
  网络7  S/R 线圈（线圈 Operand.Flags = 2/3）
  网络8  EXECUTE 框内嵌 ST 代码块（直接挂 NetworkItems，不套 NETITEM）

关键结构事实（本轮逐字段复核，与旧扫描脚本结论不同的地方已修正）：
  · AND 框 InputParam / OutputParam 都是**空列表**，不是 ['EN']
  · 比较框 InputParam=['EN'] 但 InputItems 有 **3 槽**（槽0 是 EN 触点）
  · 比较框 OutputParam=[''] 只有 1 项，OutputItems 也是 1 项（<Null/>）
  · 比较框 EN=True / ENO=False；MOVE、ADD 的 EN/ENO 都是 True
  · ADD/LE/FC_xxx 的 InputFlags 是 List2（逐引脚），AND/MOVE/EQ/GT/LT/GE/TON 是 Null
  · {505bff94} 空占位只出现在 AND 的 InputItems 槽1，紧跟一个功能框

生成：prg_ReproStudy（PROGRAM）
"""
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
from make_ld_learn import (   # noqa: E402
    G_BOX, G_BRANCH, G_NETITEM, G_RVALUE, G_OUTPUTS, G_OPERAND, G_FLAGS,
    G_CALLTYPE, G_PARAM, G_MODE, G_CONNOUT, G_CONTACT,
    nid, flags_block, conn_flags_block, operand, contact, value_pin,
    connector_slot, connector_out, coil, out_operand, and_box, network,
    netitem_box_rvalue, execute_box, build_pou, xml_text,
)

POU_NAME = u"prg_ReproStudy"
OUT = os.path.abspath(os.path.join(
    BASE_DIR, u"..", u"..", u"..", u"plc_mcp", u"ipc", POU_NAME + u".native"))


# ══════════════════════════════════════════════════════════════════════
# 通用功能框构造器（CallType 可变，InputFlags 可给 List2）
# ══════════════════════════════════════════════════════════════════════

def input_flags_block(pairs):
    """InputFlags 为 List2 的形态（ADD / LE / FC_xxx 才有）。

    pairs: [(flags_int, fixed_bool), ...]，长度必须 == InputItems 槽数。
    模板实测 ADD：[(16, True), (0, False), (0, False)]
    """
    items = []
    for fl, fx in pairs:
        items.append(
            u'    <Single Type="%s" Method="IArchivable">\n'
            u'      <Single Name="Extensible" Type="bool">False</Single>\n'
            u'      <Single Name="Fixed" Type="bool">%s</Single>\n'
            u'      <Single Name="Flags" Type="int">%d</Single>\n'
            u'    </Single>' % (G_FLAGS, u"True" if fx else u"False", fl))
    return (u'  <List2 Name="InputFlags">\n%s\n  </List2>' % u"\n".join(items))


def generic_box(box_type, call_type, in_items, in_names, in_types,
                out_items, out_names, out_types,
                en=True, eno=True, fixed=True, input_flags=None,
                is_box_type=True, instance=None):
    """通用功能框：CallType / InputFlags / EN / ENO 全部显式给。

    ⚠ 与 make_ld_learn.fb_box 的区别：那个写死 CallType=FunctionBlock、
      InputFlags=Null，只能造 FB 类框。比较框（Eq/Lt/Ge）、MOVE（Move）、
      ADD（Add）都需要不同的 CallType，ADD/LE 还需要 List2 的 InputFlags。
    ⚠ 不校验 in_items 与 in_names 等长：模板里比较框 InputParam 只有
      ['EN'] 一个名字，但 InputItems 有 3 槽（槽0=EN触点，槽1/2=比较值）。
      强行等长会造出错误的框。
    ⚠ instance：仅 FunctionBlock 类（TON / FB_xxx）需要，模板实测
      Instance.Operand = 实例名（字符串）、Instance.Type = BoxType 名。
      其余框（MOVE/EQ/ADD/...）Instance.Operand 必须是 <Null/>、Type 为空。
      写错会报「已标识项中有一项的格式无效」。
    """
    body = u"\n".join(in_items)
    outs = u"\n".join(out_items)
    inf = input_flags if input_flags is not None else u'  <Null Name="InputFlags" />'
    if instance:
        inst_op = u'    <Single Name="Operand" Type="string">%s</Single>' % instance
        inst_ty = u'    <Single Name="Type" Type="string">%s</Single>' % box_type
    else:
        inst_op = u'    <Null Name="Operand" />'
        inst_ty = u'    <Single Name="Type" Type="string"></Single>'
    return (u'<Single Type="%s" Method="IArchivable">\n'
            u'  <Single Name="ContainsExtensibleInputs" Type="bool">False</Single>\n'
            u'  <Single Name="EN" Type="bool">%s</Single>\n'
            u'  <Single Name="ENO" Type="bool">%s</Single>\n'
            u'  <Single Name="ProvidesSTSnippet" Type="bool">False</Single>\n'
            u'  %s\n'
            u'%s\n'
            u'  <List2 Name="InputItems">\n%s\n  </List2>\n'
            u'  <Single Name="CallType" Type="%s">%s</Single>\n'
            u'  <Single Name="Instance" Type="%s" Method="IArchivable">\n'
            u'    <Single Name="Boolean" Type="bool">False</Single>\n'
            u'    <Single Name="IsInstance" Type="bool">True</Single>\n'
            u'    <Single Name="LValue" Type="bool">False</Single>\n'
            u'    %s\n'
            u'    <Single Name="Address" Type="string"></Single>\n'
            u'    <Single Name="Comment" Type="string"></Single>\n'
            u'%s\n'
            u'    <Single Name="SymbolComment" Type="string"></Single>\n'
            u'%s\n'
            u'    <Single Name="IsCoil" Type="bool">False</Single>\n'
            u'    <Single Name="IsSeriesCoil" Type="bool">False</Single>\n'
            u'    <Single Name="SeriesIndex" Type="int">-1</Single>\n'
            u'    %s\n'
            u'    <Single Name="Id" Type="long">%d</Single>\n'
            u'  </Single>\n'
            u'  <Single Name="OutputItems" Type="%s" Method="IArchivable">\n'
            u'    <List2 Name="OutputItems">\n%s\n    </List2>\n'
            u'  </Single>\n'
            u'  %s\n'
            u'  %s\n'
            u'  <Single Name="BoxType" Type="string">%s</Single>\n'
            u'  <Null Name="STSnippet" />\n'
            u'  <Single Name="IsBoxType" Type="bool">%s</Single>\n'
            u'  <Single Name="Id" Type="long">%d</Single>\n'
            u'</Single>' % (G_BOX,
                            u"True" if en else u"False",
                            u"True" if eno else u"False",
                            flags_block(0, fixed), inf, body,
                            G_CALLTYPE, call_type,
                            G_OPERAND, flags_block(0), inst_op, inst_ty,
                            conn_flags_block(), nid(),
                            G_OUTPUTS, outs,
                            _param(u"InputParam", in_names, in_types),
                            _param(u"OutputParam", out_names, out_types),
                            box_type,
                            u"True" if is_box_type else u"False",
                            nid()))


def _param(name, names, types):
    nb = u"\n".join(u'    <Single Type="string">%s</Single>' % n for n in names)
    tb = u"\n".join(u'    <Single Type="string">%s</Single>' % t for t in types)
    return (u'  <Single Name="%s" Type="%s" Method="IArchivable">\n'
            u'    <List2 Name="Names">\n%s\n    </List2>\n'
            u'    <List2 Name="Types">\n%s\n    </List2>\n'
            u'  </Single>' % (name, G_PARAM, nb, tb))


# ══════════════════════════════════════════════════════════════════════
# 各类具体框
# ══════════════════════════════════════════════════════════════════════

def move_box(in_var, out_var, typ=u"BOOL", cond_var=None):
    """MOVE 框：CallType=Move，InputItems=[电源流, 源值]，OutputItems=[ENO空, 目标]。

    模板实测：InputParam=['EN'] / OutputParam=['ENO',''] / EN=True ENO=True
    槽0 电源流：顶层直挂时是连接器 {5f9848d3}；嵌在 AND 里时是条件触点。
    """
    slot0 = connector_slot() if cond_var is None else contact(cond_var)
    return generic_box(
        box_type=u"MOVE", call_type=u"Move",
        in_items=[slot0, value_pin(in_var, typ)],
        in_names=[u"EN"], in_types=[u"BOOL"],
        out_items=[u'      <Null />', u'      ' + out_operand(out_var, typ)],
        out_names=[u"ENO", u""], out_types=[u"BOOL", u""],
        en=True, eno=True, fixed=True, input_flags=None)


def cmp_box(box_type, call_type, cond_var, a_var, b_var, typ=u"INT"):
    """比较框 EQ/NE/GT/LT/GE/LE。

    模板实测（3 槽）：
      InputItems[0] = EN 触点（IsContact=True，BOOL 条件）
      InputItems[1] = 左操作数（值引脚）
      InputItems[2] = 右操作数（值引脚）
      InputParam=['EN'] / OutputParam=[''] / EN=True / ENO=False
      OutputItems 只有 1 项 <Null/>
    """
    return generic_box(
        box_type=box_type, call_type=call_type,
        in_items=[contact(cond_var), value_pin(a_var, typ), value_pin(b_var, typ)],
        in_names=[u"EN"], in_types=[u"BOOL"],
        out_items=[u'      <Null />'],
        out_names=[u""], out_types=[u"BOOL"],
        en=True, eno=False, fixed=True, input_flags=None)


def cmp_box_nested(box_type, call_type, inner_box, a_var, b_var, typ=u"INT"):
    """比较框的槽0 再嵌一个比较框（模板 LT 里嵌 GE 共 32 处）。

    ⚠ 槽0 是框而不是触点时，InputItems 就是 [框, 值, 值]。
    """
    return generic_box(
        box_type=box_type, call_type=call_type,
        in_items=[inner_box, value_pin(a_var, typ), value_pin(b_var, typ)],
        in_names=[u"EN"], in_types=[u"BOOL"],
        out_items=[u'      <Null />'],
        out_names=[u""], out_types=[u"BOOL"],
        en=True, eno=False, fixed=True, input_flags=None)


def add_box(a_var, b_var, out_var, typ=u"INT"):
    """ADD 框：InputFlags 是 List2（模板实测 [(16,True),(0,False),(0,False)]）。

    InputItems=[电源流连接器, 加数1, 加数2]，OutputParam=['ENO','']。
    注意 InputFlags 首项 flags=16 / Fixed=True —— 这是「电源流引脚」的标志，
    与 S/R 线圈无关（旧结论误判为 S/R 专用，本轮已推翻）。
    """
    return generic_box(
        box_type=u"ADD", call_type=u"Add",
        in_items=[connector_slot(), value_pin(a_var, typ), value_pin(b_var, typ)],
        in_names=[u"EN"], in_types=[u"BOOL"],
        out_items=[u'      <Null />', u'      ' + out_operand(out_var, typ)],
        out_names=[u"ENO", u""], out_types=[u"BOOL", typ],
        en=True, eno=True, fixed=True,
        input_flags=input_flags_block([(16, True), (0, False), (0, False)]))


def ton_box(instance, in_slot, pt_var):
    """TON 实例框：CallType=FunctionBlock，Instance.Operand=实例名，Instance.Type='TON'。

    ⚠ 模板实测 47 个 TON：Instance.Operand 全部有实例名（TON_0/1/2...），
      Instance.Type 全部 = 'TON'。写空 Type 会报「已标识项中有一项的格式无效」。
    ⚠ EN=False / ENO=False（全部 47 个如此）。
    ⚠ 框级 Flags.Fixed 在模板里两种都有（True 27 个 / False 20 个），均合法；
      这里取 True（与 MOVE/比较框一致，不会多画空引脚）。
    ⚠ TON 的 OutputParam 是 ['Q','ET']，**没有 ENO**，所以两个输出都不是
      「ENO 空位」语义，未接线时两项都写 <Null/>。
    """
    return generic_box(
        box_type=u"TON", call_type=u"FunctionBlock",
        in_items=[in_slot, value_pin(pt_var, u"TIME")],
        in_names=[u"IN", u"PT"], in_types=[u"BOOL", u"TIME"],
        out_items=[u'      <Null />', u'      <Null />'],
        out_names=[u"Q", u"ET"], out_types=[u"BOOL", u"TIME"],
        en=False, eno=False, fixed=True, input_flags=None,
        instance=instance)


def ph_slot():
    """{505bff94} 空占位：只出现在 AND 的 InputItems 槽1，紧跟一个功能框。

    模板实测 2205 处，形态恒为
      <Single Type="{505bff94...}" Method="IArchivable"><Single Name="Id" .../></Single>
    """
    return connector_out()


def branch(trees, input_slot=None):
    """分支组：Trees 之间是并联（OR），Mode 恒为 Sequential。

    模板实测 990 个 BRANCH，Mode 全部 = 'Sequential'；Trees 条数 2~17。
    Input 可以是 Null、触点(PIN)、比较框、TON 框、AND 框、嵌套 BRANCH。
    """
    inp = (u'  <Null Name="Input" />' if input_slot is None
           else u'  ' + input_slot.replace(u'<Single Type="',
                                           u'<Single Name="Input" Type="', 1))
    return (u'<Single Type="%s" Method="IArchivable">\n'
            u'%s\n'
            u'  <List2 Name="Trees">\n%s\n  </List2>\n'
            u'  <Single Name="Mode" Type="%s">Sequential</Single>\n'
            u'  <Single Name="Id" Type="long">%d</Single>\n'
            u'</Single>' % (G_BRANCH, inp, u"\n".join(trees), G_MODE, nid()))


def netitem_rv(node, coils, inverted=False):
    """NETITEM 的 RValue 挂任意图形节点（框 / 分支组 / 裸触点）。"""
    rv = node.replace(u'<Single Type="', u'<Single Name="RValue" Type="', 1)
    return (u'<Single Type="%s" Method="IArchivable">\n'
            u'  %s\n'
            u'  %s\n'
            u'  <Single Name="OutputItems" Type="%s" Method="IArchivable">\n'
            u'    <List2 Name="OutputItems">\n%s\n    </List2>\n'
            u'  </Single>\n'
            u'  <Single Name="Id" Type="long">%d</Single>\n'
            u'</Single>' % (G_NETITEM, flags_block(1 if inverted else 0), rv,
                            G_OUTPUTS, u"\n".join(coils), nid()))


def netitem_plain(coils, inverted=False):
    """NETITEM 的 RValue 只有电源流连接器（无任何条件元件）。"""
    return netitem_rv(connector_slot(), coils, inverted)


# ══════════════════════════════════════════════════════════════════════
# 网络构建
# ══════════════════════════════════════════════════════════════════════

def build_networks():
    nets = []

    # ── 网络1：并联分支组（模板最主流写法）─────────────────────────
    # Trees[0] = 无条件支路：NETITEM(RValue=连接器) → R 线圈
    # Trees[1] = AND[MOVE框, {505bff94}占位] → 无输出（MOVE 自带输出引脚）
    n1 = branch([
        netitem_plain([coil(u"o_xBranchA", flags=3)]),
        and_box([
            move_box(u"i_xMode", u"o_xMode"),
            ph_slot(),
        ]),
    ])
    nets.append(network(
        [n1],
        u"// 网络1：并联分支组 BRANCH(Trees=2)。"
        u"支路1 = 无条件 R 线圈；支路2 = AND[MOVE框, {505bff94}占位]"))

    # ── 网络2：裸触点直挂 + 普通线圈（单条件，不建 AND 框）──────────
    nets.append(network(
        [netitem_rv(contact(u"i_xCond"), [coil(u"o_xDirect")])],
        u"// 网络2：单条件 —— 裸触点直接作 RValue，不套 AND 框、不补 TRUE"))

    # ── 网络3：RValue 直挂 EQ 比较框（3 槽）────────────────────────
    nets.append(network(
        [netitem_rv(cmp_box(u"EQ", u"Eq", u"i_xCond", u"i_iStep", u"i_iTarget"),
                    [coil(u"o_xStepEq")])],
        u"// 网络3：EQ 比较框直挂 RValue。InputItems 3 槽 = EN触点 + 左值 + 右值"))

    # ── 网络4：LT 里嵌 GE（比较框可嵌套）──────────────────────────
    inner_ge = cmp_box(u"GE", u"Ge", u"i_xCond", u"i_iStep", u"i_iLow")
    nets.append(network(
        [netitem_rv(cmp_box_nested(u"LT", u"Lt", inner_ge, u"i_iStep", u"i_iHigh"),
                    [coil(u"o_xInRange")])],
        u"// 网络4：LT 的槽0 再嵌一个 GE 比较框（模板 32 处）"))

    # ── 网络5：ADD 框（InputFlags 是 List2）───────────────────────
    nets.append(network(
        [netitem_rv(add_box(u"i_iA", u"i_iB", u"o_iSum"), [coil(u"o_xSumDone")])],
        u"// 网络5：ADD 框。InputFlags=List2[(16,True),(0,False),(0,False)]"))

    # ── 网络6：BRANCH.Input 挂 TON，两条 Trees 各带线圈 ────────────
    ton = ton_box(u"fbDelay", connector_slot(), u"T#2S")
    n6 = branch([
        netitem_plain([coil(u"o_xTimerDone")]),
        netitem_plain([coil(u"o_xTimerDone2")]),
    ], input_slot=ton)
    nets.append(network(
        [n6],
        u"// 网络6：BRANCH.Input = TON 实例框，两条 Trees 共享定时器输出"))

    # ── 网络7：S/R 线圈（Flags=2 置位 / 3 复位）────────────────────
    nets.append(network(
        [netitem_rv(contact(u"i_xSet"), [coil(u"o_xLatch", flags=2)])],
        u"// 网络7a：置位 S 线圈（Operand.Flags=2）"))
    nets.append(network(
        [netitem_rv(contact(u"i_xRst"), [coil(u"o_xLatch", flags=3)])],
        u"// 网络7b：复位 R 线圈（Operand.Flags=3）"))

    # ── 网络8：EXECUTE 内嵌 ST ───────────────────────────────────
    st = [
        u"// EXECUTE 框：LD 网络里内嵌 ST 代码块",
        u"IF o_xTimerDone THEN",
        u"    i_iStCount := i_iStCount + 1;",
        u"END_IF",
        u"",
        u"o_xStOut := o_xStepEq AND o_xInRange;",
    ]
    nets.append(network([execute_box(st, 496, 200)],
                        u"// 网络8：EXECUTE 内嵌 ST（直接挂 NetworkItems，不套 NETITEM）"))

    return nets


DECL = [
    u"PROGRAM %s" % POU_NAME,
    u"VAR",
    u"    (* ~~~~ 网络1 并联分支组 / MOVE ~~~~~~~~~~~~~~ *)",
    u"    i_xMode        : BOOL;   // MOVE 源",
    u"    o_xMode        : BOOL;   // MOVE 目标",
    u"    o_xBranchA     : BOOL;   // 支路1 的 R 线圈",
    u"",
    u"    (* ~~~~ 网络2 裸触点 ~~~~~~~~~~~~~~ *)",
    u"    i_xCond        : BOOL;   // 通用条件",
    u"    o_xDirect      : BOOL;   // 单条件线圈",
    u"",
    u"    (* ~~~~ 网络3/4 比较框 ~~~~~~~~~~~~~~ *)",
    u"    i_iStep        : INT;    // 当前步序号",
    u"    i_iTarget      : INT;    // 目标步序号",
    u"    i_iLow         : INT;    // 区间下限",
    u"    i_iHigh        : INT;    // 区间上限",
    u"    o_xStepEq      : BOOL;   // EQ 结果",
    u"    o_xInRange     : BOOL;   // LT(GE(...)) 结果",
    u"",
    u"    (* ~~~~ 网络5 ADD ~~~~~~~~~~~~~~ *)",
    u"    i_iA           : INT;    // 加数1",
    u"    i_iB           : INT;    // 加数2",
    u"    o_iSum         : INT;    // 和",
    u"    o_xSumDone     : BOOL;   // ADD 输出线圈",
    u"",
    u"    (* ~~~~ 网络6 TON ~~~~~~~~~~~~~~ *)",
    u"    fbDelay        : TON;    // 定时器实例",
    u"    o_xTimerDone   : BOOL;   // 支路1 输出",
    u"    o_xTimerDone2  : BOOL;   // 支路2 输出",
    u"",
    u"    (* ~~~~ 网络7 S/R 线圈 ~~~~~~~~~~~~~~ *)",
    u"    i_xSet         : BOOL;   // 置位条件",
    u"    i_xRst         : BOOL;   // 复位条件",
    u"    o_xLatch       : BOOL;   // 锁存变量",
    u"",
    u"    (* ~~~~ 网络8 EXECUTE 内嵌 ST ~~~~~~~~~~~~~~ *)",
    u"    i_iStCount     : INT;    // ST 里累加",
    u"    o_xStOut       : BOOL;   // ST 里赋值",
    u"END_VAR",
]


def main():
    from make_ld_learn import _id
    _id[0] = 9000
    out = build_pou(POU_NAME, DECL, build_networks(), OUT)
    print(u"OK %s" % out)


if __name__ == "__main__":
    main()
