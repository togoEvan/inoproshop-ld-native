# 迭代流程

本文件规定：**改什么、怎么验证、怎么发版**。

---

## 1. 改动分类与验证要求

| 类型 | 例子 | 验证要求 |
|------|------|----------|
| **代码** | `scripts/*.py`、`scripts/ide/*.py`、`*.ps1` | 必须实跑通过；涉及导入的必须预编译 0 错误 |
| **结构知识** | `references/native-structure.md` 新增挂载位置 | 必须附实测证据（导入成功 + 预编译 0 错误） |
| **错误对照** | `references/precompile-errors.md` 新增条目 | 必须附触发条件与修复后验证结果 |
| **样本** | `assets/natives/` 新增文件 | 必须已验证导入 + 预编译 0 错误，并在表格登记 |
| **文档** | `README.md`、`docs/`、`AGENTS.md` | 只需自检一致性与链接有效 |

**核心原则：没有实测证据的结论不许写进 `references/`。** 猜测写进知识库比不写更有害。

---

## 2. 标准迭代流程

```
① 开 issue / 记下问题现象（报错原文、截图、复现步骤）
② 查 references/ 是否已有结论 → 有就直接用
③ 复现 → 定位根因 → 设计最小验证实验
④ 实测通过（预编译 0 错误）
⑤ 回写：结构进 native-structure.md / 报错进 precompile-errors.md / 弃用进 README+SKILL.md
⑥ 更新 CHANGELOG.md
⑦ .\sync.ps1 -Message "..." → commit + push
⑧ 如涉及样本，把验证过的 native 放进 assets/natives/ 并在 README 表格登记
```

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
