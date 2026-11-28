# @py3
# -*- coding: utf-8 -*-
"""把工站流程写进工站自动 POU 的动作槽 A04_（槽位下标 4）。

依据（2026-11-28 用户纠正，替代「新建 PROGRAM 再挂任务」的旧写法）：
  宿主 STN1_02_Auto 的 ST 体里已经无条件调用 A00_上料移栽() ... A09_()，
  动作槽天然被调用，写流程 = 往动作里的空「流程」网络补步序，不需要任何接线。
动作没有自己的声明区（ActionEntry，无 Interface/VAR），只能用宿主 POU 与全局符号。

用法：
  python scripts/examples/gen_a04.py            # 输出 prg_A04_slot4.native 到本目录
  LDTPL=<A04_ 导出> LDOUT=<输出路径> python scripts/examples/gen_a04.py
"""
import io, os, re, sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(sys.argv[0]))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import ldgen as L

TPL_A04 = os.environ.get("LDTPL") or os.path.join(ROOT, "assets", "natives", "a04-action-skeleton.native")
TPL_CYL = os.path.join(ROOT, "assets", "natives", "a00-fragments", "fc_cylinderexe.xml")
TPL_AXIS = os.path.join(ROOT, "assets", "natives", "a00-fragments", "fc_axisabsgo.xml")
OUT = os.environ.get("LDOUT") or os.path.join(HERE, "prg_A04_slot4.native")

G_NET = u'<Single Type="{d9a99d73-b633-47db-b876-a752acb25871}"'


def fc_box(tpl_path, operands):
    """取一个功能框片段，按文档顺序替换所有 Single Name="Operand" Type="string" 的文本。"""
    root = ET.fromstring(io.open(tpl_path, "r", encoding="utf-8").read().strip())
    els = [e for e in root.iter()
           if e.tag == "Single" and e.get("Name") == "Operand" and e.get("Type") == "string"]
    for el, val in zip(els, operands):
        el.text = val
    return ET.tostring(root, encoding="unicode")


def cyl(name, val):
    return fc_box(TPL_CYL, [name, val])


def axis(name, pos):
    return fc_box(TPL_AXIS, [name, pos, u"0"])


def cdone(c):
    return L.contact(u"G_astCylinder[%s].xDone" % c)


def adone(a):
    return L.contact(u"G_astAxis[%s].o_xAbsDone" % a)


# 工站 1（STNControl[1]）的第 4 号动作槽 = 数组下标 4
STN = u"STNControl[1]."
L.AUTOING = STN + u"xAutoing"
L.STEP = STN + u"aiAutoStep[4]"
L.BUF = STN + u"aiAutoStepBuffer[4]"
L.DESC = STN + u"awstrAutoDescription[4]"

AX0 = u"A0_上料移栽直线电机轴"
AX1 = u"A1_上料移栽R轴"
C0 = u"C0_上料移载夹紧气缸"
C1 = u"C1_上料移载升降气缸"
C2 = u"C2_上料移载伸出气缸"

nets = []
nets.append(L.note_net(u"*工位4：上料机取料 -> 擦拭A1平台1放料*"))
# 取料段 1000-1070
nets.append(L.step_net(1000, u"C0_上料移载夹紧气缸复位、A0_上料移栽直线电机轴去取料位",
                       [cyl(C0, u"0"), axis(AX0, u"A0P_上料机取料位")], 1010,
                       L.and_box([cdone(C0), adone(AX0)])))
nets.append(L.step_net(1010, u"A1_上料移栽R轴去取料位",
                       [axis(AX1, u"A1P_上料机取料位")], 1020, adone(AX1)))
nets.append(L.step_net(1020, u"等待上料机请求取料", [], 1030,
                       done_contact=L.contact(u"G_xS1上料机请求取料")))
nets.append(L.step_net(1030, u"C2_上料移载伸出气缸伸出", [cyl(C2, u"1")], 1040, cdone(C2)))
nets.append(L.step_net(1040, u"C1_上料移载升降气缸伸出", [cyl(C1, u"1")], 1050, cdone(C1)))
nets.append(L.step_net(1050, u"C0_上料移载夹紧气缸伸出（抓料）", [cyl(C0, u"1")], 1060, cdone(C0)))
nets.append(L.step_net(1060, u"C1_上料移载升降气缸复位", [cyl(C1, u"0")], 1070, cdone(C1)))
nets.append(L.step_net(1070, u"C2_上料移载伸出气缸缩回", [cyl(C2, u"0")], 1080, cdone(C2)))

# 放料段 1080-1150
nets.append(L.step_net(1080, u"A0/A1 去擦拭A1平台1放料位",
                       [axis(AX0, u"A0P_擦拭A1放料位"), axis(AX1, u"A1P_擦拭A1放料位")], 1090,
                       L.and_box([adone(AX0), adone(AX1)])))
nets.append(L.step_net(1090, u"等待擦拭A1平台1请求放料", [], 1100,
                       done_contact=L.contact(u"G_xS2擦拭A1平台1请求上料移栽放料")))
nets.append(L.step_net(1100, u"C2_上料移载伸出气缸伸出", [cyl(C2, u"1")], 1110, cdone(C2)))
nets.append(L.step_net(1110, u"C1_上料移载升降气缸伸出", [cyl(C1, u"1")], 1120, cdone(C1)))
nets.append(L.step_net(1120, u"C0_上料移载夹紧气缸复位（放料）", [cyl(C0, u"0")], 1130, cdone(C0)))
nets.append(L.step_net(1130, u"C1_上料移载升降气缸复位", [cyl(C1, u"0")], 1140, cdone(C1)))
nets.append(L.step_net(1140, u"C2_上料移载伸出气缸缩回", [cyl(C2, u"0")], 1150, cdone(C2)))
nets.append(L.step_net2(1150, u"本工位完成，回工位判断", [], 100, unconditional=True))

# ── 拼进模板：保留前 5 个网络（骨架），丢弃原空"流程"与占位注释网络 ──
s = io.open(TPL_A04, "r", encoding="utf-8").read()
key = u'<List2 Name="NetworkList">'
i = s.find(key)
if i < 0:
    raise RuntimeError("template: NetworkList not found")
inner_start = i + len(key)
j = L.find_list2_end(s, i)
inner_end = j - len(u'</List2>')
inner = s[inner_start:inner_end]
starts = [m.start() for m in re.finditer(re.escape(G_NET), inner)]
if len(starts) < 6:
    raise RuntimeError("template: networks = %d (need >=6)" % len(starts))
kept = []
for k, st in enumerate(starts):
    en = starts[k + 1] if k + 1 < len(starts) else len(inner)
    kept.append(inner[st:en])
kept = kept[:5]

s2 = s[:inner_start] + u"\n" + u"\n".join(kept + nets) + u"\n  " + s[inner_end:]
s2 = L.renumber(s2, [0])
ids = [int(x.group(1)) for x in re.finditer(r'<Single Name="Id" Type="long">(\d+)</Single>', s2)]
dup = [v for v in set(ids) if ids.count(v) > 1]
if dup:
    raise RuntimeError("duplicate Id: %s" % dup[:5])
uid = max(ids) + 1
s2 = re.sub(r'<Single Name="UniqueIdGenerator" Type="string">\d+</Single>',
            u'<Single Name="UniqueIdGenerator" Type="string">%d</Single>' % uid, s2, count=1)

d = os.path.dirname(OUT)
if not os.path.isdir(d):
    os.makedirs(d)
f = io.open(OUT, "w", encoding="utf-8", newline=u"")
try:
    f.write(s2)
finally:
    f.close()

stat = {
    "out": OUT,
    "bytes": len(s2.encode("utf-8")),
    "networks": len(kept) + len(nets),
    "ids": len(ids),
    "max_id": max(ids),
    "AND": len(re.findall(r'Name="BoxType" Type="string">AND<', s2)),
    "MOVE": len(re.findall(r'Name="BoxType" Type="string">MOVE<', s2)),
    "EQ": len(re.findall(r'Name="BoxType" Type="string">EQ<', s2)),
    "branch": len(re.findall(r'Type="\{827b9ec2', s2)),
}
print(stat)