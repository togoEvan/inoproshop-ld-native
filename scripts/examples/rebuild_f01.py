# -*- coding: utf-8 -*-
# @py3
"""把 F01_Variable 文件夹「重新写一遍」：读原始导出 -> 用 make_gvl 生成器重建
-> 逐字段比对 -> 输出可导入的 native。

用法：
    python rebuild_f01.py <原始导出> <输出 native>

设计要点：
  · **不手抄任何声明**，全部从原始导出里读 TextLines 原文（保留 tab/空格）
  · GUID 沿用原始值（Folder/各 GVL 的 guid、时间戳），保证「重写」后工程里
    的对象身份不变，其它 POU 对 GVL 变量的引用不受影响
  · 生成完立刻做「自比对」：把生成结果重新解析成 {name: (guid, parent,
    parent_sv, path, lines)} 与原始导出对比，任何一处不同就报错退出
"""
import io
import os
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_gvl


def cn(el, name):
    if el is None:
        return None
    for c in el:
        if c.get("Name") == name:
            return c
    return None


def txt(el):
    return (el.text or "") if el is not None else u""


def read_export(path):
    """把导出文件解析成 [{name, type_guid, guid, parent_guid, parent_sv,
    sv_guid, path, timestamp, lines}]，按出现顺序。"""
    root = ET.parse(path).getroot()
    sv = root.find("StructuredView")
    sv_root_guid = (sv.get("Guid") or "").strip("{}")
    ents = list(sv.find("Single").find("List2"))
    out = []
    for e in ents:
        m = cn(e, "MetaObject")
        obj = cn(e, "Object")
        rec = {
            "name": txt(cn(m, "Name")).strip(),
            "type_guid": txt(cn(m, "TypeGuid")).strip(),
            "guid": txt(cn(m, "Guid")).strip(),
            "parent_guid": txt(cn(m, "ParentGuid")).strip(),
            "parent_sv": txt(cn(e, "ParentSVNodeGuid")).strip(),
            "timestamp": txt(cn(m, "Timestamp")).strip(),
            "is_root": (txt(cn(e, "IsRoot")).strip().lower() == u"true"),
            "path": [(x.text or "") for x in cn(e, "Path")],
            "sv_guid": None,
            "lines": None,
            "ids": None,
        }
        svg = cn(obj, "StructuredViewGuid")
        if svg is not None:
            rec["sv_guid"] = txt(svg).strip()
        iface = cn(obj, "Interface")
        if iface is not None:
            td = cn(iface, "TextDocument")
            if td is not None:
                rec["lines"] = [txt(cn(s, "Text")) for s in cn(td, "TextLines")]
                rec["ids"] = [int(txt(cn(s, "Id"))) for s in cn(td, "TextLines")]
        out.append(rec)
    return sv_root_guid, out


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    src, dst = sys.argv[1], sys.argv[2]

    sv_root_guid, orig = read_export(src)
    print(u"source: %s" % src)
    print(u"  sv_root_guid = %s" % sv_root_guid)
    print(u"  entries      = %d" % len(orig))

    folder = orig[0]
    if folder["type_guid"].lower() != make_gvl.G_FOLDER.strip("{}"):
        raise SystemExit(u"第一个 entry 不是 Folder：%s" % folder["type_guid"])

    make_gvl.reset_ids(5000)
    entries = []
    # 1) Folder 本体：ParentGuid 全零，own_sv = 导出根 SV
    entries.append(make_gvl.folder_entry(
        name=folder["name"],
        guid=folder["guid"],
        own_sv_guid=sv_root_guid,
        parent_container_guid=folder["parent_sv"],
        path_parts=folder["path"],
        sv_root_guid=sv_root_guid,
        parent_guid=None,
        is_root=folder["is_root"],
        timestamp=folder["timestamp"]))
    # 2) 各 GVL
    for g in orig[1:]:
        if g["type_guid"].lower() != make_gvl.G_GVL.strip("{}"):
            print(u"  [skip] %s 不是 GVL（%s）" % (g["name"], g["type_guid"]))
            continue
        entries.append(make_gvl.gvl_entry(
            name=g["name"],
            lines=g["lines"],
            guid=g["guid"],
            parent_container_guid=folder["guid"],
            path_parts=g["path"],
            sv_root_guid=sv_root_guid,
            timestamp=g["timestamp"],
            is_root=g["is_root"],
            ids=g["ids"]))
        print(u"  + GVL %-18s lines=%-4d guid=%s" % (g["name"], len(g["lines"]), g["guid"]))

    make_gvl.build_export(entries, dst, sv_root_guid)
    print(u"\ngenerated -> %s (%d bytes)" % (dst, os.path.getsize(dst)))

    # ---------- 自比对 ----------
    sv2, gen = read_export(dst)
    print(u"\n=== self-check ===")
    ok = True
    if sv2 != sv_root_guid:
        print(u"  FAIL sv_root_guid %s != %s" % (sv2, sv_root_guid))
        ok = False
    if len(gen) != len(orig):
        print(u"  FAIL entry count %d != %d" % (len(gen), len(orig)))
        ok = False
    for a, b in zip(orig, gen):
        for k in ("name", "type_guid", "guid", "parent_guid", "parent_sv",
                  "timestamp", "is_root", "path", "sv_guid", "lines", "ids"):
            if a[k] != b[k]:
                ok = False
                if k == "lines":
                    la, lb = a[k] or [], b[k] or []
                    print(u"  FAIL %s.%s 行数 %d != %d" % (a["name"], k, len(la), len(lb)))
                    for i in range(min(len(la), len(lb))):
                        if la[i] != lb[i]:
                            print(u"       line %d\n         orig=%r\n         gen =%r"
                                  % (i, la[i], lb[i]))
                            break
                else:
                    print(u"  FAIL %s.%s\n       orig=%r\n       gen =%r"
                          % (a["name"], k, a[k], b[k]))
    total_lines = sum(len(g["lines"] or []) for g in orig)
    print(u"  entries=%d  total_lines=%d  -> %s"
          % (len(orig), total_lines, u"全部一致 OK" if ok else u"有差异 FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
