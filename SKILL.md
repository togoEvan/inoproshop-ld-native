---
name: inoproshop-ld-native
description: 汇川 InoProShop（CODESYS V3.5 SP11 系）LD 梯形图 native XML 直接生成与静默导入技能。当需要通过脚本/MCP 桥向已打开的 InoProShop 工程写入梯形图（LD）程序、生成功能框（MOVE/AND 等）、修改 native XML 结构、静默导入导出（不弹确认框）、或排查 LD 预编译错误（如"不允许对类型 'SINT' 进行 'NOT' 操作"、红框、格式无效）时使用。触发词：InoProShop、汇川、CODESYS、梯形图、LD、native、导入导出、MOVE 框、状态机写入、预编译错误。
---

# InoProShop LD Native 直接写入

## 核心工作流

1. 用 Python（xml.etree.ElementTree）从已验证的 native 样本克隆节点，修改后生成 native 文件
2. 经 MCP 桥（bridge.py → plc_daemon.py）静默导入到**已打开的工程**（不关 IDE、不弹框、不动鼠标）
3. 执行「检查程序」命令后读**预编译分类**消息验证

## 铁律（违反必踩坑）

1. **验收标准 = 预编译分类 0 错误**（`217bc73e-759b-4a3c-bfa1-991c938a6541`），不是编译分类（`97f48d64-a2a3-4856-b640-75c046e37ea9`，它永远显示 0 错误，build()/rebuild() 只填这个分类）
2. **功能框 InputItems 槽位数必须 == InputParam 参数数**（如 MOVE 的 [EN, IN] = 2 槽）
3. **值输入引脚（IN 槽）必须 `IsContact=False`** —— 从触点模板克隆时残留 `IsContact=True` 是预编译报 `不允许对类型 'SINT' 进行 'NOT' 操作` 的根因（IDE 把常量当触点做取反逻辑）
4. **操作数内部 Flags 的 Flags=1 是 NOT（取反）标志**，常量引脚必须清 0；触点取反则用 Flags=1 + IsContact=True
5. **IN 引脚 `Type=INT`、`Boolean=False`**（Type=BOOL 会红框）
6. **绝不动真实鼠标/不抢焦点**：只用消息式自动化（文件 IPC、PostMessage）；绝不 SetCursorPos/mouse_event/SetForegroundWindow
7. **不关闭 IDE**：改名让位法静默替换（先 `prg_X → prg_X_old_tmp` → import → 删旧）
8. **校验导出文件每次唯一命名**（如 `silent_after_HHMMSS.native`），否则弹覆盖确认框

## 结构速查（详见 references/）

- [native 结构与节点类型](references/native-structure.md)：全部节点 GUID、槽位规则、合法挂载位置
- [预编译错误对照表](references/precompile-errors.md)：错误 → 根因 → 修复
- [MCP 桥与命令](references/mcp-bridge.md)：bridge.py 用法、诊断脚本、消息分类 GUID

## 已验证的合法模式

- MOVE 框直接挂 `Network/NetworkItems`（不能挂 NETITEM.OutputItems 或 RValue → "已标识项格式无效"）
- **MOVE 框也可直接挂分支组 `{827b9ec2}` 的 `Trees`**：每条支路 = 一个 MOVE 框（内含 EN 槽 AND + IN 槽常量）。8 支路实测预编译 0 错误
- EN 槽放 AND 框（内含条件触点），IN 槽放常量引脚（IsContact=False + 内部 Flags=0）
- 触点并联：分支组 `{827b9ec2}` 内 Trees 放多个触点
- 触点/线圈取反、置位、复位都用 Operand 内部 Flags 位掩码：1=NOT、2=S、3=R
- **功能链末端的 `ENO` 引脚可以删掉**（不往后连接），实测预编译 0 错误

## 弃用路径（勿重试）

- PLCopenXML `import_xml`（schema 严格，反复失败）
- `export_xml` 读 ST（无参数构造函数错误）
- `system.get_messages()`（返回字符串数组 DeprecationWarning，必须用 `get_message_objects(category_guid)`）
- 全局 `find_named` 找 POU（会递归误命中 Task Configuration 里的调用对象；用 `app.get_children()` 过滤直接子对象）

## 维护规则（用户批准 2026-11-24）

- **遇新坑必回写**：每次 InoProShop LD native 写入任务中遇到新坑（新报错、新结构限制、新弹框/异常），任务完成后立即回写本技能——报错进 [precompile-errors.md](references/precompile-errors.md) 对照表，结构限制进 [native-structure.md](references/native-structure.md)，弃用路径进本文件"弃用路径"节
- **用户手改=已验证模式**：用户在 IDE 中手改修正的结构，导出对比确认后记录为"已验证模式"，后续生成必须照搬
- **回写时机**：任务收尾时统一回写，不阻塞排障过程

## 自带脚本与部署（scripts/ + assets/）

### scripts/（桥接与诊断，已做成环境变量可移植）

| 文件 | 用途 |
|------|------|
| bridge.py | IPC 客户端（本地 Python 3 运行） |
| do_replace.py | 静默导入入口（本地 Python 3 运行） |
| launch_ide_daemon.py | 启动 IDE + 注入 daemon（本地 Python 3 运行） |
| ide_trigger.ps1 | UIA 触发 daemon 注入 |
| ide/plc_daemon.py | IDE 内守护（IronPython 2.7） |
| ide/task_*.py | 诊断脚本（IronPython 2.7；`except Exception, e` 是合法语法，勿用 Python 3 校验） |

**环境变量**（换机部署时设置）：
- `PLC_MCP_BASE`：桥接工作目录（含 ipc/、ide/）
- `PLC_MCP_IPC`：daemon 的 IPC 目录（cmd.json/result.json 所在地）
- `INOPROSHOP_EXE`：InoProShop.exe 完整路径（launch_ide_daemon.py 用）

### 新机器部署步骤

1. 安装本 .skill（或复制整个技能目录到目标 skills/）
2. 选定工作目录（如 `D:/plc_mcp`），把 scripts/ 里 ide/ 结构照原样复制过去
3. 设环境变量 `PLC_MCP_BASE`、`PLC_MCP_IPC`（或改脚本内默认值）
4. 用 launch_ide_daemon.py 启动 IDE 注入 daemon（首次需一次「执行脚本文件」确认）
5. 之后全程静默：do_replace.py 导入 → task_check.py 验证预编译

### assets/natives/（克隆模板样本）

| 文件 | 用途 |
|------|------|
| ss_manual_142651.native | 用户手画并联起保停基线（触点/分支组标准样本） |
| prg_EM01_Logic.native | 旧工程完整 LD（功能框/多线圈/连接器样本） |
| user_fixed.native | 用户修正版（IN 引脚 IsContact=False 已验证） |
| startstop_state3.native | 最终通过预编译 0 错误版本（MOVE 状态字状态机） |

生成新 native 时**必须从这些已验证样本克隆节点**，不要凭空构造。
