# -*- coding: utf-8 -*-
# @py3
"""AxesGroup（运动轴组）对象复制器。

AxesGroup 特点（TypeGuid ad3ae438-9dc8-4473-b82c-f59e508baec4）：
  - 没有 textual_declaration / textual_implementation / TextLines
  - 没有 get_children()（探测返回 []），所有数据在导出 native 的 <Object> 下
  - 因此「翻译」= 只改 MetaObject.Name

Object 结构（2026-11-26 实测，AxesGroup_A1 / AxesGroup_C1）：
    <Object>
      <Id>                      uint，同文件夹内递增（A1=0, C1=1）
      <Type>                    CART_XY（笛卡尔 XY 二轴）
      <AxisMappingCollection>   轴映射列表
        <AxisMappings>
          <AxisGuid>            指向 Device/ETHERCAT_C/ServoXX/AxisXX 的 guid
          <Description>         轴在组内的名字（A1/A2/A3/A4）
          <ZeroingIndex>        int
      <WorkspaceConfig>
        <PositionConfig>        MaxVelocity/MaxAcceleration/MaxDeceleration/MaxJerk/UnitTyp
        <AttitudeConfig>        同上（姿态轴，单位「度」）
      <ReadInputsPouGuid>       ⚠ 轴组内部自动生成的 4 个 POU
      <WriteOutputsPouGuid>     ⚠ 这些 guid 在全工程树里都找不到
      <InitPouGuid>             ⚠ 说明是 IDE 内部对象，不暴露给脚本
      <gvlPouGuid>              ⚠
      <PositionDimensionType>   Metre
      <AttitudeDimensionType>   Degrees
      <UserMasterDimensionType> Position
      ... 机器人学参数（AltitudeHeightL0 / 臂长 L1 L2 / 运动系数 / 基坐标 / 工件坐标 / 工具坐标）
      <CurveType>               T
      <ContinuousPathEnable>    bool
      <SavingsLength> / <ForwardLookingLength> / <ForwardLookingAccuracy>   前瞻
      <AxisSettingEnable>       bool

⚠ 复制时的三个关键点（本脚本实测结论见 references/native-structure.md §33）：
  1) MetaObject.Guid 必须换新 —— 否则导入时与原件冲突
  2) Object.Id 必须换新 —— 同文件夹内不能重复
  3) AxisGuid / 4 个 POU Guid **原样保留**：
     - AxisGuid 指向真实设备轴，保留 = 副本组引用同一批轴（软冗余，可用）
     - 4 个内部 POU Guid 保留后 IDE 会自动为新轴组重建自己的 POU
       实测导入后 POU Guid 被 IDE 改写为新值，不冲突

用法：
    python examples/make_f08_axesgroup_copy.py ipc/f08 ipc/f08_out _F08V
"""
import io
import os
import re
import sys
import uuid

try:
    import xml.etree.ElementTree as ET
except ImportError:
    import elementtree.ElementTree as ET

AXESGROUP_TYPE_GUID = u"ad3ae438-9dc8-4473-b82c-f59e508baec4"

# 这 4 个是轴组内部 POU 引用；实测 IDE 在导入时会重新生成，所以不动
INTERNAL_POU_KEYS = (u"ReadInputsPouGuid", u"WriteOutputsPouGuid",
                     u"InitPouGuid", u"gvlPouGuid")


def U(s):
    try:
        return unicode(s)  # noqa: F821
    except NameError:
        return str(s)


def find_single(root, name, deep=True):
    """按 Name 属性找第一个 <Single>"""
    it = root.iter(u"Single") if deep else root
    for s in it:
        if s.get(u"Name") == name:
            return s
    return None


def find_metaobject(root):
    return find_single(root, u"MetaObject")


def meta_get(mo, key):
    for c in mo:
        if c.get(u"Name") == key:
            return c
    return None


def set_text(el, val):
    if el is None:
        return False
    el.text = U(val)
    return True


def new_guid():
    return U(str(uuid.uuid4())).lower()


def process_axesgroup(native_path, suffix, out_path, new_id=None):
    """复制一个 AxesGroup：改 Name / Guid / Id，其余原样。"""
    t = ET.parse(native_path)
    root = t.getroot()

    mo = find_metaobject(root)
    if mo is None:
        raise RuntimeError(u"MetaObject not found: %s" % native_path)

    tg = meta_get(mo, u"TypeGuid")
    if tg is None or (tg.text or u"").strip() != AXESGROUP_TYPE_GUID:
        raise RuntimeError(u"not an AxesGroup (TypeGuid=%r): %s"
                           % (tg.text if tg is not None else None, native_path))

    # --- 1) Name ---
    name_el = meta_get(mo, u"Name")
    if name_el is None or not (name_el.text or u"").strip():
        raise RuntimeError(u"MetaObject.Name missing: %s" % native_path)
    old_name = name_el.text.strip()
    new_name = old_name if old_name.endswith(suffix) else old_name + suffix
    set_text(name_el, new_name)

    # --- 2) Guid（必须换，否则导入冲突）---
    guid_el = meta_get(mo, u"Guid")
    old_guid = (guid_el.text or u"").strip() if guid_el is not None else u""
    new_guid_val = new_guid()
    set_text(guid_el, new_guid_val)

    # --- 3) Object.Id（同文件夹内不能重复）---
    obj = find_single(root, u"Object")
    old_id = None
    if obj is not None:
        id_el = None
        for c in obj:
            if c.get(u"Name") == u"Id":
                id_el = c
                break
        if id_el is not None:
            old_id = (id_el.text or u"").strip()
            if new_id is not None:
                set_text(id_el, U(new_id))

    t.write(out_path, encoding=u"utf-8", xml_declaration=False)
    return {
        u"old_name": old_name, u"new_name": new_name,
        u"old_guid": old_guid, u"new_guid": new_guid_val,
        u"old_id": old_id, u"new_id": new_id,
    }


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else u"ipc/f08"
    out = sys.argv[2] if len(sys.argv) > 2 else u"ipc/f08_out"
    suffix = sys.argv[3] if len(sys.argv) > 3 else u"_F08V"

    if not os.path.isdir(out):
        os.makedirs(out)

    # 收集源文件（排除探测产物）
    files = []
    for f in sorted(os.listdir(src)):
        if not f.endswith(u".native"):
            continue
        if u"probe" in f:
            continue
        files.append(f)

    if not files:
        print(u"ERROR: no .native in %s" % src)
        return 1

    done = []
    for i, f in enumerate(files):
        p = os.path.join(src, f)
        base = f[:-len(u".native")]
        dst = os.path.join(out, u"%s%s.native" % (base, suffix))
        # Id 顺延：原件 0/1 -> 副本 100/101，避开与原件和其他副本冲突
        r = process_axesgroup(p, suffix, dst, new_id=100 + i)
        done.append(u"%-16s -> %-24s guid %s -> %s  id %s -> %s  (%d bytes)" % (
            r[u"old_name"], r[u"new_name"],
            r[u"old_guid"][:8], r[u"new_guid"][:8],
            r[u"old_id"], r[u"new_id"],
            os.path.getsize(dst)))
        print(done[-1])

    io.open(os.path.join(out, u"_report.txt"), u"w", encoding=u"utf-8").write(
        u"\n".join(done) + u"\n")
    print(u"total: %d" % len(done))
    return 0


if __name__ == u"__main__":
    sys.exit(main())
