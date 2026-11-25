# -*- coding: utf-8 -*-
"""新建一个 Folder + 若干 GVL 做「全局变量声明」结构验证。

用法：
    python make_gvl_verify.py <输出 native 路径> [文件夹名] [GVL名]

验证点（全部来自 F01_Variable 真实导出的实测规律）：
  · Folder（738bea1e）直属 Application：ParentGuid 全零、ParentSVNodeGuid =
    Application 的 SV 节点、Object.StructuredViewGuid = 自己的 SV 节点
  · GVL（ffbfa93a）：MetaObject.ParentGuid = Application 的 SV 节点（祖父），
    ParentSVNodeGuid / ParentObjects.Value = Folder 的 guid
  · EmbeddedTypeGuids：GVL = Array[a9ed5b7e]，Folder = <Null/>
  · TextLines 里多段 VAR_GLOBAL（含 CONSTANT / PERSISTENT RETAIN /
    RETAIN PERSISTENT 三种写法）
  · 注释里带 `>` `&` 的 XML 转义
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_gvl

FOLDER_NAME = u"F99_GVLVerify"
GVL_NAME = u"GVL_VerifyTest"
GVL_NAME2 = u"GVL_VerifyConst"

PATH_APP = [u"Device", u"PLC 逻辑", u"Application"]

LINES_MAIN = [
    u"VAR_GLOBAL",
    u"\tGv_xEnable\t\t\t\t:BOOL\t:=FALSE;\t\t//使能位",
    u"\tGv_iCount\t\t\t\t:INT\t:=0;\t\t\t//计数 0->100",
    u"\tGv_uiSpeed\t\t\t\t:UINT\t:=1500;\t\t//速度 rpm",
    u"\tGv_rTemp\t\t\t\t:REAL\t:=0.0;\t\t//温度 ℃",
    u"\tGv_sName\t\t\t\t:STRING(80)\t:='GVL_VERIFY';\t//名称",
    u"\tGv_tDelay\t\t\t\t:TIME\t:=T#1S;\t\t//延时",
    u"\tGv_abyBuf\t\t\t\t:ARRAY[0..15] OF BYTE;\t//缓冲区",
    u"END_VAR",
    u"VAR_GLOBAL PERSISTENT RETAIN",
    u"\tGv_xSaved\t\t\t\t:BOOL\t:=TRUE;\t\t//掉电保持",
    u"\tGv_diTotal\t\t\t\t:DINT\t:=0;\t\t\t//累计值",
    u"END_VAR",
    u"VAR_GLOBAL RETAIN PERSISTENT",
    u"\tGv_xRetain2\t\t\t\t:BOOL;\t\t\t\t//保持位（两种顺序都合法）",
    u"END_VAR",
]

LINES_CONST = [
    u"VAR_GLOBAL CONSTANT",
    u"\tGc_uiVerifyNum\t\t\t:UINT\t:=8;\t\t\t//数量",
    u"\tGc_sVersion\t\t\t\t:STRING(20)\t:='V1.0';\t//版本 A>B & C<D",
    u"END_VAR",
]


def main():
    dst = sys.argv[1] if len(sys.argv) > 1 else u"GVL_Verify.native"
    folder = sys.argv[2] if len(sys.argv) > 2 else FOLDER_NAME
    gvl1 = sys.argv[3] if len(sys.argv) > 3 else GVL_NAME
    gvl2 = sys.argv[4] if len(sys.argv) > 4 else GVL_NAME2

    make_gvl.reset_ids(90000)

    folder_guid = make_gvl.new_guid()
    folder_sv = make_gvl.new_guid()
    sv_root = folder_sv            # 这个导出文件的根 SV 就是这个 Folder 自己的 SV

    entries = []
    # 1) Folder 本体（直属 Application）
    entries.append(make_gvl.folder_entry(
        name=folder,
        guid=folder_guid,
        own_sv_guid=folder_sv,
        parent_container_guid=make_gvl.APP_SV_NODE,
        path_parts=PATH_APP,
        sv_root_guid=sv_root,
        parent_guid=None,
        is_root=False))
    # 2) 两个 GVL
    for nm, lines in ((gvl1, LINES_MAIN), (gvl2, LINES_CONST)):
        entries.append(make_gvl.gvl_entry(
            name=nm,
            lines=lines,
            guid=make_gvl.new_guid(),
            parent_container_guid=folder_guid,
            path_parts=PATH_APP + [folder],
            sv_root_guid=sv_root,
            is_root=False))

    make_gvl.build_export(entries, dst, sv_root)
    print(u"folder guid     = %s" % folder_guid)
    print(u"folder sv guid  = %s" % folder_sv)
    print(u"generated -> %s (%d bytes)" % (dst, os.path.getsize(dst)))
    print(u"  %s : %d lines" % (gvl1, len(LINES_MAIN)))
    print(u"  %s : %d lines" % (gvl2, len(LINES_CONST)))


if __name__ == "__main__":
    main()
