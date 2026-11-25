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

1. **验收 = 预编译分类 0 错误 _且_ 编译分类 0 错误**。预编译 `217bc73e-759b-4a3c-bfa1-991c938a6541` 抓结构错误（槽位/IsContact/声明缺失）；编译 `97f48d64-a2a3-4856-b640-75c046e37ea9` 抓语义错误（如 AND 操作数不足）。**只读预编译会漏掉后者**——实测：预编译 0，构建报 N 条 `'AND'需要至少'2' 个操作数`。`task_check.py` 已同时跑「检查程序」+ `build()`
2. **功能框 InputItems 槽位数必须 == InputParam 参数数**（如 MOVE 的 [EN, IN] = 2 槽）
3. **值输入引脚（IN 槽）必须 `IsContact=False`** —— 从触点模板克隆时残留 `IsContact=True` 是预编译报 `不允许对类型 'SINT' 进行 'NOT' 操作` 的根因（IDE 把常量当触点做取反逻辑）
4. **操作数内部 Flags 的 Flags=1 是 NOT（取反）标志**，常量引脚必须清 0；触点取反则用 Flags=1 + IsContact=True
5. **IN 引脚 `Type=INT`、`Boolean=False`**（Type=BOOL 会红框）
6. **绝不动真实鼠标/不抢焦点**：只用消息式自动化（文件 IPC、PostMessage）；绝不 SetCursorPos/mouse_event/SetForegroundWindow
7. **不关闭 IDE**：改名让位法静默替换（先 `prg_X → prg_X_old_tmp` → import → 删旧）
8. **校验导出文件每次唯一命名**（如 `silent_after_HHMMSS.native`），否则弹覆盖确认框
9. **图形里引用的每个符号，声明区必须有一行对应声明**（`Interface/TextDocument/TextLines` 里的 `VAR…END_VAR`）。`import_native` 不会替你补声明；漏一个就报一串 `C0046: 没有定义标识符`，**每个引用点一条**（例：8 个未声明变量共 45 次引用 → 45 个错误）
10. **AND 框（含 NETWORK 顶层 `RValue` 的 AND）至少 2 个输入槽**。单条件 rung 只给 1 个槽时预编译不报错，但构建报 `'AND'需要至少'2' 个操作数`；补一个 `TRUE` 触点（`Operand=TRUE`、内部 `Flags=0`、`IsContact=True`）即可，语义不变
11. **分支组 `{827b9ec2}` 的 `Trees` 必须 ≥ 2 条支路**。只有 1 条时**预编译 0 错误、编译 0 错误，但 IDE 绘制该网络直接崩**：「在绘制该网络的时候遇到错误 / 不能显示内容 / 索引超出了数组界限」，堆栈在 `IBoxTreeParallel`。单支路**不要用 `branch()`、不要套 `NETITEM`**，直接把 AND 框挂 `NetworkItems`（act90 网络3 实测形态）
12. **改声明区必须锚定 `Interface` 再找 `TextLines`，禁止裸 `find('<Array Name="TextLines"')`**。一份 native 里 `TextLines` 至少 2 处：`Interface` 下的 POU 声明区 + EXECUTE 框 `STSnippet` 里的 ST 代码；`find()` 取文档中**靠前**的那个，而网络列表排在 `Interface` 之前，所以只要网络里有 EXECUTE 框，裸 `find` 就会把声明写进 ST 代码块、真正声明区留着骨架旧变量 → 预编译 40+ 条 `符号 'PROGRAM'/'FUNCTION_BLOCK'/'BOOL' 不能识别`（2026-11-25 实测 48 条）。正确：`raw.find('<Array Name="TextLines"', raw.find('<Single Name="Interface"'))`
13. **验收脚本「读不到消息」必须抛错，绝不能返回空列表当 0 错误**。按 GUID 匹配分类写成 `except Exception: continue` + `return []`，匹配失败就静默输出 `total=0 / 通过` —— **假通过**。实测预编译真实 48 条 Error，旧脚本报 `total=0 errors=0` 并判「通过」。必须 `raise`，并先打印全部分类便于核对
14. **往返 diff PASS 不等于内容正确**。`rt_diff` 一致只能证明「IDE 没改写我的结构」；源文件本身错时 IDE 原样保留，往返照样 PASS（2026-11-25 实测：两个 POU 都 diffs=0，但源文件声明区是错的）。必须配合双分类 0 错误 + **语义抽查**（打印声明区首行确认是 `PROGRAM xxx` / `FUNCTION_BLOCK xxx`）
15. **`OutputItems` 项数 == `OutputParam` 个数；`OutputParam` 含不含 `ENO` 由 `EN`/`ENO` 字段决定**。`EN/ENO=True` 的框（Function/Program/常规 FB/EXECUTE）第一项是 `ENO`；**`TON` 是 `EN/ENO=False`，`OutputParam=['Q','ET']` 不含 ENO**，两个输出不接线就写两个 `<Null/>`。19/19 样本 0 例外。⚠ 这条**预编译/编译/往返 diff 全都查不出来**（IDE 静默接受），只能靠 `scripts/check_slots.py` 或「项数 vs 参数数」比对发现——`fb_box()` 已加 `raise` 断言
16. **往 XML 文本节点塞自由文本必须转义 `<` `>` `&`**。网络注释/声明区/ST 代码都是直接拼进 `<Single Name="Comment" Type="string">…</Single>` 的，注释里写 `<Null/>` 会被解析成**真实子节点**，导致该 Network 的 `Comment` 下凭空多一个 `Null`，节点数不等、`rt_diff` 从某处起整段错位报几十处 diff（2026-11-25 实测 55 处）。统一走 `make_ld_learn.xml_text()`，且它必须定义在 `textlines_block()` **之前**。**排查提示**：diff 报「节点数不同 + 整段错位」时先看错位处父节点是不是 `Comment`/`Text`/`Title`/`Label`，是就 100% 是转义问题，别去改结构

## 结构速查（详见 references/）

- [native 结构与节点类型](references/native-structure.md)：全部节点 GUID、槽位规则、合法挂载位置
- [预编译错误对照表](references/precompile-errors.md)：错误 → 根因 → 修复
- [MCP 桥与命令](references/mcp-bridge.md)：bridge.py 用法、诊断脚本、消息分类 GUID

## 已验证的合法模式

- MOVE 框直接挂 `Network/NetworkItems`（不能挂 NETITEM.OutputItems 或 RValue → "已标识项格式无效"）
- **分支组 Trees 里的「完整支路」= 外层 AND 框包住 `[MOVE 框, 连接器 {505bff94}]`**（用户手改已验证 2026-11-25）。裸 MOVE 框挂 Trees 能过预编译但功能链断头、图形不完整
  - 外层 AND 的 `InputItems` 两槽：`[0]` MOVE 框、`[1]` 连接器（只有 Id 子节点）
  - **任何一层（含嵌套分支组内部）都要这样包装**；唯一例外是分支组 `Input` 槽的公共前缀触点
  - 写树形结构必须从 `assets/natives/user_fixed.native` 克隆（8 支路全完整版）
- EN 槽放 AND 框（内含条件触点，至少 2 个），IN 槽放常量引脚（IsContact=False + 内部 Flags=0）
- 触点并联：分支组 `{827b9ec2}` 内 Trees 放多个支路（**必须 ≥2 条**，单支路见铁律 11）
- 触点/线圈取反、置位、复位都用 Operand 内部 Flags 位掩码：1=NOT、2=S、3=R
- **功能链末端的 `ENO` 引脚可以删掉**（不往后连接），实测预编译 0 错误
- **公共前缀去重**：公共 TRUE 放分支组 `Input` 后，支路 EN 条件框里不要再放 TRUE（否则图形出现两个 TRUE 串联）
- **声明区**：`TextLines` 里逐行写声明，`Id` 全表唯一且递增（插完从 900 重排最省事），中文注释可直接写
  - ⚠ **定位必须锚定 `Interface`**（铁律 12）：`raw.find('<Array Name="TextLines"', raw.find('<Single Name="Interface"'))`
- **定时器框（TON）**：`CallType=FunctionBlock` 但 `EN/ENO=False`；顶层时 `InputItems[0]` 是连接器 `{5f9848d3}`，嵌在 AND 里时是条件触点 `{9de7f100}`（IsContact=True）；输出 Q/ET 可空接线（`Operand=""`）不报错；ST 里读 `ET` 直接写 `实例名.ET`
- **EXECUTE 框（LD 内嵌 ST）**：`BoxType=EXECUTE`、`CallType=None`（不是 And/Move/Function/FunctionBlock）、`ProvidesSTSnippet=True`、`STSnippet` 三层（`{b2131366}`→`{3b83b776}`→`TextDocument`→`TextLines`）；**直接挂 `Network/NetworkItems`，不套 NETITEM**；InputItems 仅 1 个连接器槽、OutputItems 仅 `<Null/>`
- **FUNCTION_BLOCK 里的 LD**：native 层与 PROGRAM **完全同构**（`TypeGuid=6f9dac99-…`、`EmbeddedTypeGuids=[a9ed5b7e,25e509de]`、`SpecialFunc=None`、`POULevel=Standard`、`DefaultViewMode=Ld` 全一致），**唯一区别是声明区首行**（`FUNCTION_BLOCK xxx` + VAR_INPUT/VAR_OUTPUT/VAR_IN_OUT/VAR 分段）。实测 `fb_LdLearnTest` 导入 + 双分类 0 + 往返一致
- **线圈 / 功能框输出引脚接线的 Operand 不带 `Name` 属性**（`<Single Type="{c9b2f165}">`）；触点/值引脚带 `Name="Operand"`、Instance 带 `Name="Instance"`。写错时预编译/编译/图形都正常，**只有往返 diff 会现形**（IDE 静默抹掉该属性）
- **`AND` 框与功能框的 `EN`/`ENO` 是两种形态**：`AND` 是 `<Null Name="EN" />` / `<Null Name="ENO" />`（无值）；功能框是 `<Single Name="EN" Type="bool">True|False</Single>`。`AND` 的 `InputParam`/`OutputParam` 是**空 List2**（无参数名），所以「槽位数 == 参数数」对 `AND` 不适用（它按条件个数自由伸缩，但**至少 2 槽**）
- **多输出 FB 实际接线**：`OutputItems` 每项的 `Operand.Type` 必须与 `OutputParam.Types` **逐字一致**，包括复合类型（`ARRAY [0..(c_uiEventNumber - 1)] OF BOOL`、`WSTRING(32)`、`sPmlCtrlCmd`）；`LValue=True`、`Boolean=False`、`IsCoil=False`、`IsSeriesCoil=False`、`SeriesIndex=-1`
- **轴控 FB 在 LD 里的调用**：`CallType=FunctionBlock`，`BoxType` 写 FB 名（如 `HC_MovePtpV`），`Instance.Operand` 写实例（可带数组下标 `fbPtpV[0]`）。**`[REF]` 形参在 `InputParam.Types` 里带 `[REF]` 后缀**（`HC_sPtpInfo[REF]`、`AXIS_REF_SM3[REF]`），但引脚 `Operand.Type` 写**去掉后缀**的实际类型；`AXIS_REF_SM3` 引脚的操作数直接写**轴名**（`Master`）。实测 `prg_AxisCallTest` 导入 + 双分类 0 + 往返一致
- **`CallType=Action`（调 POU 内 action）**：`BoxType` 写 action 名；只有 `EN` 一个参数、`InputItems` 1 个连接器槽；`OutputParam=['ENO']`、1 项 `<Null/>`。**`Instance.Operand` 和 `Instance.Type` 都是空字符串 `""`，不是 `<Null/>`**（这是第三种形态：`<Null/>`=Function/Program 无实例、实例名=FB、空串=Action）。实测 `prg_AxisCallTest` 网络2 通过
- **网络注释里的自由文本必须转义**（铁律 16）：`network()` 的 `comment` 和 `textlines_block()` 的每一行都过 `xml_text()`；`xml_text` 必须定义在 `textlines_block` **之前**
- **轴控指令不在 LD 里画**：`MC_Power`/`MC_MoveAbsolute`/`HMC_MoveJog` 等全部写在轴控 FB 内部的 **ST** 里（`Implementation` 的 `TextLines`），LD 层只出现「调用封装 FB」一个框。想在 LD 里直接画 `MC_xxx` 框走不通
- **轴引用必须放 `VAR_IN_OUT`**：`AXIS_REF_SM3` / `AXIS_REF_ETC_DS402_CS` 是结构体，放 `VAR_INPUT` 会复制一份，运动指令作用不到真实轴
- **输入引脚（值引脚 `{9de7f100}`）**：`IsContact=False`，内部 `Operand` 带 `Name="Operand"`；REF 形参在 `InputParam.Types` 里带 `[REF]` 后缀，引脚 `Operand.Type` 写去掉后缀的实际类型

## 弃用路径（勿重试）

- PLCopenXML `import_xml`（schema 严格，反复失败）
- `export_xml` 读 ST（无参数构造函数错误）
- `system.get_messages()`（返回字符串数组 DeprecationWarning，必须用 `get_message_objects(category_guid)`）
- 全局 `find_named` 找 POU（会递归误命中 Task Configuration 里的调用对象；用 `app.get_children()` 过滤直接子对象）

## 更新规则（用户批准 2026-11-25，四类触发）

### ⚠ 适用范围：只记中型 PLC 梯形图相关问题

**只记录 InoProShop（CODESYS V3.5 SP11 系）中型 PLC 梯形图 native XML 相关的问题**——结构、导入导出、预编译/编译错误、IDE 行为、工程配置。

**不记录**：git 推送、DNS、网络、凭据、代理、GitHub 访问这类**仓库工具链**问题。它们不是中型 PLC 知识，混进 `references/` 只会稀释信噪比。工具链问题直接在 `sync.ps1` / `sync.cmd` 等脚本里修，**不写文档、不记 CHANGELOG**。

**为什么分四类**：这四类分别对应知识库必须补的四种东西——**新知识**（没见过的格式）、**缺陷**（bug）、**教训**（吃过的亏）、**环境**（新配置）。少记任何一类，后人就会在同一处重踩。

| # | 类别 | 触发信号（满足任一即回写） | 落到哪 | 必带证据 |
|---|------|--------------------------|--------|---------|
| ① | **没见过的格式** | 见到 `references/` 里没有的：节点 GUID、层级嵌套、属性组合、`CallType` 取值、槽位排布、`Flags` 位含义、声明区写法 | `references/native-structure.md` 新增「XX 标准结构」一节<br>+ `assets/natives/` 存克隆样本<br>+ `scripts/examples/make_*.py` 加可复用生成器 | 结构解析输出 + 导入成功 + **双分类 0 错误** + 导出往返一致 |
| ② | **Bug** | 脚本报错 / IDE 崩 / 静默导入失败 / 弹框 / 验收脚本漏报 / daemon 异常 | 报错类 → `references/precompile-errors.md`（编号续写）<br>工具类 → 直接修 `scripts/` 并在 `docs/iteration.md` 记一条 | 报错**原文**（含堆栈）+ 复现步骤 + 根因 + 修复后验证结果 |
| ③ | **吃过的亏** | 按错误理解做过事、浪费了时间；或文档里已有结论被实测**证伪** | 提炼成**铁律第 N 条**（README + 本文件双写）<br>+ 相关 reference 加 `⚠` 警告块<br>+ `CHANGELOG` 的「修改」 | 「错在哪 / 对的是什么 / **怎么自检**」三句话，缺自检方法不算记完 |
| ④ | **新配置** | 换机器、换 IDE 版本、换工程路径、环境变量行为变、目录布局变（**限中型 PLC 侧**；git/DNS/凭据等工具链配置不记） | `references/mcp-bridge.md`「环境要点」<br>+ `scripts/ide/_base.py` 顶部注释<br>+ `docs/iteration.md` §7 | **一条自检命令**（能直接验证配置是否生效，而不是"我这边能用"） |

### 编程过程中哪些数据要回写（现场采集清单）

回写的前提是**手上真有东西**。这些数据要在报错/崩溃的**当次**就采下来，收尾只做归类，不重新取证。

| 数据 | 采集方式 | 必须原样留下的形态 | 服务于 |
|------|---------|-------------------|--------|
| 新结构的 XML | `task_export_fixed.py` 导出目标 POU | 完整 `.native` 文件（含 `Id`/`GUID`/层级），不是截图或摘要 | ① |
| 报错原文 | `ipc/check.log` 每条 message 的 `Text` + 分类 GUID | 整行照抄，连编号带标点（`C0046: 没有定义标识符 "x"`） | ② |
| 定位信息 | 报错所属 POU / 网络序号 / 行号 / 槽位 | 能唯一定位到「哪个 POU 的哪个网络」 | ② |
| 最小实验记录 | 单变量实验 | 改了哪个字段（旧值→新值）→ 导入 → check + build → 结果 | ②③ |
| 通过态证据 | `task_check.py` 末行 | 预编译 `total/errors` + 编译 `total/errors` + `=== 验收结论 ===` | ①③ |
| 往返一致性 | 导入后再导出，与源文件 diff | diff 结果 + 比对了哪些节点（只写"往返一致"不算证据） | ① |
| IDE 行为异常 | IDE 弹窗/崩溃框 | 标题 + 正文原文 + 堆栈特征（如 `IBoxTreeParallel`）+ 触发动作 | ②③ |
| 用户手改前后 | 手改前后各导出一次 | 两份 native + 结构差异结论 | 「已验证模式」 |
| 环境快照 | `check.log` 第一行 | `BASE = … (source: …)` + IDE 版本 + 工程绝对路径 | ④ |

**硬要求**：新结构类（①）缺「native 文件 / 双分类数字 / 往返 diff」任一项，**不许**写进 `references/`。

### 怎么跟其他 AI 解释「哪些该回写」

不要只说「遇到新坑要回写」，各人会各理解。统一用**四问自查法**，每问只答「有 / 无」：答「有」必须附证据，答「无」要写清查过哪个文件。

| 问 | 问的是什么 | 答「有」之后必须做的 |
|---|-----------|---------------------|
| Q1 新格式 | 有没有见到 `references/` 里查不到的 GUID / 层级 / 属性组合 / `CallType` / 槽位 / `Flags` / 声明写法？ | 导出样本 + `native-structure.md` 加一节 + 生成器 + 双分类 0 错误 + 往返一致 |
| Q2 Bug | 有没有哪一步报错 / 崩溃 / 弹框 / 导入失败 / 验收漏报 / daemon 异常？ | 报错原文（含堆栈）+ 复现步骤 + 根因 + 修复验证 |
| Q3 吃过的亏 | 有没有按错误理解做过事、浪费时间，或文档结论被实测推翻？ | 铁律第 N 条（README + SKILL 双写）+ `⚠` 块 + 「错在哪 / 对的是什么 / 怎么自检」 |
| Q4 环境 | 换机器 / IDE 版本 / 工程路径 / 环境变量行为 / 目录布局变了吗？ | `mcp-bridge.md` 环境要点 + `_base.py` 注释 + 一条能跑的自检命令 |

可直接粘贴给其他 AI 的完整说明块见 `AGENTS.md` §6.2（含硬规则 6 条与「常见误判」表），**别转述，原文照发**。

**四种常见误判**：①导入失败一次、重试就好 → 不写（不可复现）；②双分类 0 错误但图形打不开 → **写**（渲染错误不参与编译）；③用户手改过结构 → **写，最高优先**；④`git push` 超时/代理报错 → 不写（只修 `sync.ps1`）。

### 四类的共同底线

- **没有实测证据的结论不许写进 `references/`**。猜测写进去比不写更有害。
- **分类冲突时**（一个坑同时属于多类）：按「后人最可能在哪一步踩到」落**主库**，其余位置只放一句话 + 链接，不复制全文。
- **不许写的**：只跑过一次且无法复现的环境异常（除非能给稳定触发条件）、「可能是 XX 原因」这类未证实的推断、一次性调试脚本（进 `work/`，不进仓库）。

### 收尾检查清单（每次任务必过）

- [ ] 走完**四问自查**（Q1 新格式 / Q2 Bug / Q3 吃过的亏 / Q4 环境），逐条对表，别只挑自己记得的那条
- [ ] 现场采集清单里的数据采全了吗？（尤其报错原文、双分类数字、往返 diff）
- [ ] 每类都带了**证据**吗？（①双分类 0 错误 + 往返一致 ②报错原文 ③自检方法 ④自检命令）
- [ ] 属于③的，铁律加了吗？（README + SKILL 双写，AGENTS 条数同步）
- [ ] `assets/natives/` 需要加或**换**样本吗？（样本被证伪时必须替换，不能只加新的）
- [ ] `CHANGELOG.md` 写了吗？（`sync.ps1` 没看到 CHANGELOG 变动会拒绝提交）
- [ ] 重新打包 `.skill` 并同步本机技能目录了吗？

### 其他两条常驻规则

- **用户手改 = 已验证模式**：用户在 IDE 中手改修正的结构，导出对比确认后记录为「已验证模式」，后续生成必须照搬。
- **回写时机**：任务收尾时统一回写，不阻塞排障过程。

## 自带脚本与部署（scripts/ + assets/）

### scripts/（桥接与诊断，已做成环境变量可移植）

| 文件 | 用途 |
|------|------|
| bridge.py | IPC 客户端（本地 Python 3 运行） |
| do_replace.py | 静默导入入口（本地 Python 3 运行） |
| check_slots.py | **结构自检**（本地 Python 3 运行）：校验所有功能框「`OutputItems` 项数 == `OutputParam` 个数」与「`InputItems` 槽数 == `InputParam` 个数」，`AND` 框校验至少 2 槽。**唯一能发现「编译器查不出来的结构错误」的手段**（预编译/编译/往返 diff 都查不出来）。退出码 0/1，可当 CI 断言 |
| launch_ide_daemon.py | 启动 IDE + 注入 daemon（本地 Python 3 运行） |
| ide_trigger.ps1 | UIA 触发 daemon 注入 |
| ide/_base.py | 路径自解析（IDE 内环境变量无效，靠它从脚本路径反推 BASE） |
| ide/plc_daemon.py | IDE 内守护（IronPython 2.7） |
| ide/task_check.py | 预编译检查（**验收必用**，读 `217bc73e` 分类） |
| ide/task_silent_import.py | 静默导入核心（由 do_replace.py 调用） |
| ide/task_readnow.py | 不清空直接读全部消息（排查异步） |
| ide/task_export_fixed.py | 导出指定 POU（学结构用） |
| examples/make_*.py | 生成脚本范例。`make_full8.py` / `make_fix45.py` 读 `PLC_SRC_NATIVE` / `PLC_DST_NATIVE` 环境变量；`make_packml_cmd_test.py` / `make_fb_call_test.py` 用相对路径（前者含 `contact/coil/and_box/branch/netitem/network` 全套节点构造函数；后者含 `fb_box/pin/connector_input/output_target` FB 调用构造函数）；`make_ld_learn.py` 是**当前最完整的可复用基座**（`contact/value_pin/connector_slot/coil/fb_box/ton_box/execute_box/network/textlines_block/xml_text/build_pou` 全套，带 `__main__` 守卫可被 import）；`make_axis_call.py` 演示轴控 FB 调用 + `CallType=Action`；`extract_action_entry.py` 从模板 native 里切出 action Entry 原始 XML 作模板 |

`ide/*.py` 是 IronPython 2 语法，`except Exception, e:` 合法，**勿用 Python 3 的 ast 校验**。

**路径解析**（换机部署必读）：**IDE 内脚本读不到 shell 设的环境变量**（daemon 跑在 IDE 进程内，继承的是 IDE 启动那一刻的环境，实测恒为 `None`）。`ide/_base.py` 与 `bridge.py` 按此顺序自动定位：

1. 环境变量 `PLC_MCP_BASE`（仅当 IDE 由 `launch_ide_daemon.py` 启动时有效）
2. `<BASE>/base_path.txt` 第一行（手工兜底）
3. 从脚本自身路径反推 `scripts/ide/x.py → scripts/`（**默认，铺好文件即可用**）
4. `D:\plc_mcp`（最后兜底）

`ipc/check.log` 第一行会打印 `BASE = ... (source: ...)`，出现 `source: fallback` 就是解析失败，写个 `base_path.txt` 即可。

**环境变量**（可选）：
- `PLC_MCP_BASE`：工作根目录（含 ipc/、ide/）
- `PLC_MCP_IPC`：daemon 的 IPC 目录（cmd.json/result.json 所在地）
- `INOPROSHOP_EXE`：InoProShop.exe 完整路径（launch_ide_daemon.py 用）
- `PLC_PROJECT`：工程文件路径（launch_ide_daemon.py 用，等价 `--project=`）

### 新机器部署步骤

1. 安装本 .skill（或复制整个技能目录到目标 skills/）
2. 选定工作目录（如 `D:/plc_mcp`），把 scripts/ 里 ide/ 结构照原样复制过去
3. **不用设环境变量**——路径会自动从脚本位置反推。若铺在奇怪位置，写个 `base_path.txt`
4. 用 `launch_ide_daemon.py --project=<工程路径>` 启动 IDE 注入 daemon
5. 之后全程静默：do_replace.py 导入 → task_check.py 验证预编译

首次「执行脚本文件」对话框：IDE 已启动时 `bridge.py` 会自动用 UIA 点掉；只有 IDE 未启动才需人工点一次。

### assets/natives/（克隆模板样本）

| 文件 | 用途 |
|------|------|
| `user_fixed.native` | **首选模板**。8 支路树形状态机，完整支路（AND[MOVE, CONN]）+ 声明区齐全，预编译 0 错误 0 警告 |
| `ss_manual_142651.native` | 用户手画并联起保停基线（触点/分支组最小样本） |
| `prg_EM01_Logic.native` | 旧工程完整 LD（功能框/多线圈/连接器样本） |
| `startstop_state3.native` | 早期 MOVE 状态字版本（历史对照，新写请用 `user_fixed.native`） |
| `fb_call_test.native` | **FB 调用模板**。三类 CallType（Function/Program/FunctionBlock）各一个，含 REF 形参、实例调用、12 入 12 出；双分类 0 错误 |

生成新 native 时**必须从这些已验证样本克隆节点**，不要凭空构造。
