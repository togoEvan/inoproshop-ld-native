# scripts/examples/ —— native 生成器（40 个 + 本索引）

这里都是**主机侧 Python 3** 脚本：读现有 native / 从零构造节点 → 生成新的 `.native` → 交给 `scripts/do_replace.py` 导入。
节点构造的公共层在 [`ldgen.py`](ldgen.py)，它才是唯一需要当「库」用的文件。

## 先分清三类（边界比目录重要）

| 类别 | 判断标准 | 能不能改 |
|------|----------|----------|
| **可复用库 / 模板生成器**（7） | 不依赖具体工程的对象名，参数化后可对任意工程用 | ✅ 改，且改动要跑验收 |
| **已验证结构样本生成器**（13） | 绑定 InoPack 模板里的具体对象名，但结论已进 `references/`，可照抄结构 | 参考用，换个工程要改符号 |
| **一次性 F0x 考古**（20） | 只用于回答「F0x 这组对象能不能复制/翻译」这一类问题，答完即冻结 | ❌ 不改（要新写就新建文件） |

## 一、可复用库 / 模板生成器（7）

| 脚本 | 用途 |
|------|------|
| `ldgen.py` | **节点构造库**：`operand_container` / `contact` / `value_pin` / `coil` / `netitem` / `and_box` / `eq_box` / `move_box` / `add_box` / `ton_box` / `branch` / `network` + 模板 helper（`step_net` / `step_net2` / `judge_net` / `counter_net` / `timeout_net` / `abort_coils_net` / `buf_commit_net`）+ `build_doc()` 重编 Id。⚠ `contact(edge=True)` 直接 raise——边沿在框的 `InputFlags[0]=16`，不在触点 |
| `gen_seq_ld.py` | 生成「步序状态机」示例（对应模式卡 `references/mode-cards/step-sequence.md`） |
| `gen_flow_ld.py` | 生成「完整工站流程」示例 35 网络（对应模式卡 `references/mode-cards/process-flow.md`） |
| `gen_tontest.py` | 最小 TON 样本（2 网络），验证「TON 每周期执行 + 线圈挂 NETITEM」 |
| `gen_coiltest.py` | 最小线圈样本（2 网络），验证普通 / S / R 三种线圈同梯级并联 |
| `gen_a00_stn3.py` | 生成**独立 `PROGRAM` 版**工站骨架 31 网络样本（记录器 / 缓存放行 / 工位判断 / 取放料两段），片段读 `assets/natives/a00-fragments/`，对应模式卡 `references/mode-cards/a00-skeleton.md` 附录 A |
| `gen_a04.py` | **模板正解**：把流程写进工站自动 POU 的动作槽（`A04_`，下标 4）——读动作骨架 `assets/natives/a04-action-skeleton.native`、保留前 5 个骨架网络、拼 16 个步序网络，输出 22 网络样本；动作不能改名，替换要 `remove()` + `import_native()` |

三件套用法（`gen_a00_stn3.py` 同理，另需 `assets/natives/a00-fragments/` 5 个片段；`gen_a04.py` 需要 `assets/natives/a04-action-skeleton.native`）：

```
set LDSKEL=<骨架 native，例如 assets/natives/prg_FlowDemo.native>
set LDOUT=<输出路径>
python gen_flow_ld.py
python ..\do_replace.py <LDOUT> Application bNeedLoad
```

## 二、已验证结构样本生成器（13）

| 脚本 | 验证了什么结构 |
|------|----------------|
| `make_ld_learn.py` | LD 语法全集：触点 / 并联 / 线圈 / S / R / AND / MOVE / 状态机（最全的学习样本） |
| `make_packml_cmd_test.py` | 从零生成完整 POU（7 网络 PackML 命令层） |
| `make_fb_call_test.py` | FB 调用框三种形态：Function / Program / FunctionBlock |
| `make_func_return_test.py` | Function 框返回值槽（`OutputParam.Names[1]` 恒空 = 返回值）端到端 |
| `make_axis_call.py` | 轴控指令调用（FC_AxisAbsGo / MC_* 系列） |
| `make_cam1_curve.py` | CAM 曲线数据（Points / Segments，`p1` 是段内增量） |
| `make_gvl.py` | GVL / Folder 从零生成（四条 GUID 关系 + 花括号铁律） |
| `make_gvl_verify.py` | GVL 副本带后缀重建后自比对 |
| `make_gvl_bad.py` | GVL 负样本（引用不存在的类型，用于确认编译器真会报错） |
| `make_full8.py` | 把裸 MOVE 支路批量包装成「完整支路」（AND 框包 [MOVE, 连接器]） |
| `make_fix45.py` | 补声明 + 删多余 TRUE 触点（旧占位法的修复） |
| `make_srcoil_test.py` | S/R 线圈的 Flags 编码（2=S / 3=R）对照 |
| `make_repro_study.py` | 复杂图形复现（分支组 / 比较框 / 算术框 / TON / EXECUTE 混排） |

## 三、一次性 F0x 考古（20）

| 脚本 | 当时要回答的问题 |
|------|------------------|
| `analyze_f04.py` / `analyze_f05.py` | F04_FB / F05_FC 组内的对象构成（语言、大小、依赖） |
| `analyze_f10.py` / `analyze_f11.py` | F10/F11 任务层 POU 的构成 |
| `analyze_f20.py` / `analyze_f21.py` | F20/F21 工站 POU 的构成（F21 是 ST+LD 混合） |
| `make_f01_copy.py` | F01_Variable 的 GVL 全量复制（8 个 GVL，AT 地址冲突首次暴露） |
| `make_f02_copy.py` | F02_Struct 的 DUT 复制（枚举字面量重名首次暴露） |
| `make_f04_translate.py` / `make_f05_translate.py` | F04/F05 全量翻译（58 个对象，空文件夹误建首次暴露） |
| `make_f07_cam_copy.py` | CAM 对象复制（`AxisGuid` / 曲线段隔离） |
| `make_f08_axesgroup_copy.py` / `make_f08_alt_mapping.py` | 轴组复制与轴映射冲突对照 |
| `make_f10_translate.py` / `make_f11_translate.py` | F10/F11 任务层 POU 翻译 |
| `make_f20_translate.py` / `make_f21_translate.py` | F20/F21 工站 POU 翻译（F21 实测四类标识符载体） |
| `rebuild_f01.py` | 用导出的 GVL 重建（逐字段比对，RETAIN 段不可字节比对） |
| `extract_action_entry.py` | 从 FB 的 action 导出里抽 Entry 结构（action 的 ST 体作用域证据） |
| `del_task_pou.py` | 从 Task Configuration native 里删一个 `<Single>` 块（铁律 38 的唯一可靠摘槽法） |

## 冻结规则

1. 第三类脚本**只读不改**：它们记录的是「当时的实验条件」，改了就不再是可追溯的证据。
2. 第二类里被 `references/` 引用的结构（TON / NETITEM / Function 返回值 / GVL）改动后必须重跑双分类验收。
3. 任何新生成器都要先过 `check_symbols.py` + `check_slots.py`，再导入隐藏实例验收；**不要直接写进用户工程**。