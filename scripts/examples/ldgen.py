# -*- coding: utf-8 -*-
# @py3
"""ldgen —— InoProShop LD（梯形图）原生 XML 生成库（从 A00 实测结构抽出）。

用途：以「骨架 POU 导出文件」为文档外壳，替换声明区与 NetworkList，从零生成一个
可被 InoProShop 静默导入的 .native。

骨架要求：任意一个已存在的 Application 直属 POU 的 export_native 结果
（本库会替换：对象名 1 处、第一个 Guid、TextLines、NetworkList 全部内容）。

本文件由 D:\\plc_mcp\\work\\gen_stn_edge.py 抽取（构造层与模板 helper 均照 A00 实测），
2026-11-27 补 check_skeleton() 与框 EN 边沿（InputFlags[0]=16）支持。
"""
import collections
import io
import os
import re
import uuid


# ═══════════════════════ 节点构造层（照 A00 实测） ═══════════════════════

G_BOX = u"{acfc6f68-8e3a-4af5-bf81-3dd512095a46}"
G_PIN = u"{9de7f100-1b87-424c-a62e-45b0cfc85ed2}"
G_OPERAND = u"{c9b2f165-48a2-4a45-8326-3952d8a3d708}"
G_CONNECTOR = u"{5f9848d3-568d-4cc5-9e31-8e28e9607ff1}"
G_OUTCONN = u"{505bff94-4c90-4e17-ac28-b8ac69d1b9e2}"
G_BRANCH = u"{827b9ec2-2032-40da-9f4e-7670ca2d55a8}"
G_NETITEM = u"{9873c309-1f09-4ebf-9078-42d8057ef11b}"
G_OUTPUTS = u"{f40d3e09-c02c-4522-a88c-dac23558cfc4}"
G_NETWORK = u"{d9a99d73-b633-47db-b876-a752acb25871}"
G_CALLTYPE = u"{bffb3c53-f105-4e85-aba2-e30df579d75f}"
G_FLAGS = u"{668066f2-6069-46b3-8962-8db8d13d7db2}"
G_PARAMS = u"{71496971-9e0c-4677-a832-b9583b571130}"
G_MODE = u"{3b9474d0-c98b-4935-8ce5-65f06808350d}"
G_TEXTLINE = u"{a5de0b0b-1cb5-4913-ac21-9d70293ec00d}"

_id = [30000]


def nid():
    _id[0] += 1
    return _id[0]


def esc(s):
    return s.replace(u"&", u"&amp;").replace(u"<", u"&lt;").replace(u">", u"&gt;")


def flags_block(fixed=False, val=0):
    return (u'<Single Name="Flags" Type="%s" Method="IArchivable">\n'
            u'  <Single Name="Extensible" Type="bool">False</Single>\n'
            u'  <Single Name="Fixed" Type="bool">%s</Single>\n'
            u'  <Single Name="Flags" Type="int">%d</Single>\n'
            u'</Single>' % (G_FLAGS, u"True" if fixed else u"False", val))


def conn_flags_block():
    return (u'<Single Name="ConnectorFlags" Type="%s" Method="IArchivable">\n'
            u'  <Single Name="Extensible" Type="bool">False</Single>\n'
            u'  <Single Name="Fixed" Type="bool">False</Single>\n'
            u'  <Single Name="Flags" Type="int">0</Single>\n'
            u'</Single>' % G_FLAGS)


def input_flags_block(n_pins, edge=False):
    """框的 InputFlags：每个输入引脚一项；第 0 项（EN）Flags=16 = 该引脚带边沿检测。

    2026-11-27 用户手工示范（IDE 原生形态）：MOVE(EN+IN) → ('16','0')。
    不加边沿时写 <Null Name="InputFlags" />（我此前所有框都是这个，导致每周期都执行）。
    """
    if not edge:
        return u'<Null Name="InputFlags" />'
    items = []
    for i in range(n_pins):
        items.append(
            u'    <Single Type="{668066f2-6069-46b3-8962-8db8d13d7db2}" Method="IArchivable">\n'
            u'      <Single Name="Extensible" Type="bool">False</Single>\n'
            u'      <Single Name="Fixed" Type="bool">%s</Single>\n'
            u'      <Single Name="Flags" Type="int">%d</Single>\n'
            u'    </Single>' % (u"True" if i == 0 else u"False", 16 if i == 0 else 0))
    return (u'<List2 Name="InputFlags">\n' + u"\n".join(items) + u'\n  </List2>')


def operand_container(var, typ, boolean, lvalue, oflags=0, is_instance=False,
                      is_coil=False, name=u"Operand"):
    """OPERAND 容器。name=None → 不带 Name 属性的裸 OPERAND（输出引脚）。"""
    nm = u' Name="%s"' % name if name else u''
    return (u'<Single%s Type="%s" Method="IArchivable">\n'
            u'  <Single Name="Boolean" Type="bool">%s</Single>\n'
            u'  <Single Name="IsInstance" Type="bool">%s</Single>\n'
            u'  <Single Name="LValue" Type="bool">%s</Single>\n'
            u'  %s\n'
            u'  <Single Name="Address" Type="string" />\n'
            u'  <Single Name="Comment" Type="string" />\n'
            u'  <Single Name="Operand" Type="string">%s</Single>\n'
            u'  <Single Name="SymbolComment" Type="string" />\n'
            u'  <Single Name="Type" Type="string">%s</Single>\n'
            u'  <Single Name="IsCoil" Type="bool">%s</Single>\n'
            u'  <Single Name="IsSeriesCoil" Type="bool">False</Single>\n'
            u'  <Single Name="SeriesIndex" Type="int">-1</Single>\n'
            u'  %s\n'
            u'  <Single Name="Id" Type="long">%d</Single>\n'
            u'</Single>' % (nm, G_OPERAND,
                            u"True" if boolean else u"False",
                            u"True" if is_instance else u"False",
                            u"True" if lvalue else u"False",
                            flags_block(True, oflags),
                            esc(var), typ,
                            u"True" if is_coil else u"False",
                            conn_flags_block(), nid()))


def contact(var, typ=u"BOOL", neg=False, edge=False):
    """触点。neg=True → 常闭（Flags=1）。

    注意：触点 Flags=2 **不是**边沿。2026-11-27 实测：IDE 会把这个值原样保留、
    编译 0 错误、导出往返不变 —— 但语义上不产生边沿，属于「编译器不校验即假通过」。
    真正的边沿在**框的 EN 引脚**：InputFlags[0].Flags=16，
    用 move_box(..., en_edge=True) / add_box(..., en_edge=True) / jump_tree(..., en_edge=True)。
    """
    if edge:
        raise RuntimeError("contact(edge=True) 是错误做法：边沿要写在框的 EN 引脚（en_edge=True）")
    of = 1 if neg else 0
    return (u'<Single Type="%s" Method="IArchivable">\n'
            u'  %s\n'
            u'  <Single Name="IsContact" Type="bool">True</Single>\n'
            u'  <Single Name="Id" Type="long">%d</Single>\n'
            u'</Single>' % (G_PIN,
                            operand_container(var, typ, True, False, of), nid()))


def value_pin(var, typ=u"INT"):
    """值引脚（非触点）：常量或变量读数。
    BOOL 类型的操作数 Boolean=True（A00 实测：TRUE/FALSE 与布尔变量都是 True）。"""
    boolean = (typ == u"BOOL")
    return (u'<Single Type="%s" Method="IArchivable">\n'
            u'  %s\n'
            u'  <Single Name="IsContact" Type="bool">False</Single>\n'
            u'  <Single Name="Id" Type="long">%d</Single>\n'
            u'</Single>' % (G_PIN,
                            operand_container(var, typ, boolean, False), nid()))


def desc_pin(text):
    """描述字面量引脚：Operand 带双引号，Type=WSTRING(INT#字符数)（A00 实测）。"""
    return value_pin(u'"%s"' % text, u"WSTRING(INT#%d)" % len(text))


def out_pin(var, typ):
    """输出引脚（LValue=True，不带 Name 属性）。"""
    return operand_container(var, typ, False, True, name=None)


def connector():
    return (u'<Single Type="%s" Method="IArchivable">\n'
            u'  %s\n'
            u'  <Null Name="Input" />\n'
            u'  <Single Name="Id" Type="long">%d</Single>\n'
            u'</Single>' % (G_CONNECTOR, flags_block(False), nid()))


def coil(var, typ=u"BOOL"):
    """线圈操作数（挂在框的 OutputItems 里，不带 Name 属性）。"""
    return operand_container(var, typ, True, True, 0, is_coil=True, name=None)


def coil_net(cond_items, var, typ=u"BOOL", title=None):
    """条件 → 线圈赋值网络：链条元素放 InputItems，线圈放 OutputItems。
    （A00 实测形态：BRANCH/BOX 自带 OutputItems，线圈是 LValue+IsCoil=True 的 Operand）"""
    return network([and_box(list(cond_items), outputs=[coil(var, typ)])], title)


def outconn():
    return (u'<Single Type="%s" Method="IArchivable">\n'
            u'  <Single Name="Id" Type="long">%d</Single>\n'
            u'</Single>' % (G_OUTCONN, nid()))


def param_block(name, names, types):
    n = u"\n".join(u'    <Single Type="string">%s</Single>' % x for x in names)
    t = u"\n".join(u'    <Single Type="string">%s</Single>' % x for x in types)
    return (u'<Single Name="%s" Type="%s" Method="IArchivable">\n'
            u'  <List2 Name="Names">\n%s\n  </List2>\n'
            u'  <List2 Name="Types">\n%s\n  </List2>\n'
            u'</Single>' % (name, G_PARAMS, n, t))


def _en_str(tag, val):
    if val is None:
        return u'<Null Name="%s" />' % tag
    return u'<Single Name="%s" Type="bool">%s</Single>' % (
        tag, u"True" if val else u"False")


def _instance_null():
    """算子框（MOVE/EQ/ADD/AND）的 Instance：IsInstance=True，Operand 为 Null。"""
    return (u'<Single Name="Instance" Type="%s" Method="IArchivable">\n'
            u'  <Single Name="Boolean" Type="bool">False</Single>\n'
            u'  <Single Name="IsInstance" Type="bool">True</Single>\n'
            u'  <Single Name="LValue" Type="bool">False</Single>\n'
            u'  %s\n'
            u'  <Single Name="Address" Type="string" />\n'
            u'  <Single Name="Comment" Type="string" />\n'
            u'  <Null Name="Operand" />\n'
            u'  <Single Name="SymbolComment" Type="string" />\n'
            u'  <Single Name="Type" Type="string" />\n'
            u'  <Single Name="IsCoil" Type="bool">False</Single>\n'
            u'  <Single Name="IsSeriesCoil" Type="bool">False</Single>\n'
            u'  <Single Name="SeriesIndex" Type="int">-1</Single>\n'
            u'  %s\n'
            u'  <Single Name="Id" Type="long">%d</Single>\n'
            u'</Single>' % (G_OPERAND, flags_block(False),
                            conn_flags_block(), nid()))


def _outputs(items):
    body = u"\n".join(items) if items else u""
    return (u'<Single Name="OutputItems" Type="%s" Method="IArchivable">\n'
            u'  <List2 Name="OutputItems">\n%s\n  </List2>\n'
            u'</Single>' % (G_OUTPUTS, body))


def and_box(items, en=None, eno=None, fixed=False, outputs=None):
    body = u"\n".join(items)
    return (u'<Single Type="%s" Method="IArchivable">\n'
            u'  <Single Name="ContainsExtensibleInputs" Type="bool">False</Single>\n'
            u'  %s\n'
            u'  %s\n'
            u'  <Single Name="ProvidesSTSnippet" Type="bool">False</Single>\n'
            u'  %s\n'
            u'  <Null Name="InputFlags" />\n'
            u'  <List2 Name="InputItems">\n%s\n  </List2>\n'
            u'  <Single Name="CallType" Type="%s">And</Single>\n'
            u'  %s\n'
            u'  %s\n'
            u'  %s\n'
            u'  %s\n'
            u'  <Single Name="BoxType" Type="string">AND</Single>\n'
            u'  <Null Name="STSnippet" />\n'
            u'  <Single Name="IsBoxType" Type="bool">False</Single>\n'
            u'  <Single Name="Id" Type="long">%d</Single>\n'
            u'</Single>' % (G_BOX, _en_str(u"EN", en), _en_str(u"ENO", eno),
                            flags_block(fixed), body, G_CALLTYPE,
                            _instance_null(), _outputs(outputs or []),
                            param_block(u"InputParam", [], []),
                            param_block(u"OutputParam", [], []), nid()))


def eq_box(in1, in2, en_item=None):
    """比较框。默认 3 槽 [CONNECTOR(EN), 操作数1, 操作数2]（A00 4 处）；
    步门控形态传 en_item=xAutoing 触点 → [触点, aiAutoStep, 常量N]
    （A00 64 处：EN 槽就是触点本体，不是 CONNECTOR）。
    EN=True / ENO=False / InputParam=[EN] / OutputParam=[""]（A00 实测）。"""
    body = u"\n".join([en_item if en_item is not None else connector(), in1, in2])
    return (u'<Single Type="%s" Method="IArchivable">\n'
            u'  <Single Name="ContainsExtensibleInputs" Type="bool">False</Single>\n'
            u'  <Single Name="EN" Type="bool">True</Single>\n'
            u'  <Single Name="ENO" Type="bool">False</Single>\n'
            u'  <Single Name="ProvidesSTSnippet" Type="bool">False</Single>\n'
            u'  %s\n'
            u'  <Null Name="InputFlags" />\n'
            u'  <List2 Name="InputItems">\n%s\n  </List2>\n'
            u'  <Single Name="CallType" Type="%s">Eq</Single>\n'
            u'  %s\n'
            u'  %s\n'
            u'  %s\n'
            u'  %s\n'
            u'  <Single Name="BoxType" Type="string">EQ</Single>\n'
            u'  <Null Name="STSnippet" />\n'
            u'  <Single Name="IsBoxType" Type="bool">True</Single>\n'
            u'  <Single Name="Id" Type="long">%d</Single>\n'
            u'</Single>' % (G_BOX, flags_block(True), body, G_CALLTYPE,
                            _instance_null(), _outputs([u'      <Null />']),
                            param_block(u"InputParam", [u"EN"], [u"BOOL"]),
                            param_block(u"OutputParam", [u""], [u"BOOL"]), nid()))


def move_box(src_item, dst, typ, en_item=None, en_edge=False):
    """赋值框：EN 槽默认 CONNECTOR（A00 105/150），可传完成触点；IN 槽 = 源值。
    EN=True / ENO=True / InputParam=[EN] / OutputParam=[ENO, 空]（A00 实测）。"""
    body = u"\n".join([en_item if en_item is not None else connector(), src_item])
    return (u'<Single Type="%s" Method="IArchivable">\n'
            u'  <Single Name="ContainsExtensibleInputs" Type="bool">False</Single>\n'
            u'  <Single Name="EN" Type="bool">True</Single>\n'
            u'  <Single Name="ENO" Type="bool">True</Single>\n'
            u'  <Single Name="ProvidesSTSnippet" Type="bool">False</Single>\n'
            u'  %s\n'
            u'  %s\n'
            u'  <List2 Name="InputItems">\n%s\n  </List2>\n'
            u'  <Single Name="CallType" Type="%s">Move</Single>\n'
            u'  %s\n'
            u'  %s\n'
            u'  %s\n'
            u'  %s\n'
            u'  <Single Name="BoxType" Type="string">MOVE</Single>\n'
            u'  <Null Name="STSnippet" />\n'
            u'  <Single Name="IsBoxType" Type="bool">True</Single>\n'
            u'  <Single Name="Id" Type="long">%d</Single>\n'
            u'</Single>' % (G_BOX, flags_block(True),
                            input_flags_block(2, en_edge), body, G_CALLTYPE,
                            _instance_null(),
                            _outputs([u'      <Null />',
                                      u'      ' + out_pin(dst, typ)]),
                            param_block(u"InputParam", [u"EN"], [u"BOOL"]),
                            param_block(u"OutputParam", [u"ENO", u""],
                                        [u"BOOL", typ]), nid()))


def add_box(in1, in2, dst, typ=u"INT", en_item=None, en_edge=False):
    """加法框：EN 槽默认 CONNECTOR，InputParam 只有 EN（A00 Network25 实测）。"""
    body = u"\n".join([en_item if en_item is not None else connector(), in1, in2])
    return (u'<Single Type="%s" Method="IArchivable">\n'
            u'  <Single Name="ContainsExtensibleInputs" Type="bool">False</Single>\n'
            u'  <Single Name="EN" Type="bool">True</Single>\n'
            u'  <Single Name="ENO" Type="bool">True</Single>\n'
            u'  <Single Name="ProvidesSTSnippet" Type="bool">False</Single>\n'
            u'  %s\n'
            u'  %s\n'
            u'  <List2 Name="InputItems">\n%s\n  </List2>\n'
            u'  <Single Name="CallType" Type="%s">Add</Single>\n'
            u'  %s\n'
            u'  %s\n'
            u'  %s\n'
            u'  %s\n'
            u'  <Single Name="BoxType" Type="string">ADD</Single>\n'
            u'  <Null Name="STSnippet" />\n'
            u'  <Single Name="IsBoxType" Type="bool">True</Single>\n'
            u'  <Single Name="Id" Type="long">%d</Single>\n'
            u'</Single>' % (G_BOX, flags_block(True),
                            input_flags_block(3, en_edge), body, G_CALLTYPE,
                            _instance_null(),
                            _outputs([u'      <Null />',
                                      u'      ' + out_pin(dst, typ)]),
                            param_block(u"InputParam", [u"EN"], [u"BOOL"]),
                            param_block(u"OutputParam", [u"ENO", u""],
                                        [u"BOOL", typ]), nid()))


BOX_OPEN = u'<Single Type="%s" Method="IArchivable">' % G_BOX


def named_elem(elem_xml, name):
    """给任意元素的根标签加上 Name 属性。

    A00 实测：BRANCH.Input 的值就是那个框/触点元素本体
    （<Single Name="Input" Type="{acfc6f68...}">），不是再套一层容器。
    """
    m = re.match(r'<Single\b([^>]*)>', elem_xml)
    assert m, elem_xml[:80]
    attrs = m.group(1)
    attrs = re.sub(r'\s*Name="[^"]*"', u'', attrs)
    return (u'<Single Name="%s"%s>' % (name, attrs)) + elem_xml[m.end():]


def branch(input_item, trees):
    """分支组：Input=条件元素本体，Trees=各梯级。字段固定 Input/Trees/Mode/Id。
    Trees 至少 2 条（少于 2 条渲染器数组越界，A00 实测同构约束）。"""
    assert len(trees) >= 2, u"BRANCH needs >=2 trees"
    return (u'<Single Type="%s" Method="IArchivable">\n'
            u'  %s\n'
            u'  <List2 Name="Trees">\n%s\n  </List2>\n'
            u'  <Single Name="Mode" Type="%s">Sequential</Single>\n'
            u'  <Single Name="Id" Type="long">%d</Single>\n'
            u'</Single>' % (G_BRANCH, named_elem(input_item, u"Input"),
                            u"\n".join(trees), G_MODE, nid()))


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
            u'  <Single Name="Label" Type="string" />\n'
            u'  <Single Name="Title" Type="string" />\n'
            u'  <Single Name="Collapsed" Type="bool">False</Single>\n'
            u'  <Single Name="Id" Type="long">%d</Single>\n'
            u'</Single>' % (G_NETWORK, body, esc(comment), nid()))


# ───────────────────── 语义构件（A00 控制流程） ─────────────────────
AUTOING = u"xAutoing"
STEP = u"aiAutoStep"
BUF = u"aiAutoStepBuffer"
DESC = u"awstrAutoDescription"


def step_gate(n):
    """步门控 EQ：[xAutoing触点, aiAutoStep, N]（A00 Network4 等标准形）。"""
    return eq_box(value_pin(STEP, u"INT"), value_pin(u"%d" % n, u"INT"),
                  en_item=contact(AUTOING))


def desc_tree(text):
    """描述梯级：MOVE("描述") → awstrAutoDescription（A00 每步第一条 TREE）。"""
    return and_box([move_box(desc_pin(text), DESC, u"WSTRING(49)"),
                    outconn()])


def act_tree(act_box_xml):
    """动作梯级：AND{ 动作框(EN=CONNECTOR), OUTCONN }（A00 中间 TREE）。"""
    return and_box([act_box_xml, outconn()])


def jump_tree(next_n, done_contact=None, unconditional=False, en_edge=False):
    """完成跳步梯级：AND{ MOVE(EN=完成触点|CONNECTOR, IN=下一 步号) → aiAutoStepBuffer,
    OUTCONN }。unconditional=True → EN=CONNECTOR 无条件跳（A00 Net25 跳回100）。"""
    en = connector() if (done_contact is None or unconditional) else done_contact
    return and_box([move_box(value_pin(u"%d" % next_n, u"INT"), BUF, u"INT",
                             en_item=en, en_edge=en_edge), outconn()])


def step_net(n, desc, act_boxes, next_n, done_contact=None, title=None, done_edge=False):
    """A00 一步一网络标准形。

    BRANCH{ Input=门控EQ(step n), Trees=[
        描述MOVE, 动作框×k, 完成MOVE(EN=done, IN=next_n) ] }
    动作框由调用方传入（A00 里是 FC_CylinderExe/FC_AxisAbsGo/MOVE 等指令框）。
    """
    trees = [desc_tree(desc)]
    for a in act_boxes:
        trees.append(act_tree(a))
    trees.append(jump_tree(next_n, done_contact, en_edge=done_edge))
    return network([branch(step_gate(n), trees)], title or desc)


def note_net(text):
    """段间注释网络（A00 Net9/26/75：空 NetworkItems，只有 Comment）。"""
    return network([], text)


def counter_net(step_n, counter, desc, next_n, count_en=None):
    """计数+跳步网络（A00 Network25 同形）：
    BRANCH{ Input=门控EQ(n), Trees=[描述MOVE, ADD 计数, MOVE 跳步] }。
    count_en 非空时串到 ADD 的 EN 槽（2026-11-27：传 bStepSame 常闭触点，
    保证本步停留多周期时只计一次）。"""
    return network([branch(step_gate(step_n), [
        desc_tree(desc),
        act_tree(add_box(value_pin(counter, u"INT"), value_pin(u"1", u"INT"),
                         counter, u"INT", en_item=count_en, en_edge=True)),
        jump_tree(next_n, unconditional=True)])], desc)


def uncond_move_net(src_item, dst, typ, title):
    """无条件赋值网络（A00 Network2 同形）：顶层 AND{ MOVE(EN=CONNECTOR, IN=src) }。"""
    return network([and_box([
        move_box(src_item, dst, typ), outconn()])], title)


def cond_move_net(en_contact, src_item, dst, typ, title):
    """条件赋值网络：MOVE 的 EN 槽直接是触点（A00 完成跳步同形）。"""
    return network([and_box([
        move_box(src_item, dst, typ, en_item=en_contact), outconn()])], title)


def empty_tree():
    """空梯级（母线直通）：分支组 Trees 至少 2 条，用作占位。"""
    return and_box([connector(), outconn()])


def guard_set_net(guard_item, dst, title):
    """门控置位网络：BRANCH{ Input=guard } T1 置 TRUE / T2 空梯级。"""
    return network([branch(guard_item, [
        and_box([move_box(value_pin(u"TRUE", u"BOOL"), dst, u"BOOL"), outconn()]),
        empty_tree()])], title)


def buf_commit_net():
    """步序号缓存提交：aiAutoStep := aiAutoStepBuffer（A00 Network2 核心）。"""
    return network([and_box([
        move_box(value_pin(BUF, u"INT"), STEP, u"INT"), outconn()])],
        u"*步序号缓存提交*")


# ═══════════════════════ 文本与编号 ═══════════════════════

def find_list2_end(s, start):
    depth = 0
    for m in re.finditer(r'<List2\b[^>]*?(/?)>|</List2>', s[start:]):
        if m.group(0) == u'</List2>':
            depth -= 1
            if depth == 0:
                return start + m.end()
        elif m.group(1) == u'/':
            continue
        else:
            depth += 1
    raise RuntimeError("unbalanced List2")


def textlines(lines):
    out = []
    for t in lines:
        out.append(u'  <Single Type="%s" Method="IArchivable">\n'
                   u'    <Single Name="Id" Type="long">%d</Single>\n'
                   u'    <Null Name="Tag" />\n'
                   u'    <Single Name="Text" Type="string">%s</Single>\n'
                   u'  </Single>' % (G_TEXTLINE, nid(), esc(t)))
    return u'<Array Name="TextLines" Type="%s">\n%s\n</Array>' % (
        G_TEXTLINE, u"\n".join(out))


ID_RE = re.compile(r'<Single Name="Id" Type="long">\d+</Single>')


def renumber(text, counter):
    """把 text 里所有节点 Id 按出现顺序重编号，保证全局唯一。"""
    out = []
    pos = 0
    for m in ID_RE.finditer(text):
        counter[0] += 1
        out.append(text[pos:m.start()])
        out.append(u'<Single Name="Id" Type="long">%d</Single>' % counter[0])
        pos = m.end()
    out.append(text[pos:])
    return u"".join(out)


# ─────────────────────── 文档骨架装配 ───────────────────────

def check_skeleton(s):
    """骨架自检：必须是 Application 直属、单一实现、单一声明区的 POU。

    反面教材：raw\194_SF99_其他.native 实为 FB_Honeywell（Path 6 段 + 2 个 Method），
    用它拼出来的文件导入会弹「已标识项中有一项的格式无效」并冻死 MAIN 线程。
    """
    if s.count('<Array Name="TextLines"') != 1:
        raise RuntimeError("skeleton: TextLines arrays = %d (need 1)"
                           % s.count('<Array Name="TextLines"'))
    if s.count('<Single Name="Implementation"') != 1:
        raise RuntimeError("skeleton: Implementation = %d (need 1, no methods/actions)"
                           % s.count('<Single Name="Implementation"'))
    i = s.rfind(u'<Array Name="Path"')
    if i >= 0:
        seg = s[i:s.find(u'</Array>', i)]
        n = seg.count(u'<Single Type="string">')
        if n > 3:
            raise RuntimeError("skeleton: Path segments = %d (need <=3, not under a folder)" % n)


def build_doc(skeleton_text, out_name, decl_lines, nets, out_path):
    """用骨架 + 声明 + 网络列表拼出一个完整 native 文件，校验 Id 唯一后写盘。"""
    s = skeleton_text
    check_skeleton(s)
    m = re.search(r'<Single Name="Name" Type="string">([^<]*)</Single>', s)
    if not m:
        raise RuntimeError("skeleton: object name not found")
    old = m.group(1)
    s = s.replace('<Single Name="Name" Type="string">%s</Single>' % old,
                  '<Single Name="Name" Type="string">%s</Single>' % out_name, 1)
    guid = str(uuid.uuid4())
    s = re.sub(r'<Single Name="Guid" Type="System.Guid">[0-9a-fA-F-]+</Single>',
               '<Single Name="Guid" Type="System.Guid">%s</Single>' % guid, s, count=1)

    base = max(int(x.group(1)) for x in
               re.finditer(r'<Single Name="Id" Type="long">(\d+)</Single>', s))
    counter = [base]

    k = s.find(u'<Array Name="TextLines"')
    if k < 0:
        raise RuntimeError("skeleton: TextLines not found")
    e = s.find(u'</Array>', k) + len(u'</Array>')
    s = s[:k] + renumber(textlines(decl_lines), counter) + s[e:]

    key = u'<List2 Name="NetworkList">'
    i = s.find(key)
    if i < 0:
        raise RuntimeError("skeleton: NetworkList not found (need a non-empty POU)")
    j = find_list2_end(s, i)
    s = s[:i] + key + u"\n" + renumber(u"\n".join(nets), counter) + u"\n  </List2>" + s[j:]

    # 全文重编 Id：骨架自带的 Id 可能与新生成部分冲突（模板导出里存在重复 Id）
    s = renumber(s, [0])
    ids = [int(x.group(1)) for x in
           re.finditer(r'<Single Name="Id" Type="long">(\d+)</Single>', s)]
    dup = dict((kk, v) for kk, v in collections.Counter(ids).items() if v > 1)
    if dup:
        raise RuntimeError(u"duplicate Id: %s" % dup)
    uid = max(ids) + 1
    s = re.sub(r'<Single Name="UniqueIdGenerator" Type="string">\d+</Single>',
               u'<Single Name="UniqueIdGenerator" Type="string">%d</Single>' % uid, s, count=1)

    d = os.path.dirname(out_path)
    if d and not os.path.isdir(d):
        os.makedirs(d)
    f = io.open(out_path, "w", encoding="utf-8", newline="")
    try:
        f.write(s)
    finally:
        f.close()

    cnt = {}
    for bt in (u"AND", u"MOVE", u"EQ", u"ADD", u"GT", u"LT", u"TON"):
        cnt[bt] = len(re.findall(r'<Single Name="BoxType" Type="string">%s</Single>' % bt, s))
    return {
        "path": out_path,
        "bytes": len(s.encode("utf-8")),
        "networks": len(nets),
        "ids": len(set(ids)),
        "max_id": max(ids),
        "boxes": cnt,
        "branch": len(re.findall(r'Type="\{827b9ec2', s)),
        "pin": len(re.findall(r'Type="\{9de7f100', s)),
        "connector": len(re.findall(r'Type="\{5f9848d3', s)),
        "outconn": len(re.findall(r'Type="\{505bff94', s)),
    }