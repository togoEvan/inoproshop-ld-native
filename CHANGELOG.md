# Changelog

本项目的所有重要变更都记录在此文件。

格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### 新增
- **分支组「完整支路」标准结构**（用户手改已验证）：外层 AND 框包住 `[MOVE 框, 连接器 {505bff94}]`；**任何一层（含嵌套分支组内部）都适用**
- `assets/natives/user_fixed.native` 更新为**8 支路全部完整版**：3 顶层支路 + 内层 6 支路，每条都是 AND[MOVE, CONN]，预编译 0 错误
- `plc_mcp/make_full8.py`：把裸 MOVE 支路批量包装成完整支路的生成脚本

### 修改
- `references/native-structure.md`：重写「挂载位置规则」，补完整支路结构图与补齐前后对照表
- `SKILL.md` / `README.md`：修正「内层是裸 MOVE 框」的表述——那是用户未改完的中间状态

### 修复
- **修正认知**：裸 MOVE 框挂分支组 Trees 虽预编译 0 错误，但功能链断头、图形不完整；任何层级都需外层 AND + 连接器包装
- 已把用户工程的 6 个裸 MOVE 支路（6/8/9/4/3/5）补齐为完整结构，逻辑不变，预编译 0 错误

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
