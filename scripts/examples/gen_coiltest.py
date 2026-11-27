# -*- coding: utf-8 -*-
# @py3
"""多线圈梯级最小样本 prg_CoilTest（2 网络）。

验证两件事：
1. 一个 NETITEM 的 OutputItems 里可以挂多个线圈（S / R / 普通并存）；
2. 线圈载体必须是 NETITEM，不能是 AND 框（挂框上导入接受、编译 0 错误、IDE 只画空方块）。

用法：
    python gen_coiltest.py
环境变量：
    LDSKEL  骨架 native
    LDOUT   输出路径（默认与脚本同目录的 prg_CoilTest.native）
"""
import io, os, sys

HERE = os.path.dirname(os.path.abspath(sys.argv[0]))
sys.path.insert(0, HERE)
import ldgen as G

SKEL = os.environ.get('LDSKEL') or r'D:/plc_mcp/work/stn_edge/prg_StnAutoSeq.native'
OUT = os.environ.get('LDOUT') or os.path.join(HERE, 'prg_CoilTest.native')
NAME = u'prg_CoilTest'

DECL = [
    u'PROGRAM %s' % NAME,
    u'VAR',
    u'    xIn  : BOOL;   // 条件',
    u'    xA   : BOOL;   // 置位线圈目标',
    u'    xB   : BOOL;   // 复位线圈目标',
    u'    xC   : BOOL;   // 普通线圈目标',
    u'END_VAR',
    u'',
]

nets = []
nets.append(G.network([G.netitem(G.contact(u'xIn'),
                                   [G.set_coil(u'xA'), G.reset_coil(u'xB'), G.coil(u'xC')])],
                      u'多线圈梯级：一个 NETITEM 挂 S / R / 普通三个线圈'))
nets.append(G.network([G.netitem(G.contact(u'xIn', neg=True), [G.reset_coil(u'xC')])],
                      u'单线圈梯级：常闭条件驱动复位线圈'))

f = io.open(SKEL, encoding='utf-8')
try:
    SK = f.read()
finally:
    f.close()
info = G.build_doc(SK, NAME, DECL, nets, OUT)
print('written: %s (%d bytes)' % (info['path'], info['bytes']))
print('networks=%d ids=%d maxId=%d' % (info['networks'], info['ids'], info['max_id']))
print('boxes=%s' % info['boxes'])
f = io.open(OUT, encoding='utf-8')
try:
    s = f.read()
finally:
    f.close()
print('netitem =', s.count(u'{9873c309'))
print('IsCoil True =', s.count(u'<Single Name="IsCoil" Type="bool">True'))
print('S coils =', s.count(u'<Single Name="Flags" Type="int">2</Single>'))
print('R coils =', s.count(u'<Single Name="Flags" Type="int">3</Single>'))
