# inoproshop-ld-native

> 汇川 InoProShop（CODESYS V3.5 SP11 系）梯形图（LD）**native XML 直接生成 + 静默导入**工具包。
> 给 AI Agent 用：读完本文件 + `AGENTS.md` 就能直接上手写梯形图，不需要人肉点鼠标。

[English summary](#english-summary) · [快速开始](#快速开始5-分钟) · [规范](docs/usage.md) · [迭代流程](docs/iteration.md)

---

## 这是什么

InoProShop 的梯形图存在一个 native XML 结构里。这个仓库提供：

1. **已验证的结构知识**（`references/`）：节点 GUID、槽位规则、预编译错误对照表。所有结论都经过实测，不是猜的。
2. **可运行的桥接脚本**（`scripts/`）：通过文件 IPC 向**已经打开的** InoProShop 进程注入 IronPython 脚本，实现导入 / 导出 / 预编译检查。
3. **克隆模板**（`assets/natives/`）：5 份已验证的 native 样本，生成新结构时从这里克隆，不要凭空构造。
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
| 1 | **验收 = 预编译分类 0 错误 _且_ 编译分类 0 错误**。预编译 `217bc73e-…` 抓结构错误（槽位、IsContact、声明缺失），编译 `97f48d64-…` 抓语义错误（如 AND 操作数不足）。**只读预编译会漏掉后者**——2026-11-25 实测：预编译 0，构建报 N 条 `'AND'需要至少'2' 个操作数`。`task_check.py` 已同时跑「检查程序」+ `build()` 并输出合计结论。 |
| 2 | 功能框 `InputItems` 槽位数 **必须等于** `InputParam` 参数数（MOVE = `[EN, IN]` 2 槽）。 |
| 3 | 值输入引脚（IN 槽）必须 `IsContact=False`。从触点克隆残留 `True` → 预编译报 `不允许对类型 'SINT' 进行 'NOT' 操作`。 |
| 4 | 操作数内部 `Flags/Flags=1` 是 **NOT 取反**标志。常量引脚必须清 0；触点取反才用 1。 |
| 5 | 常量引脚 `Type=INT`、`Boolean=False`（写成 `BOOL` 会红框）。 |
| 6 | 绝不 SetCursorPos / mouse_event / SetForegroundWindow。只走文件 IPC + PostMessage。 |
| 7 | 不关 IDE。静默替换用「改名让位法」：`prg_X → prg_X_old_tmp` → import → 删旧。 |
| 8 | 导出文件名每次唯一（`silent_after_HHMMSS.native`），否则弹覆盖确认框。 |
| 9 | **图形里引用的每个符号，声明区必须有一行对应声明**。`import_native` 不会替你补声明，漏一个就报一串 `C0046: 没有定义标识符`（每个引用点一条）。 |
| 10 | **AND 框（含 NETWORK 顶层 RValue 的 AND）至少 2 个输入槽**。单条件 rung 只有 1 个槽时预编译不报错，但构建报 `'AND'需要至少'2' 个操作数`；补一个 `TRUE` 触点即可（语义不变）。 |
| 11 | **分支组 `{827b9ec2}` 的 `Trees` 必须 ≥ 2 条支路**。只有 1 条时**预编译 0 错误、编译 0 错误，但 IDE 绘制该网络直接崩**（「在绘制该网络的时候遇到错误 / 不能显示内容 / 索引超出了数组界限」，堆栈在 `IBoxTreeParallel`）。单支路**不要用 `branch()`、不要套 `NETITEM`**，直接把 AND 框挂 `NetworkItems`。 |
| 12 | **改声明区必须锚定 `Interface` 再找 `TextLines`，禁止裸 `find('<Array Name="TextLines"')`**。一份 native 里 `TextLines` 至少有 2 处：`Interface` 下的 POU 声明区，以及 EXECUTE 框 `STSnippet` 里的 ST 代码。`find()` 取到的是**文档中靠前的那个**——只要网络里有 EXECUTE 框（在网络列表里排在 Interface 前面），裸 `find` 就会把 POU 声明写进 ST 代码块、真正的声明区留着骨架旧变量，**预编译报 40+ 条 `符号 'PROGRAM'/'FUNCTION_BLOCK'/'BOOL' 不能识别` + `应该用';' 替换'...'`**（2026-11-25 实测 48 条）。正确写法：`p = raw.find('<Array Name="TextLines"', raw.find('<Single Name="Interface"'))`。 |
| 13 | **验收脚本「读不到消息」必须抛错，绝不能返回空列表当 0 错误**。`get_message_objects` 需要分类对象；按 GUID 匹配分类时若写成 `except Exception: continue` + `return []`，一旦匹配失败就静默输出 `total=0 / 验收通过`——**这是假通过**。2026-11-25 实测：预编译真实有 48 条 Error，脚本却报 `预编译 : total=0 errors=0` 并判「通过」。`task_check.py` 已改为匹配不到分类即 `raise`，并先打印全部 5 个分类便于核对。 |
| 14 | **`OutputItems` 项数必须等于 `OutputParam` 个数，且 `OutputParam` 含不含 `ENO` 由 `EN`/`ENO` 字段决定**。`EN/ENO=True` 的框（Function/Program/常规 FB/EXECUTE）第一项是 `ENO`，之后才是真输出；**`TON` 是 `EN/ENO=False`，`OutputParam=['Q','ET']` 不含 ENO**。别把「第 0 项恒为 `<Null/>` 对应 ENO」当死规矩——照抄会给 TON 少写一个输出项。19/19 样本实测 0 例外。⚠ 这条**预编译、编译、往返 diff 全都查不出来**（IDE 静默接受），只能靠「项数 vs 参数数」比对发现。 |
| 15 | **往 XML 文本节点里塞自由文本，必须转义 `<` `>` `&`**。网络注释、声明区、ST 代码都是直接拼进 `<Single Name="Comment" Type="string">…</Single>` 的；注释里只要出现 `<Null/>`、`<>` 之类的字面量，XML 解析器就把它当成**真实子节点**。2026-11-25 实测：注释写 `不是 <Null/>`，导入后该 Network 的 `Comment` 下凭空多出一个 `Null` 子节点，节点数 363 vs 362，`rt_diff` 从 #275 起整段错位报 55 处 diff。**排查提示**：`rt_diff` 报「节点数不同 + 从某一处开始整段错位」时，先看那一处的父节点是不是 `Comment`/`Text`——十有八九是没转义。统一用 `make_ld_learn.xml_text()`。 |

| 16 | **`Instance.Operand` 只有 FB 才写实例名，其余一律 `<Null/>`；写成空 `<Single>` 会在框上方多画一个可填写的小方框**。规律（按 `CallType`）：`FunctionBlock` → `<Single Type="string">实例名</Single>`；`Action` / `Function` / `Program` / `And` / `Move` → `<Null Name="Operand" />`。2026-11-25 实测：`action_box()` 写成空 Single，IDE 在 actAbs 框上方画出一个**可填参数的红色小方框**；用户两次指出「正常调用没有这个小方块」「actAbs_NOPE 上面还是有小方框可以填写参数」——第二句正是关键线索：连名字错误的框也带方框，说明与 `Flags.Fixed`、与 BoxType 是否合法**都无关**，纯粹是 Operand 节点形态问题。全量对照 16 个真实 Action 框，**全部是 `<Null/>`**。⚠ 这条预编译/编译/往返 diff 全都查不出来。 |
| 17 | **不要在 IDE 脚本里 `time.sleep()` 或轮询消息——会把 InoProShop 界面冻住**。IDE 脚本跑在主线程上，`sleep(8)` + `process_messageloop()` 循环直接导致用户反馈「你在等待的时候软件卡死了」「还是卡死」。正确分工：**IDE 侧脚本只做「读一次、写文件、立刻返回」（<1s），计时与重试全部放主机侧 Python**。`scripts/ide/task_check.py` 已改为单次快照、零 sleep、零循环。 |
| 18 | **验收消息只能靠「导入后立刻读」，任何编译命令都走缓存、都读不到真实错误**。2026-11-25 逐个实测（工程里放必然报错的 `BoxType=actAbs_NOPE`）：`清理` / `重新编译` / `（旧）编译` / `检查所有对象` / `运行静态分析` / `生成代码` / `生成二进制文件` / `编译` → **预编译分类全部 0 条**；只有 `（旧）重新编译` 会真跑构建，但预编译仍是 0。**只有导入动作触发的自动检查会产出真实预编译消息**。⚠ 另有两个致命细节：① **绝不能 `clear_messages`**——错误消息是导入时产生的，清掉就永久丢失；② 不要用「把声明改一个字符再改回」来强制变脏，实测无效。 |
| 19 | **action 的 ST 体只能引用宿主 POU 声明区里的变量**。action 属于哪个 POU，就只认那个 POU 的 `VAR`。2026-11-25 实测：`prg_AxisCallTest` 的 `actAbs` 写了 `xPtpCond := ...`，而 `xPtpCond` 只在 `fb_AxisSkelTest` 里声明 → 预编译报 `[Error] actAbs | 没有定义标识符'xPtpCond'`。三个特征：① 消息归属对象是 **action 名**不是 POU 名；② 只在**预编译**分类，不在编译分类；③ 编译分类照样报「0 错误,0 警告」。 |
| 20 | **造负样本必须精确替换目标字段，不能连带改掉同名字段**。2026-11-25 踩坑：用 `s.replace('>actAbs<', '>actAbs_ZZZ<')` 造负样本，结果把 `BoxType` **和** action Entry 的 `Name` 一起改了 → `actAbs_ZZZ` 成了真实存在的合法 action，编译 0 错误是**正确结果**，却被误判为「验收链路失效」，白折腾一轮。正确做法：只改 `<Single Name="BoxType" Type="string">actAbs</Single>` 这一处，Entry 名保持 `actAbs`；改完先 `grep -c` 自查（BoxType 1 处、Entry Name 1 处）。 |

完整对照见 [`references/precompile-errors.md`](references/precompile-errors.md)。

> **铁律 12/13 的元教训**：往返 diff PASS **不等于**内容正确。上次 `rt_diff.py` 两个 POU 都是 `total structural diffs: 0`，但源文件本身就是错的——IDE 把错误原样保留，往返当然一致。**往返一致只能证明「IDE 没改写我的结构」，不能证明「我的结构是对的」**，必须配合双分类 0 错误 + 语义抽查（如打印声明区首行确认是 `PROGRAM xxx` / `FUNCTION_BLOCK xxx`）。
>
> **铁律 15 的反向提醒**：这条与 12/13 互补——12/13 说「diff PASS 不算数」，15 说「diff FAIL 可能是自己生成的 XML 不合法」。看到 diff FAIL 先别改结构，**先确认报错位置是不是 `Comment`/`Text` 这类文本节点**。
>
> **铁律 18 的元教训（本轮最大教训）**：我连续三轮把「编译命令报 0 错误」当成「代码没问题」，实际上**所有编译命令都在读缓存**。真正的错误消息只在**导入瞬间**产生一次，`clear_messages` 一清就永久消失。所以验收流程必须是：**导入 → 等 1~2 秒（主机侧）→ 单次读快照**，而不是「清消息 → 编译 → 读」。另外，反向验证是唯一能证明验收链路有效的手段——但负样本本身必须造对（铁律 20）。

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
# 触发预编译 + 构建，读两个分类的错误（经桥在 IDE 内执行）
python -c "import sys; sys.path.insert(0, r'<BASE>'); import bridge; bridge.call('eval_file', path=r'<BASE>\ide\task_check.py')"
# 然后看 ipc/check.log 的「=== 验收结论 : 通过 (预编译+编译合计 0 错误) ===」
```

三步闭环：**克隆 → 导入 → 验收（预编译 + 编译都 0 错误）**。只跑预编译不算验收完。

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
│   ├── precompile-errors.md      # 错误 → 根因 → 修复（8 类，含 2b 单条件 AND）
│   └── mcp-bridge.md             # 桥的协议、命令、消息分类
├── scripts/
│   ├── check_slots.py            # 结构自检：槽位数 vs 参数数 + Operand 三态断言
│   ├── check_symbols.py          # 符号自检：网络引用 vs 声明区
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
│   │   ├── task_check.py         # 验收检查（必用，三分类单次快照）
│   │   ├── task_silent_import.py # 静默导入核心
│   │   ├── task_readnow.py       # 读当前全部消息（排查异步）
│   │   └── task_export_fixed.py  # 导出指定 POU（学结构用）
│   └── examples/                 # 生成脚本范例（可改环境变量复用）
│       ├── make_full8.py         # 裸 MOVE 支路批量包装成完整支路
│       ├── make_fix45.py         # 补声明 + 删多余 TRUE
│       ├── make_packml_cmd_test.py  # 从零生成完整 POU（7 网络 PackML 命令层）
│       └── make_fb_call_test.py     # FB 调用（Function/Program/FunctionBlock 三类）
├── assets/natives/               # 已验证克隆模板（5 份，含 fb_call_test.native）
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
2. 改动必须实测（**预编译 + 编译双分类 0 错误** / 或明确说明是文档改动）
3. 更新 `CHANGELOG.md`
4. `.\sync.ps1 -Message "..."` 一键提交推送

**回写四类触发**（详见 [`AGENTS.md`](AGENTS.md) §6 与 [`docs/iteration.md`](docs/iteration.md) §2.1）：

> **适用范围：只记中型 PLC 梯形图相关问题。** git 推送 / DNS / 网络 / 凭据等仓库工具链问题
> 不进知识库——它们不是中型 PLC 知识，混进来只会稀释 `references/` 的信噪比。
> 工具链问题直接在 `sync.ps1` / `sync.cmd` 里修，不写文档、不记 CHANGELOG。

| # | 类别 | 落到哪 |
|---|------|--------|
| ① | **没见过的格式**（新 GUID / 层级 / 属性组合 / 槽位排布） | `native-structure.md` + `assets/natives/` + `scripts/examples/` |
| ② | **Bug**（脚本报错 / IDE 崩 / 导入失败 / 验收漏报） | `precompile-errors.md` 或直接修 `scripts/` |
| ③ | **吃过的亏**（理解错、结论被证伪） | 提炼成铁律（README + SKILL 双写）+ `⚠` 块 |
| ④ | **新配置**（换机器 / IDE 版本 / 路径 / 凭据） | `mcp-bridge.md` 环境要点 + 一条自检命令 |

**判定的统一口径**（换人、换 AI 都照这个来）：

- **四问自查**：Q1 有没有 `references/` 里查不到的格式？Q2 有没有哪一步报错/崩溃/弹框/漏报？Q3 有没有按错误理解做事、或文档结论被推翻？Q4 环境有没有变？——每问只答「有 / 无」，答「有」必须附证据，答「无」要写清查过哪个文件。
- **现场采集清单**（报错当次就要采，收尾不重新取证）：新结构的完整 `.native`、报错原文整行、定位信息、最小实验记录、双分类错误数、导出往返 diff、IDE 弹窗原文、用户手改前后两份 native、环境快照。
- **硬要求**：①类缺「native 文件 / 双分类数字 / 往返 diff」任一项，不许写进 `references/`。

细节见 [`AGENTS.md`](AGENTS.md) §6.1（采集清单）、§6.2（四问自查 + **可直接粘贴给其他 AI 的说明块** + 常见误判表），以及 [`docs/iteration.md`](docs/iteration.md) §2.1.1 / §2.1.2。

详见 [`AGENTS.md`](AGENTS.md) 的「改动必须同步」一节。

---

## License

MIT，见 [LICENSE](LICENSE)。

---

## English summary

A toolkit for generating InoProShop (CODESYS V3.5 SP11-based) ladder-diagram (LD) **native XML** and silently importing it into an already-running IDE, with no dialogs, no mouse movement, and no IDE restart.

Key rules: acceptance means **zero errors in the precompile message category** `217bc73e-…` (the build category is always zero and proves nothing); function-block input slots must match `InputParam` arity; value input pins must have `IsContact=False`; operand `Flags=1` means NOT.

See `AGENTS.md` for the agent contract and `docs/usage.md` for the operational spec.
