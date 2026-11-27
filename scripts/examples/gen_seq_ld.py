# -*- coding: utf-8 -*-
# @py3
"""模式卡① 验证样本：用 ldgen 从零生成 5 步步序程序 prg_SeqDemo。
结构完全照模板 A00_上料移栽 的步序母语法：
  NET1 步序号缓存提交   aiAutoStep := aiAutoStepBuffer
  NET2-6 每一步一个 BRANCH{EQ(aiAutoStep,N)}
      T1 MOVE 本步描述 → awstrAutoDescription
      T2 动作框（本样本用 MOVE / ADD，EN 带边沿）
      T3 MOVE 下一步 → aiAutoStepBuffer
见 references/mode-cards/step-sequence.md
"""
import io, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ldgen import *          # noqa

# 骨架：任何 Application 直属、单一实现区的 POU 导出都可（check_skeleton 会拦不合格的）
SKEL = os.path.join(HERE, "..", "..", "assets", "natives",
                    "lead_state_machine_12seg.native")
OUT = os.path.join(HERE, "..", "..", "assets", "natives", "prg_SeqDemo.native")
NAME = u"prg_SeqDemo"

DECL = [
    u"PROGRAM %s" % NAME,
    u"VAR",
    u"    xAutoing      : BOOL;   // 自动运行总使能（模板 A00 同名门控位）",
    u"    xStart        : BOOL;   // 启动按钮",
    u"    xLoadDone     : BOOL;   // 取料到位",
    u"    xWorkDone     : BOOL;   // 加工完成",
    u"    bLoadOn       : BOOL;   // 取料输出",
    u"    bWorkOn       : BOOL;   // 加工输出",
    u"    iCycle        : INT;    // 生产节拍计数",
    u"    // ---- 以下为步序内部变量 ----",
    u"    aiAutoStep       : INT;               // 当前步（唯一状态源，只读）",
    u"    aiAutoStepBuffer : INT;               // 步序号缓存（跳步只写它）",
    u"    awstrAutoDescription : WSTRING(49);   // 当前步描述（HMI 显示）",
    u"END_VAR",
    u"",
]

nets = []
nets.append(buf_commit_net())

# 启动：xStart 普通触点判电平，边沿落在跳步 MOVE 的 EN 引脚（done_edge=True）
nets.append(step_net(0, u"待命", [], 10, contact(u"xStart"),
                     u"待命：xStart 上升沿 → 取料", done_edge=True))
nets.append(step_net(10, u"取料",
                     [move_box(value_pin(u"TRUE", u"BOOL"), u"bLoadOn", u"BOOL", en_edge=True)],
                     20, contact(u"xLoadDone"), u"取料：置输出（EN 边沿，只执行一次）"))
nets.append(step_net(20, u"加工",
                     [move_box(value_pin(u"TRUE", u"BOOL"), u"bWorkOn", u"BOOL", en_edge=True)],
                     30, contact(u"xWorkDone"), u"加工：置输出（EN 边沿），完成进复位"))
nets.append(step_net(30, u"复位",
                     [move_box(value_pin(u"FALSE", u"BOOL"), u"bLoadOn", u"BOOL", en_edge=True),
                      move_box(value_pin(u"FALSE", u"BOOL"), u"bWorkOn", u"BOOL", en_edge=True)],
                     40, None, u"复位：撤全部输出"))
nets.append(step_net(40, u"计数",
                     [add_box(value_pin(u"iCycle", u"INT"), value_pin(u"1", u"INT"),
                              u"iCycle", u"INT", en_edge=True)],
                     0, None, u"计数：节拍 +1（EN 边沿，不会多计），回待命"))

skel = io.open(SKEL, encoding="utf-8").read()
info = build_doc(skel, NAME, DECL, nets, OUT)
print("written: %s (%d bytes)" % (info["path"], info["bytes"]))
print("networks=%d  ids=%d unique  maxId=%d" % (info["networks"], info["ids"], info["max_id"]))
print("boxes=%s" % info["boxes"])
print("BRANCH=%d PIN=%d CONNECTOR=%d OUTCONN=%d" % (
    info["branch"], info["pin"], info["connector"], info["outconn"]))
