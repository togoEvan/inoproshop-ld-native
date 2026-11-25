# -*- coding: utf-8 -*-
"""学习型生成器：复现 InoPack 模板里 references 尚未记载的三种 LD 写法。

覆盖的新结构（全部来自本机实测导出，见 references/native-structure.md）：
  ① 定时器功能框（TON / CallType=FunctionBlock / EN=False,ENO=False）
     - 顶层：NETITEM.RValue 直接是 TON 框，InputItems[0] = 连接器 {5f9848d3}
     - 嵌套：TON 框挂在 AND 的 InputItems 里，InputItems[0] = 条件触点 {9de7f100}
  ② EXECUTE 框（LD 内嵌 ST 代码块 / CallType=None / ProvidesSTSnippet=True）
     - STSnippet -> STSnippet -> TextDocument -> TextLines
     - 直接挂 Network/NetworkItems，**不套 NETITEM**
  ③ FUNCTION_BLOCK 里的 LD 写法（POU 类型由声明首行决定，TypeGuid 与 PROGRAM 相同）

生成两个 POU：
  prg_LdLearnTest  —— PROGRAM，验证 ①②
  fb_LdLearnTest   —— FUNCTION_BLOCK，验证 ③（FB 内部写 LD）

骨架取自 assets/natives/user_fixed.native（已验证可导入、双分类 0 错误）。
"""
import io
import os
import re
import uuid

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))
SKELETON = os.path.join(ROOT, "assets", "natives", "user_fixed.native")
OUT_DIR = os.path.join(ROOT, "..", "plc_mcp", "ipc")

# ---------------- 节点 GUID ----------------
G_CONTACT = u"{9de7f100-1b87-424c-a62e-45b0cfc85ed2}"
G_BOX = u"{acfc6f68-8e3a-4af5-bf81-3dd512095a46}"
G_BRANCH = u"{827b9ec2-2032-40da-9f4e-7670ca2d55a8}"
G_NETITEM = u"{9873c309-1f09-4ebf-9078-42d8057ef11b}"
G_RVALUE = u"{5f9848d3-568d-4cc5-9e31-8e28e9607ff1}"
G_OUTPUTS = u"{f40d3e09-c02c-4522-a88c-dac23558cfc4}"
G_OPERAND = u"{c9b2f165-48a2-4a45-8326-3952d8a3d708}"
G_FLAGS = u"{668066f2-6069-46b3-8962-8db8d13d7db2}"
G_NETWORK = u"{d9a99d73-b633-47db-b876-a752acb25871}"
G_CALLTYPE = u"{bffb3c53-f105-4e85-aba2-e30df579d75f}"
G_PARAM = u"{71496971-9e0c-4677-a832-b9583b571130}"
G_MODE = u"{3b9474d0-c98b-4935-8ce5-65f06808350d}"
G_CONNOUT = u"{505bff94-4c90-4e17-ac28-b8ac69d1b9e2}"
G_STSNIP = u"{b2131366-6917-4304-87a9-64c0585560a8}"
G_STSNIP2 = u"{3b83b776-fb25-43b8-99f2-3c507c9143fc}"
G_TEXTDOC = u"{f3878285-8e4f-490b-bb1b-9acbb7eb04db}"
G_TEXTLINE = u"{a5de0b0b-1cb5-4913-ac21-9d70293ec00d}"

_id = [3000]


def nid():
    _id[0] += 1
    return _id[0]


def flags_block(n=0, fixed=False):
    return (u'<Single Name="Flags" Type="%s" Method="IArchivable">\n'
            u'  <Single Name="Extensible" Type="bool">False</Single>\n'
            u'  <Single Name="Fixed" Type="bool">%s</Single>\n'
            u'  <Single Name="Flags" Type="int">%d</Single>\n'
            u'</Single>' % (G_FLAGS, u"True" if fixed else u"False", n))


def conn_flags_block():
    return (u'<Single Name="ConnectorFlags" Type="%s" Method="IArchivable">\n'
            u'  <Single Name="Extensible" Type="bool">False</Single>\n'
            u'  <Single Name="Fixed" Type="bool">False</Single>\n'
            u'  <Single Name="Flags" Type="int">0</Single>\n'
            u'</Single>' % G_FLAGS)


def operand(var, typ=u"BOOL", boolean=True, is_instance=False,
            lvalue=False, flags=0, is_coil=False, inner_fixed=True,
            name=u"Operand"):
    """构造一个 Operand 节点（触点/引脚/线圈/实例共用）。

    ⚠ `name` 必须区分：
      - 触点、输入引脚、Instance  → Name="Operand" / "Instance"
      - 线圈、功能框输出引脚      → **不带 Name 属性**（`name=None`）
    线圈若多写 Name="Operand"，IDE 导入后会静默抹掉该属性，
    往返导出即与源文件不一致（实测差异点）。
    """
    if name is None:
        head = u'<Single Type="%s" Method="IArchivable">\n' % G_OPERAND
    else:
        head = u'<Single Name="%s" Type="%s" Method="IArchivable">\n' % (name, G_OPERAND)
    return (head +
            u'  <Single Name="Boolean" Type="bool">%s</Single>\n'
            u'  <Single Name="IsInstance" Type="bool">%s</Single>\n'
            u'  <Single Name="LValue" Type="bool">%s</Single>\n'
            u'  %s\n'
            u'  <Single Name="Address" Type="string"></Single>\n'
            u'  <Single Name="Comment" Type="string"></Single>\n'
            u'  <Single Name="Operand" Type="string">%s</Single>\n'
            u'  <Single Name="SymbolComment" Type="string"></Single>\n'
            u'  <Single Name="Type" Type="string">%s</Single>\n'
            u'  <Single Name="IsCoil" Type="bool">%s</Single>\n'
            u'  <Single Name="IsSeriesCoil" Type="bool">False</Single>\n'
            u'  <Single Name="SeriesIndex" Type="int">-1</Single>\n'
            u'  %s\n'
            u'  <Single Name="Id" Type="long">%d</Single>\n'
            u'</Single>' % (u"True" if boolean else u"False",
                            u"True" if is_instance else u"False",
                            u"True" if lvalue else u"False",
                            flags_block(flags, inner_fixed), var, typ,
                            u"True" if is_coil else u"False",
                            conn_flags_block(), nid()))


def contact(var, not_flag=False, typ=u"BOOL"):
    """触点 / 常量引脚（IsContact=True 的输入项）。常量必须 Flags=0。"""
    is_const = var in (u"TRUE", u"FALSE")
    ofl = 0 if is_const else (1 if not_flag else 0)
    return (u'<Single Type="%s" Method="IArchivable">\n'
            u'  %s\n'
            u'  <Single Name="IsContact" Type="bool">True</Single>\n'
            u'  <Single Name="Id" Type="long">%d</Single>\n'
            u'</Single>' % (G_CONTACT, operand(var, typ, True, False, False, ofl), nid()))


def value_pin(var, typ):
    """值输入引脚（IsContact=False）：MOVE 的 IN、TON 的 PT 等。"""
    return (u'<Single Type="%s" Method="IArchivable">\n'
            u'  %s\n'
            u'  <Single Name="IsContact" Type="bool">False</Single>\n'
            u'  <Single Name="Id" Type="long">%d</Single>\n'
            u'</Single>' % (G_CONTACT, operand(var, typ, False, False, False, 0), nid()))


def connector_slot():
    """连接器槽 {5f9848d3}：功能框的「电源流」输入（Input=Null）。"""
    return (u'<Single Type="%s" Method="IArchivable">\n'
            u'  %s\n'
            u'  <Null Name="Input" />\n'
            u'  <Single Name="Id" Type="long">%d</Single>\n'
            u'</Single>' % (G_RVALUE, flags_block(0), nid()))


def connector_out():
    """支路输出连接器 {505bff94}：完整支路的第二个槽。"""
    return (u'<Single Type="%s" Method="IArchivable">\n'
            u'  <Single Name="Id" Type="long">%d</Single>\n'
            u'</Single>' % (G_CONNOUT, nid()))


def coil(var, typ=u"BOOL", flags=0):
    """输出线圈（NETITEM.OutputItems 里的操作数）。⚠ 不带 Name 属性。"""
    return operand(var, typ, True, False, True, flags, is_coil=True,
                   inner_fixed=False, name=None)


def out_operand(var, typ):
    """功能框输出引脚接线的目标操作数（LValue=True, IsCoil=False）。⚠ 不带 Name 属性。"""
    return operand(var, typ, False, False, True, 0, is_coil=False,
                   inner_fixed=False, name=None)


def and_box(items):
    """AND 功能框：EN/ENO 是 <Null/>，IsBoxType=False，Instance.Operand=<Null/>。"""
    body = u"\n".join(items)
    return (u'<Single Type="%s" Method="IArchivable">\n'
            u'  <Single Name="ContainsExtensibleInputs" Type="bool">False</Single>\n'
            u'  <Null Name="EN" />\n'
            u'  <Null Name="ENO" />\n'
            u'  <Single Name="ProvidesSTSnippet" Type="bool">False</Single>\n'
            u'  %s\n'
            u'  <Null Name="InputFlags" />\n'
            u'  <List2 Name="InputItems">\n%s\n  </List2>\n'
            u'  <Single Name="CallType" Type="%s">And</Single>\n'
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
            u'    <List2 Name="OutputItems" />\n'
            u'  </Single>\n'
            u'  <Single Name="InputParam" Type="%s" Method="IArchivable">\n'
            u'    <List2 Name="Names" />\n    <List2 Name="Types" />\n  </Single>\n'
            u'  <Single Name="OutputParam" Type="%s" Method="IArchivable">\n'
            u'    <List2 Name="Names" />\n    <List2 Name="Types" />\n  </Single>\n'
            u'  <Single Name="BoxType" Type="string">AND</Single>\n'
            u'  <Null Name="STSnippet" />\n'
            u'  <Single Name="IsBoxType" Type="bool">False</Single>\n'
            u'  <Single Name="Id" Type="long">%d</Single>\n'
            u'</Single>' % (G_BOX, flags_block(0), body, G_CALLTYPE, G_OPERAND,
                            flags_block(0), conn_flags_block(), nid(),
                            G_OUTPUTS, G_PARAM, G_PARAM, nid()))


def param_block(name, names, types):
    """InputParam / OutputParam 的 Names/Types 列表。"""
    nb = u"\n".join(u'    <Single Type="string">%s</Single>' % n for n in names)
    tb = u"\n".join(u'    <Single Type="string">%s</Single>' % t for t in types)
    return (u'<Single Name="%s" Type="%s" Method="IArchivable">\n'
            u'  <List2 Name="Names">\n%s\n  </List2>\n'
            u'  <List2 Name="Types">\n%s\n  </List2>\n'
            u'</Single>' % (name, G_PARAM, nb, tb))


def fb_box(box_type, instance, in_items, in_names, in_types,
           out_names, out_types, out_vars=None, en=True, fixed=True):
    """通用功能框（FunctionBlock / Function / Program 类）。

    参数：
      box_type   —— BoxType 字段值（FB/FC/PRG 的名字，如 TON）
      instance   —— 实例名；Function/Program 类传 None（写 <Null Name="Operand"/>）
      in_items   —— 已渲染的 InputItems 子节点列表，长度必须 == len(in_names)
      out_vars   —— 已渲染的 OutputItems 子节点列表（第 0 项由本函数自动补 <Null/>）
      en         —— EN/ENO 字段值。FunctionBlock 常见 True；TON 实测 False
      fixed      —— 框级 Flags.Fixed。**默认 True**，见下方铁律。

    ⚠ 铁律（2026-11-25 用户截图纠正）：框级 `Flags.Fixed` 决定引脚是否「可扩展」。
      写 False 时 IDE 会在框上多画一个**空的引脚占位小方块**（用户看到的多余方块），
      真实调用框不会这样。全量样本统计（ipc/*.native 全扫）：
        Action        → Fixed=True   （act0_Ptp / act00_FirstCycle ... 无一例外）
        Function      → Fixed=True   （EventRecordV2 / PackMLSCCmdSum ...）
        FunctionBlock → Fixed=True   （HC_ValveCtrl / HC_MovePtpV / EventManager ...）
        Program       → Fixed=True   （prg_EM00_Logic / prg_UN00 ...）
        MOVE          → Fixed=True
        AND           → Fixed=False  （唯一固定为 False 的常规框）
        TON           → Fixed=False
        EXECUTE       → 两种都出现过，均合法
      所以除 AND/TON 外一律传 fixed=True；漏写就变成 False（旧默认），会出现多余小方块。
    """
    body = u"\n".join(in_items)
    # Instance
    if instance is None:
        inst_operand = u'<Null Name="Operand" />'
        inst_type = u''
    else:
        inst_operand = u'<Single Name="Operand" Type="string">%s</Single>' % instance
        inst_type = box_type
    # OutputItems：必须与 OutputParam 逐项一一对应（项数 == 参数数）。
    # 未接线的引脚写 <Null/>；已接线的写 out_operand(变量, 类型)。
    # ⚠ 不要把「第 0 项恒为 <Null/>」当死规矩：
    #   只有 OutputParam 第一项是 ENO 时才成立（Function/Program/常规 FB）。
    #   TON 的 OutputParam 是 ['Q','ET']，不含 ENO，所以它两个输出项都不是 <Null/> 语义位。
    out_vars = out_vars or []
    if len(out_vars) != len(out_names):
        raise ValueError(
            u"%s: OutputItems 项数(%d) 必须等于 OutputParam 个数(%d) [%s]"
            % (box_type, len(out_vars), len(out_names), u",".join(out_names)))
    outs = list(out_vars)
    out_body = u"\n".join(outs) if outs else u""
    en_v = u"True" if en else u"False"

    return (u'<Single Type="%s" Method="IArchivable">\n'
            u'  <Single Name="ContainsExtensibleInputs" Type="bool">False</Single>\n'
            u'  <Single Name="EN" Type="bool">%s</Single>\n'
            u'  <Single Name="ENO" Type="bool">%s</Single>\n'
            u'  <Single Name="ProvidesSTSnippet" Type="bool">False</Single>\n'
            u'  %s\n'
            u'  <Null Name="InputFlags" />\n'
            u'  <List2 Name="InputItems">\n%s\n  </List2>\n'
            u'  <Single Name="CallType" Type="%s">FunctionBlock</Single>\n'
            u'  <Single Name="Instance" Type="%s" Method="IArchivable">\n'
            u'    <Single Name="Boolean" Type="bool">False</Single>\n'
            u'    <Single Name="IsInstance" Type="bool">True</Single>\n'
            u'    <Single Name="LValue" Type="bool">False</Single>\n'
            u'    %s\n'
            u'    <Single Name="Address" Type="string"></Single>\n'
            u'    <Single Name="Comment" Type="string"></Single>\n'
            u'    %s\n'
            u'    <Single Name="SymbolComment" Type="string"></Single>\n'
            u'    <Single Name="Type" Type="string">%s</Single>\n'
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
            u'  <Single Name="IsBoxType" Type="bool">True</Single>\n'
            u'  <Single Name="Id" Type="long">%d</Single>\n'
            u'</Single>' % (G_BOX, en_v, en_v, flags_block(0, fixed), body,
                            G_CALLTYPE, G_OPERAND, flags_block(0),
                            inst_operand, inst_type, conn_flags_block(), nid(),
                            G_OUTPUTS, out_body,
                            param_block(u"InputParam", in_names, in_types),
                            param_block(u"OutputParam", out_names, out_types),
                            box_type, nid()))


def xml_text(s):
    """把文本转义成可安全放进 XML 文本节点的形式。

    ⚠ 血泪教训（2026-11-25）：网络注释里写 `<Null/>` 这种字面量，
    如果直接拼进 XML，会被解析成**真实的子节点**，导致
    「网络 Comment 下多一个 Null 节点」，往返 diff 节点数不等（363 vs 362）。
    凡是往 XML 文本节点里塞的自由文本（注释/声明/ST 代码）都必须过这里。
    """
    return (s.replace(u"&", u"&")
             .replace(u"<", u"<")
             .replace(u">", u">"))


def textlines_block(lines, start_id):
    """TextLines 数组（声明区 / 内嵌 ST 共用）。"""
    out = [u'<Array Name="TextLines" Type="%s">' % G_TEXTLINE]
    tid = start_id
    for d in lines:
        out.append(
            u'  <Single Type="%s" Method="IArchivable">\n'
            u'    <Single Name="Id" Type="long">%d</Single>\n'
            u'    <Null Name="Tag" />\n'
            u'    <Single Name="Text" Type="string">%s</Single>\n'
            u'  </Single>' % (G_TEXTLINE, tid, xml_text(d)))
        tid += 1
    out.append(u'</Array>')
    return u"\n".join(out), tid


def execute_box(st_lines, width=496, height=200):
    """EXECUTE 框：LD 内嵌 ST 代码块。

    要点：
      - CallType = None（不是 And/Function/FunctionBlock）
      - EN/ENO = True，ProvidesSTSnippet = True
      - InputItems 只有 1 个连接器槽；OutputItems 只有 1 个 <Null/>
      - 代码在 STSnippet -> STSnippet -> TextDocument -> TextLines
    """
    body, next_id = textlines_block(st_lines, nid())
    stsnip = (u'<Single Name="STSnippet" Type="%s" Method="IArchivable">\n'
              u'  <Single Name="STSnippet" Type="%s" Method="IArchivable">\n'
              u'    <Single Name="TextDocument" Type="%s" Method="IArchivable">\n'
              u'      %s\n'
              u'    </Single>\n'
              u'  </Single>\n'
              u'  <Single Name="STSnippetWidth" Type="int">%d</Single>\n'
              u'  <Single Name="STSnippetHeight" Type="int">%d</Single>\n'
              u'  <Single Name="Id" Type="long">%d</Single>\n'
              u'</Single>' % (G_STSNIP, G_STSNIP2, G_TEXTDOC, body,
                              width, height, next_id))
    _id[0] = next_id

    return (u'<Single Type="%s" Method="IArchivable">\n'
            u'  <Single Name="ContainsExtensibleInputs" Type="bool">False</Single>\n'
            u'  <Single Name="EN" Type="bool">True</Single>\n'
            u'  <Single Name="ENO" Type="bool">True</Single>\n'
            u'  <Single Name="ProvidesSTSnippet" Type="bool">True</Single>\n'
            u'  %s\n'
            u'  <Null Name="InputFlags" />\n'
            u'  <List2 Name="InputItems">\n%s\n  </List2>\n'
            u'  <Single Name="CallType" Type="%s">None</Single>\n'
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
            u'  <Single Name="BoxType" Type="string">EXECUTE</Single>\n'
            u'  %s\n'
            u'  <Single Name="IsBoxType" Type="bool">True</Single>\n'
            u'  <Single Name="Id" Type="long">%d</Single>\n'
            u'</Single>' % (G_BOX, flags_block(0), connector_slot(),
                            G_CALLTYPE, G_OPERAND, flags_block(0),
                            conn_flags_block(), nid(), G_OUTPUTS,
                            param_block(u"InputParam", [u"EN"], [u"BOOL"]),
                            param_block(u"OutputParam", [u"ENO"], [u"BOOL"]),
                            stsnip, nid()))


def ton_box(instance, in_slot, pt_var):
    """TON 定时器框（CallType=FunctionBlock，EN=False/ENO=False）。

    in_slot 决定「电源流」来源：
      - 顶层（RValue 直接是 TON）→ 传 connector_slot()
      - 嵌在 AND 的 InputItems 里   → 传 contact(条件变量)
    """
    return fb_box(
        box_type=u"TON", instance=instance,
        in_items=[in_slot, value_pin(pt_var, u"TIME")],
        in_names=[u"IN", u"PT"], in_types=[u"BOOL", u"TIME"],
        out_names=[u"Q", u"ET"], out_types=[u"BOOL", u"TIME"],
        # ⚠ TON 的 OutputParam 是 ['Q','ET']，**没有 ENO**，所以不能套「第 0 项恒为 Null」。
        # 两个输出都未接线 → 两项都是 <Null/>（InoPack HC_ValveCtrl 实测 7/7 如此）。
        out_vars=[u'   <Null/>', u'   <Null/>'],
        en=False,
        # ⚠ TON 是仅有的两个 Fixed=False 的框之一（另一个是 AND），别改成 True
        fixed=False)


def netitem_box_rvalue(box_node, coils, inverted=False):
    """NETITEM 的 RValue 直接就是一个功能框（act05 的 TON 顶层写法）。

    注意：RValue 的 Type 是 {acfc6f68 功能框}，不是 {5f9848d3} 容器。
    """
    coil_body = u"\n".join(coils)
    rv = box_node.replace(u'<Single Type="', u'<Single Name="RValue" Type="', 1)
    return (u'<Single Type="%s" Method="IArchivable">\n'
            u'  %s\n'
            u'  %s\n'
            u'  <Single Name="OutputItems" Type="%s" Method="IArchivable">\n'
            u'    <List2 Name="OutputItems">\n%s\n    </List2>\n'
            u'  </Single>\n'
            u'  <Single Name="Id" Type="long">%d</Single>\n'
            u'</Single>' % (G_NETITEM, flags_block(1 if inverted else 0), rv,
                            G_OUTPUTS, coil_body, nid()))


def network(items, comment):
    body = u"\n".join(items)
    return (u'<Single Type="%s" Method="IArchivable">\n'
            u'  <Single Name="FBDValid" Type="bool">False</Single>\n'
            u'  <Single Name="ILActive" Type="bool">False</Single>\n'
            u'  <Single Name="ILValid" Type="bool">False</Single>\n'
            u'  <Single Name="OutCommented" Type="bool">False</Single>\n'
            u'  <List2 Name="Connectors" />\n'
            u'  <List2 Name="ILLines" />\n'
            u'  <List2 Name="NetworkItems">\n%s\n  </List2>\n'
            u'  <Single Name="Comment" Type="string">%s</Single>\n'
            u'  <Single Name="Label" Type="string"></Single>\n'
            u'  <Single Name="Title" Type="string"></Single>\n'
            u'  <Single Name="Collapsed" Type="bool">False</Single>\n'
            u'  <Single Name="Id" Type="long">%d</Single>\n'
            u'</Single>' % (G_NETWORK, body, xml_text(comment), nid()))


# ===================== 网络构建 =====================

def build_networks():
    """三个网络：TON 顶层 / TON 嵌 AND / EXECUTE 内嵌 ST。"""
    nets = []

    # 网络1：TON 顶层 —— NETITEM.RValue 直接是 TON 框
    n1_ton = ton_box(u"fbDelay", connector_slot(), u"T#2S")
    nets.append(network(
        [netitem_box_rvalue(n1_ton, [coil(u"xTimerDone")])],
        u"// 网络1：TON 顶层写法 —— RValue 直接是 TON 框，Q 未接线，用 ET 在 ST 块里读"))

    # 网络2：TON 嵌在 AND 里 —— InputItems[0] 变成条件触点
    n2_and = and_box([
        contact(u"xTimerIn"),
        ton_box(u"fbEdge", contact(u"xTimerIn"), u"T#500MS"),
    ])
    nets.append(network(
        [netitem_box_rvalue(n2_and, [coil(u"xTimerPulse")])],
        u"// 网络2：TON 嵌套写法 —— AND 的第 1 槽是 TON 框，TON 自己的槽0 是条件触点"))

    # 网络3：EXECUTE 内嵌 ST —— 直接挂 NetworkItems，不套 NETITEM
    st = [
        u"// EXECUTE 框：LD 里内嵌 ST 代码块",
        u"IF xTimerDone THEN",
        u"    iTimerCount := iTimerCount + 1;",
        u"END_IF",
        u"",
        u"xTimerStOut := xTimerDone AND xTimerIn;",
    ]
    nets.append(network([execute_box(st, 496, 200)],
                        u"// 网络3：EXECUTE 内嵌 ST 代码块"))

    return nets


DECL_PRG = [
    u"",
    u"PROGRAM prg_LdLearnTest",
    u"VAR",
    u"    (* ~~~~ 定时器框测试 ~~~~~~~~~~~~~~ *)",
    u"    xTimerIn    : BOOL;   // 定时器输入条件",
    u"    xTimerDone  : BOOL;   // TON.Q 输出（网络1）",
    u"    xTimerPulse : BOOL;   // 网络2 输出",
    u"    fbDelay     : TON;    // 网络1 实例",
    u"    fbEdge      : TON;    // 网络2 实例",
    u"    (* ~~~~ EXECUTE 内嵌 ST 用变量 ~~~~~~~~~~~~~~ *)",
    u"    iTimerCount : INT;    // ST 里累加",
    u"    xTimerStOut : BOOL;   // ST 里赋值",
    u"END_VAR",
]

DECL_FB = [
    u"",
    u"FUNCTION_BLOCK fb_LdLearnTest",
    u"VAR_INPUT",
    u"    xTimerIn    : BOOL;   // 定时器输入条件",
    u"END_VAR",
    u"VAR_OUTPUT",
    u"    xTimerDone  : BOOL;   // TON.Q 输出（网络1）",
    u"    xTimerPulse : BOOL;   // 网络2 输出",
    u"    iTimerCount : INT;    // ST 里累加",
    u"    xTimerStOut : BOOL;   // ST 里赋值",
    u"END_VAR",
    u"VAR",
    u"    fbDelay     : TON;    // 网络1 实例",
    u"    fbEdge      : TON;    // 网络2 实例",
    u"END_VAR",
]


def find_block_end(s, start, open_tag, close_tag):
    """从 start 找配对 close_tag 之后的位置（跳过自闭合标签）。"""
    depth = 0
    i = start
    while i < len(s):
        no = s.find(open_tag, i)
        nc = s.find(close_tag, i)
        if nc < 0:
            return -1
        if no >= 0 and no < nc:
            gt = s.find(u">", no)
            if gt > 0 and s[gt - 1] == u"/":
                i = gt + 1
                continue
            depth += 1
            i = no + len(open_tag)
        else:
            depth -= 1
            i = nc + len(close_tag)
            if depth == 0:
                return i
    return -1


G_ENTRY = u"{6198ad31-4b98-445c-927f-3258a0e82fe3}"
G_METAOBJ = u"{81297157-7ec9-45ce-845e-84cab2b88ade}"
G_TYPE_ACTION = u"{8ac092e5-3128-4e26-9e7e-11016c6684f2}"
G_IMPL_ST = u"{3b83b776-fb25-43b8-99f2-3c507c9143fc}"


def action_entry(action_name, parent_guid, st_lines, path=None):
    """action Entry（IsRoot=False、TypeGuid=8ac092e5、没有 Interface）。

    ⚠ 铁律（2026-11-25 实测）：LD 里画一个 `CallType=Action` 的调用框，
    要求这个 action **在本 POU 的 EntryList 里真实存在**（TypeGuid=8ac092e5
    的 Entry）。只在网络里写 `BoxType=actAbs` 而不建 Entry，
    预编译会报 `没有定义标识符'actAbs'`——而且**只有全量「重新编译」才会报**，
    增量「检查程序」一条消息都没有，极易漏检。

    ⚠ 另一个坑（同一轮踩到）：`Object` 的 Type 属性必须带花括号
    `{8ac092e5-...}`。少花括号时 XML 仍然合法，但 IDE **静默丢弃整个 Entry**，
    import_native 返回 no_changes，不报任何错——只能靠对比真实模板发现。

    这里用 ST 实现（Implementation=3b83b776 -> TextDocument -> TextLines），
    比 LD 实现（25e509de -> NetworkList）简单，且同样合法。
    """
    body, next_id = textlines_block(st_lines, nid())
    path = path or [u"Device", u"PLC 逻辑", u"Application"]
    path_xml = u"\n".join(
        u'    <Single Type="string">%s</Single>' % xml_text(p) for p in path)
    return (u'<Single Type="%s" Method="IArchivable">\n'
            u'  <Single Name="IsRoot" Type="bool">False</Single>\n'
            u'  <Single Name="MetaObject" Type="%s" Method="IArchivable">\n'
            u'    <Single Name="Guid" Type="System.Guid">%s</Single>\n'
            u'    <Single Name="ParentGuid" Type="System.Guid">%s</Single>\n'
            u'    <Single Name="Name" Type="string">%s</Single>\n'
            u'    <Dictionary Type="{2c41fa04-1834-41c1-816e-303c7aa2c05b}" Name="Properties" />\n'
            u'    <Single Name="TypeGuid" Type="System.Guid">8ac092e5-3128-4e26-9e7e-11016c6684f2</Single>\n'
            u'    <Array Name="EmbeddedTypeGuids" Type="System.Guid">\n'
            u'      <Single Type="System.Guid">3b83b776-fb25-43b8-99f2-3c507c9143fc</Single>\n'
            u'    </Array>\n'
            u'    <Single Name="Timestamp" Type="long">638040560739002288</Single>\n'
            u'  </Single>\n'
            u'  <Single Name="Object" Type="%s" Method="IArchivable">\n'
            u'    <Single Name="Implementation" Type="%s" Method="IArchivable">\n'
            u'      <Single Name="TextDocument" Type="%s" Method="IArchivable">\n'
            u'        %s\n'
            u'      </Single>\n'
            u'    </Single>\n'
            u'    <Single Name="UniqueIdGenerator" Type="string">%d</Single>\n'
            u'  </Single>\n'
            u'  <Single Name="ParentSVNodeGuid" Type="System.Guid">%s</Single>\n'
            u'  <Array Name="Path" Type="string">\n%s\n  </Array>\n'
            u'  <Single Name="Index" Type="int">-1</Single>\n'
            u'</Single>' % (G_ENTRY, G_METAOBJ, str(uuid.uuid4()), parent_guid,
                             action_name, G_TYPE_ACTION, G_IMPL_ST, G_TEXTDOC,
                             body, next_id + 1, parent_guid, path_xml))



def build_pou(pou_name, decl, nets, out_path, actions=None):
    """把骨架改成指定 POU：换名、换 Guid、换网络、换声明区。

    actions: [(action_name, [st_lines]), ...]
      附加的 action Entry。网络里若有 CallType=Action 的调用框，
      这里必须给出同名 action，否则预编译报「没有定义标识符」。
    """
    raw = io.open(SKELETON, "r", encoding="utf-8").read()

    # 0) 先把根 Guid 换掉，后面 action 的 ParentGuid 要用它
    new_guid = str(uuid.uuid4())
    raw = raw.replace(
        u'<Single Name="Guid" Type="System.Guid">aa4f05c0-d089-4b64-89fe-370f00252313</Single>',
        u'<Single Name="Guid" Type="System.Guid">%s</Single>' % new_guid)

    # 1) 网络
    key = u'<List2 Name="NetworkList">'
    p = raw.find(key)
    assert p >= 0, "skeleton has no NetworkList"
    end = find_block_end(raw, p, u"<List2", u"</List2>")
    assert end > 0
    raw = raw[:p] + key + u"\n" + u"\n".join(nets) + u"\n            </List2>" + raw[end:]

    # 2) 声明区
    # ⚠ 必须锚定 Interface 之后再找 TextLines。
    # 教训（2026-11-25 预编译 48 错误）：替换网络后，文档里第一个
    # `<Array Name="TextLines"` 属于 EXECUTE 框的 STSnippet，不是 POU 声明区。
    # 用裸 find() 会把 POU 声明写进 ST 代码块，真正声明区留着骨架的旧变量，
    # 结果预编译报一堆「符号 'PROGRAM'/'FUNCTION_BLOCK'/'BOOL' 不能识别」。
    key2 = u'<Array Name="TextLines"'
    anchor = raw.find(u'<Single Name="Interface"')
    assert anchor >= 0, "skeleton has no Interface"
    p2 = raw.find(key2, anchor)
    assert p2 >= 0, "skeleton has no declaration TextLines after Interface"
    end2 = find_block_end(raw, p2, u"<Array", u"</Array>")
    assert end2 > 0
    decl_xml, _ = textlines_block(decl, 900)
    raw = raw[:p2] + decl_xml + raw[end2:]

    # 3) 名字 / Guid（根 Guid 已在步骤 0 换过）
    raw = raw.replace(u'>prg_StartStop<', u'>%s<' % pou_name)

    # 3.5) 附加 action Entry（追加到 EntryList 末尾）
    if actions:
        key3 = u'<List2 Name="EntryList">'
        p3 = raw.find(key3)
        assert p3 >= 0, "skeleton has no EntryList"
        end3 = find_block_end(raw, p3, u"<List2", u"</List2>")
        assert end3 > 0
        extra = u"\n".join(
            action_entry(nm, new_guid, lines,
                         path=[u"Device", u"PLC 逻辑", u"Application", pou_name])
            for nm, lines in actions)
        raw = (raw[:end3 - len(u"</List2>")] + u"\n" + extra + u"\n  "
               + raw[end3 - len(u"</List2>"):])

    # 4) UniqueIdGenerator 抬到最大 Id 之上
    raw = re.sub(u'<Single Name="UniqueIdGenerator" Type="string">\\d+</Single>',
                 u'<Single Name="UniqueIdGenerator" Type="string">%d</Single>' % (_id[0] + 500),
                 raw)

    io.open(out_path, "w", encoding="utf-8").write(raw)
    print(u"generated: %s (%d bytes)  networks=%d  max_id=%d"
          % (out_path, os.path.getsize(out_path), raw.count(G_NETWORK), _id[0]))
    return out_path


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    _id[0] = 3000
    build_pou(u"prg_LdLearnTest", DECL_PRG, build_networks(),
              os.path.join(OUT_DIR, "prg_LdLearnTest.native"))

    _id[0] = 5000
    build_pou(u"fb_LdLearnTest", DECL_FB, build_networks(),
              os.path.join(OUT_DIR, "fb_LdLearnTest.native"))


# 加 __main__ 守卫：其它生成器（如 make_axis_call.py）要 import 本模块的
# fb_box / contact / value_pin 等辅助函数，import 时不能顺带执行生成。
if __name__ == u"__main__":
    main()
