# -*- coding: utf-8 -*-
# @py3
"""按 act03_PackMLCmd 的写法，生成一个独立测试 POU 的 native 文件。

覆盖的写法要点（全部来自 act03_PackMLCmd 实测结构）：
  1. 模式切换：分支组 Input 放「公共前缀」，Trees 放并联输出支路（各含一个线圈）
  2. 输出取反：NETITEM.Flags=1（线圈前的小圆圈 ○）
  3. 命令网络：BRANCH{ Trees=[AND[模式, 条件], AND[模式, 条件]] } -> 一个线圈
  4. 未实现功能用常量 FALSE/TRUE 占位
  5. 公共条件只画一次：BRANCH.Input = 模式并联组，Trees = 状态条件

骨架取自 assets/natives/user_fixed.native（已验证可导入、预编译 0 错误）。
"""
import io
import os
import re
import uuid

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))
SKELETON = os.path.join(ROOT, "assets", "natives", "user_fixed.native")
OUT = os.path.join(ROOT, "..", "plc_mcp", "ipc", "prg_PackMLCmdTest.native")

POU_NAME = u"prg_PackMLCmdTest"

# ---------------- 节点 GUID ----------------
G_CONTACT = u"{9de7f100-1b87-424c-a62e-45b0cfc85ed2}"
G_AND = u"{acfc6f68-8e3a-4af5-bf81-3dd512095a46}"
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

_id = [1000]


def nid():
    _id[0] += 1
    return _id[0]


def flags_block(n=0, fixed=False):
    return (u'<Single Name="Flags" Type="%s" Method="IArchivable">\n'
            u'  <Single Name="Extensible" Type="bool">False</Single>\n'
            u'  <Single Name="Fixed" Type="bool">%s</Single>\n'
            u'  <Single Name="Flags" Type="int">%d</Single>\n'
            u'</Single>' % (G_FLAGS, u"True" if fixed else u"False", n))


def contact(var, not_flag=False, is_contact=True):
    """触点。not_flag=True -> Operand 内部 Flags=1（常闭/取反）。

    常量（TRUE/FALSE）必须 Flags=0，否则预编译报错。
    """
    is_const = var in (u"TRUE", u"FALSE")
    ofl = 0 if is_const else (1 if not_flag else 0)
    inner_id = nid()
    node_id = nid()
    return (u'<Single Type="%s" Method="IArchivable">\n'
            u'  <Single Name="Operand" Type="%s" Method="IArchivable">\n'
            u'    <Single Name="Boolean" Type="bool">True</Single>\n'
            u'    <Single Name="IsInstance" Type="bool">False</Single>\n'
            u'    <Single Name="LValue" Type="bool">False</Single>\n'
            u'    %s\n'
            u'    <Single Name="Address" Type="string"></Single>\n'
            u'    <Single Name="Comment" Type="string"></Single>\n'
            u'    <Single Name="Operand" Type="string">%s</Single>\n'
            u'    <Single Name="SymbolComment" Type="string"></Single>\n'
            u'    <Single Name="Type" Type="string">BOOL</Single>\n'
            u'    <Single Name="IsCoil" Type="bool">False</Single>\n'
            u'    <Single Name="IsSeriesCoil" Type="bool">False</Single>\n'
            u'    <Single Name="SeriesIndex" Type="int">-1</Single>\n'
            u'    <Single Name="ConnectorFlags" Type="%s" Method="IArchivable">\n'
            u'      <Single Name="Extensible" Type="bool">False</Single>\n'
            u'      <Single Name="Fixed" Type="bool">False</Single>\n'
            u'      <Single Name="Flags" Type="int">0</Single>\n'
            u'    </Single>\n'
            u'    <Single Name="Id" Type="long">%d</Single>\n'
            u'  </Single>\n'
            u'  <Single Name="IsContact" Type="bool">%s</Single>\n'
            u'  <Single Name="Id" Type="long">%d</Single>\n'
            u'</Single>' % (G_CONTACT, G_OPERAND, flags_block(ofl, True), var,
                            G_FLAGS, inner_id,
                            u"True" if is_contact else u"False", node_id))


def coil(var):
    """输出线圈（NETITEM.OutputItems 里的操作数节点，自身即 OPERAND）。"""
    node_id = nid()
    return (u'<Single Type="%s" Method="IArchivable">\n'
            u'  <Single Name="Boolean" Type="bool">True</Single>\n'
            u'  <Single Name="IsInstance" Type="bool">False</Single>\n'
            u'  <Single Name="LValue" Type="bool">True</Single>\n'
            u'  %s\n'
            u'  <Single Name="Address" Type="string"></Single>\n'
            u'  <Single Name="Comment" Type="string"></Single>\n'
            u'  <Single Name="Operand" Type="string">%s</Single>\n'
            u'  <Single Name="SymbolComment" Type="string"></Single>\n'
            u'  <Single Name="Type" Type="string">BOOL</Single>\n'
            u'  <Single Name="IsCoil" Type="bool">True</Single>\n'
            u'  <Single Name="IsSeriesCoil" Type="bool">False</Single>\n'
            u'  <Single Name="SeriesIndex" Type="int">-1</Single>\n'
            u'  <Single Name="ConnectorFlags" Type="%s" Method="IArchivable">\n'
            u'    <Single Name="Extensible" Type="bool">False</Single>\n'
            u'    <Single Name="Fixed" Type="bool">False</Single>\n'
            u'    <Single Name="Flags" Type="int">0</Single>\n'
            u'  </Single>\n'
            u'  <Single Name="Id" Type="long">%d</Single>\n'
            u'</Single>' % (G_OPERAND, flags_block(0), var, G_FLAGS, node_id))


def and_box(items):
    """AND 功能框（串联）。items 是已渲染好的子节点字符串列表。"""
    inst_id = nid()
    box_id = nid()
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
            u'    <Single Name="ConnectorFlags" Type="%s" Method="IArchivable">\n'
            u'      <Single Name="Extensible" Type="bool">False</Single>\n'
            u'      <Single Name="Fixed" Type="bool">False</Single>\n'
            u'      <Single Name="Flags" Type="int">0</Single>\n'
            u'    </Single>\n'
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
            u'</Single>' % (G_AND, flags_block(0), body, G_CALLTYPE, G_OPERAND,
                            flags_block(0), G_FLAGS, inst_id, G_OUTPUTS, G_PARAM, G_PARAM, box_id))


def branch_input(items):
    """分支组 Input 槽（精简 AND 框，无 CallType/Instance/BoxType/Id）。

    act03 网络1 实测：Input 只有
      ContainsExtensibleInputs / EN / ENO / ProvidesSTSnippet /
      Flags / InputFlags / InputItems
    不是完整的 AND 功能框 —— 多写 CallType/Instance/BoxType 会报
    「已标识项中有一项的格式无效」。
    """
    return (u'<Single Name="Input" Type="%s" Method="IArchivable">\n'
            u'  <Single Name="ContainsExtensibleInputs" Type="bool">False</Single>\n'
            u'  <Null Name="EN" />\n'
            u'  <Null Name="ENO" />\n'
            u'  <Single Name="ProvidesSTSnippet" Type="bool">False</Single>\n'
            u'  %s\n'
            u'  <Null Name="InputFlags" />\n'
            u'  <List2 Name="InputItems">\n%s\n  </List2>\n'
            u'</Single>' % (G_AND, flags_block(0), u"\n".join(items)))



def as_input_slot(node_xml):
    """把图形节点的外层 <Single Type="..."> 改写成 <Single Name="Input" Type="...">。

    分支组的 Input 槽必须带 Name="Input" 属性；直接塞 and_box()/branch()
    的原始输出会缺这个属性 —— 这是网络1/网络6 一直对不上的根因。
    """
    return node_xml.replace(u'<Single Type="', u'<Single Name="Input" Type="', 1)


def branch(trees, prefix=None):
    """分支组：Trees 之间恒为并联(OR)；prefix 放公共前缀（只画一次）。

    prefix 传【图形节点列表】：
      - 网络1 → [分支组, 触点]   经 branch_input 包成精简 AND 框
      - 网络6 → [分支组]         同样经 branch_input
    """
    bid = nid()
    inp = u'<Null Name="Input" />' if prefix is None else as_input_slot(prefix)
    body = u"\n".join(trees)
    return (u'<Single Type="%s" Method="IArchivable">\n'
            u'  %s\n'
            u'  <List2 Name="Trees">\n%s\n  </List2>\n'
            u'  <Single Name="Mode" Type="%s">Sequential</Single>\n'
            u'  <Single Name="Id" Type="long">%d</Single>\n'
            u'</Single>' % (G_BRANCH, inp, body, G_MODE, bid))


def netitem(rvalue_node, coils, inverted=False):
    """梯级：rvalue_node 是条件图形；coils 是输出线圈列表。

    inverted=True -> NETITEM.Flags=1，表示该梯级输出取反（线圈前的小圆圈 ○）。
    """
    rv_id = nid()
    item_id = nid()
    coil_body = u"\n".join(coils)
    return (u'<Single Type="%s" Method="IArchivable">\n'
            u'  %s\n'
            u'  <Single Name="RValue" Type="%s" Method="IArchivable">\n'
            u'    %s\n'
            u'    %s\n'
            u'    <Single Name="Id" Type="long">%d</Single>\n'
            u'  </Single>\n'
            u'  <Single Name="OutputItems" Type="%s" Method="IArchivable">\n'
            u'    <List2 Name="OutputItems">\n%s\n    </List2>\n'
            u'  </Single>\n'
            u'  <Single Name="Id" Type="long">%d</Single>\n'
            u'</Single>' % (G_NETITEM, flags_block(1 if inverted else 0),
                            G_RVALUE, flags_block(0), rvalue_node, rv_id,
                            G_OUTPUTS, coil_body, item_id))


def netitem_branch_rvalue(branch_node, coils):
    """RValue 节点的 Type 直接就是分支组（act03 网络2~10 的写法）。

    关键：RValue 的类型是 {827b9ec2 分支组}，不是 {5f9848d3 RValue 容器}
    里再包一层分支组 —— 多包一层就报「已标识项中有一项的格式无效」。
    """
    item_id = nid()
    coil_body = u"\n".join(coils)
    rv = branch_node.replace(u'<Single Type="', u'<Single Name="RValue" Type="', 1)
    return (u'<Single Type="%s" Method="IArchivable">\n'
            u'  %s\n'
            u'  %s\n'
            u'  <Single Name="OutputItems" Type="%s" Method="IArchivable">\n'
            u'    <List2 Name="OutputItems">\n%s\n    </List2>\n'
            u'  </Single>\n'
            u'  <Single Name="Id" Type="long">%d</Single>\n'
            u'</Single>' % (G_NETITEM, flags_block(0), rv,
                            G_OUTPUTS, coil_body, item_id))


def netitem_null_rvalue(coils, inverted=False):
    """梯级：RValue 里只有 Null Input（条件来自外层分支组公共前缀）。"""
    rv_id = nid()
    item_id = nid()
    coil_body = u"\n".join(coils)
    return (u'<Single Type="%s" Method="IArchivable">\n'
            u'  %s\n'
            u'  <Single Name="RValue" Type="%s" Method="IArchivable">\n'
            u'    %s\n'
            u'    <Null Name="Input" />\n'
            u'    <Single Name="Id" Type="long">%d</Single>\n'
            u'  </Single>\n'
            u'  <Single Name="OutputItems" Type="%s" Method="IArchivable">\n'
            u'    <List2 Name="OutputItems">\n%s\n    </List2>\n'
            u'  </Single>\n'
            u'  <Single Name="Id" Type="long">%d</Single>\n'
            u'</Single>' % (G_NETITEM, flags_block(1 if inverted else 0),
                            G_RVALUE, flags_block(0), rv_id,
                            G_OUTPUTS, coil_body, item_id))


def network(items, comment):
    nwid = nid()
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
            u'</Single>' % (G_NETWORK, body, comment, nwid))


# ===================== 声明区 =====================
DECL = [
    u"PROGRAM %s" % POU_NAME,
    u"VAR",
    u"    (* ~~~~ 模式切换（仿 act03_PackMLCmd 网络1）~~~~~~~~~~~~~~ *)",
    u"    xAutoStart  : BOOL;   // 自动启动命令（HMI 触发）",
    u"    xStopped    : BOOL;   // 已停止状态（TRUE=停止中）",
    u"    xInvaild    : BOOL;   // 无效模式",
    u"    xProduction : BOOL;   // 生产模式（输出）",
    u"    xManual     : BOOL;   // 手动模式（输出，取反得到）",
    u"    (* ~~~~ 状态控制命令条件 ~~~~~~~~~~~~~~ *)",
    u"    xAutoStop   : BOOL;   // 自动停止命令",
    u"    xResetAlarm : BOOL;   // 复位报警",
    u"    xAutoHalt   : BOOL;   // 自动暂停命令",
    u"    xIdle       : BOOL;   // 空闲状态",
    u"    xExecute    : BOOL;   // 执行状态",
    u"    xAborted    : BOOL;   // 中止状态",
    u"    xComplete   : BOOL;   // 完成状态",
    u"    (* ~~~~ 状态控制命令输出 ~~~~~~~~~~~~~~ *)",
    u"    xStart      : BOOL;   // Start 命令",
    u"    xStop       : BOOL;   // Stop 命令",
    u"    xAbort      : BOOL;   // Abort 命令",
    u"    xClear      : BOOL;   // Clear 命令",
    u"    xReset      : BOOL;   // Reset 命令",
    u"    xHold       : BOOL;   // Hold 命令",
    u"END_VAR",
]


def build_networks():
    nets = []

    # 网络1：模式切换 —— 公共前缀 + 并联输出支路 + 输出取反
    # 公共前缀 = AND[ OR[xAutoStart, xProduction], NOT xStopped ]（Input 是一个 AND 框）
    n1 = branch(
        [
            netitem_null_rvalue([coil(u"xProduction")]),
            netitem_null_rvalue([coil(u"xManual")], inverted=True),
        ],
        prefix=and_box([
            branch([contact(u"xAutoStart"), contact(u"xProduction")]),
            contact(u"xStopped", not_flag=True),
        ]),
    )
    nets.append(network([n1], u"// ~~~~ 模式切换命令：Mode：~~~~~~~~~~~~~~"))

    def cmd_net(coil_var, prod_cond, manual_cond, comment):
        b = branch([
            and_box([contact(u"xProduction"), contact(prod_cond)]),
            and_box([contact(u"xManual"), contact(manual_cond)]),
        ])
        return network([netitem_branch_rvalue(b, [coil(coil_var)])], comment)

    # 网络2：Start
    nets.append(cmd_net(u"xStart", u"xAutoStart", u"xIdle",
                        u"//* ~~~~ 状态控制命令——Start命令：~~~~~~~~~~~~~~"))
    # 网络3：Stop
    nets.append(cmd_net(u"xStop", u"xAutoStop", u"FALSE",
                        u"//* ~~~~ 状态控制命令——Stop命令：~~~~~~~~~~~~~~"))
    # 网络4：Abort（两条都是常量占位）
    nets.append(cmd_net(u"xAbort", u"FALSE", u"FALSE",
                        u"//* ~~~~ 状态控制命令——Abort命令：~~~~~~~~~~~~~~"))
    # 网络5：Clear
    nets.append(cmd_net(u"xClear", u"xResetAlarm", u"xAborted",
                        u"//* ~~~~ 状态控制命令——Clear命令：~~~~~~~~~~~~~~"))

    # 网络6：Reset —— 公共前缀只画一次（三种模式），支路只画状态
    # Input 本身就是一个分支组（不是 AND 框）
    b6 = branch(
        [contact(u"xStopped"), contact(u"xComplete")],
        prefix=branch([contact(u"xInvaild"), contact(u"xProduction"), contact(u"xManual")]),
    )
    nets.append(network([netitem_branch_rvalue(b6, [coil(u"xReset")])],
                        u"//* ~~~~ 状态控制命令——Reset命令：~~~~~~~~~~~~~~"))

    # 网络7：Hold
    nets.append(cmd_net(u"xHold", u"xAutoHalt", u"xExecute",
                        u"//* ~~~~ 状态控制命令——Hold命令：~~~~~~~~~~~~~~"))

    return nets


def textlines_block(decls):
    out = [u'<Array Name="TextLines" Type="{a5de0b0b-1cb5-4913-ac21-9d70293ec00d}">']
    tid = 900
    for d in decls:
        out.append(
            u'  <Single Type="{a5de0b0b-1cb5-4913-ac21-9d70293ec00d}" Method="IArchivable">\n'
            u'    <Single Name="Id" Type="long">%d</Single>\n'
            u'    <Null Name="Tag" />\n'
            u'    <Single Name="Text" Type="string">%s</Single>\n'
            u'  </Single>' % (tid, d))
        tid += 1
    out.append(u'</Array>')
    return u"\n".join(out)


def find_block_end(s, start, open_tag, close_tag):
    """从 start（open_tag 起始处）找到配对 close_tag 之后的位置。

    必须跳过自闭合标签（如 <List2 Name="Connectors" />），
    否则深度永远配不平（这是上一版 assert 失败的根因）。
    """
    depth = 0
    i = start
    while i < len(s):
        no = s.find(open_tag, i)
        nc = s.find(close_tag, i)
        if nc < 0:
            return -1
        if no >= 0 and no < nc:
            # 判断是否自闭合：标签内到第一个 '>' 之间是否以 '/' 结尾
            gt = s.find(u">", no)
            self_closing = gt > 0 and s[gt - 1] == u"/"
            if self_closing:
                i = gt + 1          # 跳过，不改变深度
                continue
            depth += 1
            i = no + len(open_tag)
        else:
            depth -= 1
            i = nc + len(close_tag)
            if depth == 0:
                return i
    return -1


def main():
    raw = io.open(SKELETON, "r", encoding="utf-8").read()

    # ---- 1. 替换 NetworkList 内容 ----
    key = u'<List2 Name="NetworkList">'
    p = raw.find(key)
    assert p >= 0, "skeleton has no NetworkList"
    end = find_block_end(raw, p, u"<List2", u"</List2>")
    assert end > 0
    nets_xml = u"\n".join(build_networks())
    new_netlist = key + u"\n" + nets_xml + u"\n            </List2>"
    raw = raw[:p] + new_netlist + raw[end:]

    # ---- 2. 替换声明区 TextLines ----
    key2 = u'<Array Name="TextLines"'
    p2 = raw.find(key2)
    assert p2 >= 0, "skeleton has no TextLines"
    end2 = find_block_end(raw, p2, u"<Array", u"</Array>")
    assert end2 > 0
    raw = raw[:p2] + textlines_block(DECL) + raw[end2:]

    # ---- 3. 替换 POU 名称 / Guid ----
    raw = raw.replace(u'>prg_StartStop<', u'>%s<' % POU_NAME)
    new_guid = str(uuid.uuid4())
    raw = raw.replace(u'<Single Name="Guid" Type="System.Guid">aa4f05c0-d089-4b64-89fe-370f00252313</Single>',
                      u'<Single Name="Guid" Type="System.Guid">%s</Single>' % new_guid)

    # ---- 4. UniqueIdGenerator 抬到最大 Id 之上 ----
    raw = re.sub(u'<Single Name="UniqueIdGenerator" Type="string">\\d+</Single>',
                 u'<Single Name="UniqueIdGenerator" Type="string">%d</Single>' % (_id[0] + 200),
                 raw)

    io.open(OUT, "w", encoding="utf-8").write(raw)
    print(u"generated: %s (%d bytes)" % (OUT, os.path.getsize(OUT)))
    print(u"POU name = %s" % POU_NAME)
    print(u"networks = %d" % raw.count(G_NETWORK))
    print(u"max id   = %d" % _id[0])
    print(u"guid     = %s" % new_guid)


main()
