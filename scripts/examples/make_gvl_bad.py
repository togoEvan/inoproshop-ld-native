# -*- coding: utf-8 -*-
# @py3
"""负样本：一个声明有语法错误的 GVL，用来证明「导入后读预编译」真的能抓到 GVL 错误。

用法：python make_gvl_bad.py <输出>
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_gvl

PATH_APP = [u"Device", u"PLC 逻辑", u"Application"]

LINES = [
    u"VAR_GLOBAL",
    u"\tGv_badOne\t:BOOL\t:= ;\t\t//故意语法错误",
    u"END_VAR",
]


def main():
    dst = sys.argv[1] if len(sys.argv) > 1 else u"GVL_Bad.native"
    make_gvl.reset_ids(95000)
    sv = make_gvl.new_guid()
    entries = [make_gvl.gvl_entry(
        name=u"GVL_BadTest",
        lines=LINES,
        guid=make_gvl.new_guid(),
        parent_container_guid=make_gvl.APP_SV_NODE,
        path_parts=PATH_APP,
        sv_root_guid=sv,
        is_root=False)]
    make_gvl.build_export(entries, dst, sv)
    print(u"generated -> %s (%d bytes)" % (dst, os.path.getsize(dst)))


if __name__ == "__main__":
    main()
