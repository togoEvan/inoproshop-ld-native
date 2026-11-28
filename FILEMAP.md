# FILEMAP —— 仓库文件地图

> 目的：**新会话 / 三个月后的你**，不读完全部 310 个文件也能在 30 秒内找到该改哪个。
> 整理于 2026-11-26。目录结构若再改，请同步更新本文件。

---

## 1. 先看这 5 个文件（其余都是细节）

| 文件 | 为什么先看 |
|------|-----------|
| `README.md` | 这套东西是什么、怎么装、怎么跑一次完整写入 |
| `AGENTS.md` | **铁律**（验收唯一标准、禁用 API、不抢前台、哪些做法必炸） |
| `references/native-structure.md` | native XML 的字段级真相（容器不对称、Flags 位、GUID 关系） |
| `scripts/README.md` | scripts/ 根 **19** 个脚本的分类索引（桥 / 导入 / 自检闸门 / 消息差分 / 打包） |
| `scripts/ide/README.md` | **151** 个 IDE 内脚本的索引（core 6 / tasks 47 / studies 98） |

---

## 2. 文件分布（310 个）

| 位置 | 数量 | 性质 | 能不能改 |
|------|------|------|---------|
| 根目录 | 10 | 门面 + 铁律 + 变更日志 + 本文件 + 同步脚本 | README/AGENTS/CHANGELOG 要改；LICENSE 不改 |
| 根下隐藏文件 | 2 | `.gitattributes`（`*.cmd text eol=crlf`）/ `.gitignore` | 少动 |
| `docs/` | 2 | 面向使用者的长文档（`usage.md` 操作手册、`iteration.md` 迭代史） | 要改 |
| `references/` | 58 | 知识库正文 11 篇（`native-structure.md` 102KB / `precompile-errors.md` 25KB / `mcp-bridge.md` 21KB / `edge-detection.md` 4KB / `false-pass-catalog.md` 5KB / `mode-cards/step-sequence.md` 4KB / `mode-cards/process-flow.md` 14KB / `mode-cards/a00-skeleton.md` 8KB / `corpus/inopack-template-survey.md` 5KB / `corpus/ld-network-shapes.md` 3KB / `corpus/toolchain.md` 4KB）+ `evidence/notask-scope/` 46 个原始日志 + `evidence/hidden-instance-scope/` 1 篇 | 正文要改；evidence 只加不改 |
| `scripts/`（根） | 19 | 主机侧 Python 3 工具（桥 / 导入 / 5 个自检闸门 / 消息差分 / 打包）+ 三个 .cmd / .ps1；索引见 `scripts/README.md` | 要改 |
| `scripts/ide/`（core） | 6 | IDE 内 IronPython：守护本体 5 个 + 索引 README | 谨慎改（改完要 reload） |
| `scripts/ide/tasks/` | 47 | **可复用操作**：验收 / 导入 / 导出 / 建对象 / 任务槽 / GVL | 要改 |
| `scripts/corpus/` | 5 | 语料工具链（主机 py3）：`index_native.py` / `scan_forms.py` / `parse_net.py` / `ld_dump.py` / `split_networks.py`（按网络切 native）；IDE 内的全量导出在 `ide/tasks/export_all.py` | 要改 |
| `scripts/ide/studies/` | 98 | 一次性考古脚本，回答问题即冻结 | **不改**（要新写就进 tasks/） |
| `scripts/examples/` | 39 | native 生成器（可复用库 5 / 已验证样本生成器 14 / 一次性 F0x 考古 20，分类见 `examples/README.md`） | 参考用，别当库 |
| `assets/natives/` | 24 | 已验证的克隆模板 19 份 + `a00-fragments/` 5 个 A00 骨架片段（约 3.2MB；含 `negative/` 负样本与 `prg_TonTest` / `prg_CoilTest` 最小样本） | **只读**（结构来源） |

---

## 3. 「我要做什么」→ 看哪个文件

| 我要… | 去处 |
|-------|------|
| 写一个新 POU 进工程 | `scripts/do_replace.py`（调 `ide/tasks/task_silent_import.py`） |
| 验收一次改动 | `ide/tasks/task_check.py`（**必须先 build 再等 ≥10s**，见 §4） |
| 改 POU 源码（带乐观锁、防覆盖） | `ide/tasks/task_setpou.py`；超时/未知结果语义见 `references/mcp-bridge.md` |
| 只触发构建 | `ide/tasks/task_build.py` |
| 导入前拦结构错 | `scripts/check_slots.py` / `check_symbols.py` / `ld_logic.py` |
| 从零生成一段 LD 的 native | `scripts/examples/make_ld_learn.py`（最全）、`make_gvl.py`（GVL/Folder） |
| 建程序/FB/Function（不靠模板） | `app.create_pou(name, PouType.X, ...)`；坑见 `references/native-structure.md` |
| 把 POU 挂进任务（否则不参与编译） | 结论见 `ide/studies/task_task_api_probe.py`，用法 `main_task.pous.add(name)` |
| 查某个编译错误的含义与修法 | `references/precompile-errors.md` |
| 想让某个框「只执行一次」/ 加边沿 | `references/edge-detection.md`（框的 `InputFlags[0]=16`，不是触点） |
| 从零写一段「步进/步序」状态机 | `references/mode-cards/step-sequence.md`（三梯级母语法 + 可跑的 ldgen 示例） |
| 写一个**工站子程序**（A00 骨架：步序号记录器 / 单站放行 / 工位判断 / 取放料两段） | `references/mode-cards/a00-skeleton.md`（8 段骨架 + `STNControl[n]` + 生成器 `scripts/examples/gen_a00_stn3.py`） |
| 把多网络 native 按网络切开当模板 | `scripts/corpus/split_networks.py`（ElementTree，别用字符串配对） |
| 从零写完整工站流程（延时/超时/报警/复位/中断） | `references/mode-cards/process-flow.md`（35 网络排布 + BOOL 全用线圈 + 线圈挂 NETITEM + 四道验收） |
| 验收 PASS 但怀疑是假通过 | `references/false-pass-catalog.md`（九种假象逐条对照） |
| 想知道模板里到底有哪些框、哪些网络形状 | `references/corpus/inopack-template-survey.md` + `ld-network-shapes.md`（58 个 LD POU / 2171 网络 / 127 种形状） |
| 想把另一个真实工程也导出成可统计的语料 | `scripts/corpus/`（`toolchain.md` 给了环境变量与流程） |
| 查某个 API 到底存不存在 / 怎么调 | `references/native-structure.md` + `ide/studies/` 里对应的 probe 脚本 |
| 装守护 / 重装守护 | `ide/boot_daemon.py`（人工点菜单）；改完 `plc_daemon.py` 用 `ide/reload_daemon.py` |
| 主机侧调 daemon | `scripts/bridge.py` 或 `scripts/bridge.cmd` |
| 打包成 .skill 分发件 | `scripts/pack_skill.py` |
| 发布 | `sync.ps1` / `sync.cmd`（校验 CHANGELOG → commit → push） |

---

## 4. 核心链路（唯一正确的写入顺序）

```
① 生成 native（examples/ 或手写）
        ↓
② 静态自检三道闸（主机侧，秒级，不进 IDE）
   check_symbols.py   引用符号是否都在声明区
   check_slots.py     框的槽位数 == 参数数（含豁免规则）
   ld_logic.py        图形拓扑 → 布尔表达式，与期望签名比对
        ↓  ← 这里拦住大部分「导入后弹模态框 / 编译报错」
③ do_replace.py  →  ide/tasks/task_silent_import.py
   改名让位 → import_native → 同 tick 读消息 → 失败自动回滚 → 删旧 → save
        ↓  ← 唯一真实的编译消息只在这一刻产生
④ 前置检查：目标 POU 是否已挂进 MainTask？（没挂 = 不参与编译 = 假通过）
        ↓
⑤ ide/tasks/task_build.py        （build 会清空预编译分类）
⑥ 主机侧等 ≥10s                  （IDE 脚本内 sleep 会冻死界面）
⑦ ide/tasks/task_check.py        （单次快照，不 sleep 不轮询）
⑧ 判定：预编译分类 errors==0 且未被「多于100条」截断
```

**验收分类 GUID**：预编译 `217bc73e-759b-4a3c-bfa1-991c938a6541` / 编译 `97f48d64-a2a3-4856-b640-75c046e37ea9` /
格式检查 `0986c5dd-ca06-40a7-94e5-bf42de3dfd91` / 导出导入 `2af7707f-…` / 脚本消息 `194b48a9-…`。
分类是**按需注册**的：没 build 过就没有编译分类，读不到 ≠ 0 错误。

---

## 5. 一次性产物的边界（别当资产用）

- `scripts/ide/studies/`（98 个）：探 API / 探结构 / A-B 对照 / F0x 普查的考古脚本，多数硬编码了某个工程的对象名（`prg_GvlVerifyUse`、`F08_AxisGroup_Verify`、`F10_POU_EthercatTask_Verify`…），换工程即失效。**结论要沉淀到 `references/`，脚本本身冻结。**
- `scripts/examples/` 里 `make_f0x_*`、`make_axis_call.py`、`make_cam1_curve.py`、`analyze_*`：针对 InoPack 模板特定对象写的生成器。通用度较高的只有 `make_ld_learn.py`、`make_gvl.py`、`make_full8.py`、`make_fix45.py`、`make_fb_call_test.py`、`make_packml_cmd_test.py`、`make_func_return_test.py`、`make_repro_study.py`。
- `references/evidence/notask-scope/`（46 个日志）：`task_exp_notask` 那轮「未挂任务的 POU 不参与编译」的原始证据，只读存档。
- `references/evidence/hidden-instance-scope/`（1 篇）：2026-11-28 隐藏桌面实例实测 —— 该环境只注册编译分类、未挂任务 POU 静默漏检，验收必须先挂 MainTask。
- `ipc/`、`work/`、`tmp/`：运行时产物，已在 `.gitignore` 里，不要提交。
