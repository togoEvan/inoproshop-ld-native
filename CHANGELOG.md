# Changelog

本项目的所有重要变更都记录在此文件。

格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### 新增（2026-11-26，F02_Struct 复制验证）

- **Struct DUT 全流程验证：F02_Struct_Verify**。`F02_Struct`（17 个顶层 DUT + SF01_Alarm 子文件夹 14 个报警结构体）整包导出 → `scripts/examples/make_f02_copy.py` 加 `_StructVerify` 后缀（类型名 + 成员名同加，跳过 `TYPE/STRUCT/UNION/END_*` 段标记行）→ 逐个 `import_native` 到新建文件夹 `F02_Struct_Verify`（复用 `make_gvl.folder_entry`），17/17 成功无弹窗。**A/B 验证**：ST POU `prg_StructVerifyUse` 挂 MainTask，正样本引用副本成员（`stClock.xBlink_1Hz_StructVerify` 等 + UNION 成员 `w字_StructVerify`）→ 预编译 0 错误、编译仅模板原有 1 条；负样本 `stClock.ZZZ_NotExist_Member` → 编译分类 **4 条真实错误**。结论：DUT 副本全局可见、验收链路有效。详见 `references/native-structure.md §29`。新增脚本：`task_export_f02.py`、`task_import_f02.py`、`task_f02_ab_test.py`、`task_f02_cleanup.py`、`task_list_folders.py`、`probe_windows.py`、`examples/make_f02_copy.py`。

### 修正（重要，2026-11-26）

- **`run_overwrite_import.py` 扫不到覆盖确认弹框（卡死 435s）**：覆盖确认模态框挂在**未被禁用**的框架窗口（标题 `InoProShop(V1.10.0.3)`）下，被禁用的是主工程窗口；旧逻辑「跳过 enabled 窗口、只扫被禁用窗口」导致弹框永远扫不到，`import_native` 卡 435s 直到人工点击。修法：不看 enabled，直接遍历每个顶层窗口的子控件找「全部(&A)」按钮；实测 `PostMessageW(BM_CLICK)` 点「全部」+「确定」即可解除。另外 bash heredoc 写 JSON 会吃反斜杠（`\\` 变 `//`），路径参数要用 `python -c` 或文件写入。

### 修正（重要）

- **铁律 24 二次修正：预编译分类的报错来自 `app.build()`，不是「检查程序」菜单命令**（2026-11-26）。
  上一版曾把「预编译出现 `ZZZ_NotExist_Symbol`」归因给菜单「检查程序」，**归因错误**。
  用「清空 → 单一动作 → 主机侧逐秒轮询」重做，三个可复现结论：

  | 动作（清空后单独执行） | 预编译 `217bc73e` | 编译 `97f48d64` |
  |---|---|---|
  | 什么都不做（对照） | 0 条 | 0 条 |
  | 菜单「检查程序」`ab02b3c3` | **0 条**（不刷新消息） | 0 条 |
  | `import_native` 导入 POU | 96→101 条，**ZZZ 0** | 0 条 |
  | `app.build()`（POU **未挂**任务） | 101 条，**ZZZ 1** | 105 条，**ZZZ 0** |
  | `app.build()`（POU **已挂** MainTask） | 101 条，**ZZZ 1** | 106 条，**ZZZ 2** |

  ⇒ **两分类的作用域差异仍然成立，且更强**：
  ① **预编译分类**在 `build()` 阶段覆盖 **Application 下全部 POU**，与是否挂任务无关（ZZZ 恒 1）；
  ② **编译分类**只含**挂进任务调用列表**的 POU（未挂 0 → 挂上 2）。
  ③ **菜单「检查程序」不产生任何消息**——它是走缓存的只读命令，不能用于验收。
  **用户反馈「点检查程序，预编译就有错误」的真实链路**：点「检查程序」后 IDE 触发了一次构建/检查，
  消息由构建阶段写入预编译分类；消息本身**留在分类里不会消失**，所以看起来像「检查程序产生的」。

- **铁律 18 复核后维持不变**：编译/检查类菜单命令读不到真实错误，验收必须靠**导入瞬间**或
  **`app.build()`** 产生的消息。`app.build()` 会**清空并重建**预编译分类（101 条由它写入），
  这一点与「菜单命令不刷新」不同，需分开记。

- **预编译消息是异步补齐的**：`system.clear_messages(cat)`（**必须传分类参数**，无参调用报
  `takes exactly 1 argument (0 given)`）后立刻读是 0 条，**约 10 秒**后才补齐到 101 条。
  清空后空闲 20s 仍是 0 条（不会自行恢复）。等待必须放主机侧 Python——IDE 脚本里 `sleep` 会冻死界面。

- **【重大修复】`task_check.py` 一直是假通过——`severity` 用 `getattr` 读不到值**（2026-11-26）。
  `ScriptMessage` 的属性 `severity` 是 .NET 枚举 `_3S.CoDeSys.Core.Messages.Severity`
  （取值 `Text` / `Error` / `Warning`），**`getattr(m, 'severity')` 返回空**，必须走
  `m.GetType().GetProperty('severity').GetValue(m, None)`。旧版用 `getattr` + 字符串匹配 `'err'`，
  于是真实 1 条 Error 被统计成 0、判「通过」。修复后同一工程实测：
  预编译 101 条 / 编译 105 条，准确抓到模板自带的 1 条
  `程序 E3_SystemTime 在多任务下存在多处调用`，结论「不通过」。
- **【重大修复】`app.build()` 会清空预编译分类并异步重建**。build 返回后**立刻**读预编译是
  **0 条**，约 10s 后才回到 101 条——所以「build 后立刻读」必然假通过。`task_check.py`
  已改为**只读不编译**；要强制重建就走「`task_build.py` → 主机侧 sleep ≥10s → `task_check.py`」。
  并在日志里对「预编译 0 条而编译有消息」这一异步窗口特征给出提示。

### 新增

- **判定实验脚本族**（`scripts/ide/`，参数统一走 `ipc/exp_args.json`，日志落 `ipc/exp/`）：
  `task_exp_clear.py`（清空 + 单一动作）、`task_exp_poll.py`（只读两分类条数与 ZZZ 命中）、
  `task_exp_delay.py`（命令后立即读，测延迟）、`task_exp_cmd.py`（按 GUID 只执行命令）、
  `task_exp_build.py`（只 `app.build()`）、`task_exp_op.py`（只删/只导入对象）、
  `task_exp_task.py`（挂/摘任务槽）、`task_exp_dump.py`（全分类 dump）、
  `task_exp_probe_editor.py` / `task_exp_probe_ui.py`（API 能力探测）。
- **证据归档** `references/evidence/notask-scope/`：34 份原始日志 + `README.md` 结论。

### 文档

- `README.md` 铁律 24、`SKILL.md` 铁律 25 按上述结论重写；
  `references/native-structure.md`「POU 参与编译的前提」整节重写为「两个分类的作用域」对照表。
- **CHANGELOG 整理**：Unreleased 下原有 6 组重复的 `### 新增 / 修复 / 修改` 标题合并为
  `修正 / 新增 / 修复 / 修改` 四节，同一主题的条目合并叙述，删除重复论证。

## [1.0.1] - 2026-11-25

### 新增

- **GVL（全局变量列表）全流程验证**：在真实产线工程里新建 `F01_Variable_GVLVerify` 文件夹，
  2 个手写 GVL + `F01_Variable` 的 8 个 GVL 副本（737 变量加 `_GVLVerify` 后缀），三阶段 A/B 对照：
  ① 手写 GVL 正样本 0 错误 / 负样本 2 条 ⇒ 变量确实全局可见；② 副本剥 `AT` 交给 IDE 分配，通过；
  ③ 副本保留 `AT` → **13 条「地址重复」**，按区平移 `MB +311228 / MW +2000` 后重叠 0，通过。
  新增生成器 `make_gvl.py`（GVL/Folder 骨架 + 花括号铁律 + GUID 关系）、`make_f01_copy.py`
  （复制 + 后缀 + `keep`/`drop` AT + 按区偏移）。
- **真实产线工程全量结构普查 + 端到端复现**（400 entries / 403 对象 / 5804 功能框 / 940 分支组）：
  - `NetworkItems` 直接子节点里**分支组是主流**（679 网络），`NETITEM` 直挂仅 18 —— 真实程序主结构是
    `NetworkItems → 分支组 → Trees`。分支组 `Mode` 恒为 `Sequential`（990/990），`Input` 节点
    **必须带 `Name="Input"` 属性**，漏写报「格式无效」。
  - `InputFlags` 只有 `FC_AxisAbsGo`/`FC_CylinderExe`/`ADD`/`LE` 是 `List2`，其余 `<Null/>`。
  - 比较框 `InputParam` 只有 `['EN']` 但 `InputItems` 恒 3 槽；可嵌套比较框。
  - `{505bff94}` 空占位只出现在 `InputItems` 槽 1。
  - `Instance.Operand` + `Instance.Type` 必须成对：FB 类 → 实例名 + BoxType 名，其余 → `<Null/>` + 空串。
  - `Implementation` 的 `Type` 属性区分语言：`{3b83b776}`=ST、`{25e509de}`=LD。
  - POU `MetaObject.TypeGuid` 语义表（PRG/FB/GVL/Folder/Task/Trace 等 10 类）。
  - 导出 XML 真实层级 + 4 个读取 bug（`Object` 是属性值不是标签名、容器不对称、`NETITEM` 无 `Name`、`Flags` 两层）。
- **Function 调用框 + MOVE 三形态 + 容器不对称铁律**（557 框无一例外）：
  `InputItems` 是 `<List2>` 直挂，`OutputItems` 是 `<Single>` 包 `<List2>`。
  Function 框 `OutputParam.Names[1]` 恒空串＝返回值槽（35/35），`OutputItems[i]` 与 `Names[i]` 按索引对应。
  MOVE 三形态：标准 EN+IN / 多槽触点链 / 嵌套框接 EN。框可嵌套（整体出现在另一个框的 `InputItems[0]`）。
- **轴控指令写法**：`MC_Power`/`MC_MoveAbsolute`/`HMC_MoveVelocity` 等**全部写在轴控 FB 内部的 ST 里**，
  LD 层只有「调用封装 FB」一个框，想在 LD 里直接画 `MC_xxx` 走不通。`[REF]` 形参在 `InputParam.Types`
  里带后缀、引脚 `Operand.Type` 写去掉后缀的实际类型。`HMC_Home` 的 `fHmoeVelocity` 是库里的**原始拼写错误**。
- **`scripts/ld_logic.py`：逻辑层验收（第四层）**——把 native 图形拓扑还原成布尔表达式，DNF 规范化后比对，
  Id 重编号/节点顺序不影响结论。补前四层盲区（双分类 0 错误只证明编译器不报错，往返 diff 只证明 IDE
  没改写结构，`check_slots` 只证明槽位对得上——**都不证明「画的是你要的逻辑」**）。
- `boot_daemon.py`（唯一守护注入入口）、`probe_daemon.py`（守护诊断）、`scan_all_native.py`（全工程批量导出）、
  `task_cmd_list.py` / `task_cmd_run.py`（枚举/执行 817 条 IDE 命令）、`task_msg_text.py`
  （`system.get_messages` 字符串接口 dump 消息）。

### 修复

- **【重大纠正】单条件 rung 不该建 AND 框，触点直挂 `NETITEM.RValue`**（用户质疑触发）。
  旧文档「单条件补 `TRUE` 触点占位」是绕行修法：TRUE 恒通等于没加。三方对照实测——2 槽 AND 可用但冗余、
  1 槽 AND 报 `'AND'需要至少'2' 个操作数`、**裸触点直挂 0 错误**。同时纠正「RValue 不能是裸触点」：
  合法值域是 功能框 / 分支组 / 连接器 / **裸触点**。
  **元教训**：凡是「必须补占位 / 必须加冗余元素」的绕行修法，都要追问「不绕行能不能直接不建这个东西」。
  生成器自检四层全过却仍错，因为它们校验的是「结构合法」，没有一层校验「这个结构该不该存在」。
- **`SystemExit` / `SystemError` 穿透 `except Exception` 杀死守护线程**：IronPython 2.7 里它们只继承
  `BaseException`。守护循环必须 `except BaseException`；`a_status()` 的在线查询失败要降级为字段而非抛错。
- **守护挂错 BASE**：`_base.resolve_base()` 从 `sys.argv[0]` 反推，手动执行过旧路径后会恒定到旧目录，
  导致 `bridge` 找不到 `ready.flag` 误判「未启动」。`boot_daemon.py` 强制改写 `sys.argv[0]` 并清理陈旧心跳。
- **分支组 `Trees` 只有 1 条支路 → IDE 绘制该网络直接崩**（`IBoxTreeParallel` 索引越界）。
  预编译 0 错误、编译 0 错误，但图形打不开。单支路**不要用 `branch()`、不要套 `NETITEM`**。
- **`TON` 的 `OutputItems` 少写一项**：`EN/ENO=False`，`OutputParam=['Q','ET']` 不含 ENO，不接线要写**两个**
  `<Null/>`。⚠ 这条预编译/编译/往返 diff 全都查不出来。
- **生成器把 POU 声明写进 EXECUTE 框的 ST 代码块**：裸 `find('<Array Name="TextLines"')` 命中了
  `STSnippet` 里的 ST 代码（`List2[NetworkList]` 在文档中排在 `Interface` 之前），预编译报 48 条错误。
  必须锚定：`raw.find('<Array Name="TextLines"', raw.find('<Single Name="Interface"'))`。
- **验收脚本假通过**：`except Exception: continue` + `return []` 把「读失败」伪装成「没错误」。
  实测真实 48 条 Error 却报「通过」。改为匹配不到分类即 `raise`，并先打印全部分类清单。
- **`CallType=Action` 的 `Instance.Operand` 必须是 `<Null/>`**：写成空 `<Single>` 会让 IDE 在框上方多画一个
  可填参数的红色小方框。旧结论「空字符串」是从自己导入再导出的文件里反推的**循环论证**。
  规律：`FunctionBlock` → `Single(实例名)`；`Action`/`Function`/`Program`/`And`/`Move` → `Null`。
- **`check_slots.py` 对比较框/MOVE/算术框误报**：按「槽数 == 参数名数」校验会把模板原生 POU 全部误报，
  已加 `_input_exempt()` 豁免。**元教训**：校验脚本的规则本身也要拿真实工程回归。
- **`AT %MBxxxx` 副本必冲突**（13 条地址重复）；**含 RETAIN 段的 GVL 无法字节级往返**（IDE 自动补地址）；
  **`ScriptPouObjectList.remove` 留空槽项**（唯一修法：导出 Task Config → 删空块 → 覆盖导入）；
  **`Task Configuration` 不允许改名**（必须覆盖导入 + 自动点「全部」）。

### 修改

- **验收标准统一为「双分类 0 错误」**，并把 `app.build()` 加进 `task_check.py`（只跑「检查程序」读不到构建期错误）。
- **库更新规则从「遇新坑必回写」升级为「四类触发」**：新格式 → `native-structure.md` + 样本 + 生成器；
  Bug → `precompile-errors.md` 或直接修脚本；吃过的亏 → 提炼铁律（README + SKILL 双写）；
  新配置 → `mcp-bridge.md`。每类规定必带证据。适用范围收窄为**只记中型 PLC 梯形图相关问题**
  （git/DNS/凭据等工具链问题不进知识库）。
- **全部脚本去掉硬编码用户目录**：`_base.py` 统一路径解析，优先级
  `sys.argv[0]` 反推 > `base_path.txt` > 环境变量 > `D:\plc_mcp`（环境变量对 IDE 内脚本无效）。

### 删除

- `docs/github-新手操作手册.md`（一次性对话记录）、`scripts/ide/task_cleanup4.py`（硬编码工程 POU 白名单）、
  被 `get_messages` 字符串接口取代的 `task_msg_snapshot*.py` 与被 `task_exp_*` 取代的
  `task_notask_{test,verify}.py`。

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
