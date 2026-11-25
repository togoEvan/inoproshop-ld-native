# Changelog

本项目的所有重要变更都记录在此文件。

格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### 新增
- **【补全性扫描：RValue 值域/触点位掩码/网络级字段/文档级转换标志】** 全工程 127 对象扫描补齐四块拼图：①**RValue 容器完整值域**（143 处）：Null 69 / 功能框直挂 52（**最常见**——AND 框直接当 NETITEM 条件，不必先包 `{5f9848d3}` 容器）/ 容器包分支组 6 / 容器包触点 4；②**触点 `Operand.Flags.Flags` 值域仅 0/1**（1295+62 处，无 P/N 边沿形态——边沿检测必须走 R_TRIG/F_TRIG FB）；③**网络级 `Connectors`/`ILLines` 恒空**（429 网络全空，FBD/IL 视图残留字段，生成时写空 List2）；④**LD 文档级转换标志字段群**（`DefaultViewMode=Ld`、`CodesysLDConverted=True` 等 11 个恒定值字段，骨架已含、生成器不用管，读别人工程时别当网络内容解析）。另补值引脚常量类型规律（BOOL 用 `Boolean=True`，数值/时间型用 `Boolean=False`+对应 `Type`）。已回写 `references/native-structure.md`
- **【端到端验证：FUNCTION 调用框返回值结构】** 新增 `scripts/examples/make_func_return_test.py`（生成 `prg_FuncRetTest`：两个 Function 框并联——`PackMLScCmdInit` 最简形态 + `PackMLSCCmdSum` 带 VAR_OUTPUT 尾参，全部用本 POU 局部变量 + 工程全局实例）。验证结果：check_slots / check_symbols（`PLC_GLOBAL_SYMBOLS=Master,PML0`）全 PASS；静默导入（`do_replace.py <file> Application`——parent 传 `Application` 可挂 Application 直属，此前默认 `prg_EM01_Logic`）后**双分类 0 错误**；往返导出结构保持：`[0]=Null(ENO)`、`[1]=返回值变量`、`[2]=VAR_OUTPUT`，索引严格一一对应。**两个新坑**：① `sUnitScCmd[REF]` 形参类型不是简单可见名，本地声明 `stSumTest : sUnitScCmd` 预编译报「没有定义标识符」——照模板 `act90_ScCmd` 接法直接接全局实例成员 `PML0.stCmd.stSc`；② 首次导入报 1 个真实预编译错误被验收流程准确抓到（证明流程有效）。已回写 `references/native-structure.md`
- **【新结构学习：Function 调用框 + MOVE 三形态 + 容器不对称铁律】** 新增 `scripts/ide/scan_all_native.py`（IDE 内 eval_file 执行，递归导出全工程所有对象，实测一次 126 个），基于全量样本摸清四项此前未知的结构：①**容器不对称铁律**（557 框无一例外）：`InputItems` 是 `<List2>` 直接挂在框下、`OutputItems` 是 `Single>List2` 包一层——用同一段代码取两者会把 MOVE 的输入槽数成 0（实测踩坑）；②**Function 调用框**（35 处）：`OutputParam.Names[1]` 恒为空字符串＝函数返回值槽（35/35），`OutputItems[i]` 与 `Names[i]` 严格按索引一一对应，接住返回值＝在 `[1]` 放操作数（已在 `prg_FbCallTest` 实测），InputItems 槽数 == InputParam 数（与 FB 框一致，⚠ 初版统计踩容器不对称坑误判为「恒为空」，已修正）；③**MOVE 三形态**：标准 EN+IN（133 处）/ 多槽触点链（EN 直接串联无显式 AND 框，`dump_155228` 段2 状态机）/ 嵌套框接 EN（`InputParam=['EN']` 无 IN，前框 ENO 链式供 EN，7 处）；④**框可嵌套**：一个功能框可以整体出现在另一个框的 `InputItems[0]` 槽里（EN/ENO 链式调用）。全部回写 `references/native-structure.md`
- **`check_slots.py` 修复 MOVE 原生形态误报 + 容器不对称**：`slots_of()` 按「InputItems 直接 List2 / OutputItems Single>List2」分别取值（旧代码用回退查找，碰巧兼容但语义错误）；新增 `_input_exempt()`——MOVE 的「嵌套框接 EN」（槽0 是 `{acfc6f68}`）与「多槽触点链」（槽0 是触点且槽>2）两种 IDE 原生形态下「输入槽 == InputParam 数」断言不成立是正常的，放行。全量验证：126 个模板 POU + `dump_155228` + 修复后往返文件全部 PASS；历史负样本（TON 少写输出项 18 处、Operand 空单 1 处——均为修复前导出）全部准确抓到，证明豁免没有放过真错误

### 修复
- **修正「Function 框 InputItems 恒为空」的错误结论**：初版统计脚本用 `find("Single[@Name='InputItems']")` 解析，踩了刚写进文档的**容器不对称坑**（InputItems 是 `List2` 直接挂、不在 `Single` 里，find 不到返回 0），得出「35/35 恒为空」的错误结论。用正确解析器复核：**Function 框 InputItems 槽数 == InputParam 参数个数（35/35 等长，与 FB 框一致，槽0=连接器、槽1..n=参数引脚）**。`native-structure.md` 已修正，并补充教训：统计 InputItems 必须走「直接挂 List2」分支，否则静默数 0
- **【重大】`SystemExit` / `SystemError` 穿透 `except Exception` 杀死守护线程**（2026-11-25 实测）：IronPython 2.7 里 `SystemExit`、`KeyboardInterrupt`、`SystemError` **都不继承 `Exception`**，只继承 `BaseException`。后果有两处致命：① `plc_daemon.loop()` 的命令执行层只写了 `except Exception`，被 `eval_file` 执行的脚本一旦 `raise SystemExit`（例如重复注入 daemon 时 `_acquire_instance()` 判定「已有实例存活」），异常会穿透到 `exec` 外层，**把整个轮询线程连同正在运行的守护一起干掉**——实测现象是注入后 0.7 秒内心跳停摆、`bridge` 全部超时，而日志里只有一行 `skip: another daemon alive`，完全看不出是异常穿透。② `a_status()` 里 `online.create_online_application(app)` 在非主线程调用会抛 `SystemError("堆栈为空。")`，同样穿透，导致**整个 `status` 命令失败**（本来只是拿不到在线状态，离线开发时根本用不到）。修复：`loop()` 的命令执行与循环体都补 `except BaseException`；`a_status()` 的在线查询独立 try 并把失败降级为 `online_error` 字段，其余信息照常返回。**教训：在 IronPython 里写「绝不能让线程死」的守护循环，`except Exception` 是不够的**
- **守护进程挂错 BASE 导致 `bridge` 误判「未启动」**（2026-11-25 实测）：`_base.resolve_base()` 最高优先级是「从 `sys.argv[0]` 反推 `<BASE>/ide/xxx.py → <BASE>`」，而 IDE 里手动执行过 `D:\plc_mcp\ide\plc_daemon.py` 之后，`sys.argv[0]` 就固定成那条旧路径——守护把 `ready.flag` / 心跳 / 日志全写进 `D:\plc_mcp\ipc`，而技能包的 `bridge.py` 在 `<技能包>/scripts/ipc` 找不到 `ready.flag`，于是**误判守护没起 → 转去 UIA 点菜单 → 菜单自绘读不到 → 报 `Tools not found`**。权限、IDE 状态都是好的，纯粹是路径不一致。修复：新增 `scripts/ide/boot_daemon.py`（见下）
- **`_acquire_instance()` 的陈旧心跳导致新实例直接 `SystemExit` 退出**：判定「已有守护存活」只看心跳文件 mtime，上一次守护异常退出或 IDE 重开时心跳文件还留着，新实例会误判并退出。`boot_daemon.py` 在启动前检查心跳年龄，超过 `HEARTBEAT_FRESH`(8s) 就把 `heartbeat` / `instance.lock` / `daemon.pid` / `ready.flag` / `cmd.json` / `running.json` / `result.json` 一并清掉

### 新增
- **`scripts/ide/boot_daemon.py`：唯一的守护注入入口**。解决上面三个问题，并把「怎么注入」这件事从「靠 UIA 点菜单」改成「人工点一次菜单 + 这个脚本」。设计要点：① **自解析目录**——先看 globals 里预置的 `PLC_IDE_DIR`（供 `eval_file` 包装器用），再试 `sys.argv[0]`，最后从 `sys.modules` 里已加载的 `plc_daemon` 模块的 `__file__` 反推；优先选「同时含 `boot_daemon.py` 与 `plc_daemon.py`」的目录，避开历史遗留目录。② **强制改写 `sys.argv[0]`** 为 `<BASE>/ide/plc_daemon.py`，让 `_base` 的 derive 逻辑恒等于本技能包，与 `bridge.py` 完全一致。③ **命名空间钉在 `sys._plc_mcp_keep`**——`exec` 的命名空间一旦被回收，`_logf` 被关闭、线程对象被 GC，守护静默死掉（症状：`daemon.log` 0 字节、没有 `heartbeat`）。④ **单独捕获 `SystemExit`**，重复注入时只记一行「已有守护在运行」，不再掀掉正在跑的线程。⑤ 注入全过程写 `ipc/boot_daemon.log` 便于排错
- **`scripts/ide/probe_daemon.py`**：守护诊断脚本（本地 Python 3）。一次性打印「IDE 进程 / 各候选 BASE 的 `ready.flag`+心跳年龄 / 当前 `bridge` 解析到的 BASE 与 IPC / `ping` 结果」，用来快速定位「到底是没注入、还是注入了但挂错目录」

- **【新增 `scripts/ld_logic.py`：逻辑层验收（第四层）】**学自 `Wayan123/multi-plc-agent` 的 `multiplc/iec_ld.py`——它的核心论断是 `The verification compares logic, not XML`：把 native 图形拓扑还原成布尔表达式，DNF 规范化后比对，这样 Id 重编号、节点顺序变化、厂商布局差异都不影响结论。**补现有三层验收的盲区**：双分类 0 错误只证明「编译器不报错」、往返 diff 只证明「IDE 没改写结构」（源文件本身错时照样 PASS）、check_slots 只证明「槽位数对得上」——**都不证明「画的是你要的逻辑」**。实现要点（本机实测结构）：串联条件 = AND 框 `{acfc6f68}`（CallType=And，InputItems 为子条件）；并联 = 分支组 `{827b9ec2}`（Trees 为支路）；触点 = `{9de7f100}`，**`Operand.Flags.Flags` bit0 = 1 即常闭取反**；线圈 = `{c9b2f165}` 且 IsCoil=True；网络 = `{d9a99d73}`，网络项 = `{9873c309}`。**两个踩过的坑**：① `OutputItems` 是 Single 包一层 List2，直接数外层恒得 1 项（与 check_slots 同一个坑）；② 触点变量名在 `Operand{c9b2f165}` 容器的 **`Operand` 子节点**里，容器自身 `.text` 是 None。实测：`user_fixed` 正确还原 `COIL:xOut <= (xOut AND xStopNC) OR (xStartBtn AND xStopNC)`；`prg_LdLearnTest` 与真实往返导出文件逻辑等价 PASS；两个负样本（线圈改名 / 触点加取反）均被精确抓到。已知局限：分支组内 MOVE 框、EXECUTE 块无法还原成布尔式（显示 `TRUE` 或 `BLOCK:类型(实例)`）
- **`task_check.py` 用 `get_message_category_description()` 取分类名**（学自 `multi-plc-agent` 的 `codesys_job.py`）。实测本机可用且返回中文，直接解决上一条留下的「5 个分类里 2 个 GUID 不明身份」：`2af7707f` = **导出/导入**、`194b48a9` = **脚本消息**。验收日志从此全部是人类可读名称，不再硬编码中文标签——GUID 集合因版本/配置而异，**名称才是稳定语义**
- **探测确认本机 SP11 的导出 API 签名**（学自 `tkucic/codesys_workflow_automation` 的 `codesysBulker.saveAndExport`）：`export_native(objects, destination=..., recursive=True, one_file_per_subtree=..., profile_name=..., reporter=...)` 与 `export_xml(objects, path=..., recursive=True, export_folder_structure=..., declarations_as_plaintext=...)` 在本机都可用（`import_xml`/`import_native` 同样存在）。价值：`export_native` 可整工程一次性导出，免去逐个 POU 导出；`export_xml` 的 PLCopenXML 可跨工具交换。⚠ 反射签名时 `fn.Overloads` 在 IronPython 下 `len()` 会报错，直接读 `fn.__doc__` 更可靠。已回写 `references/mcp-bridge.md`
- **【学习外部项目 inoproshop-mcp（x2124824695-stack fork，源自 luke-harriman codesys-mcp-persistent）】两处实质改进融入**：① **消息分类动态枚举 + 全量扫描**——该项目 `compile_project.py` 发现大工程里编译错误会落到硬编码分类之外（Library Manager、POU 专属、工程树等），必须 `get_message_categories()` 动态枚举。`task_check.py` 已改：先枚举并打印全部分类清单，三个基础分类（预编译 `217bc73e` / 编译 `97f48d64` / 格式检查 `0986c5dd`）缺一即 `raise`，其余分类（含外部项目记录的 `220493a1` 附加代码检查）**存在才读、计入合计**。**实测本机 SP11 只暴露 5 个分类（含脚本 `194b48a9`、导入导出 `2af7707f`），`220493a1` 不存在——GUID 集合因版本/配置而异，不能照抄外部项目的分类清单，也不能设为「缺了就 raise」**。附带发现：`Guid` 是 `script_engine.Guid`（.NET 类型），裸写会静默 `NameError`。② **daemon 命令领取-改名防重复执行**——旧机制用 mtime+size 签名判重，执行中途崩溃或签名比较失败时同一命令可能执行两遍（对写入类命令是事故）。改为先原子改名 `cmd.json` → `running.json` 再执行，改名即领取，端到端恰好一次（`bridge.py` 原子写 + daemon 领取改名）。两处均已回写 `references/mcp-bridge.md`
- **`scripts/check_slots.py` 补 `Instance.Operand` 三态断言**：按 CallType 校验 Operand 形态（`FunctionBlock` → 必须 `<Single>实例名</Single>`；`Action`/`Function`/`Program` → 必须 `<Null/>`）。实测负样本验证：对修复前的 `rt_prg_AxisCallTest_155621/153916`（当时 Operand 是空 `<Single>`）准确报出 `CallType=Action 的 Instance.Operand 必须是 <Null/>`，对修复后的 5 个文件全部 PASS。`check_symbols.py`（符号自检：网络引用 vs 声明区）与 `check_slots.py` 的 Operand 断言已补进 `SKILL.md`/`README.md` 脚本表
- **【纠正错误结论】`CallType=Action` 的 `Instance.Operand` 必须是 `<Null/>`，不是空字符串**。之前 `native-structure.md` / `SKILL.md` / `CHANGELOG` 里写的「Action 的 `Instance.Operand` 和 `Instance.Type` 都是空字符串 `""`」是**错的**——那个结论是从「自己导入后再导出的文件」里反推的，属于**循环论证**（IDE 把自己写进去的空 `<Single>` 原样导出，于是"验证"通过）。对照 InoPack 真实模板 16 个 Action 框，**全部是 `<Null Name="Operand" />`**。写成空 `<Single Name="Operand" Type="string" />` 会让 IDE 在框上方多画一个**可填写参数的红色小方框**（用户两次反馈：「正常调用没有这个小方块」「actAbs_NOPE 上面还是有小方框可以填写参数」）。规律：`FunctionBlock` → `Single(实例名)`；`Action`/`Function`/`Program`/`And`/`Move` → `Null`
- **`references/precompile-errors.md` 新增「类型 D：IDE 图形异常」**：D-1 框上方多出可填写小方框。含完整排查过程（先误判为 `Flags.Fixed`，用户第二句「actAbs_NOPE 也有方框」才定位到 Operand 形态）、三态规律表、一行自检代码，以及「自己验证自己 = 没验证」的循环论证教训
- **`references/precompile-errors.md` 新增「类型 E：验收链路本身失效」**：E-1 **所有编译命令都走缓存**（9 条命令逐个实测对照表：预编译分类全部 0 条，只有 `（旧）重新编译`/`检查所有对象`/`运行静态分析`/`生成二进制文件` 会真跑构建但预编译仍是 0）——**只有 `import_native()` 那一刻产生的消息是真的**；E-2 **负样本造错导致误判**（`s.replace('>actAbs<', ...)` 把 BoxType 和 Entry Name 一起改了，`actAbs_ZZZ` 成了合法 action，0 错误是正确结果）
- **`README.md` 铁律新增第 16~20 条、`SKILL.md` 新增第 17~21 条**：16/17 Operand 三态；17/18 **不要在 IDE 脚本里 `sleep`/轮询——会把 InoProShop 界面冻死**（用户原话「你在等待的时候软件卡死了」「还是卡死」），计时重试必须放主机侧；18/19 验收消息只能靠「导入后立刻读」；19/20 action 的 ST 体只能引用宿主 POU 的变量；20/21 造负样本必须精确替换目标字段
- **`README.md` 补一段「铁律 18 的元教训（本轮最大教训）」**：连续三轮把「编译命令报 0 错误」当成「代码没问题」，实际所有编译命令都在读缓存；真正错误只在导入瞬间产生一次，`clear_messages` 一清就永久消失
- **`scripts/ide/task_check.py` 重写**：改为**单次快照、零 sleep、零循环、不 clear_messages**。旧版在 IDE 主线程里 `sleep(8)` + `process_messageloop()` 轮询，直接把界面冻死；且先 `clear_messages` 再编译，导致预编译分类恒为 0 条（假通过）。新版只做「读一次、写文件、立刻返回」（<1s），并同时读预编译/编译/格式检查三个分类，分类不存在直接 `raise`
- **`scripts/examples/make_axis_call.py` 修正 `ACT_ABS_ST`**：原本写 `xPtpCond := xAxisSafety AND xAxisCalling;`，但 `xPtpCond` 只在 `fb_AxisSkelTest` 里声明，`actAbs` 属于 `prg_AxisCallTest` → 预编译报 `[Error] actAbs | 没有定义标识符'xPtpCond'`。改为 `xAxisActAbs := xAxisSafety AND xAxisCalling;`（`xAxisActAbs` 是本 PROGRAM 声明的）。这类错误的三个特征：消息归属对象是 **action 名**不是 POU 名、只在**预编译**分类、编译分类照样报「0 错误,0 警告」
- **`references/native-structure.md` 新增「轴控指令」整节（InoPack `HC_MovePtpV` / `HC_MovePtpR` 实测）**。核心结论：轴控指令（`MC_Power`/`MC_MoveAbsolute`/`MC_MoveRelative`/`MC_Stop`/`MC_Halt`/`MC_SetPosition`/`MC_Reset`/`HMC_MoveVelocity`/`HMC_MoveJog`/`HMC_Home`）**全部写在轴控 FB 内部的 ST 里，LD 层只有「调用封装 FB」一个框**——想在 LD 里直接画 `MC_xxx` 框走不通。含：虚轴 `AXIS_REF_SM3` vs 实轴 `AXIS_REF_ETC_DS402_CS` 的区别、可直接抄的 `HC_MovePtpV` 声明骨架（轴引用必须放 `VAR_IN_OUT`）、8 个指令的完整形参调用写法、**标准 MC 与汇川 HMC 的形参风格差异表**（HMC 用小写 `xEnable/fVelocity/xJogForward`，且 `HMC_Home` 的 `fHmoeVelocity` 是库里的**原始拼写错误**，写 `fHomeVelocity` 会编译报错）、错误码归集（`UINT_TO_DWORD` vs 直接赋 `eErrorID`）、`nAxisState` 状态读法、`HC_sPtpInfo`/`HC_sPtpMan` 数据结构分工、实轴版**双实例交替**避坑（同一实例不能重复触发 Execute，正是 AM521 螺旋插补踩过的坑）
- **`CallType=Action`（全新取值，本轮首次发现）**。调用 POU 内 action 时用，`BoxType` 写 action 名；只有 `EN` 一个参数、`InputItems` 1 个连接器槽。~~`Instance.Operand` 和 `Instance.Type` 都是空字符串 `""`~~ ⚠ **此结论已被证伪**（见本节首条）：正确写法是 `Instance.Operand` 为 `<Null Name="Operand" />`；「空字符串」是从自己导入再导出的文件里反推的循环论证。已记入 `native-structure.md` + `SKILL.md` 已验证模式
- **轴控 FB 在 LD 里的调用写法**：`[REF]` 形参在 `InputParam.Types` 里带 `[REF]` 后缀（`HC_sPtpInfo[REF]`、`AXIS_REF_SM3[REF]`），但引脚 `Operand.Type` 写**去掉后缀**的实际类型；`AXIS_REF_SM3` 引脚的操作数直接写**轴名**（`Master`）
- **`scripts/examples/make_axis_call.py`**：轴控生成器，复现 ①轴控 FB 在 LD 里的调用（4 槽：连接器 + `xCondition` + `stInfo[REF]` + `VirtualAxis[REF]`）、②`CallType=Action` 调用。生成 `prg_AxisCallTest`（PROGRAM，验证 ①②）与 `fb_AxisSkelTest`（FUNCTION_BLOCK，轴控 FB 声明骨架：8 个指令实例 + 轴引用放 `VAR_IN_OUT`）。实测静默导入成功、**双分类 0 错误**、往返 diff 节点数 330/330 与 399/399 全一致
- **`scripts/examples/extract_action_entry.py`**：从模板导出的 native 里切出「action Entry」原始 XML 块作生成模板（action Entry 特征：`EntryList` 下 `IsRoot=False`、`TypeGuid=8ac092e5`、**没有 `Interface`**，`Object` 直接是 `Implementation{25e509de}` + `NetworkList`）
- **`references/precompile-errors.md` 新增「C. 网络注释里的 `<` `>` 未转义 → 凭空多出 XML 子节点」**：预编译 0 / 编译 0 / 导入完全正常，但往返 diff 报「节点数不同 + 从某处起整段错位 + 55 处 diff」。根因是注释文本直接拼进 `<Single Name="Comment" Type="string">`，里面的 `<Null/>` 被 XML 解析器当成**真实子节点**。给出 `xml_text()` 修复、函数定义顺序要求（必须在 `textlines_block` 之前）、以及**排查口诀：diff 报「节点数不同 + 整段错位」时先看错位处父节点是不是 `Comment`/`Text`/`Title`/`Label`，是就 100% 是转义问题，别去改结构**
- **`README.md` 铁律新增第 16 条、`SKILL.md` 新增第 16 条**：往 XML 文本节点塞自由文本必须转义 `<` `>` `&`
- **`README.md` 元教训补一段「铁律 15 的反向提醒」**：铁律 12/13 说「diff PASS 不算数」，铁律 16 说「diff FAIL 可能是自己生成的 XML 不合法」——两者互补，看到 diff FAIL 先排除自身 XML 合法性再改结构
- **`scripts/examples/make_ld_learn.py` 加 `xml_text()` 并给 `__main__` 守卫**：`network()` 的 `comment`、`textlines_block()` 的每一行都过转义；加守卫后其它生成器可以 `import make_ld_learn` 复用 `contact/value_pin/fb_box/network` 等辅助函数而不会顺带执行生成。该文件现在是**最完整的可复用基座**
- **`scripts/check_slots.py`：结构自检脚本**。检查 native 里所有功能框的「`OutputItems` 项数 == `OutputParam` 个数」与「`InputItems` 槽数 == `InputParam` 个数」，`AND` 框豁免参数比对但校验「至少 2 槽」。退出码 0/1，可直接当 CI 断言。**这是唯一能发现「编译器查不出来的结构错误」的手段**——预编译、编译、往返 diff 都查不出来。实测：对 10 个 InoPack 真实样本全部 PASS；对修 bug 前的旧文件准确报出 `TON 输出槽 1 != OutputParam 2 ['Q','ET']` 两处
- **`references/precompile-errors.md` 新增「编译器查不出来的结构错误」一节**：列出两类**不产生任何 Error/Warning、双分类 0、往返 diff 也 PASS** 的错误结构——A. `TON` 的 `OutputItems` 少写一项；B. `AND` 框被误套功能框规则。每类给出「错在哪 / 对的是什么 / 规律表 / 怎么自检」。这类错误只能靠与真实样本逐字段比对发现
- **`references/native-structure.md` 新增「`OutputParam` 里有没有 `ENO`，由 `EN`/`ENO` 字段决定（19/19 实测）」**：`EN/ENO=True` 的框第一项是 `ENO`；`TON` 是 `EN/ENO=False`、`OutputParam=['Q','ET']` 不含 `ENO`。附 8 个框的实测证据表，并更正了原文「第 0 项恒为 `<Null/>` 对应 ENO」的过窄表述（TON 一节同步更正）
- **`references/native-structure.md` / `SKILL.md` 补 `AND` 框与功能框的 `EN`/`ENO` 形态差异**：`AND` 是 `<Null Name="EN"/>`，功能框是 `<Single Type="bool">`；`AND` 的 `InputParam`/`OutputParam` 是空 `List2`，所以「槽位数 == 参数数」对 `AND` 不适用
- **多输出 FB 实际接线的字段规律**：`OutputItems` 每项 `Operand.Type` 必须与 `OutputParam.Types` 逐字一致（含 `ARRAY [0..(c_uiEventNumber - 1)] OF BOOL`、`WSTRING(32)` 等复合类型），`LValue=True`、`Boolean=False`、`IsCoil=False`、`SeriesIndex=-1`
- **`README.md` 铁律新增第 14 条、`SKILL.md` 新增第 15 条**：`OutputItems` 项数 == `OutputParam` 个数，且含不含 `ENO` 由 `EN`/`ENO` 决定；并注明这条**预编译/编译/往返 diff 全都查不出来**
- **`references/precompile-errors.md` 第 8 类问题**：一次性 40+ 条 `符号 'PROGRAM'/'FUNCTION_BLOCK'/'BOOL' 不能识别` + `应该用';' 替换'...'`。给出报错原文、根因（裸 `find` 命中 ST 代码块）、修复代码、**以及往返 diff 查不出来时必须用的语义自检片段**
- **`references/precompile-errors.md` 第 9 类问题**：验收脚本报 `total=0 / 通过` 但 IDE 里真有 48 条 Error。给出假通过的根因代码、修复代码，并立规矩「验收脚本宁可崩，也不能把『读不到』当成『没错误』」
- **`references/native-structure.md`「新建 POU 的完整流程」补两道卡**：第 3 步加「必须锚定 `Interface` 再找 `TextLines`」的警告；第 8 步加「先确认 `check.log` 列出全部 5 个分类，看不到清单 = `total=0` 无效」；新增第 9 步「语义抽查声明区首行（`PROGRAM xxx` / `FUNCTION_BLOCK xxx`）」
- **`README.md` 铁律表新增第 12、13 条**（`TextLines` 定位必须锚定 `Interface`；验收脚本读不到消息必须抛错），并加一段元教训：**往返 diff PASS 不等于内容正确**——源文件本身错时 IDE 原样保留，`rt_diff` 照样 `diffs=0`
- **`SKILL.md` 铁律新增第 12、13、14 条**，并在「已验证的合法模式」补 4 条本轮实测结论：**TON 定时器框**（`CallType=FunctionBlock` 但 `EN/ENO=False`；顶层 `InputItems[0]` 是连接器 `{5f9848d3}`、嵌在 AND 里时是条件触点 `{9de7f100}`；Q/ET 可空接线）、**EXECUTE 框**（`CallType=None`、`ProvidesSTSnippet=True`、`STSnippet` 三层、直挂 `NetworkItems` 不套 NETITEM）、**FUNCTION_BLOCK 里的 LD**（native 层与 PROGRAM 完全同构，唯一区别是声明区首行）、**线圈/输出引脚的 Operand 不带 `Name` 属性**（写错只有往返 diff 会现形）
- **`scripts/examples/make_ld_learn.py`**：学习型生成器，复现 InoPack 模板里 `references` 尚未记载的三种 LD 写法——TON 定时器框（顶层 + 嵌 AND 两种挂载）、EXECUTE 内嵌 ST 代码块、FUNCTION_BLOCK 内的 LD。同时生成 `prg_LdLearnTest`（PROGRAM）与 `fb_LdLearnTest`（FUNCTION_BLOCK），各 3 网络。实测静默导入成功、**双分类 0 错误**、往返 diff `diffs=0`
- **「可回写数据清单」+「四问自查法」**（`AGENTS.md` §6.1 / §6.2，`SKILL.md` 精简版，`docs/iteration.md` §2.1.1 / §2.1.2）。原四类触发只说了「什么类别落到哪个文件」，没说**编程过程中到底要留下哪些原始数据**、也没说**怎么跟另一个 AI 讲清判定口径**，导致换人接手时取证口径不一致。现在补两块：①**现场采集清单 9 项**（新结构完整 `.native`、报错原文整行、定位信息、最小实验记录、双分类错误数、导出往返 diff、IDE 弹窗原文、用户手改前后两份 native、环境快照），明确「报错当次就采，收尾只做归类不重新取证」，并规定①类条目缺「native 文件 / 双分类数字 / 往返 diff」任一项**不许**写进 `references/`；②**四问自查法**（Q1 新格式 / Q2 Bug / Q3 吃过的亏 / Q4 环境），每问只答「有 / 无」，答「有」必须附证据、答「无」要写清查过哪个文件，另附**可直接原文粘贴给其他 AI 的说明块**（含 6 条硬规则）与**常见误判表**（重试即好的抖动不写 / 双分类 0 但图形打不开要写 / 用户手改最高优先 / git 推送问题不写）

### 修改
- **库更新规则从「遇新坑必回写」升级为「四类触发」**。原来只笼统说"遇到新坑要回写"，容易漏记。现明确为四类，每类都规定了**触发信号 / 落到哪个文件 / 必带什么证据**：①**没见过的格式**（新 GUID、层级、属性组合、槽位排布）→ `native-structure.md` + `assets/natives/` 样本 + `scripts/examples/` 生成器，须附双分类 0 错误与往返一致；②**Bug**（脚本报错 / IDE 崩 / 导入失败 / 验收漏报）→ `precompile-errors.md` 或直接修 `scripts/`，须附报错原文与复现步骤；③**吃过的亏**（理解错、结论被证伪）→ 提炼成铁律（README + SKILL 双写），须写清「错在哪 / 对的是什么 / 怎么自检」；④**新配置**（换机器 / IDE 版本 / 路径 / 凭据）→ `mcp-bridge.md` 环境要点，须附一条能直接跑的自检命令。四处同步改写：`SKILL.md`「更新规则」、`AGENTS.md` §6、`docs/iteration.md` §2.1、`README.md`「贡献 / 迭代」
- **更新规则适用范围收窄为「只记中型 PLC（InoProShop 梯形图）相关问题」**。git 推送、DNS、网络、凭据这类仓库工具链问题不再进知识库——它们不是中型 PLC 梯形图知识，混进来会稀释 `references/` 的信噪比。工具链问题只在 `sync.ps1` 等脚本里修，不写文档、不记 CHANGELOG
- `references/mcp-bridge.md`「环境要点」新增**换环境必查的自检表**（BASE 解析 / IPC 目录 / daemon 存活 / IDE 进程与工程 / IronPython 语法 / Git 凭据），每项给出可直接执行的命令与失效表现
- `docs/iteration.md` §1 改动分类表：验证要求从「预编译 0 错误」统一改为「**双分类 0 错误**」；新增「环境配置」类；样本类补「被证伪的旧样本必须替换而非仅追加」；并加注「双分类 0 错误 ≠ 图形没问题」的实测案例（单支路分支组）
- `docs/iteration.md` §2 标准流程补第 ⑨ 步（重新打包 `.skill` 并同步本机技能目录），并新增 §2.1「回写四类触发」对表

### 修复
- **`TON` 的 `OutputItems` 少写一项（编译器查不出来）**。原 `fb_box()` 把「`OutputItems` 第 0 项恒为 `<Null/>`（对应 ENO）」当死规矩写死，给 TON 写 `OutputParam=['Q','ET']` 却只输出 1 个 `<Null/>`。实际 TON 的 `EN`/`ENO` 都是 `False`，`OutputParam` **不含 ENO**，是 `['Q','ET']` 两项，两个输出不接线要写**两个** `<Null/>`（InoPack `HC_ValveCtrl` 7 处 TON 实测全是 `[Null, Null]`）。**这条预编译 0 错误、编译 0 错误、往返 diff 也 PASS，IDE 静默接受**，只有拿真实样本比对「项数 vs 参数数」才发现。已修，并在 `fb_box()` 加 `len(out_vars) != len(out_names)` 即 `raise ValueError` 的断言。修正后重新导入，双分类 0 错误、往返 `diffs=0`（节点数 489→491 / 495→497，正好各多 2 个 `<Null/>`），导出后 IDE 保留两个 `<Null/>`
- **生成器把 POU 声明写进 EXECUTE 框的 ST 代码块，导致预编译 48 条错误**。`make_ld_learn.py` 改声明区时用裸 `raw.find('<Array Name="TextLines"')`，而一份 native 里 `TextLines` 至少两处（`Interface` 下的 POU 声明区 + EXECUTE 框 `STSnippet` 里的 ST 代码），且 `List2[NetworkList]` 在文档中排在 `Interface` **之前**——只要网络里有 EXECUTE 框，`find()` 就命中 ST 代码块。结果声明被塞进 ST、ST 代码被覆盖成 `PROGRAM xxx / VAR ...`，真正的声明区留着骨架 `prg_StartStop` 的旧变量，预编译逐行炸出 `符号 'FUNCTION_BLOCK'/'PROGRAM'/'BOOL' 不能识别`（number=9）、`应该用';' 替换'...'`（number=189）、`POU应以';'结尾`（number=190）、`没有定义标识符'...'`（number=46），共 48 条 Error + 23 条 Warning。修法：`p = raw.find('<Array Name="TextLines"', raw.find('<Single Name="Interface"'))`。修正后重新导入，**预编译 0 错误 + 编译 0 错误**，往返 diff 两个 POU 均 `diffs=0`
- **验收脚本 `task_check.py` 会「假通过」：读不到消息时静默输出 `total=0` 并判验收通过**。`_objs_by_guid` 按 GUID 匹配消息分类时写成 `except Exception: continue` + `return []`，把「读失败」和「没匹配上」全吞掉，`return []` 再把它伪装成干净。实测预编译真实有 48 条 Error，脚本却报 `预编译 : total=0 errors=0` + `验收结论 : 通过`。修法：匹配不到分类即 `raise RuntimeError`，`get_message_objects` 失败也抛错，并先打印全部 5 个分类便于核对（正常 `check.log` 必须能看到 5 个分类清单）。同步更新 `scripts/ide/task_check.py`
- **分支组 `Trees` 只有 1 条支路会让 IDE 绘制网络时崩溃**（用户截图报「在绘制该网络的时候遇到错误 / 不能显示内容 / 索引超出了数组界限」，堆栈在 `IBoxTreeParallel`）。`make_fb_call_test.py` 首版给只有一条 FB 调用的网络套了「单支路分支组 + NETITEM.RValue」，**预编译 0 错误、编译 0 错误，但梯形图编辑器打不开这一级网络**。脚本枚举全部样本后确认：act03_PackMLCmd 的 10 个网络、prg_PackMLCmdTest 的 7 个网络，所有分支组 `Trees` 都是 2，工程里从未出现过 `Trees=1`。修法：单支路时**不用 `branch()`、不套 `NETITEM`**，直接把 AND 框挂 `NetworkItems`（照 act90_PackMLManager 网络3）。改后重新导入，导出结构与实测样本一致，预编译 0 + 编译 0，程序段 2 正常显示
- `scripts/examples/make_fb_call_test.py`：`build_networks()` 改为「多支路 → 分支组直挂；单支路 → AND 框直挂」；`netitem_rvalue()` 标记为**已弃用**并在 docstring 写明踩坑原因，防止后来者照抄

### 新增
- `references/native-structure.md` 新增「⚠ 铁律：分支组的 Trees 必须有 ≥ 2 条支路」一节：症状（绘制错误原文 + 堆栈特征）、根因（`IBoxTreeParallel` 按 ≥2 计算几何）、4 行实测证据表（哪些文件哪些网络 Trees=2 / =1 及绘制结果）、正确与错误结构对照图、参考实现指向 `make_fb_call_test.py` 的 `build_networks()`。并在「关键节点类型」表的分支组一行加上「Trees 必须 ≥2」约束
- **功能块（FB）调用的 native 结构**（act04_Interface + act90_PackMLManager 实测）。FB 框与 MOVE 框同属 `{acfc6f68}`，但 `CallType` 为 `Function`/`Program`/`FunctionBlock`、`BoxType` 填 POU 名、`EN`/`ENO` 是纯 `<Single Type="bool">True</Single>`（不是条件槽）、`Instance.Operand` 只有 `FunctionBlock` 类才填实例名。槽位规则：**`InputItems` 槽位数 == `InputParam` 参数个数（EN 算一个），槽0 恒为连接器 `{5f9848d3}` 且 `Input=Null`，槽1..n 与去掉 EN 后的参数严格一一对应；`OutputItems` 长度 == `OutputParam` 个数，第 0 项恒为 `<Null />`（对应 ENO）**。另记 `InputParam.Names` 填参数名而非操作数、REF 形参在 Types 里带 `[REF]` 后缀
- **`scripts/examples/make_fb_call_test.py`：FB 调用生成器**。三类 `CallType` 各生成一个调用（`Function` 的 `PackMLScCmdInit`、`Program` 的 `prg_EM00_Logic`、`FunctionBlock` 的 `PackMLUnitManager` 带实例 12 入 12 出），全部用本 POU 局部变量、不依赖工程其它对象。实测静默导入成功、导出往返结构与源完全一致、**预编译 0 错误 + 编译 0 错误**
- `references/native-structure.md` 新增「功能块（FB）调用标准结构」一节：与 MOVE 框的 8 项差异对照表、三类 CallType 语义、槽位规则、完整 13 槽结构示例、已验证样本清单
- `scripts/start_daemon.cmd`：给**已经开着的** IDE 注入守护的一键入口。用 UIA `InvokePattern` 点「工具 → 脚本 → 执行脚本文件」，不移动鼠标、不抢键盘焦点、不激活窗口；注入完自检 `ipc/ready.flag` 并打印 `[OK]`/`[FAIL]`
- `scripts/bridge.cmd`：命令行调用入口，按 `PLC_PYTHON` → `py -3` → `python` 顺序挑一个真能跑的 Python 3，避开 Windows 应用商店那个 0 字节的 `python.exe` 存根
- **`scripts/examples/make_packml_cmd_test.py`：从零生成一个完整 LD POU 的可复用生成器**。以 `assets/natives/user_fixed.native` 为骨架，生成 7 网络 PackML 命令层测试程序 `prg_PackMLCmdTest`（模式切换 + Start/Stop/Abort/Clear/Reset/Hold），实测静默导入成功、**预编译 0 错误 0 警告**。脚本内含 `contact/coil/and_box/branch/netitem/network` 全套节点构造函数，可直接改造成任意 POU 生成器
- `references/native-structure.md` 新增 4 节：**NETITEM.Flags 整级输出取反**、**RValue 类型可以是分支组本身**、**分支组 Input 槽公共前缀的两种合法形态**、**新建 POU 的完整 8 步流程**
- `scripts/pack_skill.py`：打包 `.skill` 分发件。文件清单严格取自 `git ls-files`，只打 `SKILL.md` + `references/` + `scripts/` + `assets/`，保证包里永远是已提交版本，不会混入本地改动或已删除的旧文件
- `references/precompile-errors.md` 第 6、7 类问题：C0046 批量未定义标识符、两个 TRUE 串联
- `references/precompile-errors.md` 第 2b 类问题：单条件 rung 的顶层 AND 只有 1 个输入——**预编译 0 错误，构建却报 N 条 `'AND'需要至少'2' 个操作数`**
- `references/mcp-bridge.md`「textual_* 接口不可用时的退路」：用户手工启动的 IDE 实例里对象全是 `ExtendedObject[IScriptObject]`，文本接口失效（`list_pous` 恒 0、`get_pou` 报 POU not found），只能 `export_native` 读、`import_native` 写
- `references/native-structure.md`「声明区（TextLines）结构」与「公共前缀与支路条件去重」两节
- `scripts/examples/make_fix45.py`：补声明 + 删多余 TRUE 的修复脚本
- **分支组「完整支路」标准结构**（用户手改已验证）：外层 AND 框包住 `[MOVE 框, 连接器 {505bff94}]`；**任何一层（含嵌套分支组内部）都适用**
- `scripts/examples/make_full8.py`：把裸 MOVE 支路批量包装成完整支路的生成脚本

### 修改
- `assets/natives/user_fixed.native` 更新为**修复后最终版**：8 支路完整结构（3 顶层 + 内层 6）+ 声明区齐全，预编译 0 错误 0 警告；并在文档中标记为树形结构**首选克隆模板**
- **全部脚本去掉硬编码的用户目录 + 路径自解析**：新增 `scripts/ide/_base.py` 统一路径解析——**环境变量对 IDE 内脚本无效**（daemon 跑在 IDE 进程内，继承的是 IDE 启动那一刻的环境，实测恒为 `None`），且含中文的路径经 `subprocess` 环境变量传给 IDE 会按 GBK 解码损坏。解析优先级改为：`scripts/ide/xxx.py → scripts/` 自身路径反推（`sys.argv[0]` 走 Windows UTF-16 命令行，中文无损，**最可靠**）> `<BASE>/base_path.txt`(手工兜底) > 环境变量(仅 `launch_ide_daemon.py` 启动且路径真实存在时) > `D:\plc_mcp`。`bridge.py` / `do_replace.py` 用同一套规则。日志打印 `BASE = ... (source: ...)` 便于排错
- `README.md`：目录结构补全到实际文件（含 `scripts/examples/`、`sync.cmd`、各 `task_*.py` 用途）；铁律表新增第 9 条；「已验证的合法模式」补公共前缀去重与声明区
- `SKILL.md`：`assets/natives/` 与 `scripts/` 表格按实际用途重排；铁律新增第 9 条；合法模式补两条
- `docs/usage.md`：目录约定补全实际文件；快速排错索引补 §6 与 §7
- `docs/iteration.md`：新增 §5.4「为什么不弹凭据窗口了」，记录 `helper-selector` 弹窗根因与 `wincred` 方案
- `README.md`：快速开始补「IDE 已开着」的一键注入（`start_daemon.cmd`）与 `bridge.cmd`；路径解析表补 IPC 目录优先级**与它和 BASE 解析顺序不同的原因**（IDE 继承旧环境变量导致 ready.flag 写错目录）；目录结构补两个新脚本
- `references/mcp-bridge.md`：修正 `bridge.py` 的 PowerShell 示例（原引号不匹配、路径末尾多一个 `/`），改为推荐 Python 调用 + 正确的 CLI 转义写法
- `references/native-structure.md`：重写「挂载位置规则」，补完整支路结构图与补齐前后对照表
- `.gitignore` / `.gitattributes`：注释从「一句话标签」改写为「为什么 + 挡什么 + 自检命令」。`.gitignore` 补充 gitignore 只对未跟踪文件生效、`git check-ignore -v` 自检、凭据已提交需吊销并清历史的说明；`.gitattributes` 补充跨平台换行根因、`git check-attr` 自检、`*.native` 为何按二进制处理。规则内容本身未变
- `task_silent_import.py`：全局递归 `find_named`/`walk` 替换为 `find_child()`——只在目标父对象（Application）的**直接子对象**里用 `get_children()` 过滤查找，符 README 铁律「禁止全局 find_named」，避免误命中 Task Configuration 里的同名调用对象
- **验收标准从「只看预编译」改为「预编译 + 编译双分类」（库内容整理）**。原先 4 处文档（README/SKILL/AGENTS/usage）都写着「编译分类永远 0 错误，拿它验收等于没验收」，但实测证伪：单条件 rung 的顶层 AND 只有 1 个输入槽时，预编译 0 错误而构建报 N 条 `'AND'需要至少'2' 个操作数`。现在统一为「预编译 `217bc73e` 抓结构错误 + 编译 `97f48d64` 抓语义错误，两者都必须为 0」
- **`scripts/ide/task_check.py` 加 `app.build()`**：原先只执行「检查程序」，不触发构建，导致只在构建期报的错误永远读不到（上面那个矛盾的结构性根源）。现在先「检查程序」再 `build()`，末尾输出 `=== 验收结论 : 通过/不通过 (合计 N 错误) ===`。实测 check 4.42s + build 4.03s，结论正确
- **`references/native-structure.md` 新增「AND 框的输入元数：至少 2 个槽」一节**：原来只在 `precompile-errors.md §2b` 记了症状，结构文档没有对应规则。现补「任何 AND 框（含 NETWORK 顶层 `RValue` 的那个）都要 ≥2 个 `InputItems` 槽，单条件补 `TRUE`」并交叉引用 §2b
- **`references/precompile-errors.md` 消息分类表重写**：删掉「编译分类永远 0 错误、不能当验收」的错误结论，改为「两个分类抓不同错误，缺一不可」
- **`docs/usage.md` §3 验收规范重写**：3.1 改为双分类标准 + 对照表；3.2 输出示例补编译分类与验收结论行；3.3「什么不算验收」补「只看预编译」与「只看编译」两条对称项；§6 禁止事项「用编译分类验收」改为「只看单一分类验收」
- **`AGENTS.md` §2 验收标准重写**：补两分类对照表与实测案例；铁律条数从「8 条」修正为「10 条」
- **`README.md`**：铁律表新增第 10 条（AND 至少 2 个输入槽）；`precompile-errors.md` 描述从「7 类」修正为「8 类」；目录结构补 `make_packml_cmd_test.py`
- **`SKILL.md`**：铁律新增第 10 条；`examples/make_*.py` 说明改为如实描述（`make_full8`/`make_fix45` 读环境变量，`make_packml_cmd_test` 用相对路径）
- **清理失效引用**：`docs/usage.md` 失败排查表引用的 `inspect_native.py` 仓库里不存在，改为实际可用的「与样本逐层标签 diff」做法；`references/native-structure.md` 引用的 `task_precompile.py` 不存在，改为 `task_check.py`

### 修复（早期）
- **PLC_PRG 12 段状态机首版构建报 6 条 `'AND'需要至少'2' 个操作数`**：生成器给单条件 rung
  （上电初始化、进入急停、4 段输出映射）只 append 了 1 个输入槽，AND 框退化成单操作数。
  已改为条件数 < 2 时自动补 `TRUE` 触点；修复后预编译 0 错误、编译 0 错误（仅 CmpLog 库警告）
- **同步时弹「选择凭据助手」窗口**：Git for Windows 的系统级配置是 `credential.helper=helper-selector`，
  每次联网都会弹窗。`sync.ps1` 现在会自动把仓库级凭据助手设为 `wincred`（纯命令行读 Windows 凭据管理器，零弹窗），
  并强制 `GIT_TERMINAL_PROMPT=0` + `GCM_INTERACTIVE=never`；凭据失效时直接报错而不是弹窗等待
- **C0046 批量未定义标识符**（45 个错误的真实根因）：native 只搬「图形 + 声明文本」，图形引用的符号必须在 `Interface/TextDocument/TextLines` 里逐行声明；漏声明 = 每个引用点报一条错误。已为 `prg_StartStop` 补全 8 个状态机变量声明，45 → 0
- **两个 TRUE 串联**：分支组 `Input` 已有公共前缀 TRUE 时，支路 EN 条件框里不要再放 TRUE。已删除 8 条支路里多余的 TRUE
- **修正认知**：裸 MOVE 框挂分支组 Trees 虽预编译 0 错误，但功能链断头、图形不完整；任何层级都需外层 AND + 连接器包装
- `SKILL.md` / `README.md`：修正「内层是裸 MOVE 框」的表述——那是用户未改完的中间状态
- **`plc_daemon.py` 加载即崩（NameError: a_import_native）**：`ACTIONS` 字典引用了在它之后才定义的 `a_import_native` 函数，前向引用导致模块级加载失败、daemon 永远起不来。已把 `a_import_native` 移到 `ACTIONS` 之前
- **daemon 日志文件被锁导致整个守护崩死**：`daemon.log` 被上一个实例的句柄锁住时，`io.open` 抛异常直接中断 daemon 启动。已改为 `_open_log()`：打不开 `daemon.log` 就用带时间戳的日志名降级，绝不让日志问题拖垮守护
- **`task_check.py` 读预编译报 category null**：`get_message_objects` 不能传字符串/GUID 分类，需先枚举 `get_message_categories()` 按 GUID 匹配到分类对象再取消息。已改 `_objs_by_guid`
- **守护 `ready.flag` 写到旧目录、新版永远等不到就绪**（2026-11-25 部署实测）：IDE 进程会继承「启动它的环境」里的 `PLC_MCP_IPC`（实测指向旧工作区 `D:\小艺Work工作空间\20261123160323\plc_mcp\ipc`），而 `_base.resolve_ipc()` 原来环境变量优先，导致 `plc_daemon.py` 把 `ready.flag` / 心跳 / 日志全写进旧目录，`bridge.start_daemon()` 傻等 30 秒后报「守护进程未就绪」。已改为 `<BASE>/ipc` 优先、环境变量仅在该目录不存在时兜底

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
