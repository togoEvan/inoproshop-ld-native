# -*- coding: utf-8 -*-
"""按规划曲线生成 Cam1 的 CAM native。

规划曲线（停-升-停，3-4-5 五次多项式）：
    段1 直线        x[  0 -> 120]  y 0 -> 0
    段2 五次多项式  x[120 -> 240]  y 0 -> H
    段3 直线        x[240 -> 360]  y H -> H

输入：scripts/ipc/f07/Cam0_folder.native（模板，取其外壳/元数据）
输出：scripts/ipc/f07_out/Cam1_F07V.native

只改：
    MetaObject.Name        -> Cam1_F07V
    MetaObject.Guid        -> 新 guid（避免与 Cam0 冲突）
    Object.Dimension       -> dMaster 0..360, dSlave 0..H
    Object.Period / Points / Segments / Periodic
不动：TappetTracks / Properties / ContinuityRequirements / 外层 sv 结构

⚠⚠ 两条硬规则（2026-11-26 实测，违反必报 Cam 分类错误）⚠⚠

  1) 直线段 y = p0 + p1*u   （u = 段内归一化位置 0..1）
       p0 = 起点 y
       p1 = **y1 - y0（段内增量，不是终点绝对值！）**
     由模板 Cam0 三段实测反解确认：
       段1 p0=0  p1=0   -> y(0)=0  y(1)=0   cp 0->0    ✓
       段3 p0=20 p1=80  -> y(0)=20 y(1)=100 cp 20->100 ✓
       段5 p0=0  p1=0   -> y(0)=0  y(1)=0   cp 0->0    ✓
     写成 p0=y0/p1=y1 会让停歇段斜率变成 y1，与相邻多项式段的零速度冲突，
     报「在点 (x/y) 的连续性要求不能填充 速度」。
     自检口诀：p0 == cp0.Y 且 p0+p1 == cp1.Y

  2) 分度凸轮必须 Periodic=False
     分度凸轮每周期从轴累进 H（y(360) = y(0) + H），周期性假设不成立。
     沿用模板的 Periodic=True 会报
       「在点 (0/0) 的连续性要求不能填充 位置」+「不能填充 速度」。
     自检：y(360) - y(0) != 0 就必须 False。摆动凸轮（回原点）才用 True。

  另注：Cam 子对象无法用脚本删除（remove/replace 均失败），改曲线只能同名覆盖导入。
"""
import io
import os
import re
import sys
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
IPC = os.path.normpath(os.path.join(HERE, u"..", u"ipc"))
SRC = os.path.join(IPC, u"f07", u"Cam0_folder.native")
OUTDIR = os.path.join(IPC, u"f07_out")
OUT = os.path.join(OUTDIR, u"Cam1_F07V.native")

# ---------------- 规划参数（与 gen_cam_curve.py 保持一致）----------------
N_STATION = 8
H = 360.0 / N_STATION          # 45.0
BETA = 120.0
X0 = (360.0 - BETA) / 2.0      # 120.0
X1 = X0 + BETA                 # 240.0

LINE_GUID = u"{7ede90d3-c635-4970-9884-6cb82027dc11}"
POLY_GUID = u"{3bfb4cba-336c-4ed3-b189-88789dd9592e}"
POINT_GUID = u"{33af5b4b-b53e-4699-8a38-5b974f57f906}"

# 五次多项式 y = p0 + p1*u + ... + p5*u^5（u 归一到段内）
P = [0.0, 0.0, 0.0, 10.0 * H, -15.0 * H, 6.0 * H]


def fnum(v):
    """double 文本：整数值不带小数点，其余保留 12 位有效并去尾零"""
    if v == int(v):
        return u"%d" % int(v)
    s = (u"%.12f" % v).rstrip(u"0").rstrip(u".")
    return s


def pt_fields(indent, x, y, v, a, j, xedit, yedit):
    """只输出控制点的 10 个字段（不带外层 <Single Type=...> 包装）。
    用于 Points 列表内的元素、以及段内 cp0/cp1 的内容。"""
    sp = u" " * indent
    return (u"%s<Single Name=\"X\" Type=\"double\">%s</Single>\n"
            u"%s<Single Name=\"Y\" Type=\"double\">%s</Single>\n"
            u"%s<Single Name=\"V\" Type=\"double\">%s</Single>\n"
            u"%s<Single Name=\"A\" Type=\"double\">%s</Single>\n"
            u"%s<Single Name=\"J\" Type=\"double\">%s</Single>\n"
            u"%s<Single Name=\"XEditable\" Type=\"bool\">%s</Single>\n"
            u"%s<Single Name=\"YEditable\" Type=\"bool\">%s</Single>\n"
            u"%s<Single Name=\"VEditable\" Type=\"bool\">False</Single>\n"
            u"%s<Single Name=\"AEditable\" Type=\"bool\">False</Single>\n"
            u"%s<Single Name=\"JEditable\" Type=\"bool\">False</Single>"
            % (sp, fnum(x), sp, fnum(y), sp, fnum(v), sp, fnum(a), sp, fnum(j),
               sp, xedit, sp, yedit, sp, sp, sp))


def pt_xml(indent, x, y, v, a, j, xedit, yedit):
    """Points 列表内的一个控制点（带 <Single Type={33af5b4b}> 包装）"""
    sp = u" " * indent
    return (u"%s<Single Type=\"%s\" Method=\"IArchivable\">\n%s\n%s</Single>"
            % (sp, POINT_GUID, pt_fields(indent + 2, x, y, v, a, j, xedit, yedit), sp))


def _cp_block(indent, cname, cp):
    """段内 cp0/cp1：<Single Name="cpN" Type="{33af5b4b}"> 直接含 10 字段"""
    sp = u" " * indent
    return (u"%s<Single Name=\"%s\" Type=\"%s\" Method=\"IArchivable\">\n%s\n%s</Single>\n"
            % (sp, cname, POINT_GUID, pt_fields(indent + 2, *cp), sp))


def seg_line_xml(indent, y0, y1, cp0, cp1):
    """直线段。

    【关键】直线段的 y 表达式是  y = p0 + p1*u  （u = 段内归一化位置 0..1）
      p0 = 起点 y
      p1 = y1 - y0   （段内增量，不是终点绝对值！）
    由 Cam0 实测验证：
      段1 p0=0  p1=0   -> y(0)=0  y(1)=0   cp 0->0    ✓
      段3 p0=20 p1=80  -> y(0)=20 y(1)=100 cp 20->100 ✓
      段5 p0=0  p1=0   -> y(0)=0  y(1)=0   cp 0->0    ✓
    写成 p0=y0, p1=y1 会让停歇段斜率变成 y1，与相邻多项式段的零速度冲突，
    IDE 报「在点 (x/y) 的连续性要求不能填充 速度」。
    """
    sp = u" " * indent
    sp2 = u" " * (indent + 2)
    body = (u"%s<Single Type=\"%s\" Method=\"IArchivable\">\n"
            u"%s<Single Name=\"p0\" Type=\"double\">%s</Single>\n"
            u"%s<Single Name=\"p1\" Type=\"double\">%s</Single>\n"
            % (sp, LINE_GUID, sp2, fnum(y0), sp2, fnum(y1 - y0)))
    body += _cp_block(indent + 2, u"cp0", cp0)
    body += _cp_block(indent + 2, u"cp1", cp1)
    body += sp + u"</Single>"
    return body


def seg_poly_xml(indent, cp0, cp1):
    """五次多项式段：p0..p5 + cp0/cp1"""
    sp = u" " * indent
    sp2 = u" " * (indent + 2)
    body = u"%s<Single Type=\"%s\" Method=\"IArchivable\">\n" % (sp, POLY_GUID)
    for k in range(6):
        body += (u"%s<Single Name=\"p%d\" Type=\"double\">%s</Single>\n"
                 % (sp2, k, fnum(P[k])))
    body += _cp_block(indent + 2, u"cp0", cp0)
    body += _cp_block(indent + 2, u"cp1", cp1)
    body += sp + u"</Single>"
    return body


def build_points(indent):
    sp = u" " * indent
    sp2 = u" " * (indent + 2)
    # (x, y, v, a, j, XEditable, YEditable)
    pts = [
        (0.0, 0.0, 0.0, 0.0, 0.0, u"False", u"True"),
        (X0, 0.0, 0.0, 0.0, 0.0, u"True", u"True"),
        (X1, H, 0.0, 0.0, 0.0, u"True", u"True"),
        (360.0, H, 0.0, 0.0, 0.0, u"False", u"True"),
    ]
    out = [u"%s<List Name=\"Points\" Type=\"System.Collections.ArrayList\">" % sp]
    for p in pts:
        out.append(pt_xml(indent + 2, *p))
    out.append(sp + u"</List>")
    return u"\n".join(out)


def build_segments(indent):
    sp = u" " * indent
    out = [u"%s<List Name=\"Segments\" Type=\"System.Collections.ArrayList\">" % sp]

    # 段1 直线 0->X0，y 0->0
    cp0 = (0.0, 0.0, 0.0, 0.0, 0.0, u"False", u"True")
    cp1 = (X0, 0.0, 0.0, 0.0, 0.0, u"True", u"True")
    out.append(seg_line_xml(indent + 2, 0.0, 0.0, cp0, cp1))

    # 段2 五次多项式 X0->X1，y 0->H
    cp0 = (X0, 0.0, 0.0, 0.0, 0.0, u"True", u"True")
    cp1 = (X1, H, 0.0, 0.0, 0.0, u"True", u"True")
    out.append(seg_poly_xml(indent + 2, cp0, cp1))

    # 段3 直线 X1->360，y H->H
    cp0 = (X1, H, 0.0, 0.0, 0.0, u"True", u"True")
    cp1 = (360.0, H, 0.0, 0.0, 0.0, u"False", u"True")
    out.append(seg_line_xml(indent + 2, H, H, cp0, cp1))

    out.append(sp + u"</List>")
    return u"\n".join(out)


def replace_list(text, name, new_block):
    """替换 <List Name="xxx" ...> ... </List>（同名只出现一次）"""
    pat = re.compile(r'[ \t]*<List Name="%s" Type="System\.Collections\.ArrayList">.*?</List>'
                     % name, re.S)
    m = pat.search(text)
    if not m:
        raise RuntimeError(u"list %s not found" % name)
    return text[:m.start()] + new_block + text[m.end():]


def main():
    if not os.path.isfile(SRC):
        print(u"ERROR: template not found: %s" % SRC)
        return 1
    raw = io.open(SRC, "r", encoding="utf-8").read()

    # 1) MetaObject.Name
    m = re.search(r'(<Single Name="MetaObject"[^>]*>\s*(?:<[^>]+>[^<]*</[^>]+>\s*)*?'
                  r'<Single Name="Guid" Type="System\.Guid">)([^<]*)(</Single>\s*'
                  r'<Single Name="ParentGuid" Type="System\.Guid">)([^<]*)(</Single>\s*'
                  r'<Single Name="Name" Type="string">)([^<]*)', raw, re.S)
    if not m:
        print(u"ERROR: MetaObject block not matched")
        return 1
    raw = raw[:m.start(2)] + str(uuid.uuid4()) + raw[m.end(2):]
    # 重新定位（长度已变）
    m2 = re.search(r'(<Single Name="MetaObject"[^>]*>.*?<Single Name="Name" Type="string">)([^<]*)(</Single>)',
                   raw, re.S)
    if not m2:
        print(u"ERROR: MetaObject.Name not matched")
        return 1
    old_name = m2.group(2)
    raw = raw[:m2.start(2)] + u"Cam1_F07V" + raw[m2.end(2):]
    print(u"MetaObject.Name: %s -> Cam1_F07V" % old_name)

    # 2) Dimension
    dim_pat = re.compile(
        r'(<Single Name="Dimension" Type="\{d33a766f-2682-46e4-9246-c08c4c59ed7e\}" Method="IArchivable">\s*)'
        r'<Single Name="dMasterStart" Type="double">[^<]*</Single>\s*'
        r'<Single Name="dMasterEnd" Type="double">[^<]*</Single>\s*'
        r'<Single Name="dSlaveStart" Type="double">[^<]*</Single>\s*'
        r'<Single Name="dSlaveEnd" Type="double">[^<]*</Single>', re.S)
    ind = u" " * 10
    dim_new = (u'<Single Name="dMasterStart" Type="double">0</Single>\n'
               + ind + u'<Single Name="dMasterEnd" Type="double">360</Single>\n'
               + ind + u'<Single Name="dSlaveStart" Type="double">0</Single>\n'
               + ind + u'<Single Name="dSlaveEnd" Type="double">%s</Single>' % fnum(H))
    raw, n = dim_pat.subn(lambda mm: mm.group(1) + dim_new, raw, count=1)
    print(u"Dimension replaced: %d" % n)

    # 3) Points / Segments
    raw = replace_list(raw, u"Points", build_points(8))
    print(u"Points replaced")
    raw = replace_list(raw, u"Segments", build_segments(8))
    print(u"Segments replaced")

    # 4) Periodic 必须改 False
    #    分度凸轮每周期从轴前进 H（0 -> 45），y(360) != y(0)，
    #    Periodic=True 会让 IDE 报「(0/0) 连续性要求不能填充 位置/速度」。
    per_pat = re.compile(r'(<Single Name="Periodic" Type="bool">)([^<]*)(</Single>)')
    raw, np_ = per_pat.subn(lambda mm: mm.group(1) + u"False" + mm.group(3), raw, count=1)
    print(u"Periodic -> False (%d)" % np_)

    if not os.path.isdir(OUTDIR):
        os.makedirs(OUTDIR)
    io.open(OUT, "w", encoding="utf-8").write(raw)
    print(u"written: %s (%d bytes)" % (OUT, len(raw.encode("utf-8"))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
