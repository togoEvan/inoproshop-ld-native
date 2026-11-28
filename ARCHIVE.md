# ARCHIVE —— 2026-11-28 精简说明

> 精简动作：313 个文件 / 6.4MB → 126 个文件 / 3.6MB。
> 之后新增冷启动三件套（hidden_launch / accept / selfcheck + quickstart），当前 **130 个 / 3.6MB**；本文件的删除清单仍是那 188 项，不受影响。
> 原则：库给 AI 读，删掉「只证明一次」的探针与原始日志，保留「生成 → 验证 → 写入」的闭环。
> **所有删除的文件都能从 git 历史取回**，见下方命令。

## 1. 删了什么

| 位置 | 数量 | 内容 | 为什么删 |
|---|---|---|---|
| `scripts/ide/studies/` | 98 | 一次性考古脚本（回答完问题即冻结） | 结论已并入铁律与 mode-cards，脚本本身不再执行 |
| `references/evidence/` | 47 | 原始消息读数与长日志（notask-scope 46 + hidden-instance-scope 1） | 结论已写进 `native-structure.md`「隐藏实例」节；日志只是证据副本 |
| `scripts/examples/` | 27 | 一次性探针：`analyze_f0x` / `make_f0x_*` / `make_axis_call` / `make_cam1_curve` / `make_full8` / `make_fix45` / `gen_a00_stn3` / `rebuild_f01` 等 | 只在当时那次验证里用；做法已写进对应 reference |
| `assets/natives/` | 16 | 重复或历史样本：`prg_Stn3LoadSeq`（1.1MB）/ `prg_EM01_Logic` / `lead_state_machine_12seg` / `startstop_state3` / `ss_manual_142651` / `cam_*` / `axesgroup_*` / `action_entry_*` / `a00-fragments/` 5 个 | 大部分有更小的首选样本（`user_fixed` / `fb_call_test` / `A04_slot4` / `a04-action-skeleton`）；**例外：运动对象（`cam_*` / `axesgroup_*`）与整段 ST（`prg_EM01_Logic`）没有替代样本**，见 §3 |

同时删掉/收缩的文档：

- README：29KB → 3KB（门面 + 速查）。51 条铁律不再双写，唯一权威版是 `SKILL.md`。
- CHANGELOG：56KB → 23KB。11-26 及更早的 35 段合并成一条归档说明（原文在 git 历史）。
- `docs/iteration.md`、`docs/usage.md`：保留（迭代流程与使用规范不可从别处还原）。

## 2. 怎么取回

单文件：

```bash
git show 014a4ab:references/evidence/notask-scope/README.md > /tmp/x.md
# 或（本机没有 git 时）走 GitHub Raw：
# https://raw.githubusercontent.com/togoEvan/inoproshop-ld-native/014a4ab/<path>
```

整批对比（精简前的完整树）：

```bash
git ls-tree -r --name-only 014a4ab | wc -l     # 313
git diff --stat 014a4ab HEAD -- . | tail -1
```

## 3. 精简后要特别注意的两处样本真空

| 想写什么 | 现在只有 | 要先做什么 |
|---|---|---|
| 运动控制：轴组 / 凸轮 / 轴控调用 | `native-structure.md` §27 / §32 / §33 的字段级描述 | `git show 014a4ab:assets/natives/axesgroup_cart_xy_sample.native`（或 `cam_index_345_sample.native`）先取回样本再改 |
| 整段 ST 的 POU（不是 LD 内嵌 EXECUTE） | §24 的 STSnippet 三层结构（框级） | 取回 `prg_EM01_Logic.native` 对照，或先补一个最小 ST POU 样本并实测 |

其余能力（LD 任意框 / 分支树 / TON / GVL / DUT / FB·FC / 动作槽 / 完整流程）都有保留样本或生成器，见 `FILEMAP.md` §1。

## 3. 精简后仍然成立的约定

- `assets/natives/` 只读；新结构先在真实工程里导出样本，再进库。
- 新增知识写进 `references/`；一次性探针不要进库（放本地 `work/`）。
- 铁律编号不重排，只让号；删除的条目在 `SKILL.md` 留一行「已归档，见 ARCHIVE.md」。
