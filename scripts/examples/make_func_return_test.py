# -*- coding: utf-8 -*-
# @py3
"""验证 2026-11-25 新学的「FUNCTION 调用框返回值」结构（生成 prg_FuncRetTest）。

验证目标（全部来自全工程 126 POU 扫描得出的规律）：
  1. CallType=Function 的框：OutputParam.Names[1] = 空字符串 = 函数返回值槽
     OutputItems[i] 与 OutputParam.Names[i] 严格按索引一一对应：
       [0] <-> ENO（未接线写 <Null />）
       [1] <-> 返回值（接变量，LValue=True）
       [2..] <-> 其余 VAR_OUTPUT 参数
  2. InputItems 槽数 == InputParam 参数个数（槽0=连接器、槽1..n=参数引脚，
     与 FB 框一致——初版统计曾误判「恒为空」，正确解析后 35/35 等长）
  3. 容器不对称：InputItems 直接挂 <List2>，OutputItems 是 Single>List2

测试对象（模板自带 Function，全部用本 POU 局部变量，不依赖工程其它对象）：
  - PackMLScCmdInit（2 入 2 出：ENO + 返回值，最简形态）
  - PackMLSCCmdSum（4 入 3 出：ENO + 返回值 + VAR_OUTPUT xWarn，
    正好覆盖「[2..] 继续按索引对应」）

骨架取自 assets/natives/user_fixed.native（已验证可导入、预编译 0 错误）。
节点构造复用 make_fb_call_test.py 的经验（fb_box 直接搬来当 func_box 用）。
"""
import io
import os
import re
import uuid

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))
SKELETON = os.path.join(ROOT, "assets", "natives", "user_fixed.native")
OUT = os.path.join(ROOT, "..", "plc_mcp", "ipc", "prg_FuncRetTest.native")

POU_NAME = u"prg_FuncRetTest"

# ---------------- 节点 GUID ----------------
G_CONTACT = u"{9de7f100-1b87-424c-a62e-45b0cfc85ed2}"
G_BOX = u"{acfc6f68-8e3a-4af5-bf81-3dd512095a46}"
G_BRANCH = u"{827b9ec2-2032-40da-9f4e-7670ca2d55a8}"
G_NETITEM = u"{9873c309-1f09-4ebf-9078-42d8057ef11b}"
G_RVALUE = u"{5f9848d3-568d-4cc5-9e31-8e28e9607ff1}"
G_CONN_END = u"{505bff94-4c90-4e17-ac28-b8ac69d1b9e2}"
G_OUTPUTS = u"{f40d3e09-c02c-4522-a88c-dac23558cfc4}"
G_OPERAND = u"{c9b2f165-48a2-4a45-8326-3952d8a3d708}"
G_FLAGS = u"{668066f2-6069-46b3-8962-8db8d13d7db2}"
G_NETWORK = u"{d9a99d73-b633-47db-b876-a752acb25871}"
G_CALLTYPE = u"{bffb3c53-f105-4e85-aba2-e30df579d75f}"
G_PARAM = u"{71496971-9e0c-4677-a832-b9583b571130}"
G_MODE = u"{3b9474d0-c98b-4935-8ce5-65f06808350d}"

_id = [3000]


def nid():
    _id[0] += 1
    return _id[0]


def _indent(text, n):
    pad = u" " * n
    return u"\n".join(pad + ln for ln in text.split(u"\n"))


def flags_block(n=0, fixed=False):
    return (u'<Single Name="Flags" Type="%s" Method="IArchivable">\n'
            u'  <Single Name="Extensible" Type="bool">False</Single>\n'
            u'  <Single Name="Fixed" Type="bool">%s</Single>\n'
            u'  <Single Name="Flags" Type="int">%d</Single>\n'
            u'</Single>' % (G_FLAGS, u"True" if fixed else u"False", n))


# ---------------------------------------------------------------- 基本节点
def operand(var, typ, is_instance=False, lvalue=False, is_coil=False, flags=0):
    """Operand 节点（{c9b2f165}）。var=None -> <Null Name="Operand" />。"""
    op = (u'<Null Name="Operand" />' if var is None
          else u'<Single Name="Operand" Type="string">%s</Single>' % var)
    return (u'<Single Name="Boolean" Type="bool">False</Single>\n'
            u'<Single Name="IsInstance" Type="bool">%s</Single>\n'
            u'<Single Name="LValue" Type="bool">%s</Single>\n'
            u'%s\n'
            u'<Single Name="Address" Type="string"></Single>\n'
            u'<Single Name="Comment" Type="string"></Single>\n'
            u'%s\n'
            u'<Single Name="SymbolComment" Type="string"></Single>\n'
            u'<Single Name="Type" Type="string">%s</Single>\n'
            u'<Single Name="IsCoil" Type="bool">%s</Single>\n'
            u'<Single Name="IsSeriesCoil" Type="bool">False</Single>\n'
            u'<Single Name="SeriesIndex" Type="int">-1</Single>\n'
            u'<Single Name="ConnectorFlags" Type="%s" Method="IArchivable">\n'
            u'  <Single Name="Extensible" Type="bool">False</Single>\n'
            u'  <Single Name="Fixed" Type="bool">False</Single>\n'
            u'  <Single Name="Flags" Type="int">0</Single>\n'
            u'</Single>\n'
            u'<Single Name="Id" Type="long">%d</Single>' % (
                u"True" if is_instance else u"False",
                u"True" if lvalue else u"False",
                flags_block(flags),
                op, typ,
                u"True" if is_coil else u"False",
                G_FLAGS, nid()))


def pin(var, typ, is_contact=False, flags=0):
    """参数引脚（{9de7f100}）。FB 的输入参数槽用它，IsContact=False。"""
    return (u'<Single Type="%s" Method="IArchivable">\n'
            u'  <Single Name="Operand" Type="%s" Method="IArchivable">\n'
            u'    %s\n'
            u'  </Single>\n'
            u'  <Single Name="IsContact" Type="bool">%s</Single>\n'
            u'  <Single Name="Id" Type="long">%d</Single>\n'
            u'</Single>' % (G_CONTACT, G_OPERAND,
                            _indent(operand(var, typ, flags=flags), 4),
                            u"True" if is_contact else u"False", nid()))


def connector_input():
    """InputItems 槽0：连接器 {5f9848d3}，Input=Null（EN 引脚无来源）。"""
    return (u'<Single Type="%s" Method="IArchivable">\n'
            u'  %s\n'
            u'  <Null Name="Input" />\n'
            u'  <Single Name="Id" Type="long">%d</Single>\n'
            u'</Single>' % (G_RVALUE, _indent(flags_block(0), 2), nid()))


def connector_end():
    """支路末尾连接器 {505bff94}，只有 Id。"""
    return (u'<Single Type="%s" Method="IArchivable">\n'
            u'  <Single Name="Id" Type="long">%d</Single>\n'
            u'</Single>' % (G_CONN_END, nid()))


def output_target(var, typ):
    """OutputItems 里的输出目标操作数（LValue=True, IsCoil=False）。"""
    return (u'<Single Type="%s" Method="IArchivable">\n'
            u'  %s\n'
            u'</Single>' % (G_OPERAND, _indent(operand(var, typ, lvalue=True), 2)))


def str_list(items):
    return _indent(u"\n".join(u'<Single Type="string">%s</Single>' % x for x in items), 6)


# ---------------------------------------------------------------- 功能框
def fb_box(box_type, call_type, inputs, outputs, instance=None):
    """生成一个功能块/函数/程序调用框。

    inputs:  [(param_name, param_type, operand)]
             param_name -> InputParam.Names；param_type -> InputParam.Types
             （REF 形参照抄 [REF] 后缀）；operand -> 引脚接的变量/常量
    outputs: [(param_name, param_type, target_operand)]
             第 0 项恒为 ENO（target 忽略，写 <Null />）
    instance: None=无名实例；("实例名", "FB类型")=带实例
    """
    slots = [connector_input()]
    for nm, tp, op in inputs:
        slots.append(pin(op, tp.replace(u"[REF]", u"")))

    names = [u"EN"] + [p[0] for p in inputs]
    types = [u"BOOL"] + [p[1] for p in inputs]

    out_items = [u'<Null />']
    for nm, tp, tgt in outputs[1:]:
        out_items.append(output_target(tgt, tp))

    inst_op = u'<Null Name="Operand" />' if instance is None else \
        u'<Single Name="Operand" Type="string">%s</Single>' % instance[0]
    inst_ty = u'' if instance is None else instance[1]

    return (u'<Single Type="%s" Method="IArchivable">\n'
            u'  <Single Name="ContainsExtensibleInputs" Type="bool">False</Single>\n'
            u'  <Single Name="EN" Type="bool">True</Single>\n'
            u'  <Single Name="ENO" Type="bool">True</Single>\n'
            u'  <Single Name="ProvidesSTSnippet" Type="bool">False</Single>\n'
            u'  %s\n'
            u'  <Null Name="InputFlags" />\n'
            u'  <List2 Name="InputItems">\n%s\n  </List2>\n'
            u'  <Single Name="CallType" Type="%s">%s</Single>\n'
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
            u'    <Single Name="ConnectorFlags" Type="%s" Method="IArchivable">\n'
            u'      <Single Name="Extensible" Type="bool">False</Single>\n'
            u'      <Single Name="Fixed" Type="bool">False</Single>\n'
            u'      <Single Name="Flags" Type="int">0</Single>\n'
            u'    </Single>\n'
            u'    <Single Name="Id" Type="long">%d</Single>\n'
            u'  </Single>\n'
            u'  <Single Name="OutputItems" Type="%s" Method="IArchivable">\n'
            u'    <List2 Name="OutputItems">\n%s\n    </List2>\n'
            u'  </Single>\n'
            u'  <Single Name="InputParam" Type="%s" Method="IArchivable">\n'
            u'    <List2 Name="Names">\n%s\n    </List2>\n'
            u'    <List2 Name="Types">\n%s\n    </List2>\n'
            u'  </Single>\n'
            u'  <Single Name="OutputParam" Type="%s" Method="IArchivable">\n'
            u'    <List2 Name="Names">\n%s\n    </List2>\n'
            u'    <List2 Name="Types">\n%s\n    </List2>\n'
            u'  </Single>\n'
            u'  <Single Name="BoxType" Type="string">%s</Single>\n'
            u'  <Null Name="STSnippet" />\n'
            u'  <Single Name="IsBoxType" Type="bool">True</Single>\n'
            u'  <Single Name="Id" Type="long">%d</Single>\n'
            u'</Single>' % (
                G_BOX, _indent(flags_block(0, True), 2),
                _indent(u"\n".join(slots), 4),
                G_CALLTYPE, call_type, G_OPERAND,
                _indent(flags_block(0), 4), inst_op, inst_ty, G_FLAGS, nid(),
                G_OUTPUTS, _indent(u"\n".join(out_items), 6),
                G_PARAM, str_list(names), str_list(types),
                G_PARAM, str_list([p[0] for p in outputs]), str_list([p[1] for p in outputs]),
                box_type, nid()))


def and_box(items):
    """AND 功能框（串联）。至少 2 个槽。"""
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
            u'</Single>' % (G_BOX, _indent(flags_block(0), 2),
                            _indent(u"\n".join(items), 4),
                            G_CALLTYPE, G_OPERAND, _indent(flags_block(0), 4),
                            G_FLAGS, nid(), G_OUTPUTS, G_PARAM, G_PARAM, nid()))


def branch(trees):
    """分支组：Trees 之间为并联(OR)。"""
    return (u'<Single Type="%s" Method="IArchivable">\n'
            u'  <Null Name="Input" />\n'
            u'  <List2 Name="Trees">\n%s\n  </List2>\n'
            u'  <Single Name="Mode" Type="%s">Sequential</Single>\n'
            u'  <Single Name="Id" Type="long">%d</Single>\n'
            u'</Single>' % (G_BRANCH, _indent(u"\n".join(trees), 4), G_MODE, nid()))


def netitem_rvalue(node):
    """【已弃用，勿用】梯级：RValue 里放图形节点。

    实测坑：若 node 是「只有 1 条支路」的分支组，导入后预编译/编译都 0 错误，
    但 IDE 在【绘制该网络】时抛「索引超出了数组界限」（堆栈在 IBoxTreeParallel），
    表现为程序段显示「不能显示内容」。

    正确做法见 build_networks()：图形节点直接挂 NetworkItems（照 act04 / act90 网络3）。
    """
    rv = node.replace(u'<Single Type="', u'<Single Name="RValue" Type="', 1)
    return (u'<Single Type="%s" Method="IArchivable">\n'
            u'  %s\n'
            u'  %s\n'
            u'  <Single Name="OutputItems" Type="%s" Method="IArchivable">\n'
            u'    <List2 Name="OutputItems" />\n'
            u'  </Single>\n'
            u'  <Single Name="Id" Type="long">%d</Single>\n'
            u'</Single>' % (G_NETITEM, _indent(flags_block(0), 2),
                            _indent(rv, 2), G_OUTPUTS, nid()))


def network(items, comment):
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
            u'</Single>' % (G_NETWORK, _indent(u"\n".join(items), 4), comment, nid()))


# ===================== 两个 Function 框调用（全部用本 POU 的局部变量）=====
def call_sc_cmd_init():
    """Function 最简形态：PackMLScCmdInit —— ENO + 返回值，无 VAR_OUTPUT。"""
    return fb_box(
        box_type=u"PackMLScCmdInit",
        call_type=u"Function",
        inputs=[(u"stScCmd", u"sPmlSCCmd[REF]", u"stScTest")],
        outputs=[(u"ENO", u"BOOL", None), (u"", u"BOOL", u"xRetInit")],
        instance=None,
    )


def call_sc_cmd_sum():
    """Function 带尾参形态：PackMLSCCmdSum —— ENO + 返回值 + VAR_OUTPUT xWarn，
    验证「[2..] 继续按索引对应」。

    ⚠ stSum[REF] 的类型 sUnitScCmd 不是本 POU 可声明的简单名（实测预编译报
    「没有定义标识符'sUnitScCmd'」），照模板 act90_ScCmd 的接法直接接
    工程全局实例成员 PML0.stCmd.stSc，不要自己声明局部变量。"""
    return fb_box(
        box_type=u"PackMLSCCmdSum",
        call_type=u"Function",
        inputs=[
            (u"stSum", u"sUnitScCmd[REF]", u"PML0.stCmd.stSc"),
            (u"stIn", u"sPmlSCCmd", u"stScTest"),
            (u"uiEmID", u"UINT", u"7"),
        ],
        outputs=[(u"ENO", u"BOOL", None), (u"", u"BOOL", u"xRetSum"), (u"xWarn", u"BOOL", u"xWarnSum")],
        instance=None,
    )


DECL = [
    u"PROGRAM %s" % POU_NAME,
    u"VAR",
    u"    (* ~~~~ FUNCTION 调用框返回值结构验证 ~~~~~~~~~~~~~~~~~~~~ *)",
    u"",
    u"    (* -- 输入参数源 -- *)",
    u"    stScTest         : sPmlScCmd;     // PackMLScCmdInit / PackMLSCCmdSum 共用",
    u"    // stSum[REF] 直接接工程全局 PML0.stCmd.stSc（sUnitScCmd 非简单可见名，",
    u"    // 不可本地声明——照模板 act90_ScCmd 接全局实例成员)",
    u"",
    u"    (* -- 输出目标：[1]=返回值、[2..]=VAR_OUTPUT，按索引对应 -- *)",
    u"    xRetInit         : BOOL;          // ScCmdInit 返回值（最简形态）",
    u"    xRetSum          : BOOL;          // SCCmdSum 返回值",
    u"    xWarnSum         : BOOL;          // SCCmdSum 的 VAR_OUTPUT xWarn",
    u"END_VAR",
]


def build_networks():
    """网络结构：图形节点【直接】挂 NetworkItems，不套 NETITEM/RValue。

    - 有 ≥2 条并联支路 -> 直接放分支组 {827b9ec2}（act04 实测）
    - 只有 1 条支路     -> 直接放 AND 框 {acfc6f68}（act90 网络3 实测）

    **绝不能**给「单支路分支组」套 NETITEM/RValue：预编译和编译都 0 错误，
    但 IDE 绘制该网络时抛「索引超出了数组界限」（IBoxTreeParallel 按 ≥2 支路取索引）。
    """
    nets = []

    # 网络1：两个 Function 框并联（各一条支路 -> 分支组直挂）
    b1 = branch([
        and_box([call_sc_cmd_init(), connector_end()]),
        and_box([call_sc_cmd_sum(), connector_end()]),
    ])
    nets.append(network([b1],
                        u"// ~~~~ Function 类：PackMLScCmdInit(返回值->xRetInit) + PackMLSCCmdSum(返回值->xRetSum, xWarn->xWarnSum) ~~~~"))

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
    depth = 0
    i = start
    while i < len(s):
        no = s.find(open_tag, i)
        nc = s.find(close_tag, i)
        if nc < 0:
            return -1
        if no >= 0 and no < nc:
            gt = s.find(u">", no)
            self_closing = gt > 0 and s[gt - 1] == u"/"
            if self_closing:
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


def main():
    raw = io.open(SKELETON, "r", encoding="utf-8").read()

    key = u'<List2 Name="NetworkList">'
    p = raw.find(key)
    assert p >= 0, "skeleton has no NetworkList"
    end = find_block_end(raw, p, u"<List2", u"</List2>")
    assert end > 0
    nets_xml = u"\n".join(build_networks())
    raw = raw[:p] + key + u"\n" + nets_xml + u"\n            </List2>" + raw[end:]

    key2 = u'<Array Name="TextLines"'
    p2 = raw.find(key2)
    assert p2 >= 0, "skeleton has no TextLines"
    end2 = find_block_end(raw, p2, u"<Array", u"</Array>")
    assert end2 > 0
    raw = raw[:p2] + textlines_block(DECL) + raw[end2:]

    raw = raw.replace(u'>prg_StartStop<', u'>%s<' % POU_NAME)
    new_guid = str(uuid.uuid4())
    raw = raw.replace(
        u'<Single Name="Guid" Type="System.Guid">aa4f05c0-d089-4b64-89fe-370f00252313</Single>',
        u'<Single Name="Guid" Type="System.Guid">%s</Single>' % new_guid)

    raw = re.sub(u'<Single Name="UniqueIdGenerator" Type="string">\\d+</Single>',
                 u'<Single Name="UniqueIdGenerator" Type="string">%d</Single>' % (_id[0] + 200),
                 raw)

    io.open(OUT, "w", encoding="utf-8").write(raw)
    print(u"generated: %s (%d bytes)" % (OUT, os.path.getsize(OUT)))
    print(u"POU name = %s" % POU_NAME)
    print(u"networks = %d" % raw.count(G_NETWORK))
    print(u"boxes    = %d" % raw.count(G_BOX))
    print(u"max id   = %d" % _id[0])
    print(u"guid     = %s" % new_guid)


main()
