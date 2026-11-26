---
name: inoproshop-ld-native
description: 汇川 InoProShop（CODESYS V3.5 SP11 系）LD 梯形图 native XML 直接生成与静默导入技能。当需要通过脚本/MCP 桥向已打开的 InoProShop 工程写入梯形图（LD）程序、生成功能框（MOVE/AND 等）、修改 native XML 结构、静默导入导出（不弹确认框）、或排查 LD 预编译错误（如"不允许对类型 'SINT' 进行 'NOT' 操作"、红框、格式无效）时使用。触发词：InoProShop、汇川、CODESYS、梯形图、LD、native、导入导出、MOVE 框、状态机写入、预编译错误。
---

# InoProShop LD Native 直接写入

## 核心工作流

1. 用 Python（xml.etree.ElementTree）从已验证的 native 样本克隆节点，修改后生成 native 文件
2. 经 MCP 桥（bridge.py → plc_daemon.py）静默导入到**已打开的工程**（不关 IDE、不弹框、不动鼠标）
3. 跑 `app.build()`，读**预编译 + 编译两个分类**验证（菜单「检查程序」不产生消息，不能用于验收）

## 铁律（违反必踩坑）

30 条，按主题分四组；编号与 `README.md` 一致（沿用历史编号、不重排）。完整论证见 `README.md`。

### A. 验收与消息

1. **验收 = 预编译 `217bc73e` 0 错误 _且_ 编译 `97f48d64` 0 错误**。预编译抓结构错误（槽位/`IsContact`/声明缺失），编译抓语义错误（AND 操作数不足等）。只读一个分类必漏。⚠ **`task_check.py` 只读不编译**：`app.build()` 会清空预编译分类再异步重建，build 后立刻读是 0 条（假通过）；强制重建须「`task_build.py` → 主机侧等 ≥10s → `task_check.py`」。
13. **验收脚本「读不到消息」必须抛错，绝不能返回空列表当 0 错误**。两个独立的假通过来源：① `except Exception: continue` + `return []` 把「读失败」伪装成「没错误」（实测真实 48 条 Error 却报「通过」）；② **`severity` 用 `getattr` 读不到值**——它是 .NET 枚举，必须 `m.GetType().GetProperty('severity').GetValue(m, None)`，否则恒空、统计恒 0。匹配不到分类即 `raise`，并先打印全部分类清单。
17. **不要在 IDE 脚本里 `sleep()` 或轮询消息**——IDE 脚本跑在主线程，会把界面冻死。IDE 侧只做「读一次、写文件、立刻返回」（<1s），**计时与重试全部放主机侧 Python**。
18. **消息来源只有两个可靠通道**：① `import_native` 导入瞬间；② `app.build()`。**编译/检查类菜单命令走缓存，读不到真实错误**；菜单「检查程序」`ab02b3c3` 实测**不产生任何消息**。⚠ 别指望 `clear_messages` 后消息自己回来；「改一个字符再改回」强制变脏实测无效。
23. **从未构建过的工程，编译分类 `97f48d64` 不存在**。必须先跑一次 `app.build()`（**不 clear**）才出现第 3 个分类。别因分类不存在就当 0 错误通过。真实工程构建后剩下的错误不一定是你的——先 `grep 你的 POU 名`，为 0 即无关。
24. **两分类作用域不同（2026-11-26 实测）**：① **预编译**在 `build()` 阶段覆盖 **Application 下全部 POU**，与挂不挂任务**无关**；② **编译**只含**挂进任务调用列表**的 POU。负样本：未挂任务 → 预编译 ZZZ **1** / 编译 **0**；挂上 MainTask → 预编译 **1** / 编译 **2**。⚠ 预编译消息**异步补齐**：`clear_messages(cat)`（**必须传分类参数**，无参报 `takes exactly 1 argument`）后立刻读 0 条，约 10s 后才 101 条；空闲 20s 仍是 0 条（不自恢复）。

### B. 结构合法性

2. **功能框 `InputItems` 槽位数必须 == `InputParam` 参数数**（MOVE = `[EN, IN]` 2 槽）。
3. **值输入引脚（IN 槽）必须 `IsContact=False`** —— 从触点模板克隆残留 `True` 是预编译报 `不允许对类型 'SINT' 进行 'NOT' 操作` 的根因。
4. **操作数内部 `Flags/Flags=1` 是 NOT（取反）标志**，常量引脚必须清 0；触点取反才用 1。`2`=S、`3`=R。
5. **IN 引脚 `Type=INT`、`Boolean=False`**（`Type=BOOL` 会红框）。
9. **图形里引用的每个符号，声明区必须有一行对应声明**。`import_native` 不补声明；漏一个就每个引用点报一条 `C0046`（8 个未声明变量共 45 次引用 → 45 个错误）。
10. **单条件 rung 不要建 AND 框**，触点直接作为 `NETITEM.RValue`。AND 框 ≥2 槽约束的是「框」：1 槽报 `'AND'需要至少'2' 个操作数` + `检测到不一致元素`；裸触点直挂 0 错误、往返不变。旧结论「补一个 `TRUE` 触点占位」**已作废**。
11. **分支组 `{827b9ec2}` 的 `Trees` 必须 ≥ 2 条支路**。只有 1 条时**预编译 0 / 编译 0，但 IDE 绘制该网络直接崩**（`IBoxTreeParallel` 索引越界）。单支路**不要 `branch()`、不要套 `NETITEM`**。
14. **往返 diff PASS ≠ 内容正确**。只证明「IDE 没改写我的结构」；源文件本身错时 IDE 原样保留。必须配合双分类 0 错误 + **语义抽查**（打印声明区首行确认 `PROGRAM xxx` / `FUNCTION_BLOCK xxx`）。
15. **`OutputItems` 项数 == `OutputParam` 个数**；含不含 `ENO` 由 `EN`/`ENO` 字段决定。**`TON` 是 `EN/ENO=False`、`OutputParam=['Q','ET']` 不含 ENO**，不接线要写**两个** `<Null/>`。⚠ 这条预编译/编译/往返 diff **全都查不出来**，只能靠 `check_slots.py`。
16. **往 XML 文本节点塞自由文本必须转义 `<` `>` `&`**。注释里写 `<Null/>` 会被解析成真实子节点，导致 `rt_diff` 整段错位。统一走 `xml_text()`，且必须定义在 `textlines_block()` **之前**。
21. **FB 类框的 `Instance.Type` 必须填 BoxType 名、`Instance.Operand` 必须填实例名**。写空 `Instance.Type` → `import_native` 抛 **「已标识项中有一项的格式无效。」**，且是**模态弹窗**：主线程阻塞 → 守护心跳停 → `bridge` 全部超时（看起来像「API 挂了」）。解除：`SendMessage(hButton, BM_CLICK=0x00F5, 0, 0)`。
22. **`check_slots.py` 不能按「输入槽数 == `InputParam` 名数」校验比较框 / MOVE / 算术框**。比较框 `InputParam` 只有 `['EN']` 但恒 3 槽；MOVE 恒 2 槽；ADD 恒 3 槽。已加 `_input_exempt()`。**元教训**：校验脚本的规则本身也要拿真实工程回归。

### C. 挂载与实例

6. **绝不动真实鼠标/不抢焦点**：只用消息式自动化（文件 IPC、`PostMessage`）；绝不 `SetCursorPos` / `mouse_event` / `SetForegroundWindow`。
7. **不关闭 IDE**：静默替换用「改名让位法」（`prg_X → prg_X_old_tmp` → import → 删旧）。
8. **导出文件每次唯一命名**（`silent_after_HHMMSS.native`），否则弹覆盖确认框。
12. **改声明区必须锚定 `Interface` 再找 `TextLines`**，禁止裸 `find('<Array Name="TextLines"')`。`TextLines` 至少 2 处（声明区 + EXECUTE 框 `STSnippet`），网络列表排在 `Interface` 之前，裸 `find` 会把声明写进 ST 代码块 → 预编译 40+ 条 `符号 'PROGRAM'/'BOOL' 不能识别`（实测 48 条）。
19. **action 的 ST 体只能引用宿主 POU 声明区的变量**。三个特征：① 消息归属对象是 **action 名**不是 POU 名；② 只在**预编译**分类；③ 编译分类照样报「0 错误, 0 警告」。
20. **造负样本必须精确替换目标字段**。`s.replace('>actAbs<', ...)` 会把 `BoxType` **和** Entry `Name` 一起改 → 0 错误是**正确结果**却被误判「验收链路失效」。改完 `grep -c` 自查。

### D. 任务配置与 GVL

25. **`ScriptPouObjectList.remove("名字")` 不报错，但留下 `Name=""` 空槽项**，之后编译报 `MainTask: 期望标识符，而不是''`。`remove(idx)`/`remove(item)`/`replace(idx,'')`/`Item[i]` 全都摘不掉。**唯一可靠修法**：导出 Task Configuration native → 删掉空 `<Single Type="{f194d1ef-…}">` 块 → 覆盖导入。
26. **`Task Configuration` 不允许改名**（报 `名称 'Task Configuration_old_tmp' 对于本工程无效。`）。必须走「`import_native` 同名覆盖 + 主机侧自动点『全部(&A)』」（`run_overwrite_import.py`）。⚠ 2026-11-26 修正：覆盖确认弹框挂在**未被禁用**的框架窗口（标题 `InoProShop(V1.10.0.3)`）下，不是被禁用的主窗口——自动点击不能按「窗口被禁用」筛，直接遍历所有顶层窗口找「全部(&A)」按钮；实测 `PostMessage(BM_CLICK)` 先点「全部」再点「确定」可解除。
27. **`AT %MBxxxx` 是绝对物理地址，副本沿用原件地址必然冲突**（实测 13 条「地址重复」）。两条合法路线：① 剥掉 `AT` 交给 IDE 分配；② 保留但整体平移到空闲区间（实测 `MB +311228 / MW +2000` 后重叠 0）。⚠ 正则要吃 `AT%MW1000` 无空格写法，用 `\s*` 不是 `\s+`。
28. **含 `PERSISTENT RETAIN` / `RETAIN PERSISTENT` 段的 GVL 无法字节级往返**。IDE 会自动补绝对地址并规范化字面量（`:=TRUE` → `AT %MB131099 : BOOL := TRUE`）。普通 `VAR_GLOBAL` 与 `CONSTANT` 段不被改写，只能逐字段比对。
29. **GVL = `Object > Interface > TextDocument > TextLines`**（无 `NetworkList`、无 `Implementation`）。一个 GVL 内可有多段 `VAR_GLOBAL`；`EmbeddedTypeGuids` 是 `Array[a9ed5b7e]` 单元素（Folder 的是 `<Null/>`）。
30. **Folder 的四条 GUID 关系**：`Properties.ParentObjects` 的 Key = 导出根 SV Guid、Value = 父容器 guid；`ParentSVNodeGuid` = 该 Value；`MetaObject.ParentGuid` = **祖父** guid（直属 Application 的 Folder → 全零）；被导出的 Folder 自身 `IsRoot=True`。

### E. CAM（电子凸轮）与曲线

| # | 铁律 |
|---|------|
| 35 | **CAM 直线段的 `p1` 是段内增量，不是终点绝对值**。`y(u) = p0 + p1·u`（u 为段内归一化 0..1），故 `p1 = y1 - y0`。按「p0=起点、p1=终点」写停歇段（`p0=45 p1=45`）会算出 `y(1)=90`、斜率 45，与相邻五次多项式段的零速度冲突，Cam 分类报 `在点 (240/45) 的连续性要求不能填充 速度`。**自检**：`p0 == cp0.Y` 且 `p0+p1 == cp1.Y`，两条都成立才对。 |
| 36 | **分度凸轮必须 `Periodic=False`**。摆动凸轮回原点（`y(360)==y(0)`）才用 `True`；分度凸轮每周期累进 H（`y(360)==y(0)+H`），沿用 `True` 会报 `在点 (0/0) 的连续性要求不能填充 位置`+`速度`。**自检**：`y(360)-y(0) != 0` 就必须 `False`。⚠ CAM 错误**只落 Cam 分类 `de128929`**，预编译/编译可能全 0——只看那两个会漏判通过；Cam 子对象也**无法脚本删除**（`remove`/`replace` 均失败），只能同名覆盖导入。详见 `references/native-structure.md §32`。 |

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
- **`CallType=Action`（调 POU 内 action）**：`BoxType` 写 action 名；只有 `EN` 一个参数、`InputItems` 1 个连接器槽；`OutputParam=['ENO']`、1 项 `<Null/>`。**`Instance.Operand` 必须是 `<Null/>`**（旧结论「空字符串 `""`」已证伪——那是从自己导入再导出的文件里反推的**循环论证**；写成空 `<Single>` 会让 IDE 在框上方多画一个可填参数的红色小方框）。规律见铁律 21：`FunctionBlock` → `Single(实例名)`；其余一律 `Null`
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
| check_slots.py | **结构自检**（本地 Python 3 运行）：校验所有功能框「`OutputItems` 项数 == `OutputParam` 个数」与「`InputItems` 槽数 == `InputParam` 个数」，`AND` 框校验至少 2 槽，并断言 **`Instance.Operand` 三态**（`FunctionBlock`→`<Single>实例名</Single>`；`Action`/`Function`/`Program`→`<Null/>`，写空 `<Single>` 会让 IDE 多画可填参数小方框）。⚠ 容器不对称：`InputItems` 直接挂 `List2`、`OutputItems` 是 `Single>List2`；⚠ MOVE 豁免：IDE 原生「嵌套框接 EN」与「多槽触点链」形态下输入槽 ≠ InputParam 数是正常的（详见 native-structure.md「MOVE 三形态」）。**唯一能发现「编译器查不出来的结构错误」的手段**（预编译/编译/往返 diff 都查不出来）。退出码 0/1，可当 CI 断言 |
| check_symbols.py | **符号自检**（本地 Python 3 运行）：校验 POU 网络里引用的符号是否都在声明区定义过。用于「编译器没报错、消息窗口读不到，但 POU 打开就是红的」这类问题——不依赖 IDE 消息，直接比对操作数与声明 |
| ld_logic.py | **逻辑层验收**（本地 Python 3 运行）：把 native 图形拓扑还原成布尔表达式并 DNF 规范化。单文件打印逻辑签名 / 双文件逻辑等价比对。**第四层验收**，补前三层盲区：双分类 0 错误只证明「编译器不报错」、往返 diff 只证明「IDE 没改写结构」、check_slots 只证明「槽位数对得上」——都不证明「画的是你要的逻辑」。学自 `Wayan123/multi-plc-agent`（`The verification compares logic, not XML`）：Id 重编号、节点顺序变化都不影响比对。已知局限：分支组内 MOVE 框 / EXECUTE 块无法还原成布尔式，显示为 `TRUE` 或 `BLOCK:类型(实例)` |
| launch_ide_daemon.py | 启动 IDE + 注入 daemon（本地 Python 3 运行） |
| ide/boot_daemon.py | **守护注入的唯一推荐入口**（IDE 内 IronPython 2.7）。`ide_trigger.ps1` 的 UIA 自动注入在 InoProShop 上**根本不可能成功**——菜单是自绘的，UIA 枚举整个窗口树 `MenuBar`=0、`MenuItem`=0，Win32 `GetMenu` 也返回 0（2026-11-25 实测）。所以必须人工点一次菜单：`工具 → 脚本 → 执行脚本文件... → 选本文件`。它解决三个坑：① 自解析目录（`PLC_IDE_DIR` > `sys.argv[0]` > 已加载 `plc_daemon.__file__`），避开「守护挂到历史遗留的 `D:\plc_mcp` 导致 bridge 误判未启动」；② 强制改写 `sys.argv[0]` 让 BASE 恒等于本技能包；③ 命名空间钉在 `sys._plc_mcp_keep` 防止被 GC、并单独捕获 `SystemExit` 防止重复注入掀掉正在跑的线程 |
| ide/probe_daemon.py | **守护诊断**（本地 Python 3）：一次打印 IDE 进程 / 各候选 BASE 的 `ready.flag` 与心跳年龄 / `bridge` 解析到的 BASE / `ping` 结果。**卡住时先跑它**，能直接判出「没注入」还是「注入了但挂错目录」 |
| ide_trigger.ps1 | UIA 触发 daemon 注入（⚠ **对 InoProShop 无效**，菜单自绘不暴露 UIA；保留仅供其它 CODESYS 系 IDE 参考） |
| ide/_base.py | 路径自解析（IDE 内环境变量无效，靠它从脚本路径反推 BASE） |
| ide/plc_daemon.py | IDE 内守护（IronPython 2.7）。⚠ **循环与命令执行层必须兜 `BaseException`**：IronPython 里 `SystemExit`/`KeyboardInterrupt`/`SystemError` 都**不继承 `Exception`**，只写 `except Exception` 会让一个 `raise SystemExit` 穿透并杀死整个轮询线程（实测现象：注入后 0.7s 心跳停摆、bridge 全超时，日志里却只有一行无关信息） |
| ide/task_check.py | 验收检查（**验收必用**，单次快照、零 sleep、零循环——IDE 脚本跑主线程，sleep/轮询会冻死界面，计时全部放主机侧；同时读预编译 `217bc73e` + 编译 `97f48d64` + 格式检查三分类，匹配不到分类必须 `raise` 防假通过） |
| ide/task_silent_import.py | 静默导入核心（由 do_replace.py 调用） |
| ide/task_readnow.py | 不清空直接读全部消息（排查异步） |
| ide/task_export_fixed.py | 导出指定 POU（学结构用） |
| ide/scan_all_native.py | **批量导出全工程**（IDE 内 eval_file 执行）：递归遍历 `active_application` 全部后代，凡能 `export_native` 的都导出为 `<IPC>/scan_<序号>_<名字>.native`，空壳自动删。用途：①学习时批量扫描未知 BoxType；②回归对比（新生成结构与模板原生 POU 同场跑 check_slots）。实测一次导出 126 个对象 |
| examples/make_*.py | 生成脚本范例。`make_full8.py` / `make_fix45.py` 读 `PLC_SRC_NATIVE` / `PLC_DST_NATIVE` 环境变量；`make_packml_cmd_test.py` / `make_fb_call_test.py` 用相对路径（前者含 `contact/coil/and_box/branch/netitem/network` 全套节点构造函数；后者含 `fb_box/pin/connector_input/output_target` FB 调用构造函数）；`make_ld_learn.py` 是**当前最完整的可复用基座**（`contact/value_pin/connector_slot/coil/fb_box/ton_box/execute_box/network/textlines_block/xml_text/build_pou` 全套，带 `__main__` 守卫可被 import）；`make_axis_call.py` 演示轴控 FB 调用 + `CallType=Action`；`make_func_return_test.py` 演示 **Function 调用框接返回值**（OutputItems 按索引对应 OutputParam.Names，[1]=返回值；含「REF 形参接全局实例成员」避坑）；`extract_action_entry.py` 从模板 native 里切出 action Entry 原始 XML 作模板 |

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
4. 打开 InoProShop 并打开工程，**人工点一次菜单注入守护**：
   `工具 → 脚本 → 执行脚本文件... → 选 <BASE>\ide\boot_daemon.py`
   （菜单是自绘的，UIA 读不到，`ide_trigger.ps1` 走不通，只能人工点这一次）
5. 跑 `python ide/probe_daemon.py` 确认 `ping` 通
6. 之后全程静默：do_replace.py 导入 → task_check.py 验证预编译

**卡住时先跑 `ide/probe_daemon.py`**，它会直接告诉你是「守护没起」还是「守护起在别的 BASE 上了」。后者是换机部署最常见的问题：如果之前手工执行过别处的 `plc_daemon.py`，`sys.argv[0]` 会固定成那条旧路径，守护就把 `ready.flag` 写进旧目录，`bridge.py` 找不到就误判「未启动」，转去点菜单（而菜单点不到），最终报 `Tools not found`——**看到 `Tools not found` 不要以为是权限问题，先查 BASE 一致性**。

### assets/natives/（克隆模板样本）

| 文件 | 用途 |
|------|------|
| `user_fixed.native` | **首选模板**。8 支路树形状态机，完整支路（AND[MOVE, CONN]）+ 声明区齐全，预编译 0 错误 0 警告 |
| `ss_manual_142651.native` | 用户手画并联起保停基线（触点/分支组最小样本） |
| `prg_EM01_Logic.native` | 旧工程完整 LD（功能框/多线圈/连接器样本） |
| `startstop_state3.native` | 早期 MOVE 状态字版本（历史对照，新写请用 `user_fixed.native`） |
| `fb_call_test.native` | **FB 调用模板**。三类 CallType（Function/Program/FunctionBlock）各一个，含 REF 形参、实例调用、12 入 12 出；双分类 0 错误 |

生成新 native 时**必须从这些已验证样本克隆节点**，不要凭空构造。
