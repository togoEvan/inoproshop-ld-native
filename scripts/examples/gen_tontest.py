# -*- coding: utf-8 -*-
# @py3
"""TON 构件最小样本 prg_TonTest（2 网络）。

验证：TON 可以直接挂在 NetworkItems 上（不必进分支），InputItems 只有 IN / PT 两槽，
Instance 是独立操作数容器；输出 Q 接 BOOL 变量、ET 也占一个输出槽。

用法：
    python gen_tontest.py
环境变量：
    LDSKEL  骨架 native（默认指向本机已验证的 14 网络 POU）
    LDOUT   输出路径（默认与脚本同目录的 prg_TonTest.native）
"""
import io, os, sys

HERE = os.path.dirname(os.path.abspath(sys.argv[0]))
sys.path.insert(0, HERE)
import ldgen as L

SKEL = os.environ.get('LDSKEL') or r'D:/plc_mcp/work/stn_edge/prg_StnAutoSeq.native'
OUT = os.environ.get('LDOUT') or os.path.join(HERE, 'prg_TonTest.native')
NAME = u'prg_TonTest'

DECL = [
    u'PROGRAM %s' % NAME,
    u'VAR',
    u'    xEn        : BOOL;   // 使能',
    u'    bTonQ      : BOOL;   // 延时到',
    u'    bDone      : BOOL;   // 结果',
    u'    fbTonTest  : TON;    // 延时框实例',
    u'END_VAR',
    u'',
]

nets = []
nets.append(L.network([L.ton_box(u'fbTonTest', L.contact(u'xEn'), u't#500ms', u'bTonQ')],
                      u'TON 结构试验：xEn 保持 500ms 后 Q 置位'))
nets.append(L.coil_net([L.contact(u'bTonQ')], u'bDone', u'BOOL', u'结果显示'))

f = io.open(SKEL, encoding='utf-8')
try:
    SK = f.read()
finally:
    f.close()
info = L.build_doc(SK, NAME, DECL, nets, OUT)
print('written: %s (%d bytes)' % (info['path'], info['bytes']))
print('networks=%d ids=%d maxId=%d' % (info['networks'], info['ids'], info['max_id']))
print('boxes=%s' % info['boxes'])
f = io.open(OUT, encoding='utf-8')
try:
    s = f.read()
finally:
    f.close()
print('TON boxes =', s.count(u'BoxType" Type="string">TON'))
print('FunctionBlock CallType =', s.count(u'>FunctionBlock<'))
print('netitem =', s.count(u'{9873c309'))
