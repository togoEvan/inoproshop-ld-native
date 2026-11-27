# -*- coding: utf-8 -*-
# @py3
"""模式卡 02 验证样本：prg_FlowDemo v2 —— 完整工站流程（35 网络）。

用户 2026-11-27 两条规范：
  1) BOOL 量一律用线圈（普通 ( ) / 置位 (S) / 复位 (R)），禁用 MOVE；MOVE 只用于 INT/WSTRING
  2) 每条路末尾必须是线圈或功能框，不许出现只有连接器的空梯级

步序 0→10→15→20→25→30→40→(50|60)→…→90→0，含：
  · 三个到位超时（TON 各 3s，独立实例，单独成网络每周期执行）
  · 三个保持延时（TON 500/300/500ms）
  · 良品/不良双路径（ADD 的 EN 边上沿，各 +1）
  · 99 报警步（置位线圈 xAlarm + iErrCode，复位回 0）
  · 手动/安全链中断（最高优先级：4 个网络撤 7 个输出 + 清步序）

用法：python gen_flow_ld.py  → 在当前目录生成 prg_FlowDemo.native
      LDSKEL=<骨架 native> LDOUT=<输出路径> 可覆盖
"""
import io, os, sys

HERE = os.path.dirname(os.path.abspath(sys.argv[0])) if sys.argv[0] else os.getcwd()
sys.path.insert(0, HERE)
import ldgen as G

# 骨架：任何一个已验证的 PRG native 都行（本仓库 assets/natives/ 里有多个可选）
SKEL = os.environ.get('LDSKEL') or r'D:/plc_mcp/work/stn_edge/prg_StnAutoSeq.native'
OUT = os.environ.get('LDOUT') or os.path.join(HERE, 'prg_FlowDemo.native')
f = io.open(SKEL, encoding='utf-8'); SK = f.read(); f.close()

DECL = [
    u'PROGRAM prg_FlowDemo',
    u'VAR',
    u'    (* 外部输入 *)',
    u'    xAutoing : BOOL;',
    u'    xSafetyOK : BOOL;',
    u'    xManualMode : BOOL;',
    u'    xStart : BOOL;',
    u'    xReset : BOOL;',
    u'    xLoadAtPos : BOOL;',
    u'    xClampAtPos : BOOL;',
    u'    xEjectAtPos : BOOL;',
    u'    xScanDone : BOOL;',
    u'    xScanOK : BOOL;',
    u'    (* 阀输出：全部由线圈驱动 *)',
    u'    xLoadExt : BOOL;',
    u'    xLoadRet : BOOL;',
    u'    xClampExt : BOOL;',
    u'    xClampRet : BOOL;',
    u'    xEjectExt : BOOL;',
    u'    xEjectRet : BOOL;',
    u'    xScanTrig : BOOL;',
    u'    xAlarm : BOOL;',
    u'    (* 步序 *)',
    u'    aiAutoStep : INT;',
    u'    aiAutoStepBuffer : INT;',
    u'    awstrAutoDescription : WSTRING(49);',
    u'    iErrCode : INT;',
    u'    iGoodCnt : INT;',
    u'    iBadCnt : INT;',
    u'    (* 辅助位 *)',
    u'    bSafeStart : BOOL;',
    u'    bNeedLoad : BOOL;',
    u'    bNeedClamp : BOOL;',
    u'    bNeedEject : BOOL;',
    u'    (* 定时器 *)',
    u'    fbTLoad : TON;',
    u'    fbTClamp : TON;',
    u'    fbTEject : TON;',
    u'    fbTStab1 : TON;',
    u'    fbTStab2 : TON;',
    u'    fbTStab3 : TON;',
    u'END_VAR',
]

nets = []
def add(x):
    nets.append(x)

# ── 每周期辅助 ──
add(G.buf_commit_net())
add(G.coil_net([G.contact(u'xAutoing'), G.contact(u'xSafetyOK'),
                G.contact(u'xManualMode', neg=True)], u'bSafeStart', title=u'安全链就绪'))
add(G.coil_net([G.eq_box(G.value_pin(G.STEP, u'INT'), G.value_pin(u'10', u'INT')),
                G.contact(u'xLoadAtPos', neg=True)], u'bNeedLoad', title=u'上料未到位'))
add(G.coil_net([G.eq_box(G.value_pin(G.STEP, u'INT'), G.value_pin(u'20', u'INT')),
                G.contact(u'xClampAtPos', neg=True)], u'bNeedClamp', title=u'压紧未到位'))
add(G.coil_net([G.eq_box(G.value_pin(G.STEP, u'INT'), G.value_pin(u'60', u'INT')),
                G.contact(u'xEjectAtPos', neg=True)], u'bNeedEject', title=u'剔除未到位'))

# ── 六个 TON（单独成网络，每周期执行） ──
add(G.ton_net(u'fbTLoad', G.contact(u'bNeedLoad'), u't#3s', title=u'上料超时 3s'))
add(G.ton_net(u'fbTClamp', G.contact(u'bNeedClamp'), u't#3s', title=u'压紧超时 3s'))
add(G.ton_net(u'fbTEject', G.contact(u'bNeedEject'), u't#3s', title=u'剔除超时 3s'))
add(G.ton_net(u'fbTStab1', G.eq_box(G.value_pin(G.STEP, u'INT'), G.value_pin(u'15', u'INT')),
              u't#500ms', title=u'上料保持 500ms'))
add(G.ton_net(u'fbTStab2', G.eq_box(G.value_pin(G.STEP, u'INT'), G.value_pin(u'25', u'INT')),
              u't#300ms', title=u'压紧保持 300ms'))
add(G.ton_net(u'fbTStab3', G.eq_box(G.value_pin(G.STEP, u'INT'), G.value_pin(u'65', u'INT')),
              u't#500ms', title=u'剔除保持 500ms'))

# ── 主流程（BOOL 一律线圈） ──
add(G.step_net2(0, u'待命', [], 10, done_contact=G.contact(u'xStart'), done_edge=True))
add(G.step_net2(10, u'上料伸出', [G.set_coil(u'xLoadExt'), G.reset_coil(u'xLoadRet')], 15,
                done_contact=G.contact(u'xLoadAtPos')))
add(G.step_net2(15, u'上料保持', [], 20, done_contact=G.contact(u'fbTStab1.Q')))
add(G.step_net2(20, u'压紧伸出', [G.set_coil(u'xClampExt'), G.reset_coil(u'xClampRet')], 25,
                done_contact=G.contact(u'xClampAtPos')))
add(G.step_net2(25, u'压紧保持', [], 30, done_contact=G.contact(u'fbTStab2.Q')))
add(G.step_net2(30, u'检测触发', [G.set_coil(u'xScanTrig')], 40,
                done_contact=G.contact(u'xScanDone')))
add(G.judge_net(40, u'检测判定', [(G.contact(u'xScanOK'), 50),
                                  (G.contact(u'xScanOK', neg=True), 60)]))
add(G.step_net2(50, u'良品松夹缩回',
                [G.reset_coil(u'xScanTrig'), G.set_coil(u'xLoadRet'), G.reset_coil(u'xLoadExt'),
                 G.set_coil(u'xClampRet'), G.reset_coil(u'xClampExt')], 55, unconditional=True))
add(G.counter_net(55, u'iGoodCnt', u'良品计数', 90))
add(G.step_net2(60, u'剔除伸出', [G.set_coil(u'xEjectExt'), G.reset_coil(u'xEjectRet')], 65,
                done_contact=G.contact(u'xEjectAtPos')))
add(G.step_net2(65, u'剔除保持', [], 70, done_contact=G.contact(u'fbTStab3.Q')))
add(G.step_net2(70, u'三缸缩回',
                [G.set_coil(u'xEjectRet'), G.reset_coil(u'xEjectExt'),
                 G.set_coil(u'xClampRet'), G.reset_coil(u'xClampExt'),
                 G.set_coil(u'xLoadRet'), G.reset_coil(u'xLoadExt')], 75, unconditional=True))
add(G.counter_net(75, u'iBadCnt', u'不良计数', 90))
add(G.step_net2(90, u'全部复位',
                [G.reset_coil(u'xLoadExt'), G.reset_coil(u'xLoadRet'),
                 G.reset_coil(u'xClampExt'), G.reset_coil(u'xClampRet'),
                 G.reset_coil(u'xEjectExt'), G.reset_coil(u'xEjectRet'),
                 G.reset_coil(u'xScanTrig')], 0, unconditional=True))
add(G.step_net2(99, u'报警', [G.set_coil(u'xAlarm')], 0,
                done_contact=G.contact(u'xReset'), done_edge=True))

# ── 复位清报警 / 清错误码（末端线圈 / MOVE） ──
add(G.network([G.and_box([G.contact(u'xReset'), G.connector()],
                          outputs=[G.reset_coil(u'xAlarm')])], u'复位清报警'))
add(G.network([G.and_box([G.contact(u'xReset'),
                          G.move_box(G.value_pin(u'0', u'INT'), u'iErrCode', u'INT')])],
              u'复位清错误码'))

# ── 超时（末尾 MOVE） ──
add(G.timeout_net(G.contact(u'fbTLoad.Q'), 10, u'上料超时'))
add(G.timeout_net(G.contact(u'fbTClamp.Q'), 20, u'压紧超时'))
add(G.timeout_net(G.contact(u'fbTEject.Q'), 60, u'剔除超时'))

# ── 中断（必须放最后、每周期执行） ──
ABORT_COILS = [G.reset_coil(u'xLoadExt'), G.reset_coil(u'xLoadRet'),
               G.reset_coil(u'xClampExt'), G.reset_coil(u'xClampRet'),
               G.reset_coil(u'xEjectExt'), G.reset_coil(u'xEjectRet'),
               G.reset_coil(u'xScanTrig')]
add(G.abort_coils_net(G.contact(u'xManualMode'), ABORT_COILS, u'手动中断-撤全部输出'))
add(G.abort_clear_net(G.contact(u'xManualMode'), u'手动中断-清步序'))
add(G.abort_coils_net(G.contact(u'xSafetyOK', neg=True), ABORT_COILS, u'安全链断-撤全部输出'))
add(G.abort_clear_net(G.contact(u'xSafetyOK', neg=True), u'安全链断-清步序'))

r = G.build_doc(SK, u'prg_FlowDemo', DECL, nets, OUT)
print(r)