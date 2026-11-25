# Changelog

本项目的所有重要变更都记录在此文件。

格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### 新增
- `scripts/pack_skill.py`：打包 `.skill` 分发件。文件清单严格取自 `git ls-files`，只打 `SKILL.md` + `references/` + `scripts/` + `assets/`，保证包里永远是已提交版本，不会混入本地改动或已删除的旧文件
- `references/precompile-errors.md` 第 6、7 类问题：C0046 批量未定义标识符、两个 TRUE 串联
- `references/native-structure.md`「声明区（TextLines）结构」与「公共前缀与支路条件去重」两节
- `scripts/examples/make_fix45.py`：补声明 + 删多余 TRUE 的修复脚本
- **分支组「完整支路」标准结构**（用户手改已验证）：外层 AND 框包住 `[MOVE 框, 连接器 {505bff94}]`；**任何一层（含嵌套分支组内部）都适用**
- `scripts/examples/make_full8.py`：把裸 MOVE 支路批量包装成完整支路的生成脚本

### 修改
- `assets/natives/user_fixed.native` 更新为**修复后最终版**：8 支路完整结构（3 顶层 + 内层 6）+ 声明区齐全，预编译 0 错误 0 警告；并在文档中标记为树形结构**首选克隆模板**
- **全部脚本去掉硬编码的用户目录**：`task_check.py` / `task_readnow.py` / `task_export_fixed.py` / `task_silent_import.py` / `plc_daemon.py` / `launch_ide_daemon.py` 的兜底路径统一为占位符 `D:\plc_mcp`（仍优先读 `PLC_MCP_BASE` / `PLC_MCP_IPC`）；`examples/make_full8.py` 改用 `PLC_SRC_NATIVE` / `PLC_DST_NATIVE`
- `README.md`：目录结构补全到实际文件（含 `scripts/examples/`、`sync.cmd`、各 `task_*.py` 用途）；铁律表新增第 9 条；「已验证的合法模式」补公共前缀去重与声明区
- `SKILL.md`：`assets/natives/` 与 `scripts/` 表格按实际用途重排；铁律新增第 9 条；合法模式补两条
- `docs/usage.md`：目录约定补全实际文件；快速排错索引补 §6 与 §7
- `docs/iteration.md`：新增 §5.4「为什么不弹凭据窗口了」，记录 `helper-selector` 弹窗根因与 `wincred` 方案
- `references/mcp-bridge.md`：修正 `bridge.py` 的 PowerShell 示例（原引号不匹配、路径末尾多一个 `/`），改为推荐 Python 调用 + 正确的 CLI 转义写法
- `references/native-structure.md`：重写「挂载位置规则」，补完整支路结构图与补齐前后对照表

### 修复
- **同步时弹「选择凭据助手」窗口**：Git for Windows 的系统级配置是 `credential.helper=helper-selector`，
  每次联网都会弹窗。`sync.ps1` 现在会自动把仓库级凭据助手设为 `wincred`（纯命令行读 Windows 凭据管理器，零弹窗），
  并强制 `GIT_TERMINAL_PROMPT=0` + `GCM_INTERACTIVE=never`；凭据失效时直接报错而不是弹窗等待
- **C0046 批量未定义标识符**（45 个错误的真实根因）：native 只搬「图形 + 声明文本」，图形引用的符号必须在 `Interface/TextDocument/TextLines` 里逐行声明；漏声明 = 每个引用点报一条错误。已为 `prg_StartStop` 补全 8 个状态机变量声明，45 → 0
- **两个 TRUE 串联**：分支组 `Input` 已有公共前缀 TRUE 时，支路 EN 条件框里不要再放 TRUE。已删除 8 条支路里多余的 TRUE
- **修正认知**：裸 MOVE 框挂分支组 Trees 虽预编译 0 错误，但功能链断头、图形不完整；任何层级都需外层 AND + 连接器包装
- `SKILL.md` / `README.md`：修正「内层是裸 MOVE 框」的表述——那是用户未改完的中间状态

### 删除
- `docs/github-新手操作手册.md` —— 一次性的对话式操作记录，不属于工具文档
- `scripts/ide/task_cleanup4.py` —— 硬编码了某个具体工程的 POU 白名单，无法复用

## [1.0.0] - 2026-11-24

### 新增
- 首次发布：LD native 结构知识（节点 GUID、槽位规则、挂载位置）
- 预编译错误对照表（5 类错误 → 根因 → 修复）
- MCP 文件 IPC 桥（`bridge.py` + `plc_daemon.py`）
- 静默导入（改名让位法，不弹确认框）
- 预编译检查脚本（`task_check.py`，读 `217bc73e` 分类）
- 4 份已验证 native 克隆模板

### 修复
- **根因定位**：值输入引脚（IN 槽）`IsContact` 必须为 `False`；从触点模板克隆残留 `True` 是预编译报
  `不允许对类型 'SINT' 进行 'NOT' 操作` 的根本原因（此前 4 个单变量实验排除了触点写法、
  EN 槽内容、BoxType、CallType）
