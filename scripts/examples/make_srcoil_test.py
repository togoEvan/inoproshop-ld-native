# -*- coding: utf-8 -*-
# @py3
"""S/R 线圈 + NETITEM 输出取反 端到端验证生成器。

背景（2026-11-25 全工程扫描结论，本文件负责生成实测验证）：
  ① 线圈 Operand.Flags.Flags 的值域：0=普通线圈、1=NOT(非法)、2=S 置位、3=R 复位
     —— 历史样本 dump_143950（"测试2/3"）与 dump_144433（段2 状态机）里已有，
        但从未用生成器从头复现过（历史样本是手工改的，非生成产物）。
  ② NETITEM.Flags bit0 = 整级输出取反（线圈前画 ○）—— 知识库已记载，
     但同样从未生成复现过（全工程 7 处都是模板自带）。

⚠ 跳转（JMP）结构在模板中无样本、属未知结构，单独放 make_jump_test.py 探索，
  本文件只负责 ① S/R 线圈、② 输出取反 两项的端到端验证。

生成 POU：prg_SrCoilTest，共 5 个网络：
  网络1  xSetOn  ──(S) xLatch     置位线圈（Flags=2）
  网络2  xSetOff ──(R) xLatch     复位线圈（Flags=3）
  网络3  xCond   ──( ) xDirect    普通线圈（Flags=0 对照组）
  网络4  xCond   ──○──( ) xInvA   NETITEM Flags=1 输出取反（与网络5对照）
  网络5  xCond   ──( ) xInvB      普通线圈（对照组，同条件不取反）

⚠ 单条件 rung 写法：触点**直接**作为 NETITEM.RValue，不套 AND 框、不补 TRUE 占位。
  实测（2026-11-25，用户质疑"TRUE 相当于没加"后验证）：
    · AND 框 1 槽        → [Error] 'AND'需要至少'2' 个操作数
                          + [Error] 检测到不一致元素 (不正确的输入序列)
    · 裸触点直挂 RValue  → 0 错误，往返导出结构完全保留（prg_BareContactTest 验证）
  即「AND ≥2 槽」是**框**的约束；单条件压根不该有框。
  详见 references/native-structure.md「单条件 rung」一节。
"""
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
from make_ld_learn import (
    contact, coil, network, netitem_box_rvalue, and_box, build_pou, _id,
)

POU_NAME = u"prg_SrCoilTest"
OUT = os.path.abspath(os.path.join(
    BASE_DIR, u"..", u"..", u"..", u"plc_mcp", u"ipc", POU_NAME + u".native"))


def s_coil(var):
    """S 置位线圈：Operand.Flags.Flags = 2。"""
    return coil(var, flags=2)


def r_coil(var):
    """R 复位线圈：Operand.Flags.Flags = 3。"""
    return coil(var, flags=3)


def single_cond(var):
    """单条件：触点直接作为 NETITEM.RValue，不套 AND 框、不补 TRUE 占位。

    ⚠ 2026-11-25 实测纠正（用户质疑"TRUE 相当于没加，多此一举"）：
      之前用 and_box([contact(var), contact("TRUE")]) 是错的。
      IDE 实测结果：
        · AND 框 1 槽        → [Error] 'AND'需要至少'2' 个操作数
                              + [Error] 检测到不一致元素 (不正确的输入序列)
        · 裸触点直挂 RValue  → 0 错误，往返导出结构完全保留（prg_BareContactTest 验证）
      即「AND ≥2 槽」是**框**的约束；单条件压根不该有框。
    """
    return contact(var)


def build_networks():
    nets = []
    # 网络1：S 置位（Flags=2）
    nets.append(network(
        [netitem_box_rvalue(single_cond(u"xSetOn"), [s_coil(u"xLatch")])],
        u"// 网络1：置位 S 线圈：xSetOn ──(S) xLatch"))
    # 网络2：R 复位（Flags=3）
    nets.append(network(
        [netitem_box_rvalue(single_cond(u"xSetOff"), [r_coil(u"xLatch")])],
        u"// 网络2：复位 R 线圈：xSetOff ──(R) xLatch"))
    # 网络3：普通线圈对照（Flags=0）
    nets.append(network(
        [netitem_box_rvalue(single_cond(u"xCond"), [coil(u"xDirect")])],
        u"// 网络3：普通线圈对照：xCond ──( ) xDirect"))
    # 网络4：NETITEM Flags=1 输出取反（线圈前 ○）
    nets.append(network(
        [netitem_box_rvalue(single_cond(u"xCond"), [coil(u"xInvA")],
                            inverted=True)],
        u"// 网络4：输出取反：xCond ──○──( ) xInvA（NETITEM Flags=1）"))
    # 网络5：同条件普通线圈对照（网络4 的对照）
    nets.append(network(
        [netitem_box_rvalue(single_cond(u"xCond"), [coil(u"xInvB")])],
        u"// 网络5：对照：xCond ──( ) xInvB（普通线圈，同网络4条件）"))
    return nets


DECL = [
    u"PROGRAM %s" % POU_NAME,
    u"VAR",
    u"    (* ~~~~ S/R 线圈 + 输出取反 端到端验证 ~~~~~~~~~~~~~~~~~~~~ *)",
    u"",
    u"    (* -- S/R 线圈 -- *)",
    u"    xSetOn          : BOOL;   // 置位条件",
    u"    xSetOff         : BOOL;   // 复位条件",
    u"    xLatch          : BOOL;   // 被置位/复位的锁存变量",
    u"",
    u"    (* -- 普通线圈 / 取反对照 -- *)",
    u"    xCond           : BOOL;   // 网络3/4/5 条件",
    u"    xDirect         : BOOL;   // 网络3 普通线圈",
    u"    xInvA           : BOOL;   // 网络4 输出取反线圈（NETITEM Flags=1）",
    u"    xInvB           : BOOL;   // 网络5 对照普通线圈",
    u"END_VAR",
]


def main():
    _id[0] = 7000
    out = build_pou(POU_NAME, DECL, build_networks(), OUT)
    print(u"OK %s" % out)


if __name__ == "__main__":
    main()
