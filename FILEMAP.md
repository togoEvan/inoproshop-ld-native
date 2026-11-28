# FILEMAP —— 文件地图

> 130 个文件、3.6MB。目标是**新会话 30 秒内找到该改哪个**，不用通读。
> 目录结构再改，请同步本文件。

---

## 0. 先看这三个

| 文件 | 为什么 |
|---|---|
| `SKILL.md` | 铁律 1–52 全文（唯一权威版本） |
| `docs/quickstart.md` | 换电脑 / 换 AI 的冷启动 8 步 + 失败对照表（先跑通再读别的） |
| `references/native-structure.md` | native XML 字段级真相：GUID、槽位、线圈 / 边沿 / 树的载体 |
| `references/false-pass-catalog.md` | 假通过目录：哪些「0 错误」不可信 |

> ⚠ **两类对象没有可克隆的 native 样本**（写之前先补样本或从 git 取回）：
> ① 运动对象 —— 轴组 / 凸轮 / 轴控调用：按 `native-structure.md` §27（轴控）/ §32（CAM）/ §33（AxesGroup）重建，
> 或 `git show 014a4ab:assets/natives/axesgroup_cart_xy_sample.native`、`cam_index_345_sample.native`；
> ② 整段 ST 的 POU —— 库里只有「LD 内嵌 EXECUTE ST 块」（§24），ST POU 级骨架无端到端样本，
> 取回参照 `prg_EM01_Logic.native`。其余（LD 任意框 / 树 / 定时器 / GVL / DUT / FB·FC / 动作槽）都有样本或生成器。

## 1. 文件分布

| 位置 | 数量 | 内容 | 能不能改 |
|---|---|---|---|
| 根目录 | 11 | 门面（README）/ 铁律（SKILL、AGENTS）/ 地图 / 变更日志 / 归档说明 / LICENSE / 同步脚本 | README、SKILL、AGENTS、CHANGELOG、FILEMAP、ARCHIVE 要改 |
| `docs/` | 3 | `quickstart.md` 冷启动；`usage.md` 使用规范；`iteration.md` 迭代流程 / CHANGELOG 规范 | 要改 |
| `references/` | 11 | 正文 5 篇 + 模式卡 3 张 + 语料普查 3 篇 | 要改（结论变了就改正文） |
| `scripts/`（根） | 22 | 主机侧 Python 3：桥客户端、隐藏启动、导入、5 个自检闸门、一键验收、环境自检、消息差分、打包 | 要改；索引见 `scripts/README.md` |
| `scripts/ide/` | 6 | IronPython 2 守护本体 + 批量导出 + 索引 | 谨慎改（改完 reload） |
| `scripts/ide/tasks/` | 47 | 可复用单次任务：验收 / 导入 / 导出 / 建对象 / 任务槽 / GVL / 消息 | 要改 |
| `scripts/corpus/` | 5 | 语料工具：全量索引、网络切分、形状统计、native 转文本 | 要改 |
| `scripts/examples/` | 14 | 生成器：模板 6 / 结构样本 6 / 任务槽工具 1，索引见 `examples/README.md` | 参考用，别当库 |
| `assets/natives/` | 10 | 已验证克隆样本 8 份 + `negative/` 2 份（约 2.7MB） | **只读**（结构来源） |

## 2. 「我要做什么」→ 去哪

| 我要… | 去处 |
|---|---|
| 从零写一个新流程 | `references/mode-cards/process-flow.md` → `scripts/examples/gen_flow_ld.py` |
| 写进工站动作槽 `A0x` | `references/mode-cards/a00-skeleton.md` → `scripts/examples/gen_a04.py` |
| 写一段步序 | `references/mode-cards/step-sequence.md` → `scripts/examples/gen_seq_ld.py` |
| 生成节点 / 框 / 树 | `scripts/examples/ldgen.py`（基座，可 import） |
| 导入前拦结构错 | `scripts/check_symbols.py` / `check_slots.py` / `check_valpin.py` / `ld_logic.py` |
| 静默替换工程内对象 | `scripts/do_replace.py` → `ide/tasks/task_silent_import.py` |
| 只导入不删旧对象 | `ide/tasks/task_import_overwrite.py` |
| 验收一次改动 | `scripts/accept.py --names=<对象>`（= 挂载断言 → 清分类 build → 等 12s → 双通道判定，退出码 0/1/2/3） |
| 起/停隐藏 IDE | `scripts/hidden_launch.py --project=<副本>` / `--status` / `--stop`；体检 `scripts/selfcheck.py` |
| 断言对象真的进了编译单元 | `ide/tasks/task_mount_assert.py`（没挂 MainTask 一律 0 错误假通过） |
| 改 POU 源码（带读回与乐观锁） | `ide/tasks/task_setpou.py` + `ide/tasks/task_readback_pou.py` |
| 建任务 / 挪对象 | `ide/tasks/task_extended.py`；摘任务槽 `task_unhook_task.py` |
| 导出对象 / 整工程 | `task_export_one.py` / `task_export_named.py` / `export_all.py` |
| 看消息池原文 | `task_allmsg_dump.py` / `task_msgdump_now.py` |
| GVL 拷贝与符号体检 | `task_export_gvl.py` / `task_gvl_symbol_check.py` |
| 统计模板语料 | `scripts/corpus/index_native.py` → `scan_forms.py` / `parse_net.py` / `ld_dump.py` |
| 查某个结构错怎么修 | `references/precompile-errors.md` |
| 查桥 / 守护怎么通 | `references/mcp-bridge.md`；先跑 `scripts/bridge.py selftest` |

## 3. 核心链路

```text
模式卡（怎么摆） → gen_*.py + ldgen.py（生成 native）
   → check_symbols / check_slots / check_valpin / ld_logic（结构 + 符号 + 逻辑闸门）
   → do_replace.py（改名让位 → import_native → 同 tick 读消息 → 失败回滚）
   → accept.py（task_mount_assert → task_build_clean → 主机侧等 12s → task_check 双通道交叉校验）
```

## 4. 边界

- `assets/natives/` 是**克隆源**，只读；新结构必须先有样本再生成。
- `scripts/examples/` 是**生成器**，不是运行时依赖；库代码别 import 它们。
- 一次性探针、原始日志、F0x 考古脚本已移出仓库（2026-11-28 精简），清单与恢复方式见 `ARCHIVE.md`。
- 结论的**原因**写 `CHANGELOG.md`（只留 11-27 之后）与各 reference 的 ⚠ 块；铁律编号不重排。
