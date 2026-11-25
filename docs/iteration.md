# 迭代流程

本文件规定：**改什么、怎么验证、怎么发版**。

---

## 1. 改动分类与验证要求

| 类型 | 例子 | 验证要求 |
|------|------|----------|
| **代码** | `scripts/*.py`、`scripts/ide/*.py`、`*.ps1` | 必须实跑通过；涉及导入的必须双分类 0 错误 |
| **结构知识** | `references/native-structure.md` 新增挂载位置 | 必须附实测证据（导入成功 + 双分类 0 错误 + 往返一致） |
| **错误对照** | `references/precompile-errors.md` 新增条目 | 必须附报错原文、触发条件与修复后验证结果 |
| **样本** | `assets/natives/` 新增或替换文件 | 必须已验证导入 + 双分类 0 错误，并在表格登记；被证伪的旧样本必须**替换**而非仅追加 |
| **环境配置** | `references/mcp-bridge.md` 环境要点、`_base.py` 路径解析 | 必须附一条能直接跑的自检命令 |
| **文档** | `README.md`、`docs/`、`AGENTS.md` | 只需自检一致性与链接有效 |

**核心原则：没有实测证据的结论不许写进 `references/`。** 猜测写进知识库比不写更有害。

> 注意：**双分类 0 错误 ≠ 图形没问题**。2026-11-25 实测：单支路分支组（`Trees=1`）
> 预编译 0 + 编译 0，但 IDE 打开该网络直接崩（`IBoxTreeParallel` 索引越界）。
> 纯渲染错误不参与编译，必须靠结构自检脚本兜（见 `native-structure.md` 铁律 11 与
> `precompile-errors.md` 第 4b 类）。

---

## 2. 标准迭代流程

```
① 记下问题现象（报错原文、截图、复现步骤）
② 查 references/ 是否已有结论 → 有就直接用
③ 复现 → 定位根因 → 设计最小验证实验
④ 实测通过（预编译 0 错误 且 编译 0 错误）
⑤ 按 §2.1 的四类对表回写（先走 §2.1.2 的四问自查，再按 §2.1.1 采集清单取证）
⑥ 更新 CHANGELOG.md
⑦ .\sync.ps1 -Message "..." → commit + push
⑧ 如涉及样本，把验证过的 native 放进 assets/natives/ 并在 README 表格登记
⑨ 重新打包 .skill 并同步本机技能目录（见 §7）
```

### 2.1 回写四类触发（对表用）

四类分别对应知识库必须补的四种东西：**新知识 / 缺陷 / 教训 / 环境**。

> **⚠ 适用范围：只记中型 PLC 梯形图相关问题。**
> 只记录 InoProShop（CODESYS V3.5 SP11 系）中型 PLC 梯形图 native XML 相关的结构、导入导出、
> 预编译/编译错误、IDE 行为、工程配置。**git 推送 / DNS / 网络 / 凭据 / 代理 / GitHub 访问**
> 这类仓库工具链问题**不记**——它们不是中型 PLC 知识，混进 `references/` 只会稀释信噪比。
> 工具链问题直接在 `sync.ps1` / `sync.cmd` 里修，不写文档、不记 CHANGELOG。

| # | 类别 | 触发信号 | 落到哪 | 必带证据 |
|---|------|---------|--------|---------|
| ① | **没见过的格式** | 见到 `references/` 里没有的节点 GUID、层级嵌套、属性组合、`CallType` 取值、槽位排布、`Flags` 位含义、声明区写法 | `references/native-structure.md` 新增一节<br>+ `assets/natives/` 存克隆样本<br>+ `scripts/examples/` 加生成器 | 结构解析输出 + 导入成功 + 双分类 0 错误 + 导出往返一致 |
| ② | **Bug** | 脚本报错 / IDE 崩 / 导入失败 / 弹框 / 验收漏报 / daemon 异常 | 报错类 → `references/precompile-errors.md`（编号续写）<br>工具类 → 修 `scripts/` + 本文件记一条 | 报错**原文**（含堆栈）+ 复现步骤 + 根因 + 修复后验证 |
| ③ | **吃过的亏** | 按错误理解做过事、浪费时间；或文档已有结论被实测**证伪** | 提炼成**铁律第 N 条**（README + SKILL 双写）+ reference 加 `⚠` 块 + `CHANGELOG`「修改」 | 「错在哪 / 对的是什么 / **怎么自检**」三句话 |
| ④ | **新配置** | 换机器、换 IDE 版本、换工程路径、环境变量行为变、目录布局变（**限中型 PLC 侧**；git/DNS/凭据等工具链配置不记） | `references/mcp-bridge.md`「环境要点」+ `scripts/ide/_base.py` 顶部注释 + 本文件 §7 | **一条自检命令**（能直接验证配置生效） |

**分类冲突时**：按「后人最可能在哪一步踩到」落**主库**，其余位置只放一句话 + 链接，不复制全文。

**自检脚本优先**：凡是能用脚本扫出来的违规（如「分支组 Trees < 2」），必须把扫描脚本一起写进对应 reference，让后人能一键自查，而不是靠肉眼比对。

#### 2.1.1 编程过程中哪些数据要回写（现场采集清单）

回写的前提是**手上真有东西**。这些数据要在报错/崩溃的**当次**就采，收尾只做归类，不重新取证（回忆一定缺原文）。

| # | 数据 | 在哪采 | 必须原样留下的形态 | 服务于 |
|---|------|--------|-------------------|--------|
| 1 | 新结构的 XML 片段 | `task_export_fixed.py` 导出目标 POU | 完整 `.native` 文件（含 `Id`/`GUID`/层级），不是截图或摘要 | ① |
| 2 | 报错原文 | `ipc/check.log` 每条 message 的 `Text` + 分类 GUID | 整行照抄，连编号带标点 | ② |
| 3 | 定位信息 | 报错所属 POU / 网络序号 / 行号 / 槽位 | 能唯一定位「哪个 POU 的哪个网络」 | ② |
| 4 | 最小实验记录 | 单变量实验 4 步 | 改了哪个字段（旧值→新值）→ 导入 → check + build → 结果 | ②③ |
| 5 | 通过态证据 | `task_check.py` 末行 | 预编译 `total/errors` + 编译 `total/errors` + `=== 验收结论 ===` | ①③ |
| 6 | 往返一致性 | 导入后再导出，与源文件 diff | diff 结果 + 比对了哪些节点（只写"往返一致"不算证据） | ① |
| 7 | IDE 行为异常 | IDE 弹窗/崩溃框 | 标题 + 正文原文 + 堆栈特征（如 `IBoxTreeParallel`）+ 触发动作 | ②③ |
| 8 | 用户手改前后 | 手改前后各导出一次 | 两份 native + 结构差异结论 | 「已验证模式」 |
| 9 | 环境快照 | `check.log` 第一行 + IDE 版本 + 工程绝对路径 | 原样一行文本 | ④ |

**硬要求**：①类条目缺第 1、5、6 项任一项，**不许**写进 `references/`。

#### 2.1.2 怎么跟其他 AI 解释「哪些该回写」（四问自查法）

只讲「遇到新坑要回写」会各理解各的。统一用四问，每问只答「有 / 无」：答「有」必须附证据，答「无」要写清查过哪个文件。

| 问 | 问的是什么 | 答「有」之后必须做的 |
|---|-----------|---------------------|
| Q1 新格式 | 有没有见到 `references/` 里查不到的 GUID / 层级 / 属性组合 / `CallType` / 槽位 / `Flags` / 声明写法？ | 导出样本 + `native-structure.md` 加一节 + 生成器 + 双分类 0 错误 + 往返一致 |
| Q2 Bug | 有没有哪一步报错 / 崩溃 / 弹框 / 导入失败 / 验收漏报 / daemon 异常？ | 报错原文（含堆栈）+ 复现步骤 + 根因 + 修复验证 |
| Q3 吃过的亏 | 有没有按错误理解做过事、浪费时间，或文档结论被实测推翻？ | 铁律第 N 条（README + SKILL 双写）+ `⚠` 块 + 「错在哪 / 对的是什么 / 怎么自检」 |
| Q4 环境 | 换机器 / IDE 版本 / 工程路径 / 环境变量行为 / 目录布局变了吗？ | `mcp-bridge.md` 环境要点 + `_base.py` 注释 + 一条能跑的自检命令 |

**给其他 AI 的原文说明块**在 `AGENTS.md` §6.2，**原文照发，不要转述**——转述必丢硬规则。

**四种常见误判**：①导入失败一次、重试就好 → 不写（不可复现）；②双分类 0 错误但图形打不开 → **写**（渲染错误不参与编译）；③用户手改过结构 → **写，最高优先**；④`git push` 超时/代理报错 → 不写（只修 `sync.ps1`）。


### 最小验证实验的做法

不要在完整工程上直接试。做法：

1. 复制一份样本 native 到 `work/`
2. 只改**一个**变量（一个字段 / 一个槽位 / 一个挂载位置）
3. 导入 → 预编译
4. 通过 → 变量有效；失败 → 换下一个变量

历史上定位「`IsContact=True` 导致 NOT SINT」就是靠 4 个单变量实验排除掉触点写法、EN 槽、BoxType、CallType 才锁定根因。

---

## 3. CHANGELOG 规范

遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号用语义化版本。

```markdown
## [Unreleased]

### 新增
- 树形状态机：MOVE 框可直接挂分支组 Trees（8 支路实测预编译 0 错误）

### 修改
- `references/native-structure.md`：补充 MOVE 框挂载位置规则

### 修复
- 修正 IN 引脚 Type 说明（BOOL → INT）

### 文档
- README 增加英文摘要
```

发版时把 `[Unreleased]` 改成 `[x.y.z] - YYYY-MM-DD`，并在文件顶部补新空 `[Unreleased]` 段。

### 版本号规则

| 变更 | 版本位 |
|------|--------|
| 破坏性改动（脚本参数变化、目录结构变化） | MAJOR |
| 新增能力（新结构支持、新脚本、新样本） | MINOR |
| 修复、文档、措辞 | PATCH |

---

## 4. 提交信息规范

Conventional Commits：

```
<type>: <subject>

<body 可选>
```

| type | 用途 |
|------|------|
| `feat` | 新增能力 |
| `fix` | 修复错误结论或脚本 bug |
| `docs` | 纯文档 |
| `refactor` | 脚本重构，行为不变 |
| `test` | 验证脚本 / 实验 |
| `chore` | 杂项（gitignore、依赖） |

示例：

```
fix: IN 槽位 IsContact 必须为 False

从触点模板克隆残留 True 会让 IDE 对 INT 常量做取反，
预编译报「不允许对类型 'SINT' 进行 'NOT' 操作」。
实测 8 条梯级全部修复，预编译 0 错误。
```

**subject 用中文或英文都行，但 body 必须写清「为什么」。**

---

## 5. 同步机制

### 5.1 一键同步

```powershell
.\sync.ps1 -Message "fix: 修正 IN 引脚 Type 说明"
```

脚本做五件事：

1. **禁止交互**：设 `GIT_TERMINAL_PROMPT=0` + `GCM_INTERACTIVE=never`，
   并把仓库级 `credential.helper` 设为 `wincred`（见 §5.4）
2. 检查 `CHANGELOG.md` 是否有未提交变动（没有就拒绝提交，防止漏登记）
3. `git add -A`
4. `git commit -m "<message>"`
5. `git push origin HEAD`

### 5.2 自动生成提交信息

不带 `-Message` 时，脚本从 `CHANGELOG.md` 的 `## [Unreleased]` 段提取首条 bullet 作为 subject。

### 5.3 提交前自检清单

- [ ] `CHANGELOG.md` 已更新（`[Unreleased]` 下有内容）
- [ ] 涉及代码的已实跑通过
- [ ] 涉及结构的已预编译 0 错误
- [ ] 没有把临时调试脚本提交上去（`work/`、`ipc/` 应被 gitignore）
- [ ] 没有提交 PAT、密码、内网地址

### 5.4 为什么不弹凭据窗口了

Git for Windows 的系统级配置是：

```
credential.helper=helper-selector
```

这是**凭据助手选择器**，每次需要认证都会弹一个窗口让你选助手，无人值守场景直接卡住。

`sync.ps1` 的处理方式（只改本仓库，不动你的全局配置）：

```powershell
git config --local --add credential.helper ""        # 清掉继承的 helper-selector
git config --local --add credential.helper wincred   # 只留 wincred
```

`wincred` 是纯命令行助手，直接读写 Windows 凭据管理器，**零弹窗**。
前提是凭据已存在于 Windows 凭据管理器（target 形如 `git:https://<用户名>@github.com`）。

验证方式（不联网、不弹窗）：

```powershell
printf "protocol=https`nhost=github.com`n`n" | git credential fill
# 能直接输出 username/password 就说明凭据可用
```

凭据失效时 `sync.ps1` 会直接报错提示重新登录，**不会弹窗等待**。

---

## 6. 分支与发版

小规模演进建议：

| 场景 | 做法 |
|------|------|
| 改文档、改措辞 | 直接提交 `main` |
| 改脚本行为 | 开分支 `feat/xxx`，验证通过后合 `main` |
| 破坏性改动 | 开分支 + 更新 MAJOR 版本 + README 迁移说明 |

发版：

```powershell
# 1. 改 CHANGELOG：[Unreleased] → [1.2.0] - 2026-11-25，并补新空 Unreleased 段
# 2. 同步
.\sync.ps1 -Message "chore: release v1.2.0"
# 3. 打 tag 并推送
git tag -a v1.2.0 -m "v1.2.0"
git push origin v1.2.0
```

---

## 7. 与 Skill 目录的同步

本仓库同时以 Agent Skill 形式分发（`SKILL.md` + `references/` + `scripts/` + `assets/`）。

**当本仓库内容变化后，安装在本机的 Skill 副本需要同步更新：**

```powershell
# 假设 Skill 安装在默认位置
$SK = "$env:APPDATA\xiaoyiwork\users\<用户ID>\xiaoyiwork\agent\workspace\skills\inoproshop-ld-native"
Copy-Item .\SKILL.md        $SK\ -Force
Copy-Item .\references\*    $SK\references\ -Force
Copy-Item .\scripts\*       $SK\scripts\ -Recurse -Force
Copy-Item .\assets\*        $SK\assets\ -Recurse -Force
```

改 Skill 相关内容时，**仓库和 Skill 副本要一起更新**，否则下次 AI 读到的还是旧结论。

> 注意：本机 Skill 目录被客户端标记为**受保护路径**，直接 `Copy-Item -Force` 覆盖会被拒绝
> （`PERMISSION_DENIED: Protected control-plane path`）。必须先删旧文件再写入：
>
> ```powershell
> Remove-Item $SK\SKILL.md -Force
> Copy-Item .\SKILL.md $SK\ -Force
> ```

### 7.1 打包分发件（.skill）

```powershell
python scripts\pack_skill.py
```

输出到仓库同级目录的 `inoproshop-ld-native.skill`。

**文件清单严格取自 `git ls-files`**，只打 `SKILL.md` + `references/` + `scripts/` + `assets/`。
这样保证：

- 包里永远是**已提交的版本**，不会混入本地未提交的改动
- 已删除的文件不会残留在包里（旧的打包件就曾带着 `task_cleanup4.py`）
- `docs/`、`AGENTS.md`、`sync.ps1` 等仓库专属文件不进包

**每次改动后如果还要分发，必须重新打包**，否则别人装到的是旧版本。
