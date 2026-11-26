# -*- coding: utf-8 -*-
# @py3
"""CAM（电子凸轮）对象复制器。

CAM 对象特点（TypeGuid fea841a8-cb28-421c-8d22-c7226c528b66）：
  - 没有 textual_declaration / textual_implementation
  - 没有 TextLines，全部数据是二进制式的结构化数值：
    Dimension(dMasterStart/End, dSlaveStart/End) / Periodic / Period
    / Points(List of {X,Y,V,A,J,XEditable,YEditable,VEditable,AEditable,JEditable})
    / 段列表（2026-11-26 实测校正，旧版此处把两个 Guid 写反了）：
        直线        {7ede90d3-c635-4970-9884-6cb82027dc11}  p0, p1
        五次多项式  {3bfb4cba-336c-4ed3-b189-88789dd9592e}  p0..p5
        控制点      {33af5b4b-b53e-4699-8a38-5b974f57f906}  X/Y/V/A/J + 5 个 Editable
  - 因此「翻译」= 只改 MetaObject.Name（+ 可选的 Guid 重置）
  - 不存在跨对象引用（CAM 不引用 POU，POU 引用 CAM 时才需要改）

⚠ 若要改曲线内容（不只是改名），见 examples/make_cam1_curve.py 与
  references/native-structure.md §32，两条硬规则：
    1) 直线段 y = p0 + p1*u，p1 是**段内增量**（y1-y0），不是终点绝对值
    2) 分度凸轮必须 Periodic=False（y(360) != y(0)）

用法：
  python examples/make_f07_cam_copy.py ipc/f07 ipc/f07_out _F07V
"""
import io
import os
import sys
import xml.etree.ElementTree as ET

CAM_TYPE_GUID = u"fea841a8-cb28-421c-8d22-c7226c528b66"


def U(s):
    try:
        return unicode(s)  # noqa: F821
    except NameError:
        return str(s)


def find_metaobject(root):
    for s in root.iter(u"Single"):
        if s.get(u"Name") == u"MetaObject":
            return s
    return None


def meta_get(mo, key):
    for c in mo:
        if c.get(u"Name") == key:
            return c
    return None


def process_cam(native_path, suffix, out_path):
    """复制一个 CAM 对象：只改 MetaObject.Name。"""
    t = ET.parse(native_path)
    root = t.getroot()

    mo = find_metaobject(root)
    if mo is None:
        raise RuntimeError(u"MetaObject not found in %s" % native_path)

    tg = meta_get(mo, u"TypeGuid")
    if tg is None or (tg.text or u"").strip() != CAM_TYPE_GUID:
        raise RuntimeError(u"not a CAM object (TypeGuid=%r): %s"
                           % (tg.text if tg is not None else None, native_path))

    name_el = meta_get(mo, u"Name")
    if name_el is None or not (name_el.text or u"").strip():
        raise RuntimeError(u"MetaObject.Name missing: %s" % native_path)
    old = name_el.text.strip()
    new = old + suffix if not old.endswith(suffix) else old
    name_el.text = new

    t.write(out_path, encoding=u"utf-8", xml_declaration=False)
    return old, new


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else u"ipc/f07"
    out = sys.argv[2] if len(sys.argv) > 2 else u"ipc/f07_out"
    suffix = sys.argv[3] if len(sys.argv) > 3 else u"_F07V"

    if not os.path.isdir(out):
        os.makedirs(out)

    done = []
    for f in sorted(os.listdir(src)):
        p = os.path.join(src, f)
        if not os.path.isfile(p) or not f.endswith(u"_folder.native"):
            continue
        base = f[:-len(u"_folder.native")]
        dst = os.path.join(out, u"%s%s.native" % (base, suffix))
        old, new = process_cam(p, suffix, dst)
        done.append(u"%s -> %s (%d bytes)"
                    % (old, new, os.path.getsize(dst)))
        print(done[-1])

    if not done:
        print(u"ERROR: no CAM object processed")
        return 1
    io.open(os.path.join(out, u"_report.txt"), u"w", encoding=u"utf-8").write(
        u"\n".join(done) + u"\n")
    print(u"total: %d" % len(done))
    return 0


if __name__ == u"__main__":
    sys.exit(main())
