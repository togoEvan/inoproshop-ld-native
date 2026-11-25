# inoproshop-ld-native

> 汇川 InoProShop（CODESYS V3.5 SP11 系）梯形图（LD）**native XML 直接生成 + 静默导入**工具包。
> 给 AI Agent 用：读完本文件 + `AGENTS.md` 就能直接上手写梯形图，不需要人肉点鼠标。

[English summary](#english-summary) · [快速开始](#快速开始5-分钟) · [规范](docs/usage.md) · [迭代流程](docs/iteration.md)

---

## 这是什么

InoProShop 的梯形图存在一个 native XML 结构里。这个仓库提供：

1. **已验证的结构知识**（`references/`）：节点 GUID、槽位规则、预编译错误对照表。所有结论都经过实测，不是猜的。
2. **可运行的桥接脚本**（`scripts/`）：通过文件 IPC 向**已经打开的** InoProShop 进程注入 IronPython 脚本，实现导入 / 导出 / 预编译检查。
3. **克隆模板**（`assets/natives/`）：4 份已验证的 native 样本，生成新结构时从这里克隆，不要凭空构造。
   写**树形/分支组**结构时，必须从 `assets/natives/user_fixed.native` 克隆（见下方「已验证的合法模式」）。

**能做什么**

- 用脚本生成梯形图（触点、并联、线圈、置位/复位、AND 框、MOVE 功能框、状态字状态机）
- 静默替换工程内对象：不关 IDE、不弹确认框、不动鼠标、不抢焦点
- 触发预编译并读取真实错误，脚本化验收

**不能做什么**

- 不能替代对 IEC 61131-3 / 梯形图语义的理解（结构对 ≠ 逻辑对）
- 不保证跨 CODESYS 版本通用（结论基于 InoProShop，其他厂商 CODESYS 系需重新验证 GUID 与结构）

---

## 铁律（先读这段，能省几小时）

| # | 铁律 |
|---|------|
| 1 | **验收标准 = 预编译分类 0 错误**（`217bc73e-759b-4a3c-bfa1-991c938a6541`）。编译分类 `97f48d64-…` **永远显示 0 错误**，拿它验收等于没验收。 |
| 2 | 功能框 `InputItems` 槽位数 **必须等于** `InputParam` 参数数（MOVE = `[EN, IN]` 2 槽）。 |
| 3 | 值输入引脚（IN 槽）必须 `IsContact=False`。从触点克隆残留 `True` → 预编译报 `不允许对类型 'SINT' 进行 'NOT' 操作`。 |
| 4 | 操作数内部 `Flags/Flags=1` 是 **NOT 取反**标志。常量引脚必须清 0；触点取反才用 1。 |
| 5 | 常量引脚 `Type=INT`、`Boolean=False`（写成 `BOOL` 会红框）。 |
| 6 | 绝不 SetCursorPos / mouse_event / SetForegroundWindow。只走文件 IPC + PostMessage。 |
| 7 | 不关 IDE。静默替换用「改名让位法」：`prg_X → prg_X_old_tmp` → import → 删旧。 |
| 8 | 导出文件名每次唯一（`silent_after_HHMMSS.native`），否则弹覆盖确认框。 |
| 9 | **图形里引用的每个符号，声明区必须有一行对应声明**。`import_native` 不会替你补声明，漏一个就报一串 `C0046: 没有定义标识符`（每个引用点一条）。 |

完整对照见 [`references/precompile-errors.md`](references/precompile-errors.md)。

---

## 快速开始（5 分钟）

### 0. 前置

- Windows + InoProShop 已安装
- Python 3（跑桥接客户端）
- 目标机器有可写目录存放 `ipc/`

### 1. 部署（只需铺文件，不用配环境变量）

```powershell
# 选一个工作目录，把 scripts/ 原样铺过去
$BASE = "D:\plc_mcp"
New-Item -ItemType Directory -Force -Path "$BASE\ipc" | Out-Null
Copy-Item -Recurse .\scripts\* $BASE\
```

**就这一步。** 路径是自动解析的，不需要设环境变量——详见下方「路径怎么解析」。

### 2. 启动 IDE 并注入 daemon（每次开机/重开 IDE 做一次）

IDE 还没开，用这个（顺手把工程一起打开）：

```powershell
python "$BASE\launch_ide_daemon.py" --project="E:\你的工程\xxx.project"
```

工程路径也可以不写（只开 IDE 空窗口，自己手动打开工程）。IDE 路径会自动搜索常见安装位置，找不到时用 `--ide=<完整路径>` 指定。

**IDE 已经开着（你自己打开的工作工程）** —— 直接双击或用命令行跑：

```
scripts\start_daemon.cmd
```

它只用 UIA 的 `InvokePattern` 去点「工具 → 脚本 → 执行脚本文件」，**不移动鼠标、不抢键盘焦点、不激活窗口**，注入完打印 `[OK] 守护已就绪`。这也是「不打扰用户」的关键：日常写入全程走 IPC 文件，IDE 界面不会跳到前台。

首次会出现「执行脚本文件」确认框。**后续调用 `bridge.py` 时会自动用 UIA 点掉它**（`ide_trigger.ps1`），不需要人工介入；只有 IDE 完全没启动时才需要你手动点。

命令行调用也可以走 `scripts\bridge.cmd`（自动挑一个能跑的 Python 3，避开 Windows 应用商店的 0 字节 python.exe 存根）：

```
scripts\bridge.cmd ping
```

### 3. 生成 native → 导入 → 验收

```python
# 从 assets/natives/ 克隆节点，改内容，写到 work/xxx.native
python scripts\do_replace.py work\xxx.native Application prg_StartStop
```

```python
# 触发预编译并读错误（经桥在 IDE 内执行）
python -c "import sys; sys.path.insert(0, r'<BASE>'); import bridge; bridge.call('eval_file', path=r'<BASE>\ide\task_check.py')"
# 然后看 ipc/check.log 的「=== 预编译 : total=0 errors=0 ===」
```

三步闭环：**克隆 → 导入 → 预编译 0 错误**。只要预编译不为 0，就不要声称完成。

---

## 路径怎么解析（部署前必读）

**IDE 内脚本读不到你在 shell 里设的环境变量。** 这是实测结论：daemon 跑在 InoProShop 进程里，继承的是 IDE 启动那一刻的环境，`os.environ.get("PLC_MCP_BASE")` 永远是 `None`。

所以路径按这个顺序解析（`scripts/ide/_base.py`）：

| 优先级 | 来源 | 何时生效 |
|--------|------|----------|
| 1 | 环境变量 `PLC_MCP_BASE` | **仅当 IDE 由 `launch_ide_daemon.py` 启动**（子进程继承环境） |
| 2 | `<BASE>/base_path.txt` 第一行 | 手工兜底，适合 IDE 手动开、脚本放在奇怪位置的情况 |
| 3 | 从脚本自身路径反推 `scripts/ide/xxx.py → scripts/` | **默认路径，铺好文件就能用** |
| 4 | `D:\plc_mcp` | 最后兜底 |

IPC 目录另有自己的顺序，**和上面不同**：`<BASE>/ipc` 存在就用它，然后才看 `PLC_MCP_IPC`。原因是 IDE 进程会继承「启动它的那个 shell」里的环境变量——实测 IDE 被旧脚本启动时带着 `PLC_MCP_IPC` 指向旧目录，若环境变量优先，守护会把 `ready.flag` 写进旧目录，新版永远等不到就绪。

`bridge.py` 用同一套规则。日志里会打印实际解析结果和来源：

```
BASE = D:\plc_mcp (source: derive:D:\plc_mcp\ide)
```

看到 `source: fallback` 说明自动解析失败，此时写一个 `base_path.txt` 即可：

```powershell
Set-Content -Path "$BASE\base_path.txt" -Value $BASE -Encoding UTF8
```

### 相关环境变量

| 变量 | 用途 | 说明 |
|------|------|------|
| `PLC_MCP_BASE` | 工作根目录 | 只在 `launch_ide_daemon.py` 启动 IDE 时对 IDE 内脚本生效 |
| `PLC_MCP_IPC` | IPC 目录 | 一般不用设，默认 `<BASE>/ipc` |
| `INOPROSHOP_EXE` | IDE 可执行文件 | 给 `launch_ide_daemon.py` 用 |
| `PLC_PROJECT` | 工程文件 | 给 `launch_ide_daemon.py` 用，等价于 `--project=` |

---

## 目录结构

```
inoproshop-ld-native/
├── SKILL.md                      # Agent Skill 入口（YAML frontmatter + 铁律 + 工作流）
├── AGENTS.md                     # AI 协作契约：上手顺序、验收标准、改动必须同步
├── README.md                     # 本文件
├── CHANGELOG.md                  # 每次改动必须登记
├── LICENSE                       # MIT
├── docs/
│   ├── usage.md                  # 使用规范（环境、命名、验收、禁止事项）
│   └── iteration.md              # 迭代流程（改什么、怎么验证、怎么发版）
├── references/
│   ├── native-structure.md       # 节点 GUID、层级、槽位、声明区、合法挂载位置
│   ├── precompile-errors.md      # 错误 → 根因 → 修复（7 类）
│   └── mcp-bridge.md             # 桥的协议、命令、消息分类
├── scripts/
│   ├── bridge.py                 # IPC 客户端（本地 Python 3）
│   ├── do_replace.py             # 静默导入入口（本地 Python 3）
│   ├── launch_ide_daemon.py      # 启动 IDE + 注入 daemon
│   ├── pack_skill.py             # 打包 .skill 分发件（清单取自 git ls-files）
│   ├── ide_trigger.ps1           # UIA 触发注入（不动鼠标）
│   ├── start_daemon.cmd          # 一键给「已运行的 IDE」注入守护
│   ├── bridge.cmd                # 命令行入口（自动挑可用的 Python 3）
│   ├── ide/                      # IDE 内 IronPython 2.7 脚本
│   │   ├── _base.py              # 路径自解析（IDE 内环境变量无效，靠它定位）
│   │   ├── plc_daemon.py         # 守护进程（命令分发）
│   │   ├── task_check.py         # 预编译检查（验收必用）
│   │   ├── task_silent_import.py # 静默导入核心
│   │   ├── task_readnow.py       # 读当前全部消息（排查异步）
│   │   └── task_export_fixed.py  # 导出指定 POU（学结构用）
│   └── examples/                 # 生成脚本范例（可改环境变量复用）
│       ├── make_full8.py         # 裸 MOVE 支路批量包装成完整支路
│       └── make_fix45.py         # 补声明 + 删多余 TRUE
├── assets/natives/               # 已验证克隆模板（4 份）
├── sync.ps1                      # 一键：校验 CHANGELOG → commit → push
└── sync.cmd                      # PowerShell 执行策略绕过包装器
```

---

## 已验证的合法模式

- **MOVE 框**可直接挂 `Network/NetworkItems`。不能挂 `NETITEM.OutputItems` 或 `NETITEM.RValue`。
- **分支组里的「完整支路」= AND 框包住 `[MOVE 框, 连接器]`**，不是裸 MOVE 框。2026-11-25 用户手改验证：
  - 外层 AND 框 `InputItems` 两槽：`[0]` MOVE 框、`[1]` 连接器 `{505bff94}`
  - 裸 MOVE 框挂 Trees 虽能过预编译，但功能链断头，图形与后续串接都不完整
  - **无论哪一层（含嵌套分支组内部），支路都要这样包装**；唯一例外是分支组 `Input` 槽里的公共前缀触点
- **EN 槽**放 AND 框（内含条件触点，至少 2 个）；**IN 槽**放常量引脚。
- **触点并联**：分支组 `{827b9ec2}` 的 `Trees` 放多个支路节点。
- **树形状态机**：公共前缀只画一次（放分支组 `Input` 槽）+ 竖线分叉，靠分支组嵌套表达。
  **公共前缀已放在 `Input` 时，支路条件框里不要再放同样的 TRUE**，否则图形上出现两个 TRUE 串联。
- **取反/置位/复位**：Operand 内部 `Flags` 位掩码，`1=NOT`、`2=S`、`3=R`。
- **功能链末端不需要 ENO**：分支内最后一个功能框的 `ENO` 引脚可以删掉（不往后连接），已实测预编译 0 错误。
- **声明区**：`Interface/TextDocument/TextLines` 里逐行写 `VAR … END_VAR`；`Id` 全表唯一且递增。详见 `references/native-structure.md`。

---

## 弃用路径（别重试，会浪费时间）

- PLCopenXML `import_xml` —— schema 严格，反复失败
- `export_xml` 读 ST —— 无参数构造函数错误
- `system.get_messages()` —— 返回字符串数组，必须用 `get_message_objects(category_guid)`
- 全局 `find_named` 找 POU —— 会递归误命中 Task Configuration 里的调用对象；用 `app.get_children()` 过滤直接子对象
- 拿编译分类 0 错误当验收 —— 无效

---

## 贡献 / 迭代

任何改动都遵循 [`docs/iteration.md`](docs/iteration.md)：

1. 改之前先读 `references/`，确认结论是否已被验证过
2. 改动必须实测（预编译 0 错误 / 或明确说明是文档改动）
3. 更新 `CHANGELOG.md`
4. `.\sync.ps1 -Message "..."` 一键提交推送

详见 [`AGENTS.md`](AGENTS.md) 的「改动必须同步」一节。

---

## License

MIT，见 [LICENSE](LICENSE)。

---

## English summary

A toolkit for generating InoProShop (CODESYS V3.5 SP11-based) ladder-diagram (LD) **native XML** and silently importing it into an already-running IDE, with no dialogs, no mouse movement, and no IDE restart.

Key rules: acceptance means **zero errors in the precompile message category** `217bc73e-…` (the build category is always zero and proves nothing); function-block input slots must match `InputParam` arity; value input pins must have `IsContact=False`; operand `Flags=1` means NOT.

See `AGENTS.md` for the agent contract and `docs/usage.md` for the operational spec.
