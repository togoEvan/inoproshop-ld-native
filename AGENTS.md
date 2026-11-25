# AGENTS.md — AI 协作契约

> 本文件是**给 AI Agent 的操作契约**，优先级高于 README。
> 你（AI）接手本仓库时，按下面顺序执行，不要跳步。

---

## 0. 三十秒判断：这个仓库是否适用于你的任务

适用：
- 需要向**已打开的** InoProShop 工程写入/修改梯形图（LD）
- 需要生成 LD native XML、功能框（MOVE/AND）、触点、并联、线圈、状态机
- 需要静默导入导出、或排查 LD 预编译错误

不适用：
- 其他厂商 PLC（西门子/三菱/欧姆龙）—— GUID 与结构完全不同
- ST / FBD 语言写入——本仓库只覆盖 LD（GUID 见 `references/native-structure.md`）
- 没有 Windows + InoProShop 运行环境

---

## 1. 上手顺序（强制）

```
README.md  →  references/native-structure.md  →  assets/natives/ 里的样本
```

1. **先读 README 的「铁律」表格**（11 条）。违反任何一条都会浪费大量时间。
2. **读 `references/native-structure.md`** 拿到节点 GUID、层级、槽位规则、合法挂载位置。
3. **打开 `assets/natives/` 里最接近的样本**，看清楚实际 XML 长什么样。**生成新结构必须从这里克隆节点**，不要凭空手写 GUID 和字段。

不要跳过第 3 步。凭空构造是踩坑的最主要原因。

---

## 2. 验收标准（唯一）

**预编译分类 `217bc73e-…` 错误数 == 0，_且_ 编译分类 `97f48d64-…` 错误数 == 0。**

两个分类抓的是不同错误，缺一不可：

| 分类 | GUID | 抓什么 |
|------|------|--------|
| 预编译 | `217bc73e-759b-4a3c-bfa1-991c938a6541` | 结构错误：槽位不符、IsContact 错、声明缺失、红框 |
| 编译 | `97f48d64-a2a3-4856-b640-75c046e37ea9` | 语义错误：如 `'AND'需要至少'2' 个操作数`（单条件 rung 只给 1 个槽） |

**只读预编译会漏掉编译分类的错误。** 2026-11-25 实测：预编译 0 错误，构建报 N 条 AND 操作数不足。原因是单条件 rung 的顶层 AND 只有 1 个输入槽——预编译阶段不校验元数，构建阶段才报。

- `scripts/ide/task_check.py` 已同时执行「检查程序」+ `app.build()`，并输出 `=== 验收结论 : 通过/不通过 ===`。
- 报告完成前必须实际跑一次 `task_check.py` 并贴出**验收结论**那一行。
- 任一分类不为 0 时，**禁止**说「已完成」「应该没问题」。

---

## 3. 硬约束（不许突破）

| 约束 | 原因 |
|------|------|
| 不动真实鼠标、不抢焦点（禁 `SetCursorPos` / `mouse_event` / `SetForegroundWindow`） | 会打断用户正在做的事 |
| 不关闭 / 不重启 IDE | 用户明确要求；重开代价极高 |
| 不弹任何确认框（导入/覆盖/替换） | 无人值守场景会卡死 |
| 中文注释字节级完好 | 用户验收项 |
| 长任务不阻塞轮询 | 用户明确要求「不要一直运行卡死」 |
| 找 POU 用 `app.get_children()` 过滤直接子对象 | 全局 `find_named` 会误命中 Task Configuration |

---

## 4. 标准作业流程（SOP）

```
① 从 assets/natives/ 选最接近的样本
② Python + xml.etree.ElementTree 克隆节点，改 Operand / 常量 / 条件
③ Id 全部唯一，UniqueIdGenerator ≥ 最大 Id（+100 余量）
④ 写到 work/<唯一名>.native
⑤ python scripts/do_replace.py <file> Application <目标POU>
⑥ 经桥执行 scripts/ide/task_check.py
⑦ 读 ipc/check.log，确认预编译 0 错误
⑧ 若报错 → 查 references/precompile-errors.md → 修 → 回到 ④
```

第 ⑤ 步是「改名让位法」：`prg_X → prg_X_old_tmp` → `import_native` → 删旧。这样导入瞬间不存在同名冲突，不会弹框。

---

## 5. 改动必须同步（用户明确要求）

**任何一次对仓库内容的改动，都必须在同一次任务内完成提交并推送。**

改动包括但不限于：新增/修改脚本、更新 `references/` 里的结论、新增 native 样本、修正文档错字、补充错误对照表。

### 5.1 必须做的三件事

1. **更新 `CHANGELOG.md`** —— 在 `## [Unreleased]` 下按 `新增 / 修改 / 修复 / 文档` 分类追加一行，写清「改了什么 + 为什么」。
2. **跑 `sync.ps1`** —— 它会校验 CHANGELOG 有变动，然后 `git add -A` + commit + push。
3. **确认推送成功** —— `sync.ps1` 输出 `pushed to origin/main` 才算完成。

### 5.2 一键同步

```powershell
.\sync.ps1 -Message "fix: 修正 IN 引脚 Type 说明"
```

不带 `-Message` 时脚本会从 `CHANGELOG.md` 的 Unreleased 段落自动生成提交信息。

### 5.3 例外（可以不推送）

- 只是本地临时调试脚本（放在 `work/`，已被 `.gitignore` 忽略）
- 用户明确说「先别提交」

除以上两种，**默认必须推送**。忘记推送等于这次工作没交付。

---

## 6. 遇到新坑时的处理（四类触发）

### ⚠ 适用范围：只记中型 PLC 梯形图相关问题

**只记录 InoProShop（CODESYS V3.5 SP11 系）中型 PLC 梯形图 native XML 相关的问题**——结构、导入导出、预编译/编译错误、IDE 行为、工程配置。

**不记录**：git 推送、DNS、网络、凭据、代理、GitHub 访问这类**仓库工具链**问题。它们不是中型 PLC 知识，混进 `references/` 只会稀释信噪比。工具链问题直接在 `sync.ps1` / `sync.cmd` 等脚本里修，**不写文档、不记 CHANGELOG**。

用户批准的四类更新触发（2026-11-25）。**每次任务收尾必须逐条对表**，不能只挑自己记得的那条：

| # | 类别 | 触发信号 | 落到哪 | 必带证据 |
|---|------|---------|--------|---------|
| ① | **没见过的格式** | 见到 `references/` 里没有的节点 GUID、层级嵌套、属性组合、`CallType` 取值、槽位排布、`Flags` 位含义、声明区写法 | `references/native-structure.md` 新增一节 + `assets/natives/` 存克隆样本 + `scripts/examples/` 加生成器 | 结构解析输出 + 导入成功 + **双分类 0 错误** + 导出往返一致 |
| ② | **Bug** | 脚本报错 / IDE 崩 / 导入失败 / 弹框 / 验收漏报 / daemon 异常 | 报错类 → `references/precompile-errors.md`；工具类 → 修 `scripts/` + `docs/iteration.md` 记一条 | 报错**原文**（含堆栈）+ 复现步骤 + 根因 + 修复后验证 |
| ③ | **吃过的亏** | 按错误理解做过事、浪费了时间；或文档已有结论被实测**证伪** | 提炼成**铁律第 N 条**（README + SKILL 双写）+ reference 加 `⚠` 块 + `CHANGELOG`「修改」 | 「错在哪 / 对的是什么 / **怎么自检**」三句话 |
| ④ | **新配置** | 换机器、换 IDE 版本、换工程路径、环境变量行为变、目录布局变（**限中型 PLC 侧**；git/DNS/凭据等工具链配置不记） | `references/mcp-bridge.md`「环境要点」+ `_base.py` 顶部注释 + `docs/iteration.md` §7 | **一条自检命令**（能直接验证配置生效） |

共同底线：

- **没有实测证据的结论不许写进 `references/`**
- **分类冲突**时按「后人最可能在哪一步踩到」落主库，其余位置只放一句话 + 链接
- **不许写**：无法复现的一次性异常、未证实的推断、一次性调试脚本

铁律的计数以 `README.md` 的表格为准，改了铁律要同步这里的条数。回写后同样要走第 5 节的同步流程。

---

## 7. 汇报格式（给用户）

完成一次 LD 写入任务后，按这个结构汇报：

```
✅ 已写入 <POU 名>，预编译 0 错误
- 结构：<一句话描述，如「分支组 8 支路，每支路一个 MOVE 框」>
- 验收：预编译 total=0 errors=0（编译 0 错误 1 警告 CmpLog，可忽略）
- 文件：<native 路径>
- 同步：CHANGELOG 已更新，已 push 到 origin/main
```

预编译有错时**不要**用这个格式，直接报错误清单和下一步计划。
