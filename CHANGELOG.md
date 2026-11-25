# Changelog

本项目的所有重要变更都记录在此文件。

格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### 新增
- 树形状态机：MOVE 框可直接挂分支组 `{827b9ec2}` 的 `Trees`（8 支路实测预编译 0 错误）
- 分支内最后一个功能框可省略 `ENO` 引脚（不往后连接），实测预编译 0 错误
- `AGENTS.md`：AI 协作契约（上手顺序、验收标准、改动必须同步）
- `docs/usage.md`：操作规范（环境、命名、验收、禁止事项）
- `docs/iteration.md`：迭代流程（改动分类、CHANGELOG、提交信息、发版）
- `sync.ps1`：一键校验 CHANGELOG → commit → push
- `docs/github-新手操作手册.md`：面向非技术用户的 GitHub 建仓与登录推送步骤

### 修改
- `sync.ps1`：推送阶段增加最多 5 次重试与退避，仅对网络类错误重试（应对 github.com 连接抖动）
- `README.md`：改为面向其他 AI 的上手文档，含铁律表、快速开始、已验证模式、弃用路径
- `SKILL.md`：正文增加「已验证的合法模式」与「功能链末端可省略 ENO」说明

### 修复
- 修正 IN 引脚类型说明：应为 `Type=INT` 而非 `BOOL`（`BOOL` 会红框）

### 文档
- 补充英文摘要
- 补充「已验证的合法模式」小节

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
