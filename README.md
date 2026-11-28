# inoproshop-ld-native

> 汇川 InoProShop（CODESYS V3.5 SP11 系）梯形图（LD）**native XML 直接生成 + 静默导入**工具包。
> 给 AI Agent 用：读完本文件 + `AGENTS.md` 就能直接上手写梯形图，不需要人肉点鼠标。

[English summary](#english-summary) · [快速开始](#快速开始5-分钟) · [规范](docs/usage.md) · [迭代流程](docs/iteration.md) · [文件地图](FILEMAP.md) · [边沿检测](references/edge-detection.md) · [假通过目录](references/false-pass-catalog.md) · [模式卡·步序](references/mode-cards/step-sequence.md) · [模式卡·流程](references/mode-cards/process-flow.md) · [语料普查](references/corpus/inopack-template-survey.md) · [网络形状](references/corpus/ld-network-shapes.md) · [语料工具链](references/corpus/toolchain.md)

---

## 这是什么

InoProShop 的梯形图存在一个 native XML 结构里。这个仓库提供：

1. **已验证的结构知识**（`references/`）：节点 GUID、槽位规则、预编译错误对照表。所有结论都经过实测，不是猜的。
2. **可运行的桥接脚本**（`scripts/`）：通过文件 IPC 向**已经打开的** InoProShop 进程注入 IronPython 脚本，实现导入 / 导出 / 预编译检查。
3. **克隆模板**（`assets/natives/`）：19 份已验证的 native 样本，生成新结构时从这里克隆，不要凭空构造。
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

51 条，按主题分六组。编号沿用历史编号、不重排，方便 `SKILL.md` / `CHANGELOG.md` 交叉引用。

> **2026-11-28 修重号**：A 段原 25 / 26 → **45 / 46**（消息截断阈值、判导入成败三条），F 段原 41 → **47**（build 是增量编译）。原编号曾与 D 段 25 / 26、B 段 41 撞号。只此一次调整，之后仍不重排。

| 组 | 主题 | 条目 |
|---|---|---|
| A | 验收与消息 | 1、13、17、18、23、24、45、46（8 条） |
| B | 结构合法性 | 2、3、4、5、9、10、11、14、15、16、21、22、41（13 条） |
| C | 挂载与实例 | 6、7、8、12、19、20、51（7 条） |
| D | 任务配置与 GVL | 25、26、27、28、29、30（6 条） |
| E | 枚举 / POU / 凸轮 / 轴组 | 31、32、33、34、35、36、37、38（8 条） |
| F | 桥与守护 · 脚本卫生 | 39、40、42、43、44、47、49（7 条） |

（编号沿用历史编号，不重排，方便 `SKILL.md` / `CHANGELOG.md` 交叉引用。）

### A. 验收与消息

| # | 铁律 |
|---|------|
| 1 | **验收 = 预编译 `217bc73e` 0 错误 _且_ 编译 `97f48d64` 0 错误**。预编译抓结构错误（槽位、`IsContact`、声明缺失），编译抓语义错误（AND 操作数不足等）。只读一个分类必漏。⚠ **`task_check.py` 只读不编译**——`app.build()` 会**清空预编译分类再异步重建**，build 返回后立刻读是 0 条（假通过）；要强制重建须「`task_build.py` → 主机侧等 ≥10s → `task_check.py`」。 |
| 13 | **验收脚本「读不到消息」必须抛错，绝不能返回空列表当 0 错误**。两个独立的假通过来源：① `except Exception: continue` + `return []` 把「读失败」伪装成「没错误」（实测真实 48 条 Error 却报「通过」）；② **`severity` 用 `getattr` 读不到值**——它是 .NET 枚举，必须 `m.GetType().GetProperty('severity').GetValue(m, None)`，否则恒空、统计恒 0。匹配不到分类即 `raise`，并先打印全部分类清单。 |
| 17 | **不要在 IDE 脚本里 `sleep()` 或轮询消息**——IDE 脚本跑在主线程，会把界面冻死（用户两次反馈「软件卡死了」）。IDE 侧只做「读一次、写文件、立刻返回」（<1s），**计时与重试全部放主机侧 Python**。 |
| 18 | **消息来源只有两个可靠通道**：① `import_native` 导入瞬间；② `app.build()`。**编译/检查类菜单命令走缓存，读不到真实错误**（逐个实测 8 条命令，预编译分类全部 0 条）。菜单「检查程序」`ab02b3c3` 实测**不产生任何消息**。⚠ 另两个致命细节：**绝不能 `clear_messages` 后就指望消息回来**（除非再 build）；「改一个字符再改回」强制变脏实测无效。③ 导入失败的原因**不看**编译分类，看 `194b48a9`「脚本消息」的新增 Error（见 46）。 |
| 23 | **从未构建过的工程，编译分类 `97f48d64` 不存在**。`get_message_categories()` 只返回 2 个；必须先跑一次 `app.build()`（**不 clear**）才出现第 3 个。别因分类不存在就当 0 错误通过。真实工程构建后剩下的错误不一定是你的——先 `grep 你的 POU 名`，为 0 即无关，结论须如实区分「模板原有」与「本次新增」。 |
| 24 | **两分类的作用域不同（2026-11-26 实测）**：① **预编译分类**在 `build()` 阶段覆盖 **Application 下全部 POU**，与是否挂任务**无关**；② **编译分类**只含**挂进任务调用列表**的 POU。负样本 `xOut := ZZZ_NotExist_Symbol;`：未挂任务 → 预编译 ZZZ **1**、编译 ZZZ **0**；挂上 MainTask → 预编译 **1**、编译 **2**。**预编译消息异步补齐**：`clear_messages(cat)`（**必须传分类参数**）后立刻读 0 条，约 10s 后 101 条；空闲 20s 仍是 0 条（不自恢复）。⚠ **隐藏桌面实例差异（2026-11-28 实测）**：`HiddenLaunch` + `--runscript` 起的实例上 `app.build()` 后**只出现编译分类 `97f48d64`，预编译分类 `217bc73e` 从不出现** —— 未挂任务的 POU 一条消息都不产生（样本 A 未挂 hit=0，挂进 MainTask 后立刻 2 条）。**隐藏实例的验收必须先把目标 POU 挂进 MainTask 再 build**，不能指望预编译兜底。证据：references/evidence/hidden-instance-scope/README.md。 |
| 45 | **消息截断阈值按 severity 各自计数：Warning 100、Error 500**（lead 隐藏实例 1.10.0.3 实测：灌 1300 个未定义标识符 → Error 恰 **501** = 500 实体 + 1 提示行）。**提示措辞不统一**：警告/消息级是「多于N个**警告/消息发生**：跳过更多的…」，错误级**不带「发生」**——原文 `多于500个错误：跳过更多的错误信息`。按文本识别截断的正则**绝不能锚定「发生」**，否则 >500 错误的工程看不见截断 → 条数差恒 0 → **假 PASS**（2026-11-26 踩过）。 |
| 46 | **判导入成败要看三条，`2af7707f` 不是结果台账**（lead 实测）：① `import_native()` 是否抛异常——**不可靠**，同 GUID+同名的二次导入会**卡死 6 分钟**，不返回不报错；② **唯一可靠的「真成功」信号**：`2af7707f` 是否新增 `Text|导入对象 '<name>'`（它的 Error **恒 0 是设计如此**）；③ 失败原因看 `194b48a9`「脚本消息」的新增 Error。坏文件（截断的 native）抛异常时：`194b48a9 n=1 err=1`、`2af7707f` 完全不变。外层必须有超时 + 「台账没新增就判失败」。 |
| 48 | **验收要双通道交叉校验，单通道的 `errors=0` 随时可能是读漏**。通道 1 `get_message_objects(cat)` 全量：单分类最多 100 条、错误池 500 条，超了截断少报。通道 2 `get_message_objects(cat, Severity.Error / FatalError)` 在**完整池**上过滤：1.10 实测 `all=540 / Error=502`、各 severity 相加等于 all；灌 1300 个未定义标识符时 Error 恰 500 实体 + 1 提示行，说明过滤通道不受可见截断影响。**计数取两通道较大值**：过滤通道坏（inoproshop-mcp 在 CODESYS SP19 上实测「2 错误只回 1 条 warning、0 错误」）不能把已有错误洗成 0，可见通道被截断时由过滤通道补。未截断的分类要求两通道**相等**，不等标 `cross=BAD` → `UNKNOWN`；已截断的分类只做单向校验（过滤 ≥ 可见）标 `cross=GE`。另：**消息分类是按需注册的**，刚打开、从没 build 过的工程可能一个分类都没有（隐藏实例上 `cats=0`）→ 先 `app.build()` + `system.process_messageloop()` 各一次再枚举，仍为空才判 `UNKNOWN`，绝不当 0 错误。工具 `scripts/ide/tasks/task_check.py` v4：末行 `VERDICT: PASS|FAIL|UNKNOWN`，并把通道状态（`dual / dual-unchecked / mismatch / all`）一并写出；**`UNKNOWN` 不是通过**。 |

### B. 结构合法性

| # | 铁律 |
|---|------|
| 2 | 功能框 `InputItems` 槽位数 **==** `InputParam` 参数数（MOVE = `[EN, IN]` 2 槽）。 |
| 3 | 值输入引脚（IN 槽）必须 `IsContact=False`。从触点克隆残留 `True` 有两种后果：**SINT 等类型报错**（`不允许对类型 'SINT' 进行 'NOT' 操作`）；**INT 等类型则完全不报错**——预编译 0 / 编译 0 / 往返 diff PASS，`check_symbols` / `check_slots` / `ld_logic` 三层也全 PASS（lead 隐藏实例实证：MOVE.IN 的 INT 引脚改 True，唯一差异是导入分类多一条 Text）。所以这条**必须靠静态断言**，判据看引脚自己的 `Operand.Type`：非 BOOL 却 `IsContact=True` 即违规；**不要**按 `InputParam` 索引对齐判（比较框槽数不齐，见铁律 22），**也不要**反向断言 BOOL 引脚必须 True（FB 的 BOOL 值槽合法为 False，会误报 20 处）。→ `check_valpin.py` |
| 4 | 操作数内部 `Flags/Flags=1` 是 **NOT 取反**。常量引脚必须清 0；触点取反才用 1。`2`=S、`3`=R。 |
| 5 | 常量引脚 `Type=INT`、`Boolean=False`（写 `BOOL` 会红框）。 |
| 9 | **图形里引用的每个符号，声明区必须有一行对应声明**。`import_native` 不补声明，漏一个就每个引用点报一条 `C0046`（8 个未声明变量共 45 次引用 → 45 个错误）。 |
| 10 | **单条件 rung 不要建 AND 框**，触点直接作为 `NETITEM.RValue`。AND 框 ≥2 槽约束的是「框」：1 槽报 `'AND'需要至少'2' 个操作数` + `检测到不一致元素`；裸触点直挂 0 错误、往返不变。旧结论「补一个 `TRUE` 触点占位」**已作废**（TRUE 恒通等于没加）。 |
| 11 | **分支组 `{827b9ec2}` 的 `Trees` 必须 ≥ 2 条支路**。只有 1 条时**预编译 0 / 编译 0，但 IDE 绘制该网络直接崩**（`IBoxTreeParallel` 索引越界）。单支路**不要 `branch()`、不要套 `NETITEM`**，AND 框直挂 `NetworkItems`。 |
| 14 | **往返 diff PASS ≠ 内容正确**。它只证明「IDE 没改写我的结构」；源文件本身错时 IDE 原样保留，diff 照样 0。必须配合双分类 0 错误 + **语义抽查**（打印声明区首行确认 `PROGRAM xxx` / `FUNCTION_BLOCK xxx`）。 |
| 15 | **`OutputItems` 项数 == `OutputParam` 个数**；含不含 `ENO` 由 `EN`/`ENO` 字段决定。`EN/ENO=True`（Function/Program/常规 FB/EXECUTE）第一项是 `ENO`；**`TON` 是 `EN/ENO=False`、`OutputParam=['Q','ET']` 不含 ENO**，不接线要写**两个** `<Null/>`。19/19 样本 0 例外。⚠ 这条预编译/编译/往返 diff **全都查不出来**，只能靠 `check_slots.py`。 |
| 16 | **往 XML 文本节点塞自由文本必须转义 `<` `>` `&`**。注释里写 `<Null/>` 会被解析成**真实子节点**，导致节点数不等、`rt_diff` 整段错位报几十处。统一走 `xml_text()`，且必须定义在 `textlines_block()` **之前**。**排查提示**：diff 报「节点数不同 + 整段错位」时先看父节点是不是 `Comment`/`Text`/`Title`/`Label`——是就 100% 是转义问题。 |
| 21 | **FB 类框（TON / FB_xxx）的 `Instance.Type` 必须填 BoxType 名、`Instance.Operand` 必须填实例名**。写空 `Instance.Type` → `import_native` 抛 **「已标识项中有一项的格式无效。」**，且是**模态弹窗**：主线程阻塞 → 守护心跳停 → `bridge.py` 全部超时（看起来像「API 挂了」）。判断：枚举该 PID 可见窗口，主窗口 `IsWindowEnabled=False` + 另有窗口挂 `确定`；解除：`SendMessage(hButton, BM_CLICK=0x00F5, 0, 0)`。⚠ `ET.parse()` 验不出这类语义错误。 |
| 22 | **`check_slots.py` 不能按「输入槽数 == `InputParam` 名数」校验比较框 / MOVE / 算术框**。比较框 `InputParam` 只有 `['EN']` 但 `InputItems` **恒 3 槽**；MOVE 恒 2 槽；ADD 恒 3 槽。旧规则会把模板原生 POU 全部误报，已加 `_input_exempt()`。**元教训**：校验脚本的规则本身也要拿真实工程回归。 |
| 41 | **线圈只能挂 NETITEM（9873c309-1f09-4ebf-9078-42d8057ef11b）或触点 PIN 的 OutputItems，不能挂功能框**。挂到 AND 框的 OutputItems 上时：导入接受、预编译 0、编译 0、导出原样保留，唯独 IDE 里该梯级末尾只画一个**空方块**（无名字无括号）——四条验收链全部放行，用户连说三次「还是没有更新」。A00 全工程分布：NETITEM→线圈 **15** 处、触点 PIN→线圈 **5** 处、BOX→线圈 **0** 处。→ 生成器用 netitem() / coil_tree() / coil_net() 包一层（条件有多个时先 and_box 合成 RValue）；验收链必须补「图形（人眼）」一项。 |

### C. 挂载与实例

| # | 铁律 |
|---|------|
| 6 | **绝不动真实鼠标/不抢焦点**：只用消息式自动化（文件 IPC、`PostMessage`）；绝不 `SetCursorPos` / `mouse_event` / `SetForegroundWindow`。 |
| 7 | **不关闭 IDE**：静默替换用「改名让位法」（`prg_X → prg_X_old_tmp` → import → 删旧）。 |
| 8 | **导出文件每次唯一命名**（`silent_after_HHMMSS.native`），否则弹覆盖确认框。 |
| 12 | **改声明区必须锚定 `Interface` 再找 `TextLines`**，禁止裸 `find('<Array Name="TextLines"')`。一份 native 里 `TextLines` 至少 2 处（声明区 + EXECUTE 框 `STSnippet`），而网络列表排在 `Interface` 之前——只要网络里有 EXECUTE 框，裸 `find` 就会把声明写进 ST 代码块，预编译报 40+ 条 `符号 'PROGRAM'/'BOOL' 不能识别`（实测 48 条）。正确：`raw.find('<Array Name="TextLines"', raw.find('<Single Name="Interface"'))`。 |
| 19 | **action 的 ST 体只能引用宿主 POU 声明区的变量**。三个特征：① 消息归属对象是 **action 名**不是 POU 名；② 只在**预编译**分类；③ 编译分类照样报「0 错误, 0 警告」。 |
| 51 | **工站子程序按 A00 骨架写，由总控 POU 调用，不挂 `MainTask`**。模板里每个工站 POU（`A00_上料移栽`/`A01_中转移栽`…）都由 `F20_POU_Station0_总控` 按工站号调用，本身不在任务调用列表里 —— 2026-11-28 用户明确「可以不用调用到MainTask」。骨架固定 8 段：NET1 步序号记录器（`FB_StepLogger`，整块克隆 A00 net01）/ NET2 步序号缓存处理（单步·单站·总控三路放行，整块克隆 net02）/ NET3 流程开始 `10000→10` / NET4–7 安全自检 `10→15→20→30→100` / NET8 工位判断（产品状态 0/1 → 取料段 1000 / 放料段 2000，异常置多料·少料，克隆 net08 换 4 个符号）/ 取料段 `1000–1120` / 放料段 `2000–2060`，两段收尾都无条件 `MOVE 100`。变量不要新建结构体，直接用模板的 `STNControl[0..20] OF Struct_StationControl`（0 总控 / 1 上料移栽 / 2 擦拭，3..20 空闲），生成前把 `ldgen` 的 `AUTOING/STEP/BUF/DESC` 指向 `STNControl[n]`。片段在 `assets/natives/a00-fragments/`，生成器 `scripts/examples/gen_a00_stn3.py`，配方 `references/mode-cards/a00-skeleton.md`。⚠ 不挂任务时它不进编译单元，验证阶段必须临时挂一次或用总控真实调用，否则 0 错误是假通过。 |
| 20 | **造负样本必须精确替换目标字段**。`s.replace('>actAbs<', '>actAbs_ZZZ<')` 会把 `BoxType` **和** Entry `Name` 一起改 → `actAbs_ZZZ` 成了合法 action，0 错误是**正确结果**却被误判「验收链路失效」。只改 `<Single Name="BoxType">` 一处，改完 `grep -c` 自查。 |

### D. 任务配置与 GVL

| # | 铁律 |
|---|------|
| 25 | **`ScriptPouObjectList.remove("名字")` 不报错，但留下 `Name=""` 空槽项**，之后编译报 `MainTask: 期望标识符，而不是''`。`remove(idx)` / `remove(item)` / `replace(idx,'')` / `Item[i]` 全都摘不掉。**唯一可靠修法**：导出 Task Configuration native → 删掉空 `<Single Type="{f194d1ef-…}">` 块 → 覆盖导入。 |
| 26 | **`Task Configuration` 不允许改名**（报 `名称 'Task Configuration_old_tmp' 对于本工程无效。`）。必须走「`import_native` 同名覆盖 + 主机侧自动点确认框」（`run_overwrite_import.py`）。⚠ 覆盖确认弹框挂在**未被禁用**的框架窗口（标题 `InoProShop(V1.10.0.3)`）下，不是被禁用的主窗口——自动点击不能按「窗口被禁用」筛，直接遍历所有顶层窗口找按钮。**必须两步点击**：先「全部(&A)」全选、再「&确定」提交。只点「全部」对话框不关闭，`import_native` 一直阻塞——2026-11-26 实测卡 **323.79s** 直到人工补点确定；补齐第二步后同一导入 **3.45s** 完成。统一走 `scripts/click_overwrite_all.py`（`run_overwrite_import.py` / `run_build_check.py` 都复用它），禁止各处自写一份点击逻辑。 |
| 27 | **`AT %MBxxxx` 是绝对物理地址，副本沿用原件地址必然冲突**（实测 13 条「地址重复」）。两条合法路线：① 剥掉 `AT` 交给 IDE 分配；② 保留但整体平移到空闲区间（实测 `MB +311228 / MW +2000` 后重叠 0）。⚠ 正则要吃 `AT%MW1000` 无空格写法，用 `\s*` 不是 `\s+`。 |
| 28 | **含 `PERSISTENT RETAIN` / `RETAIN PERSISTENT` 段的 GVL 无法字节级往返**。IDE 会自动补绝对地址并规范化字面量（`:=TRUE` → `AT %MB131099 : BOOL := TRUE`）。普通 `VAR_GLOBAL` 与 `CONSTANT` 段不被改写。这类 GVL 只能逐字段比对。 |
| 29 | **GVL = `Object > Interface > TextDocument > TextLines`**（无 `NetworkList`、无 `Implementation`）。一个 GVL 内可有多段 `VAR_GLOBAL`；`EmbeddedTypeGuids` 是 `Array[a9ed5b7e]` 单元素（Folder 的是 `<Null/>`）。 |
| 30 | **Folder 的四条 GUID 关系**：`Properties.ParentObjects` 的 Key = 导出根 SV Guid、Value = 父容器 guid；`ParentSVNodeGuid` = 该 Value；`MetaObject.ParentGuid` = **祖父** guid（直属 Application 的 Folder → 全零）；被导出的 Folder 自身 `IsRoot=True`。详见 `references/native-structure.md`。 |
| 31 | **枚举字面量是全局符号，不是类型内作用域**。复制 DUT 副本时若沿用原枚举值（`A1_上料移栽R轴:=1,`），会与原件全局符号**重名**（实测 277 条「符号'xxx'存在重名」），且所有裸引用变「未知类型」。**必须给枚举值也加后缀**。提取正则要吃行尾注释：`^\s*(ident)\s*:=\s*-?\d+\s*,?\s*(//.*)?$`（最后一个值可能无逗号）。字面量是中文常见词（提示/警告/故障）时先扫描确认只在声明行出现再替换。 |
| 32 | **POU TypeGuid 正确取值**：FB/FC = `6f9dac99-8de1-4efc-8465-68ac443b7d08`、DUT = `2db5746d-d284-4425-9f7f-2663a34b0ebc`、Folder = `738bea1e-…`、GVL = `ffbfa93a-…`。⚠ 旧记录里的 `6f9dac99-f3a6-45e5-…` 是错的。**根下直接 POU 导出时也会生成「空目录 + `<名>_folder.native`」，看起来像子文件夹**，判别只能靠 TypeGuid。 |
| 33 | **`Implementation` Type GUID**：ST = `{3b83b776-fb25-43b8-99f2-3c507c9143fc}`、LD = `{25e509de-33d4-4447-93f8-c9e4ea381c8b}`（DUT 无此节点）。⚠ 旧记录的 `3b83b776-a464-…` / `25e509de-a6c5-…` 是错的，以实测为准。 |
### E. 枚举 / POU / 凸轮 / 轴组

| # | 铁律 |
|---|------|
| 34 | **根下直接 POU 会在工程里被误建为空文件夹**。导出时根下 POU 也生成同名空目录 → 翻译复制该目录 → 导入对每个目录 `mk_folder`，最终工程多出 N 个空文件夹（F05 实测 5 个）。**防护**：翻译与导入都先判断「目录内有无 `.native`」，无则跳过。**判别空 Folder**：`kids==0` 且 `textual_declaration`/`textual_implementation` 都取不到（真 POU 即使 kids==0 也能取到声明）。空文件夹不影响编译但污染结构，需 `remove()` 清掉。 |
| 35 | **CAM 直线段的 `p1` 是段内增量，不是终点绝对值**。直线段 `y(u) = p0 + p1·u`（u 为段内归一化 0..1），所以 `p1 = y1 - y0`。按「p0=起点、p1=终点」写停歇段（`p0=45 p1=45`）会算出 `y(1)=90`、段内斜率 45，与相邻五次多项式段的零速度冲突，Cam 分类报 `在点 (240/45) 的连续性要求不能填充 速度`。**自检（两条都成立才对）**：`p0 == cp0.Y` 且 `p0+p1 == cp1.Y`。模板 Cam0 三段实测反解：`p0=20 p1=80 → cp 20→100` ✓。 |
| 36 | **分度凸轮必须 `Periodic=False`**。摆动凸轮一周期回原点（`y(360)==y(0)`）才用 `True`；分度凸轮每周期从轴累进 H（`y(360)==y(0)+H`），沿用模板的 `True` 会报 `在点 (0/0) 的连续性要求不能填充 位置` + `不能填充 速度`。**自检**：算 `y(360)-y(0)`，≠0 就必须 `False`。⚠ 另：CAM 对象的错误只落 **Cam 分类 `de128929`**，预编译/编译可能全是 0 错误——**只看那两个分类会漏判通过**（详见 `mcp-bridge.md`）。Cam 子对象也**无法脚本删除**（`remove`/`replace` 均失败），改曲线只能同名覆盖导入。 |
| 37 | **AxesGroup（轴组）复制：`AxisGuid` 指向的物理轴不能同时属于两个轴组**。复制时只改 `MetaObject.Name` + `MetaObject.Guid` + `Object.Id` 三处（实测 diff 精确 3 处）；若 `AxisGuid` 沿用原件、而原轴已被原轴组占用，**IDE 导入时会把 `AxisGuid` 全部清成 `00000000`**，编译报 `X轴轴映射为空`。这不是脚本 bug，是 SoftMotion 的占用保护——对照实验证明：改成空闲轴（Axis9/Axis10）后 `AxisGuid` 完整保留、0 错误。⚠ 脚本**无法建虚拟轴**（`SoftMotion General Axis Pool.get_children()` 返回 `[]`），只能手工在 IDE 里加。另：轴组**必须在「轴所在的那个任务」里被引用**，本工程轴挂 `ETHERCAT` 而非 `MainTask`，挂错报 `轴组 xxx 与所选轴所在任务不同`；同一 POU 挂两个任务报 `在多任务下存在多处调用`。详见 §33。 |
| 38 | **任务槽摘除 `pous.remove("名字")` 打印成功但实际无效**（铁律 25 的完全同源问题，2026-11-26 再次实测确认）。`MainTask.pous.remove()` / `ETHERCAT.pous.remove()` 都回读仍在。唯一可靠做法：`export_native` 导出 Task Configuration → 主机侧删 `<Single Type="{f194d1ef-7376-42ce-a729-4a5485a97a46}">`…`</Single>` 块 → 同名覆盖导入。⚠ **不能用跨行正则 `.*?</Single>`** —— 会连相邻的 `</Single>` 一起吃，导入报 `开始标记"List"与结束标记"Single"不匹配`。必须从该行起逐行走到**单独一行 `</Single>`** 为止（`scripts/examples/del_task_pou.py`）。 |

### F. 桥与守护

| # | 铁律 |
|---|------|
| 39 | **结果必须与命令对账（`run_id`），「文件出现」不等于「这是我这轮的结果」**。旧 bridge 只做「删 `result.json` → 写 `cmd.json` → 等 `result.json` 出现」。上一条命令超时后守护迟一点才写结果，这条**迟到结果**会被下一次调用当成自己的读走——`ok` 是 `true`、JSON 能解析，只有内容是错的，是最阴险的假成功。现在每条命令带唯一 `run_id`，守护原样回带，对不上就丢弃继续等；旧版守护不回带时退化为「出现即认」并标 `legacy_daemon: true`（向后兼容但失去保护）。**自检**：`python bridge.py selftest`，`ping` 结果里必须有 `run_id` 且 `legacy_daemon` 不出现。 |
| 40 | **`os.kill(pid, 0)` 在 Windows 上不能判活**，别照 POSIX 的 `ESRCH` 写。实测（Win11 / Python 3.12）：`os.kill(999999, 0)` → `errno 22 (WinError 87)`，`os.kill(36704, 0)`（这个 pid **明明活着**，InoProShop）→ **同一个 `errno 22`**，`os.kill(4, 0)` → `errno 13`。也就是说「不存在的 pid」和「活着的 pid」抛的是同一个 errno，按 `== ESRCH` 判活会把所有进程都判成死的——陈旧锁永远能抢，等于没锁（实测 T7 直接失败）。**正确做法**：Windows 上走 `OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION)` + `GetExitCodeProcess`，拿得到句柄且 `STILL_ACTIVE(259)` 才算活；判不了时**当作活着**（宁可等锁超时，也不要抢活人的锁）。`bridge.py` 的 `_pid_alive()` 已按此实现。 |
| 47 | **`app.build()` 是增量编译：无改动时预编译分类不重跑，读到的是上一轮的陈旧消息**。2026-11-27 F20 实测：连跑三次 build 都是「预编译 0 / 编译 104」，看似干净 0 错误，实为上一轮留下的 104 条——预编译语义检查没重跑，分类保持空。**验收前必须先清分类**：`system.clear_messages(cat)` 逐个清预编译 `217bc73e` 与编译 `97f48d64`（**必须传分类参数**，无参重载报 `takes exactly 1 argument`），再 `app.build()`，主机侧等 ≥10s 后读。**自检**：清完再 build，预编译必须重新出现 ~101 条（本项目基线），若仍为 0 说明没重跑，结论无效。工具：`scripts/ide/tasks/task_build_clean.py`。⚠ `clear_messages` 是**进程级**：同一 IDE 进程里别的守护/脚本的消息会被一起清掉，与他人共用实例时不要清。 |
| 50 | **写源码要带乐观锁，超时后先锁死（`task_setpou.py` / `deadline` / `uncertain.json`）**。① 写前算 `sha256(decl + '\x00' + impl)`，连同读到的内容一起传 `expect_hash`，不符抛 `STALE_WRITE` 且**一个字都不写** —— 两个 agent 同工程时，后写者会静默覆盖前写者，改名让位法防不住这一层。② 写完必须读回逐字比对（`READBACK_MISMATCH`），不符把 decl/impl 逆序 `replace` 回旧值 + `save()`，结果里报 `rolled_back`。③ bridge 每条命令自动带 `deadline = now + timeout - 2`，守护发现已过期直接回 `expired:true` 且**不执行** —— 排队过久的命令宁可丢弃也不能双重执行。④ 守护把 `timeout waiting for main thread` 判为**结果未知**（主线程可能还在跑），写 `ipc/uncertain.json` latch；latch 存在时除 `ping` / `ack_uncertain` / `stop` 外一律拒绝，bridge 抛 `E_UNCERTAIN`，必须人工确认后 `python bridge.py ack_uncertain` 才解锁（`boot_daemon.py` 判陈旧时也会清掉它）。⑤ `eval_file` 里被执行的脚本 `__name__` 是 `__eval__`，**不能用 `__main__` 守卫**（否则函数全定义完就结束，看起来成功、实际什么都没做）；`eval_file` 现在会临时改写 `sys.argv[0]`，让 `_base` 按被执行脚本自身路径推导 BASE。工具 `scripts/ide/tasks/task_setpou.py`；副本实测：`FC_XOR8` 错哈希 → `STALE_WRITE`（未写、`rolled_back:ok`）→ 正确哈希写入 `saved:true` 且 `hash_after` 变化 → 再用旧哈希 → 再次 `STALE_WRITE`；带过期 `deadline` 的 ping 回 `expired:true`；latch 下 `get_decl` 抛 `E_UNCERTAIN`、`ping` 正常、`ack_uncertain` 后恢复。 |
| 42 | **ST 声明区在 native 里是「每行一个独立 Text 节点」，不能按 VAR/PROGRAM 关键字筛节点**。`Single Name="Text"` 节点粒度是**一行**（如 `\ti\t\t\t\t:INT;`），整块 `VAR…END_VAR` 从不落在同一个节点里；按关键字筛会漏掉绝大多数声明行，导致 `locals` 识别为空。**后果最危险**：局部名被当成全局名一起改写（静默错误，双分类仍 0 错误）。**正确做法**：从 `PROGRAM/FUNCTION_BLOCK/FUNCTION <name>` 那一行开始，**把所有后续 Text 节点 join 起来**再解析 `VAR…END_VAR`，并剥掉 `//` 行注释。**自检**：locals 数量应为个位数到十几（F20 实测 6~16/个），出现 0 一定是提取逻辑坏了。 |
| 43 | **IDE 脚本不要用 `sys.exit()` 收尾 —— 会弹出 `Uncaught exception` 模态框**。IronPython 里 `SystemExit` 不继承 `Exception`，`handle_on_main` 的 `except Exception` 兜不住，IDE 弹出标题 `Uncaught exception, please check the error log for details.`、内容 `SystemExit` 的模态框，一直挡着界面（轮询线程靠 `except BaseException` 能活，但弹框要人工关）。**做法**：脚本末尾直接 `print(u"done")` 结束，需要分步就在文件/标志位上判断，不要 `sys.exit(0)`。⚠ 附带两类弹框的关法（`PostMessage`，不动鼠标/不抢焦点）：`Uncaught exception` 的「确定」对 `WM_COMMAND IDOK(1)` **无反应**，须 `WM_CLOSE(0x0010)`；`导出的文件已经存在：…，是否希望替换？` 是 `IDYES(6)`/`IDNO(7)`，**误点「是」会覆盖主机侧刚改好的 native**，选之前必须核对目标文件 mtime 与内容。 |
| 44 | **LD POU 的标识符有 4 类载体，只改 `Text` 会漏掉约 90%**。纯 ST 组（F01~F11/F20）只处理 `Text` + `Operand` 就够；2026-11-27 F21 实测 `STN1_02_Auto` 的 2155 处改写里 **1953 处落在 `Operand Type="string"`**，`Text` 只有 114 处。四类载体：① `Single Name="Text"`（ST 代码）；② `Operand Type="string"`（LD 触点/线圈操作数）；③ `BoxType`（LD 功能框类型名，如 `AND`/`MOVE`/`EQ`/`FC_CylinderExe`）；④ `Instance > Operand Type="string"`（FB 实例操作数）。`SymbolComment` / `Address` 在 LD native 里**全为空**，不能靠它们定位。⚠ 另：**LD 的 `Path` 数组是「每个 network 一个」**（`STN1_02_Auto` 有 87 个，`STN1_03_Manual` 2 个），每个数组元素 4 = POU 自身名（必须改）、元素 5 = network 名（不能改）；纯 ST 的 POU 一个 `Path` 数组都没有，按「每文件一个 Path」的旧写法会漏改 86 个。**自检**：翻译后按载体统计命中数，若某 POU 含 `NetworkList` 而 `Operand` 命中数为 0 → 一定漏改。参考 `scripts/examples/make_f21_translate.py`。 |
| 49 | **任务与对象移动走「改 → 逐字段读回 → 失败回滚」，且不能靠 `dir()` / `is` 判断**。① `TaskConfiguration.create_task(name)` 存在（`dir()` 里看不见，`hasattr` 或直接调用才有效）；新建默认 `interval_unit=ms` / `priority=2` / `kind_of_task=Cyclic`，`interval` 读回可能是 `t#20ms` 字面量，设成 `'20'` 后读回 `'20'`，比较前先归一化；`KindOfTask` **按名字反射 `System.Type.GetType(...)` 返回 `None`**，要拿已有任务的 `kind_of_task` 当枚举值赋值。② 对象移动 `obj.move(parent, -1)` 返回 `None`，**没有 `get_parent()`**，且每次 `get_children()` 返回的 .NET 包装对象都是新实例、`k is target` 恒假 —— 父节点与移动结果只能靠 `get_children()` 的名字列表核对。③ 保护对象四类 `is_application / is_device / is_task_configuration / is_task`，命中即拒。④ 失败必须回滚（任务 `t.remove()`；移动 `obj.move(old, -1)`）。工具 `scripts/ide/tasks/task_extended.py`；副本实测：建任务 20ms/优先级 5 → 改 50ms/6 → 关工程重开仍是 50/6；`prg_SeqDemo` 移进 `F05_FC` 再移回 `Application`，重开位置正确；受保护对象与不存在对象被明确拒绝。 |

### 三条元教训

> **① 往返 diff PASS 不等于内容正确**（铁律 14）。`rt_diff` 报 0 只说明「IDE 没改写我的结构」；源文件本身错时 IDE 原样保留，diff 当然一致。必须配合双分类 0 错误 + 语义抽查。
>
> **② 「必须补占位 / 必须加冗余元素」这类绕行修法要追问一句：不绕行能不能直接不建这个东西**。铁律 10 就是靠用户看图形发现「TRUE 恒通等于没加」。生成器四层自检（`check_slots` / 双分类 / 往返 diff / `ld_logic`）全过却仍错，因为它们校验的是「结构合法」，没有一层校验「这个结构该不该存在」。
>
> **③ A/B 验证：正向必做，负向默认不做（2026-11-27 用户决定）**。正向 = 副本 POU 挂进 MainTask 调一次、确认双分类 0 错误，证明副本确实在编译作用域内；负向 = 故意写未定义标识符、确认编译器真的报错。链路已在 F01~F11、F20、F21 多轮跑通，负向属重复劳动，**仅在用户明确要求、或怀疑 0 错误是假通过、或首次验证全新对象类型（F07 CAM / F08 轴组这类）时才做**。要做负向时必须造对（铁律 20），造错了会得出「验收链路失效」的错误结论。等待时长不足还会造成**假阴性**——比假阳性更危险：曾因只等 10s 而漏读消息。
>
> **④ 验证语义规则前，先确认工程能走到语义分析阶段。** 「设备未安装」的工程是**脏容器**：编译器在「不能生成代码」处就退出，根本没做语义分析，所有语义错误都不报（lead 实测：120 个未定义标识符的 POU 挂进任务后 build，错误数一条没变）。拿这种工程验证任何语义规则，得到的全是**假阴性**——看着"规则没生效"，其实是编译器压根没跑那段。判断方法：base 的 error 数在导入前后完全不变，就是撞上了。

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

**IDE 已经开着（你自己打开的工作工程）** —— 在 IDE 里人工点一次菜单：

```
工具 → 脚本 → 执行脚本文件... → 选 <BASE>\ide\boot_daemon.py
```

**为什么不能自动点**：InoProShop 的菜单栏是**自绘**的，UIA 枚举整个窗口树拿到 `MenuBar` = 0、`MenuItem` = 0，Win32 `GetMenu` 也返回 0（2026-11-25 实测）。所以 `ide_trigger.ps1` / `start_daemon.cmd` 走 UIA 的这条路在 InoProShop 上**根本不可能成功**，会报 `Tools not found`。这一次人工点击是唯一入口，注入之后全程静默——日常写入走 IPC 文件，IDE 界面不会跳到前台。

注入完跑一下自检确认：

```
python scripts\bridge.py selftest
```

它一次给出 `base` / `ipc` / `ide_running` / `ready_flag` / `heartbeat_age` / `ping` / `cancel_gen`，
并逐条列出 `problems`（每条都写明下一步该做什么）。`ok: true` 才算通了。

> **看到 `Tools not found` 不要以为是权限问题。** 十有八九是「守护挂错目录」：如果你之前手工执行过别处的 `plc_daemon.py`，`sys.argv[0]` 就固定成那条旧路径，守护把 `ready.flag` 写进旧目录，`bridge.py` 在 `<BASE>\ipc` 找不到就误判「未启动」，转去点菜单、点不到，于是报 `Tools not found`。先跑 `bridge.py selftest`，把 `base` 与 `ipc` 跟实际部署目录一对就出来了。

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
python -c "import sys; sys.path.insert(0, r'<BASE>'); import bridge; bridge.call('eval_file', path=r'<BASE>\ide\tasks\task_check.py')"
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
│   ├── edge-detection.md         # 边沿检测：框的 InputFlags[0]=16（不是触点、不是 R_TRIG）
│   ├── false-pass-catalog.md     # 0 错误的九种假象（验收器只防它建模的那一维）
│   ├── mode-cards/               # 模式卡：step-sequence.md（步序）、process-flow.md（完整流程）、a00-skeleton.md（A00 工站骨架）
│   ├── corpus/                   # 语料普查：模板全量导出 → 对象索引 / 网络形状 / 工具链
│   └── mcp-bridge.md             # 桥的协议、命令、消息分类
├── scripts/
│   ├── README.md                 # scripts/ 根 19 个脚本的分类索引（桥 / 导入 / 自检 / 差分 / 打包）
│   ├── check_slots.py            # 结构自检：槽位数 vs 参数数 + Operand 三态断言（含 MOVE 原生形态豁免）
│   ├── check_symbols.py          # 符号自检：网络引用 vs 声明区
│   ├── ld_logic.py               # 逻辑层验收：图形拓扑 → 布尔表达式，DNF 规范化比对
│   ├── check_valpin.py           # 值引脚自检：非 BOOL 引脚 IsContact 必须 False（编译链查不出的第五类假通过）
│   ├── check_ipy_syntax.py       # 语法门禁：按文件头 @py3/@ipy2 标记分流（py3 不降级，否则门禁失效）
│   ├── bridge.py                 # IPC 客户端（本地 Python 3）
│   ├── do_replace.py             # 静默导入入口（本地 Python 3）
│   ├── launch_ide_daemon.py      # 启动 IDE + 注入 daemon
│   ├── pack_skill.py             # 打包 .skill 分发件（清单取自 git ls-files）
│   ├── ide_trigger.ps1           # UIA 触发注入（⚠ 对 InoProShop 无效，菜单自绘）
│   ├── start_daemon.cmd          # ⚠ 已失效，改用 IDE 菜单 + ide/boot_daemon.py
│   ├── bridge.cmd                # 命令行入口（自动挑可用的 Python 3）
│   ├── ide/                      # IDE 内 IronPython 2.7 脚本（分层索引见 ide/README.md）
│   │   ├── _base.py              # 路径自解析（IDE 内环境变量无效，靠它定位）
│   │   ├── boot_daemon.py        # 守护注入入口（人工点菜单执行本文件）
│   │   ├── reload_daemon.py      # 热重载守护（改完 plc_daemon.py 后用它换新）
│   │   ├── plc_daemon.py         # 守护进程（命令分发 + 独立心跳线程）
│   │   ├── scan_all_native.py    # 全工程批量导出（结构学习语料，只读）
│   │   ├── tasks/                # ★ 45 个可复用操作：验收 / 导入 / 导出 / 建对象 / 任务槽 / GVL
│   │   │   ├── task_check.py     #   验收（必用，单次快照，不 sleep 不轮询）
│   │   │   ├── task_build.py     #   只 build 不读消息（build 会清空预编译分类，必须与上一条配对）
│   │   │   ├── task_silent_import.py  #   静默导入核心（改名让位 + 失败回滚）
│   │   │   └── …                 #   其余 41 个见 scripts/ide/README.md
│   │   └── studies/              # ✗ 98 个一次性考古脚本（探 API / 探结构 / A-B / F0x 普查）
│   │       └── …                 #   冻结存档，新功能不要写这里，验收链路不许引用
│   └── examples/                 # 39 个 native 生成器（分类索引见 examples/README.md）
│       ├── README.md             # 可复用库 / 已验证样本 / 一次性考古 三类说明
│       ├── ldgen.py              # ★ 可复用生成库：节点构造层 + 模板 helper + build_doc
│       ├── make_full8.py         # 裸 MOVE 支路批量包装成完整支路
│       ├── make_fix45.py         # 补声明 + 删多余 TRUE
│       ├── make_packml_cmd_test.py  # 从零生成完整 POU（7 网络 PackML 命令层）
│       ├── make_fb_call_test.py     # FB 调用（Function/Program/FunctionBlock 三类）
│       └── gen_a00_stn3.py          # ★ A00 工站骨架生成器（31 网络样本）
├── assets/natives/               # 已验证克隆模板 19 份 + a00-fragments/ 5 个 A00 骨架片段（含 negative/ 负样本）
├── scripts/corpus/                # 语料工具链：index_native / scan_forms / parse_net / ld_dump / split_networks
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
- **工站子程序 = A00 骨架**：NET1 记录器 / NET2 缓存放行 / NET8 工位判断三块整块克隆，取料 1000 段、放料 2000 段，收尾无条件回 100；变量用 `STNControl[n]`，由总控调用而不挂 `MainTask`（铁律 51，配方 `mode-cards/a00-skeleton.md`）。

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
