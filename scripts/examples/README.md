# scripts/examples · 生成器索引

> 14 个文件。**生成器是参考实现，不是运行时依赖**：库代码不应 import 它们。
> 生成任何 native 前，先读 `references/mode-cards/` 里对应的模式卡。

## 1. 模板生成器（直接产出可导入 POU）

| 文件 | 产出 | 说明 |
|---|---|---|
| `gen_seq_ld.py` | 步序 POU | 模式卡 01；步号唯一状态源 + 分支跳步 |
| `gen_flow_ld.py` | 完整工站流程 | 模式卡 02；37 网络，步序 / 延时（TON）/ 超时 / 报警 / 复位 / 中断六件套 |
| `gen_a04.py` | 工站动作槽 `A04_` | 模式卡 03；读 `assets/natives/a04-action-skeleton.native` → 拼 16 步取放料。产物与 `A04_slot4.native` 逐字节相同 |
| `gen_tontest.py` | TON 最小样本 | 单个定时器单独成网络、每周期执行的反例对照 |
| `gen_coiltest.py` | 线圈最小样本 | S / R / 普通线圈的载体与位置 |
| `ldgen.py` | —— | **基座**：节点层 + 框构造（and / eq / move / add / ton）+ 网络 helper（step_net / judge_net / coil_net / counter_net / abort_coils_net）+ `build_doc` / `check_skeleton` |

## 2. 结构样本生成器（产出一个已验证的结构，供克隆对照）

| 文件 | 产出样本 | 说明 |
|---|---|---|
| `make_ld_learn.py` | —— | 最完整的可复用写法：contact / value_pin / connector_slot / coil / fb_box / ton_box / execute_box / network / textlines_block / build_pou，带 `__main__` 守卫 |
| `make_fb_call_test.py` | `fb_call_test.native` | 三类 CallType（Function / Program / FunctionBlock）各一个，含 REF 形参与 12 入 12 出 |
| `make_gvl.py` | GVL 样本 | 全局变量表的最小形态 |
| `make_packml_cmd_test.py` | PackML 命令框 | 含 contact / coil / and_box / branch / netitem / network 全套节点构造函数；配套配对扫描工具 |
| `make_func_return_test.py` | Function 调用框 | 演示 `OutputItems` 按索引对应 `OutputParam.Names`（[1] = 返回值） |
| `make_repro_study.py` | 状态字复现样本 | 早期复现实验用，保留作对照 |

## 3. 任务槽工具

| 文件 | 用途 |
|---|---|
| `del_task_pou.py` | 从 Task Configuration 摘掉一个 POU：`pous.remove()` 无效（回读仍在），只能导出 → 删 `<Single Type="{f194d1ef…}">` 块 → 覆盖导入 |

## 4. 写新生成器的约定

1. 先有一份**真实导出**的样本（`task_export_one.py`），在样本上改，不要凭空拼 GUID。
2. 复用 `ldgen.py` 的节点函数，别复制粘贴 XML 模板。
3. 产物必须过 `check_symbols.py` / `check_slots.py` / `ld_logic.py`，再谈导入。
4. 导入后**双分类 0 错误**才算生成成功；负样本造错验证编译器真的编了这个对象。
5. 新生成器如果产出了通用结构，把样本放进 `assets/natives/` 并在上面第 2 节登记一行。
