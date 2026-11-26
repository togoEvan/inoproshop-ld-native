# -*- coding: utf-8 -*-
# @py3
"""GVL（全局变量列表）+ Folder 的 native 生成器 —— 从零构造，不依赖 LD 骨架。

⚠ 本仓库第一份 GVL 生成器。此前 `assets/natives/` 无任何 GVL 样本，
   知识库也只记了「`ffbfa93a` = GVL」一行。以下结构全部来自
   「除油倒盘-擦拭机-PLCV20261124」真实工程导出逐字段核对。

GVL 与 POU 的结构差异：
  · GVL 没有 NetworkList / Implementation，声明**只有** Interface > TextDocument
    > TextLines（与 POU 声明区同构，但没有 Implementation 兄弟节点）
  · `MetaObject.EmbeddedTypeGuids` = Array[a9ed5b7e]（单元素）
  · `Object.NetVarProperties` = `<Null/>`，`AddAttributeSubsequent` /
    `ParameterList` 都是 `<Single Type="bool">False</Single>`
  · 一个 GVL 的 TextLines 里**可以有多段** `VAR_GLOBAL ... END_VAR`；
    `VAR_GLOBAL PERSISTENT RETAIN`（PLC_Auto）与 `VAR_GLOBAL RETAIN PERSISTENT`
    （PLC_Common）两种顺序在真实工程里都存在
  · `AT %MBxxxxxx` 直接地址直接写在声明行文本里，native 层无专用字段

Folder（`738bea1e`）：
  · `Object` 只有一个 `StructuredViewGuid`
  · `EmbeddedTypeGuids` 必须是 `<Null/>`（不是空 `<Array>`）

★ 三条实测的 GUID 关系铁律（本项目 9 个 entry 全部符合）：
  ① `MetaObject.Properties.ParentObjects` 的 **Key = 导出根 StructuredView 的 Guid**
     （同一个导出文件里所有 entry 都相同），**Value = 父容器的 guid**
  ② `ParentSVNodeGuid` == `ParentObjects` 的 Value（即父容器 guid）
  ③ `MetaObject.ParentGuid` = **祖父** guid：
     · 直属 Application 的 Folder → `00000000-0000-0000-0000-000000000000`
     · Folder 的子对象 → Application 的 SV 节点 guid
  ④ Folder 的 `Object.StructuredViewGuid` == **导出根的 SV Guid**（不是自身 guid）
     —— 因为导出根 SV 就是该 Folder 自己的 SV 节点
"""
import io
import uuid

# ---------------- 节点类型 GUID（实测） ----------------
G_ENTRY = u"{6198ad31-4b98-445c-927f-3258a0e82fe3}"
G_META = u"{81297157-7ec9-45ce-845e-84cab2b88ade}"
G_PROPS = u"{2c41fa04-1834-41c1-816e-303c7aa2c05b}"
G_PROPKEY = u"{829a18f2-c514-4f6e-9634-1df173429203}"
G_PARENTOBJS = u"{fa2ee218-a39b-4b6d-b249-49dbddbd168a}"
G_GVL = u"{ffbfa93a-b94d-45fc-a329-229860183b1d}"
G_FOLDER = u"{738bea1e-99bb-4f04-90bb-a7a567e74e3a}"
G_IFACE = u"{a9ed5b7e-75c5-4651-af16-d2c27e98cb94}"
G_TEXTDOC = u"{f3878285-8e4f-490b-bb1b-9acbb7eb04db}"
G_TEXTLINE = u"{a5de0b0b-1cb5-4913-ac21-9d70293ec00d}"
G_SV = u"{3daac5e4-660e-42e4-9cea-3711b98bfb63}"

ZERO_GUID = u"00000000-0000-0000-0000-000000000000"

# ⚠ `MetaObject.TypeGuid` / `EmbeddedTypeGuids` 的**文本值不带花括号**，
#    只有节点的 `Type="..."` 属性才带。实测：
#      <Single Name="TypeGuid" Type="System.Guid">ffbfa93a-...</Single>
#      <Single Type="{ffbfa93a-...}" Method="IArchivable">
T_GVL = u"ffbfa93a-b94d-45fc-a329-229860183b1d"
T_FOLDER = u"738bea1e-99bb-4f04-90bb-a7a567e74e3a"
T_IFACE = u"a9ed5b7e-75c5-4651-af16-d2c27e98cb94"
T_PROPKEY = u"829a18f2-c514-4f6e-9634-1df173429203"
# Application 的 SV 节点 guid（本工程恒定；换工程需重新取）
APP_SV_NODE = u"2fb5ae21-d973-4d6a-92c0-c5721f941d64"

_id = [5000]


def nid():
    _id[0] += 1
    return _id[0]


def reset_ids(start=5000):
    _id[0] = start


def xml_text(s):
    """XML 文本转义（声明里可能出现 `<` `>` `&`，如 `// MW1000-MW1250 本机->从机`）。

    s 为 None 表示该行是空串（ElementTree 把空元素文本读成 None），按空串处理。
    """
    if s is None:
        return u""
    return (s.replace(u"&", u"&amp;")
             .replace(u"<", u"&lt;")
             .replace(u">", u"&gt;"))


def new_guid():
    # 兼容 IronPython 2.7 / CPython 3：两者都能拿到 str
    try:
        return unicode(uuid.uuid4())  # noqa: F821  (IronPython 2.7)
    except NameError:
        return str(uuid.uuid4())


def _props_block(sv_root_guid, parent_container_guid):
    """MetaObject.Properties：Key = 导出根 SV Guid，Value = 父容器 guid。"""
    return (u'        <Dictionary Type="%s" Name="Properties">\n'
            u'          <Entry>\n'
            u'            <Key>\n'
            u'              <Single Type="System.Guid">%s</Single>\n'
            u'            </Key>\n'
            u'            <Value>\n'
            u'              <Single Type="%s" Method="IArchivable">\n'  # 注意：这里带花括号
            u'                <Dictionary Type="%s" Name="ParentObjects">\n'
            u'                  <Entry>\n'
            u'                    <Key>\n'
            u'                      <Single Type="System.Guid">%s</Single>\n'
            u'                    </Key>\n'
            u'                    <Value>\n'
            u'                      <Single Type="System.Guid">%s</Single>\n'
            u'                    </Value>\n'
            u'                  </Entry>\n'
            u'                </Dictionary>\n'
            u'              </Single>\n'
            u'            </Value>\n'
            u'          </Entry>\n'
            u'        </Dictionary>'
            % (G_PROPS, T_PROPKEY, G_PROPKEY, G_PARENTOBJS,
               sv_root_guid, parent_container_guid))


def _textlines_block(lines, ids=None):
    """TextLines 数组。ids 给定时逐行沿用原始 Id（重建/往返时保持一致）。"""
    out = [u'            <Array Name="TextLines" Type="%s">' % G_TEXTLINE]
    for i, ln in enumerate(lines):
        lid = ids[i] if (ids is not None and i < len(ids)) else nid()
        out.append(
            u'              <Single Type="%s" Method="IArchivable">\n'
            u'                <Single Name="Id" Type="long">%d</Single>\n'
            u'                <Null Name="Tag" />\n'
            u'                <Single Name="Text" Type="string">%s</Single>\n'
            u'              </Single>' % (G_TEXTLINE, lid, xml_text(ln)))
    out.append(u'            </Array>')
    return u"\n".join(out)


def _path_block(path_parts):
    body = u"\n".join(
        u'        <Single Type="string">%s</Single>' % xml_text(p) for p in path_parts)
    return (u'      <Array Name="Path" Type="string">\n%s\n      </Array>' % body)


def gvl_entry(name, lines, guid, parent_container_guid, path_parts,
              sv_root_guid, timestamp=u"639106591923465391",
              is_root=False, ids=None):
    """一个 GVL Entry（TypeGuid = ffbfa93a）。

    name                  —— GVL 名（如 PLC_Auto）
    lines                 —— 声明文本行列表（原样，含 tab/空格）
    guid                  —— 本 GVL 的 MetaObject.Guid
    parent_container_guid —— 父容器（Folder）的 guid；同时用作 ParentSVNodeGuid
                             和 ParentObjects 的 Value
    path_parts            —— Path 数组（不含自身名）
    sv_root_guid          —— 导出根 StructuredView 的 Guid（本导出内恒定）
    """
    return (u'    <Single Type="%s" Method="IArchivable">\n'
            u'      <Single Name="IsRoot" Type="bool">%s</Single>\n'
            u'      <Single Name="MetaObject" Type="%s" Method="IArchivable">\n'
            u'        <Single Name="Guid" Type="System.Guid">%s</Single>\n'
            u'        <Single Name="ParentGuid" Type="System.Guid">%s</Single>\n'
            u'        <Single Name="Name" Type="string">%s</Single>\n'
            u'%s\n'
            u'        <Single Name="TypeGuid" Type="System.Guid">%s</Single>\n'
            u'        <Array Name="EmbeddedTypeGuids" Type="System.Guid">\n'
            u'          <Single Type="System.Guid">%s</Single>\n'
            u'        </Array>\n'
            u'        <Single Name="Timestamp" Type="long">%s</Single>\n'
            u'      </Single>\n'
            u'      <Single Name="Object" Type="%s" Method="IArchivable">\n'
            u'        <Single Name="Interface" Type="%s" Method="IArchivable">\n'
            u'          <Single Name="TextDocument" Type="%s" Method="IArchivable">\n'
            u'%s\n'
            u'          </Single>\n'
            u'        </Single>\n'
            u'        <Null Name="NetVarProperties" />\n'
            u'        <Single Name="AddAttributeSubsequent" Type="bool">False</Single>\n'
            u'        <Single Name="ParameterList" Type="bool">False</Single>\n'
            u'      </Single>\n'
            u'      <Single Name="ParentSVNodeGuid" Type="System.Guid">%s</Single>\n'
            u'%s\n'
            u'      <Single Name="Index" Type="int">-1</Single>\n'
            u'    </Single>'
            % (G_ENTRY, u"True" if is_root else u"False",
               G_META, guid, APP_SV_NODE, xml_text(name),
               _props_block(sv_root_guid, parent_container_guid), T_GVL, T_IFACE,
               timestamp, G_GVL, G_IFACE, G_TEXTDOC,
               _textlines_block(lines, ids),
               parent_container_guid, _path_block(path_parts)))


def folder_entry(name, guid, own_sv_guid, parent_container_guid, path_parts,
                 sv_root_guid, parent_guid=None, timestamp=u"639105476849082988",
                 is_root=False):
    """一个 Folder Entry（TypeGuid = 738bea1e）。

    ⚠ `EmbeddedTypeGuids` 必须是 `<Null/>`。
    ⚠ `Object.StructuredViewGuid` = `own_sv_guid`：若这个 Folder 就是导出根，
      则它等于 `sv_root_guid`；否则是它自己的独立 SV 节点 guid。
    ⚠ 直属 Application 的 Folder，`ParentGuid` 是全零（`parent_guid` 传 None）。
    """
    pg = parent_guid if parent_guid is not None else ZERO_GUID
    return (u'    <Single Type="%s" Method="IArchivable">\n'
            u'      <Single Name="IsRoot" Type="bool">%s</Single>\n'
            u'      <Single Name="MetaObject" Type="%s" Method="IArchivable">\n'
            u'        <Single Name="Guid" Type="System.Guid">%s</Single>\n'
            u'        <Single Name="ParentGuid" Type="System.Guid">%s</Single>\n'
            u'        <Single Name="Name" Type="string">%s</Single>\n'
            u'%s\n'
            u'        <Single Name="TypeGuid" Type="System.Guid">%s</Single>\n'
            u'        <Null Name="EmbeddedTypeGuids" />\n'
            u'        <Single Name="Timestamp" Type="long">%s</Single>\n'
            u'      </Single>\n'
            u'      <Single Name="Object" Type="%s" Method="IArchivable">\n'
            u'        <Single Name="StructuredViewGuid" Type="System.Guid">%s</Single>\n'
            u'      </Single>\n'
            u'      <Single Name="ParentSVNodeGuid" Type="System.Guid">%s</Single>\n'
            u'%s\n'
            u'      <Single Name="Index" Type="int">-1</Single>\n'
            u'    </Single>'
            % (G_ENTRY, u"True" if is_root else u"False",
               G_META, guid, pg, xml_text(name),
               _props_block(sv_root_guid, parent_container_guid), T_FOLDER, timestamp,
               G_FOLDER, own_sv_guid, parent_container_guid,
               _path_block(path_parts)))


def build_export(entries, out_path, sv_root_guid):
    """把若干 Entry 组装成完整 ExportFile 并写文件。"""
    body = u"\n".join(entries)
    xml = (u'<ExportFile>\n'
           u'  <StructuredView Guid="{%s}">\n'
           u'<Single xml:space="preserve" Type="%s" Method="IArchivable">\n'
           u'  <Null Name="Profile" />\n'
           u'  <List2 Name="EntryList">\n'
           u'%s\n'
           u'  </List2>\n'
           u'  <Null Name="ProfileName" />\n'
           u'</Single>  </StructuredView>\n'
           u'</ExportFile>\n' % (sv_root_guid, G_SV, body))
    with io.open(out_path, "w", encoding="utf-8") as f:
        f.write(xml)
    return out_path, len(xml)
