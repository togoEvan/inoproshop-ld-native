# -*- coding: utf-8 -*-
# @py3
"""模式卡② 验证样本：prg_FlowDemo —— 完整工站流程。
步序 0→10→15→20→25→30→40→(50|60)→...→90→0，含：
  · 三个到位超时（TON，各 3s，独立实例）
  · 三个保持延时（TON，500/300/500ms）
  · 良品/不良双路径（计数各 +1）
  · 99 报警步（xAlarm + iErrCode，复位回 0）
  · 手动/安全链中断（最高优先级：全撤 + 回 0）
"""
import io, os, sys

HERE = os.path.dirname(os.path.abspath(sys.argv[0])) if sys.argv[0] else os.getcwd()
sys.path.insert(0, HERE)
from ldgen import *

# 用法：python gen_flow_ld.py <已验证的PRG骨架.native> [输出路径]
# 骨架要求：Application 直属、单一实现区（ldgen.check_skeleton 会自检）
SKEL = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("LD_SKEL", "")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("LD_OUT", "prg_FlowDemo.native")
if not SKEL or not os.path.isfile(SKEL):
    raise SystemExit("用法: python gen_flow_ld.py <已验证的PRG骨架.native> [输出.native]")
NAME = u"prg_FlowDemo"

DECL = [
    u"PROGRAM %s" % NAME,
    u"VAR",
    u"    // ---- 输入 ----",
    u"    xAutoing     : BOOL;   // 自动运行总使能",
    u"    xSafetyOK    : BOOL;   // 安全链正常",
    u"    xManualMode  : BOOL;   // 手动模式（中断自动流程）",
    u"    xStart       : BOOL;   // 启动按钮",
    u"    xReset       : BOOL;   // 复位按钮",
    u"    xLoadAtPos   : BOOL;   // 上料到位",
    u"    xClampAtPos  : BOOL;   // 压紧到位",
    u"    xEjectAtPos  : BOOL;   // 剔除到位",
    u"    xScanDone    : BOOL;   // 检测完成",
    u"    xScanOK      : BOOL;   // 检测结果：TRUE 良品",
    u"    // ---- 输出 ----",
    u"    xLoadExt     : BOOL;   // 上料伸出",
    u"    xLoadRet     : BOOL;   // 上料缩回",
    u"    xClampExt    : BOOL;   // 压紧伸出",
    u"    xClampRet    : BOOL;   // 压紧缩回",
    u"    xEjectExt    : BOOL;   // 剔除伸出",
    u"    xEjectRet    : BOOL;   // 剔除缩回",
    u"    xScanTrig    : BOOL;   // 检测触发",
    u"    xAlarm       : BOOL;   // 报警",
    u"    // ---- 内部 ----",
    u"    aiAutoStep           : INT;            // 当前步（唯一状态源，只读）",
    u"    aiAutoStepBuffer     : INT;            // 步序号缓存（跳步只写它）",
    u"    awstrAutoDescription : WSTRING(49);    // 当前步描述（HMI 显示）",
    u"    iGoodCnt     : INT;    // 良品计数",
    u"    iBadCnt      : INT;    // 不良计数",
    u"    iErrCode     : INT;    // 故障步号",
    u"    bSafeStart   : BOOL;   // 安全启动条件",
    u"    bNeedLoad    : BOOL;   // 10 步未到位 → 计时",
    u"    bNeedClamp   : BOOL;   // 20 步未到位 → 计时",
    u"    bNeedEject   : BOOL;   // 60 步未到位 → 计时",
    u"    bAt40OK      : BOOL;   // 40 步且检测良品",
    u"    bStab1Done   : BOOL;   // 上料保持延时到",
    u"    bStab2Done   : BOOL;   // 压紧保持延时到",
    u"    bStab3Done   : BOOL;   // 剔除保持延时到",
    u"    bLoadTimeout : BOOL;",
    u"    bClampTimeout: BOOL;",
    u"    bEjectTimeout: BOOL;",
    u"    fbTLoad      : TON;    // 上料超时",
    u"    fbTClamp     : TON;    // 压紧超时",
    u"    fbTEject     : TON;    // 剔除超时",
    u"    fbTStab1     : TON;    // 上料保持",
    u"    fbTStab2     : TON;    // 压紧保持",
    u"    fbTStab3     : TON;    // 剔除保持",
    u"END_VAR",
    u"",
]

nets = []
nets.append(buf_commit_net())          # 1 步序提交

# ── 辅助位（每周期无条件） ──
nets.append(coil_net([contact(u"xSafetyOK"), contact(u"xManualMode", neg=True), contact(u"xStart")],
                     u"bSafeStart", u"BOOL", u"安全启动条件：安全正常 + 非手动 + 启动按钮"))
nets.append(coil_net([eq_box(value_pin(STEP, u"INT"), value_pin(u"10", u"INT")),
                      contact(u"xLoadAtPos", neg=True)],
                     u"bNeedLoad", u"BOOL", u"10 步未到位 → 开始计时"))
nets.append(network([ton_box(u"fbTLoad", contact(u"bNeedLoad"), u"t#3s", u"bLoadTimeout")],
                    u"上料到位超时 3s（TON 每周期执行，IN 随步离开自动复位）"))
nets.append(coil_net([eq_box(value_pin(STEP, u"INT"), value_pin(u"20", u"INT")),
                      contact(u"xClampAtPos", neg=True)],
                     u"bNeedClamp", u"BOOL", u"20 步未到位 → 开始计时"))
nets.append(network([ton_box(u"fbTClamp", contact(u"bNeedClamp"), u"t#3s", u"bClampTimeout")],
                    u"压紧到位超时 3s"))
nets.append(coil_net([eq_box(value_pin(STEP, u"INT"), value_pin(u"60", u"INT")),
                      contact(u"xEjectAtPos", neg=True)],
                     u"bNeedEject", u"BOOL", u"60 步未到位 → 开始计时"))
nets.append(network([ton_box(u"fbTEject", contact(u"bNeedEject"), u"t#3s", u"bEjectTimeout")],
                    u"剔除到位超时 3s"))
nets.append(network([ton_box(u"fbTStab1", eq_box(value_pin(STEP, u"INT"), value_pin(u"15", u"INT")), u"t#500ms", u"bStab1Done")],
                    u"上料保持延时 500ms"))
nets.append(network([ton_box(u"fbTStab2", eq_box(value_pin(STEP, u"INT"), value_pin(u"25", u"INT")), u"t#300ms", u"bStab2Done")],
                    u"压紧保持延时 300ms"))
nets.append(network([ton_box(u"fbTStab3", eq_box(value_pin(STEP, u"INT"), value_pin(u"65", u"INT")), u"t#500ms", u"bStab3Done")],
                    u"剔除保持延时 500ms"))
nets.append(coil_net([eq_box(value_pin(STEP, u"INT"), value_pin(u"40", u"INT")),
                      contact(u"xScanOK")],
                     u"bAt40OK", u"BOOL", u"40 步且良品"))

# ── 主流程 ──
nets.append(note_net(u"*主流程：上料 → 保持 → 压紧 → 保持 → 检测 → 分流*"))
nets.append(step_net(0, u"待命", [], 10, contact(u"bSafeStart"),
                     u"待命：安全条件成立 + 启动上升沿 → 上料", done_edge=True))
nets.append(step_net(10, u"上料伸出",
                     [move_box(value_pin(u"TRUE", u"BOOL"), u"xLoadExt", u"BOOL", en_edge=True)],
                     15, contact(u"xLoadAtPos"), u"10：上料伸出（EN 边沿只发一次），到位进保持"))
nets.append(step_net(15, u"上料保持", [], 20, contact(u"bStab1Done"),
                     u"15：保持 500ms（TON）后压紧"))
nets.append(step_net(20, u"压紧伸出",
                     [move_box(value_pin(u"TRUE", u"BOOL"), u"xClampExt", u"BOOL", en_edge=True)],
                     25, contact(u"xClampAtPos"), u"20：压紧伸出，到位进保持"))
nets.append(step_net(25, u"压紧保持", [], 30, contact(u"bStab2Done"),
                     u"25：保持 300ms 后检测"))
nets.append(step_net(30, u"检测触发",
                     [move_box(value_pin(u"TRUE", u"BOOL"), u"xScanTrig", u"BOOL", en_edge=True)],
                     40, contact(u"xScanDone"), u"30：发检测触发（EN 边沿），等检测完成"))
nets.append(step_net(40, u"分流：良品", [], 50, contact(u"bAt40OK"),
                     u"40：检测良品 → 良品路径"))
nets.append(step_net(40, u"分流：不良", [], 60, contact(u"bAt40OK", neg=True),
                     u"40：检测不良 → 剔除路径"))
nets.append(step_net(50, u"良品收尾",
                     [move_box(value_pin(u"TRUE", u"BOOL"), u"xClampRet", u"BOOL", en_edge=True),
                      move_box(value_pin(u"TRUE", u"BOOL"), u"xLoadRet", u"BOOL", en_edge=True)],
                     55, None, u"50：压紧/上料缩回（发令即走，不等到位）"))
nets.append(counter_net(55, u"iGoodCnt", u"良品计数", 90))
nets.append(step_net(60, u"剔除伸出",
                     [move_box(value_pin(u"TRUE", u"BOOL"), u"xEjectExt", u"BOOL", en_edge=True)],
                     65, contact(u"xEjectAtPos"), u"60：剔除伸出，到位进保持"))
nets.append(step_net(65, u"剔除保持", [], 70, contact(u"bStab3Done"),
                     u"65：保持 500ms 后收尾"))
nets.append(step_net(70, u"不良收尾",
                     [move_box(value_pin(u"TRUE", u"BOOL"), u"xEjectRet", u"BOOL", en_edge=True),
                      move_box(value_pin(u"TRUE", u"BOOL"), u"xClampRet", u"BOOL", en_edge=True),
                      move_box(value_pin(u"TRUE", u"BOOL"), u"xLoadRet", u"BOOL", en_edge=True)],
                     75, None, u"70：剔除/压紧/上料全部缩回"))
nets.append(counter_net(75, u"iBadCnt", u"不良计数", 90))
nets.append(step_net(90, u"全撤",
                     [move_box(value_pin(u"FALSE", u"BOOL"), u"xLoadExt", u"BOOL", en_edge=True),
                      move_box(value_pin(u"FALSE", u"BOOL"), u"xLoadRet", u"BOOL", en_edge=True),
                      move_box(value_pin(u"FALSE", u"BOOL"), u"xClampExt", u"BOOL", en_edge=True),
                      move_box(value_pin(u"FALSE", u"BOOL"), u"xClampRet", u"BOOL", en_edge=True),
                      move_box(value_pin(u"FALSE", u"BOOL"), u"xEjectExt", u"BOOL", en_edge=True),
                      move_box(value_pin(u"FALSE", u"BOOL"), u"xEjectRet", u"BOOL", en_edge=True),
                      move_box(value_pin(u"FALSE", u"BOOL"), u"xScanTrig", u"BOOL", en_edge=True)],
                     0, None, u"90：所有输出复位，回待命（节拍结束）"))

# ── 超时 → 报警 ──
def timeout_net(sig_item, code, title):
    return network([branch(sig_item, [
        and_box([move_box(value_pin(u"%d" % code, u"INT"), u"iErrCode", u"INT", en_edge=True),
                 outconn()]),
        and_box([move_box(value_pin(u"99", u"INT"), BUF, u"INT", en_edge=True),
                 outconn()]),
        empty_tree()])], title)

nets.append(note_net(u"*超时保护：三个到位超时各自跳 99 步并记录故障步号*"))
nets.append(timeout_net(contact(u"bLoadTimeout"), 10, u"上料超时 → 99（iErrCode=10）"))
nets.append(timeout_net(contact(u"bClampTimeout"), 20, u"压紧超时 → 99（iErrCode=20）"))
nets.append(timeout_net(contact(u"bEjectTimeout"), 60, u"剔除超时 → 99（iErrCode=60）"))

nets.append(step_net(99, u"报警",
                     [move_box(value_pin(u"TRUE", u"BOOL"), u"xAlarm", u"BOOL")],
                     0, contact(u"xReset"), u"99：报警保持，按复位（上升沿）回待命", done_edge=True))
nets.append(network([and_box([move_box(value_pin(u"FALSE", u"BOOL"), u"xAlarm", u"BOOL",
                                        en_item=contact(u"xReset", neg=True)),
                              outconn()])], u"99 之外清报警"))

# ── 中断（最高优先级，放最后） ──
def interrupt_net(cond_item, title):
    outs = [u"xLoadExt", u"xLoadRet", u"xClampExt", u"xClampRet",
            u"xEjectExt", u"xEjectRet", u"xScanTrig"]
    trees = []
    for o in outs:
        trees.append(and_box([move_box(value_pin(u"FALSE", u"BOOL"), o, u"BOOL"), outconn()]))
    trees.append(and_box([move_box(value_pin(u"0", u"INT"), STEP, u"INT"), outconn()]))
    trees.append(and_box([move_box(value_pin(u"0", u"INT"), BUF, u"INT"), outconn()]))
    trees.append(empty_tree())
    return network([branch(cond_item, trees)], title)

nets.append(note_net(u"*中断：手动模式或安全链断开 → 全部输出撤回 + 步序归零（不报警）*"))
nets.append(interrupt_net(contact(u"xManualMode"), u"中断：手动模式"))
nets.append(interrupt_net(contact(u"xSafetyOK", neg=True), u"中断：安全链断开"))

skel = io.open(SKEL, encoding="utf-8").read()
info = build_doc(skel, NAME, DECL, nets, OUT)
print("written: %s (%d bytes)" % (info["path"], info["bytes"]))
print("networks=%d ids=%d unique maxId=%d" % (info["networks"], info["ids"], info["max_id"]))
print("boxes=%s" % info["boxes"])
s = io.open(OUT, encoding="utf-8").read()
print("TON boxes =", s.count(u'BoxType" Type="string">TON'))
print("FunctionBlock =", s.count(u'>FunctionBlock<'))
print("decl vars =", len(DECL) - 5)

print("")
print("下一步验收（缺一道就可能假通过）：")
print("  1) python check_symbols.py %s  → 所有操作数必须有定义(TON 的 Q 写未声明变量时编译器不报错)" % OUT)
print("  2) 导入后必须挂进 MainTask 再 build（没挂不进编译单元，0 错误是假通过）")
print("  3) build 后必须构造负样本对照，证明 0 错误不是缓存")
