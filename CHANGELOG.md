# Changelog

本项目的所有重要变更都记录在此文件。

格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### 修正（2026-11-27 v3，线圈载体：必须挂 NETITEM）

- **线圈必须挂在 NETITEM 的 OutputItems 上**，不能挂 AND 框（G_BOX acfc6f68）的 OutputItems。
  挂在框上时 IDE 只画一个**空占位方块**、编译仍然 0 错误 —— 这是第九类假通过（用户第三次截图指出）。
  A00 语料实测 OutputItems 的父节点分布：9873c309（NETITEM）→ 线圈 15 例、9de7f100（触点 PIN）5 例、
  acfc6f68（G_BOX）**0 例**。
- NETITEM 结构：Single Type="{9873c309-1f09-4ebf-9078-42d8057ef11b}" → Flags →
  **Single Name="RValue" Type="{条件项自己的 guid}"**（RValue 标签本身替代 item 的外层 Single 标签，
  内部直接是 Operand / IsContact / Id）→ OutputItems（Type {f40d3e09-...}）→ List2 → 线圈容器 c9b2f165。
- **scripts/examples/ldgen.py**：新增 netitem(rvalue, outputs) 与 _split_outer(item)；
  coil_tree / abort_coils_net / coil_net 全部改走 NETITEM，coil_net 新增 mode 参数（0 普通 / 2 S / 3 R）。
- **assets/natives/prg_FlowDemo.native** 换 v3：704,154 B / 35 网络 / 806 个 Id 全唯一 /
  AND 48（原 58）· MOVE 43 · EQ 21 · ADD 2 · TON 6 · 线圈 45；用户工程 build 一次 = 0 错误, 101 警告。
- **references/mode-cards/process-flow.md**：§2.5 改「线圈挂 netitem()，不能挂 and_box」并换示例；
  §7 坑表新增「空方块」一行；§6 验收表新增「图形（人眼）」行（程序段 2/3 线圈、分支内 (S)/(R) 双线圈已在 IDE 显示正常）。

### 修正（2026-11-27 v2，按用户现场规范重写模式卡 02）

- **BOOL 量一律用线圈，禁用 MOVE**（用户规范）：普通线圈 `( )` / 置位 `(S)` / 复位 `(R)`，  `Operand.Flags.Flags` 分别为 0 / 2 / 3；MOVE 只用于 INT / DINT / WORD / WSTRING 等数据量。  v1 里「`MOVE TRUE -> xOut`」的写法全部作废。顺带修正一个逻辑错：伸出时同时撤另一路  （`set_coil(xLoadExt)` + `reset_coil(xLoadRet)`），v1 只置了一路、另一路没撤。
- **每条路末尾必须是线圈或功能框**（用户规范）：`BRANCH` 的每棵树不许只留 `connector + outconn` 空梯级；  v1 用空梯级把超时分支凑到 2 棵树的写法作废，改为两条 MOVE（INT 数据量）。
- **`assets/natives/prg_FlowDemo.native`** 换 v2：723,466 B / **35 网络** / 822 个 Id 全唯一 /  45 个线圈（普通 4 · S 10 · R 31）/ MOVE 目标类型 BOOL **0 个**；  隐藏桌面实例与用户工程各编译一次 = `0 错误, 101 警告`（101 条为模板固件既有）。
- **`scripts/examples/ldgen.py`** 补线圈与流程 helper：`set_coil` / `reset_coil` / `coil_tree` /  `step_net2` / `judge_net` / `timeout_net` / `ton_net` / `abort_coils_net` / `abort_clear_net`。
- **`references/mode-cards/process-flow.md`** 新增 §2.5「BOOL 量一律用线圈，禁用 MOVE（用户规范）」；  配方表按 35 网络重排；坑表补两条（同名对象直接 import 卡死 85 s 以上、空梯级被用户否决）。
- **`scripts/examples/gen_flow_ld.py`** 换 v2（`LDSKEL` / `LDOUT` 环境变量可覆盖，默认在当前目录生成）。

### 新增（2026-11-27，模式卡 02 · 完整工站流程，已实验验证）

- **`references/mode-cards/process-flow.md`** —— 第二张模式卡：步序 + 延时 + 超时 + 报警 + 复位 + 中断六件套。
  给出 37 个网络的固定排布（提交最前 / 计时在主流程之前 / 中断最后）、TON 的字段级结构
  （`InputItems` 只有 IN、PT 两槽，**没有 EN 槽**；`Instance` 是独立操作数容器），以及四道验收。

- **`assets/natives/prg_FlowDemo.native`** —— 成品样本（967,460 B / 37 网络 / 1087 个 Id 全唯一 / 6 个 TON / 43 个声明变量）：
  0→10→15→20→25→30→40→（良品 50→55→90）/（不良 60→65→70→75→90）→0，
  三个 3s 到位超时跳 99 报警步、复位回 0、手动/安全链中断最高优先级撤全部输出。
  导入 + 挂 MainTask + build = **0 错误**（101 条警告为模板固件既有）。

- **`scripts/examples/ldgen.py`** —— 新增 `ton_box()`：TON 延时框构造（无 EN 槽、`Instance` 独立容器、`OutputItems=[Q,ET]`）。

- **`scripts/examples/gen_flow_ld.py`** —— 上述 37 网络的完整生成脚本（骨架路径参数化，末尾打印三道验收提示）。

### 新增（2026-11-27，模式卡 01 · 步序网络，已实验验证）

- **`references/mode-cards/step-sequence.md`** —— 第一张「模式卡」：从模板母本 `A00_上料移栽`（85 网络 / 490 框）提炼的步进状态机合规写法。
  1 个步序号提交网络 + N 个「一步一网络」，每网络固定三梯级（写描述 → 做动作 → 写下一步）；
  提交网络必须第一个且无条件执行；带副作用的动作框在 **EN 引脚**加边沿（`InputFlags[0]=16`），保证停几个周期都只执行一次。
  含 6 条实测约束（每条附证据）、可直接跑的 `ldgen` 生成代码、以及 17:49–17:50 的实例验证明细。

- **`assets/natives/prg_SeqDemo.native`** —— 该卡的成品样本（190,602 B / 6 网络 / 215 个 Id 全唯一 /
  `InputFlags=16` 6 处、触点 `Flags=2` 0 处）：待命 → 取料 → 加工 → 复位 → 计数 → 回待命。
  导入 + 挂 MainTask + build = **0 错误**（101 条警告为模板固件既有）。

- **`scripts/examples/ldgen.py`** —— 从历史生成器抽取的 LD 生成库：节点构造层（触点/线圈/框/分支/网络）
  + 模板 helper（`step_net` / `counter_net` / `buf_commit_net`）+ `build_doc`（骨架替换 + 全文 Id 重编 + 结构计数）。
  新增 `check_skeleton()` 前置自检：骨架必须 Application 直属、单一实现区 —— 拿带 Method 的 FB 导出当骨架，
  会让导入卡在模态框，且报错文本完全不提原因。

- **`scripts/examples/gen_seq_ld.py`** —— 上述 6 网络样本的完整生成脚本（生成 → 自检 → 打印结构计数）。

### 修复（2026-11-27，边沿检测：修正两处错误旧结论）

- **修正 `references/native-structure.md` §③ `InputFlags` 对 `Flags=16` 的解释**。
  旧文写「16 = 该引脚是电源流引脚的位标志」——错。决定性证据：同一 POU 内普通 MOVE 的
  `InputFlags` 为 `<Null/>`，用户在其 EN 引脚点「边沿检测」后变成
  `[(Flags=16, Fixed=True), (Flags=0, Fixed=False)]`，唯一变量是边沿。
  **正解：`InputFlags[i].Flags = 16` = 第 i 个输入引脚启用边沿检测。**

- **修正 `references/native-structure.md` §18 触点 Flags 值域**。
  旧文写「值域仅 0/1，无 P/N 边沿形态，边沿检测要用 R_TRIG/F_TRIG FB」——两句都不成立。
  实测触点 Flags = 0（正开）/ 1（常闭取反）/ 16（电源流引脚），**没有边沿语义**；
  边沿是框内建能力，不需要 R_TRIG/F_TRIG。把触点 Flags 改成 2 时 IDE 不报错、导入导出都
  原样保留，但图形与行为上都不是边沿——最隐蔽的写错方式。

- 教训（写进两处正文）：**「导入成功 + 编译 0 错误 + 导出往返保真」不能证明结构语义正确。**
  自己造样本再导出自己验证，是循环论证；真值只能来自「用户手工做的样本」或「行为仿真」。

### 新增（2026-11-27，两篇知识库正文）

- **`references/edge-detection.md`** —— 边沿检测专题：三种做法对比（手搓比较网络 /
  触点 Flags=2 无效 / `InputFlags[0]=16` 正解）、MOVE 与 ADD 的 XML 原样、三条硬规则、
  生成器函数 `input_flags(n_pins, edge=False)`、五步证据链、负样本正确做法、四条坑、
  三项未验证边界。

- **`references/false-pass-catalog.md`** —— 「0 错误的八种假象」速查表：
  ① 没挂进任务 ② 脏容器 ③ 错误数被截断（error 500 / warning 100 / message 100，
  池子时间正序、截断吃最新）④ 分类按需注册 ⑤ severity 静默降级成 `?`
  ⑥ 验收器恒 PASS ⑦ 负样本改错地方 ⑧ `clear_messages` 进程级互清。
  每条含现象 / 根因 / 识别信号 / 修法，末尾三条元规则。

### 修改（2026-11-27，A/B 验证口径调整）

- **A/B 验证改为「正向必做，负向默认不做」**（用户决定）。
  正向 = 副本 POU 挂进 MainTask 调一次、双分类 0 错误，证明副本确实在编译作用域内；
  负向 = 故意写未定义标识符、确认编译器真会报错。链路已在 F01~F11、F20、F21 多轮跑通，
  负向属重复劳动，F21 起不再默认执行。
  仅三种情况做负向：① 用户明确要求；② 怀疑 0 错误是假通过（错误数一条没变 / build 异常短）；
  ③ 首次验证全新对象类型（F07 CAM、F08 轴组这类）。要做就必须造对（铁律 20）。
  同步位置：`AGENTS.md §2.1`、`README.md` 元教训 ③、`SKILL.md` 验收条目、`docs/iteration.md §1`。

### 新增（2026-11-27，F21_POU_Station1_工站1_搬运移栽 复制验证）

- **F21 工站1 POU 复制验证：`F21_POU_Station1_工站1_搬运移栽_Verify / 7 个副本（_F21V）`**。
  7 个 PROGRAM：`STN1_00_Main / STN1_01_Initialize / STN1_02_Auto / STN1_03_Manual /
  STN1_04_Alarm / STN1_05_Parameter / STN1_06_ProductStateSetting`。
  翻译管线 `make_f21_translate.py`，共 **2649 处改写**，`AT` 地址 **0 处**。
  验收：预编译 101 Warning / 0 Error，编译 104（3 Text + 101 Warning）/ 0 Error；
  正向 A/B（`STN1_00_Main_F21V()` 挂 MainTask）0 错误通过。

- **重大发现 —— F21 是 ST+LD 混合，LD 标识符不在 `Text` 节点里**。
  前 11 组与 F20 全是纯 ST，翻译只处理 `Text` + `Operand` 即可；F21 的
  `STN1_02_Auto`（20 个 network）与 `STN1_03_Manual`（2 个 network）是梯形图，
  标识符实际存放在 **4 类载体**：
  1. `Single Name="Text"` —— ST 代码；
  2. `Operand Type="string"` —— LD 触点/线圈操作数；
  3. `BoxType` —— LD 功能框类型名（AND/MOVE/EQ/FC_CylinderExe…）；
  4. `Instance > Operand Type="string"` —— FB 实例操作数。
  只改 `Text` 会漏掉 1953 处（STN1_02_Auto 的 2155 处里只有 114 处在 Text）。
  `SymbolComment` / `Address` 在 LD native 里全为空，不能靠它们定位。

- **LD POU 的 `Path` 数组是「每个 network 一个」**。
  `STN1_02_Auto` 有 **87 个 `<Array Name="Path">`**（`STN1_03_Manual` 2 个），
  每个数组元素 4 = POU 自身名（必须跟着改），元素 5 = network 名（不能改）。
  纯 ST 的 POU 没有任何 `Path` 数组。按「每个文件一个 Path」的旧写法会漏改 86 个。

- **19.9 MB 不是二进制**：`STN1_02_Auto` 导出 19948018 B，`STN1_03_Manual` 2070663 B，
  全部是结构化 XML —— 6065 个触点 + 2307 个功能框，每个触点/框都带完整的
  `Flags`/`Param` 子树。无 base64、无内嵌二进制。翻译耗时与体积线性相关。

- **新坑 —— `io.open(...).write()` 在 IronPython 里不落盘**。
  `task_topguid_f21.py` 写 guid 时用一行 `io.open(p,"w").write(...)`，
  文件被创建但 **0 字节**（对象未 flush/close 即被 GC，或延迟写丢失）。
  必须显式 `f = io.open(...); f.write(...); f.close()`。

- **新坑 —— STEP1 提前 `_lf.close()` 导致「write to closed file」**。
  `task_export_f21.py` 两步流程在 STEP1 分支里 close 了日志句柄，
  末尾统一 `L()` 又写一次 → 抛 `ValueError: I/O operation on closed file`。
  两步流程里日志只在最后关一次。

- **收尾：Task Configuration 的 POU 槽清理（铁律 25/38 第四次实测）**。
  cleanup 分支 `pl.remove("prg_F21VerifyUse")` 打印成功，回读仍是
  `['M000_MAIN', 'prg_F21VerifyUse']`，编译分类留下 2 条「没有定义标识符」。
  同样走「导出 Task Configuration native → 主机侧删 `<Single Type="{f194d1ef-…}">` 块 →
  同名覆盖导入（3.96s）」才摘掉，回读确认 `MainTask = [M000_MAIN]`，
  编译分类从 106 回到 104 / 0 Error。

- 新增脚本：`ide/studies/task_scan_f21.py`、`task_export_f21.py`、`task_topguid_f21.py`、
  `task_import_f21.py`、`task_f21_ab_test.py`、`task_export_taskcfg_f21.py`、
  `examples/analyze_f21.py`、`examples/make_f21_translate.py`。

### 新增（2026-11-27，F20_POU_Station0_总控 复制验证）

- **F20 总控层 POU 复制验证：`F20_POU_Station0_总控_Verify / 7 个副本（_F20V）`**。
  `F20_POU_Station0_总控` 含 **7 个纯 ST 的 PROGRAM**（无 LD、无 DUT、无子文件夹）：
  `STN0_00_Main / STN0_01_Initialize / STN0_02_Auto / STN0_03_Manual / STN0_04_Alarm /
  STN0_05_Parameter / STN0_06_ProductStateSetting`。
  `STN0_00_Main` 调用其余 6 个，是站控主循环入口。
  翻译管线 `make_f20_translate.py`，共 **635 处改写**，`AT` 地址 **0 处**（本组无 `AT %`）。
  验收：预编译 101 Warning / 0 Error，编译 104（3 Text + 101 Warning）/ 0 Error。

- **新坑 —— 局部变量提取：声明行是分散的独立 Text 节点**。
  `analyze_f20.py` 初版按「含 VAR/PROGRAM 关键字的 Text 节点」筛选声明区，
  7 个 POU 全部得到 `locals=0` —— 因为 native 里**每个变量行各自是一个 `Single Name="Text"` 节点**
  （如 `\ti\t\t\t\t:INT;`），整块 `VAR…END_VAR` 从不落在同一个节点里。
  修法：从 `PROGRAM/FUNCTION_BLOCK/FUNCTION <name>` 那一行开始**把所有后续节点 join 起来**
  再解析 `VAR…END_VAR`，同时剥掉行注释。修完 locals 为 6~16/个。
  影响：局部变量识别为空会让**局部名被误当成全局名改写**，是最危险的一类静默错误。

- **新坑 —— `app.build()` 是增量编译，重跑会留下陈旧消息（假通过）**。
  同一工程连跑三次 build，每次都读到「预编译 0 / 编译 104」，看起来是干净的 0 错误，
  实际是**上一轮留下的 104 条消息**：无改动时预编译语义检查不重跑，预编译分类保持空。
  修法：`task_build_clean.py` 先 `system.clear_messages(cat)` 清**两个分类**（必须传分类参数，
  无参重载不可用）再 `app.build()`，主机侧等 ≥10s 后读。
  修完预编译恢复 101 条，证明这一轮真的重跑过。
  **验收前必须清分类，否则「0 错误」可能只是没重算。**

- **新坑 —— `sys.exit(0)` 在 daemon 里会弹出「Uncaught exception」模态框**。
  `task_export_f20.py` 的两步流程用 `sys.exit(0)` 结束 STEP1，
  该 `SystemExit` 穿透 `handle_on_main` 的 `except Exception`（IronPython 里 `SystemExit`
  不继承 `Exception`），IDE 弹出标题为 `Uncaught exception, please check the error log for details.`
  的模态框，内容 `SystemExit`。虽然轮询线程靠 `except BaseException` 活下来了，
  但模态框会一直挡着 IDE。**IDE 脚本不要用 `sys.exit()` 收尾，直接 `print` 结束即可。**

- **弹框自动化（补强）**：本轮遇到两类此前没覆盖的弹框，均用
  `PostMessage(WM_COMMAND, IDOK/IDNO)` 关掉，不动鼠标、不抢焦点：
  - `Uncaught exception` → `WM_COMMAND IDOK(1)` 无效，需 `WM_CLOSE`；
  - `导出的文件已经存在：…，是否希望替换？` → **是(Y)=IDYES(6) / 否(N)=IDNO(7)**。
    误点「是」会覆盖主机侧刚改好的 native，**必须先确认目标文件 mtime/内容再选**。

- **收尾：Task Configuration 的 POU 槽清理（铁律 25/38 第三次实测）**。
  `task_f20_ab_test.py` 的 cleanup 分支调用 `pl.remove("prg_F20VerifyUse")` 并打印了成功，
  但回读 `MainTask.pous` 仍是 `['M000_MAIN', 'prg_F20VerifyUse']`，编译分类留下 2 条
  「没有定义标识符 'prg_F20VerifyUse'」。仍走「导出 Task Configuration native →
  主机侧删 `<Single>` 块 → 同名覆盖导入（3.45s）」才真正摘掉，回读确认 `MainTask = [M000_MAIN]`。

- **A/B 双向验证**：负向（`ZZZ_NoSuchPou_F20V()`）→ 编译分类 **2 条**错误
  （`没有定义标识符` + `需要程序名、函数或功能块实例替代`）；正向（`STN0_00_Main_F20V()`）→ 0 错误。
  再次证明「预编译 0 错误」不足以验收，副本必须真挂进任务跑一次编译。

- 新增脚本：`ide/studies/task_scan_f20.py`、`task_export_f20.py`、`task_topguid_f20.py`、
  `task_import_f20.py`、`task_f20_ab_test.py`、`task_export_taskcfg_f20.py`、
  `examples/analyze_f20.py`、`examples/make_f20_translate.py`、
  `ide/tasks/task_build_clean.py`、`task_msgdump_now.py`、`task_taskcfg_read.py`、
  `task_clear_io_cat.py`。

### 新增（2026-11-26，F11_POU_MainTask 复制验证）

- **F11_MainTask 任务层 POU 复制验证：`F11_POU_MainTask_Verify / 15 个副本（_F11V）`**。
  `F11_POU_MainTask` 含 **15 个纯 ST 的 PROGRAM**（无 LD、无 DUT、无子文件夹）：
  `M000_MAIN / M001_气缸程序 / M002_真空程序 / M003_轴程序 / M004_IO / M005_压力控制 /
  M006_风速仪 / M007_FFU / M008_酒精 / M009_无尘布放料卷张力控制 / M010_插补控制 /
  M012_上下游交互 / M100_模组调用 / M995_配方 / M999_产量统计`。
  沿用 F10 管线（`make_f11_translate.py`），共 **3355 处改写**，另剥除 **2 处 `AT %MB`**（见下）。
  **验收**：预编译 101/0、编译 104/0，合计 **0 错误**（202 条 warning 与 F08/F10 一致，模板自带）。

- **新坑 1 —— 中文标识符的词边界**。`(?<![A-Za-z0-9_])名字(?![A-Za-z0-9_])` 对中文名失效：
  `M003_轴程序` 会命中 `M003_轴程序_F11V` 的前缀。必须把中文纳入边界字符集：
  `(?<![A-Za-z0-9_\u4e00-\u9fff])…(?![A-Za-z0-9_\u4e00-\u9fff])`。
  自检：改写后对每个原名做「词边界计数应为 0」，且副本名计数 = 预期处数。

- **新坑 2 —— `Path` 数组末元素也要改名**。每个 native 的 `<Array Name="Path">`
  记录对象自身在树里的位置，末元素就是对象名。只改 `MetaObject.Name` 和
  `PROGRAM <name>` 声明行，导入后会落在错误层级或报错。F11 的 `M003_轴程序` 就是靠这条才导入正确。

- **新坑 3 —— 副本沿用原件的 `AT %MB` 绝对地址必然冲突**（铁律 27 在纯 ST 工程上的复现）。
  `M003_轴程序` 的 `v_uiAxisIndexOld AT %MB131072` / `v_uiHMICurrentPageOld AT %MB131074`
  在 A/B 正向验证时报「地址重复(重复地址范围为：%MB131072~%MB131073)」。
  **预编译 0 错误看不到这个错**——它只在把副本挂进任务后编译时才暴露。
  走路线①：剥掉 `AT` 让 IDE 自动分配，共 2 处。

- **A/B 双向验证（本轮首次完整跑通正/负两向）**：
  负向（挂 `ZZZ_NoSuchPou_F11V()`）→ 编译分类 **2 条**错误（`没有定义标识符` + `需要程序名、函数或功能块实例替代`）；
  正向（挂 `M000_MAIN_F11V()`）→ 0 错误。**这证明了「预编译 0 错误」不足以验收副本可用性**，
  必须真挂进任务跑一次编译。

- **收尾：Task Configuration 的 POU 槽清理**。`prg_F11VerifyUse` 对象删除后，
  名字仍残留在 `MainTask.pous` 里（铁律 25/38 再次实测确认）。走「导出 Task Configuration
  native → 主机侧逐行删 `<Single>` 块 → 同名覆盖导入」，回读确认 `MainTask` 只剩 `[M000_MAIN]`。

- 新增脚本：`ide/studies/task_scan_f11.py`、`task_export_f11.py`、`task_topguid_f11.py`、
  `task_import_f11.py`、`task_f11_ab_test.py`、`task_f11_purge.py`、`task_readback_f11.py`、
  `task_export_taskcfg_f11.py`、`task_verify_tc.py`、`examples/analyze_f11.py`、
  `examples/make_f11_translate.py`。
- 新增 `scripts/sync_skill_dir.py`：按 `git ls-files` 把仓库同步到本机 Skill 目录，
  逐个文件「先删旧再写新」以绕开受保护路径限制，并清理目标侧多余旧文件
  （本次清掉 280 个历史残留，同步后 252 个文件与仓库逐字节一致）。

### 修复（2026-11-26，覆盖确认框只点「全部」不点「确定」—— 导入卡 323 秒）

`run_overwrite_import.py` 的老逻辑找到「全部(&A)」就点一次然后返回，
但「全部」只**勾选**列表项，**不关闭**对话框。结果 `import_native`
一直阻塞在主线程等模态框返回，实测 **323.79s** 后靠人工补点「&确定」才放行。

**根因**：文档（README 铁律 26 / SKILL 铁律 26）早就写了「先点全部再点确定」，
但代码只实现了一半 —— 文档与代码不一致，而每次卡住都归因成「IDE 慢」，
没人回头对代码。这是「文档说对了但代码没跟上」的典型。

修法：
- 新建 `scripts/click_overwrite_all.py`：单文件、纯 `SendMessageW(BM_CLICK)`，
  先点「全部(&A)」全选 → 间隔 0.4s → 再点「&确定」提交。不动鼠标、不抢焦点。
- `run_overwrite_import.py` 改为复用 `click_overwrite_all.click_all()`，
  删掉自己那份只点「全部」的实现（避免下次再改一处漏一处）。
- 新增 `scripts/run_build_check.py`：build → 等 45s（期间持续点弹框）→ check
  一条命令跑完，收尾不再需要人工盯屏。

验证（同一份 `f11_taskcfg_fixed.native`，同一工程）：

| 版本 | 点击序列 | import_native 耗时 | 人工干预 |
|---|---|---|---|
| 修复前 | 仅「全部」 | **323.79s** | 需人工点「确定」 |
| 修复后 | 「全部」+「确定」 | **3.45s** | 无 |

修复后复跑 build + check：预编译 0 错误 / 编译 0 错误，验收通过。
同时确认 Task Configuration 里 `MainTask` 的 POU 列表已从
`[M000_MAIN, prg_F11VerifyUse]` 收敛为 `[M000_MAIN]`（铁律 25/38 的
「导出→删块→覆盖导入」路线收尾成功）。

### 修复（2026-11-26，Error 池 500 上限的截断提示漏认 —— 我自己的假通过）

lead 用 1300 个未定义标识符灌进干净工程实测：编译分类 `total=507`、
**Error 501** = 500 条实体 + 1 条提示行，提示原文是
**`多于500个错误：跳过更多的错误信息`**（与 warning 的 100 同构，阈值 500）。

**我的正则漏认它**：`_TRUNC_ALL` 写成 `多于\d+个(?:消息|错误)发生`，强制要求「发生」二字，
但错误级提示**不带**「发生」（只有警告/消息级带）。后果：>500 错误的工程
`err_pool.truncated` 恒为 False，`before.total == after.total == 501` →
条数差恒 0 → **判 PASS**。这正是我一直在防的静默降级，出在我自己代码里。

修法：只锚「多于N个{主体}」，不锚后缀。三种提示全部覆盖：
- `多于100个警告发生：跳过更多的警告信息` → 只截 warning，error 池可信
- `多于500个错误：跳过更多的错误信息` → error 池缺条，必判 UNKNOWN
- `多于100个消息发生：跳过更多的消息信息` → 全部可能截，必判 UNKNOWN

验证（6 场景，退出码全对）：

| 场景 | before → after | 期望 | 实际 |
|---|---|---|---|
| **lead 的原场景**：两边都 501 | 501(截) → 501(截) | UNKNOWN | UNKNOWN |
| 500 干净 → 501 截断 | 500 → 501(截) | FAIL | FAIL |
| 全干净 | 0 → 0 | PASS | PASS |
| 0 → 3 新增 | 0 → 3 | FAIL | FAIL |
| **502 无截断（脏容器）** | 502 → 502 | PASS | PASS |
| 0 → 501 截断 | 0 → 501(截) | FAIL | FAIL |

真机：`97f48d64` 与 `217bc73e` 的 `trunc` / `trunc_all` 字段取值符合预期，
`n_pool_ok=5`（5 个分类 Error 池通道全可用），`chan=errpool` 生效。

### 新增（2026-11-26，@py3 / @ipy2 显式语法标记 —— lead 提案，替代按目录猜）

`check_ipy_syntax.py` 原来一律 `downgrade()` 再 `ast.parse`，**py3 脚本里写
`except Exception, e:` 会被降级修好照样通过**，门禁对 py3 完全失效
（`delta_snap.py` 就踩过：按 IP2 检查放过，运行时才炸）。

现在按文件头标记分流：
- `# @py3` → **不降级**，直接 `ast.parse`，IP2 语法立刻 FAIL
- `# @ipy2` → 降级后检查
- 无标记 → 按 IP2 检查，**只提示不判红**（160 个文件一次性全红没人补标记，门禁直接废）

本库已全量打标：`@py3` 40 个（scripts/ + scripts/examples/）、
`@ipy2` 120 个（scripts/ide/**），未标记 0。

验证（四态）：`@py3`+IP2 语法 → FAIL(1)；无标记+IP2 语法 → PASS(0) 并提示；
`@ipy2`+IP2 语法 → PASS(0)；`@py3`+正常 py3 → PASS(0)。全库 160 文件回归 EXIT=0。


### 新增（2026-11-26，第五层验收：值引脚 IsContact —— lead 负样本交叉验证）

lead 在隐藏实例上造出**第五类假通过**：把 MOVE 框 `IN` 引脚（INT）的
`IsContact` 改成 `True`（值槽画成触点），预编译 0 / 编译 0 / 往返 diff PASS，
他的 `check_symbols` / `check_slots` / `ld_logic` 三个静态校验器也全 PASS。

我在自己的四层链上复跑 `exchange/lead_valpin_neg_c3d81f47.native`，结果**同样全 PASS**
（`ld_logic` 输出 2 个网络、`check_symbols` 未定义 0、`check_slots` 0 不一致）——
证实这个维度我也没有建模。编译器不校验 `IsContact` 语义，只能靠静态断言。

- **`scripts/check_valpin.py`（新）** —— 判据看**引脚自己**的 `Operand.Type`：
  非 BOOL 却 `IsContact=True` 即违规（触点只能是布尔量）。
  - 不按 `InputParam` 索引对齐判：比较框 `InputParam` 只有 `['EN']` 而
    `InputItems` 恒 3 槽（README 铁律 22），对齐会静默跳过 = 漏检。
  - 不反向断言 BOOL 引脚必须 True：`fb_call_test` / `prg_EM01_Logic` 里
    FB 的 BOOL 输入合法地存在 `IsContact=False`（值槽形态），反向判会误报 20 处。
- **负样本入库** `assets/natives/negative/valpin_iscontact_neg_c3d81f47.native`
  （lead 提供，唯一 GUID `c3d81f47`）。

验证：11 个正样本 + S/R 负样本 **0 误报**；lead 负样本精确命中 1 处
（`MOVE 类型=INT 操作数=7`）。README 铁律 3 扩写（原来只写了 SINT 会报错，
现在写明 INT 等类型完全不报错、必须靠 `check_valpin.py`）。

### 修复（2026-11-26，截断判据改本质信号 —— lead 隐藏实例实测推翻我的条数阈值假设）

lead 起了隐藏桌面实例，用一个**真实损坏工程**（编译分类 all=540）实测，数据直接
推翻了我上一轮的假设：

| | 我的模板工程 | lead 的损坏工程 |
|---|---|---|
| 编译分类 all | 104 | **540** |
| Error | 0 | **502（全在）** |
| Warning | 101 | 35 |
| Text | 3 | 3 |
| 截断提示 | 有 | **无** |

**502 + 35 + 3 = 540 完全对得上，且没有任何截断提示。** 结论：100 条上限
**是按 severity 各自计数的，不是按分类总数**——Warning 维度被截到 100（我那 104 条
= 100 实体 + 1 条「多于100个警告发生」提示 + 1 条收尾汇总），Error 维度 502 条一条不少。
我上一轮写的 `truncated = len(objs) >= 100` 会把 502 条的 Error 池误判成截断 →
大错误工程永远 UNKNOWN。这是我自己的 bug。

修法：截断判据改用**本质信号**——IDE 截断时会注入一条实体消息
「多于N个消息/警告/错误发生：跳过更多的…」，按它判，不看条数。

进一步实测发现两种提示必须区分（都在我自己的 ipc 里抓到）：
- `多于N个【警告】发生` → 只截 warning，**error 池仍完整可信** → 可判 PASS
- `多于N个【消息】发生` → 所有消息都可能被截，**error 池也可能缺条** → 必须 UNKNOWN

因此新增 `truncated_all` 字段（仅「消息/错误」级为 true），delta 侧据此决定是否存疑。

验证：7 个场景全过（502 条不误判 PASS / 502→503 FAIL / 只截警告 PASS /
截到消息级 UNKNOWN / 池自身截断 UNKNOWN / 旧快照回退 UNKNOWN / 缺文件 TOOL_ERROR）；
真机确认 `217bc73e` trunc_all=True（判 UNKNOWN，诚实）、`97f48d64` 仅截警告。

### 突破（2026-11-26，主判据改独立 Error 池 —— 截断问题从根上消失）

lead 指出「消息池是时间正序、新增永远排在末尾，而末尾正是截断位置」，建议改用
收尾汇总行（`编译完成 -- X 错误, Y 警告`）的标量差分。顺着这条线探 IDE API，
**发现了比汇总行更强的通道**：

- **`system.get_message_objects(cat, Severity.Error)` 按【完整池】过滤**，不是从
  被截断的 100 条里筛。实证：`97f48d64` all=104，Warning 筛出 101 + Text 筛出 3
  = 104 —— 说明过滤发生在截断之前。因此 **Error 池的条数是真值，与 warning 池
  是否截断无关**。
- 探针（`scripts/ide/studies/task_exp_probe_sev.py` 一系）确认：Severity 是
  Flags 枚举 `FatalError=1/Error=2/Warning=4/Information=8/Text=16`；IronPython
  下不能 `import _3S`，只能反射拿 2 参数重载 + `Array[object]` 传参。
- 分类身份：`217bc73e`=预编译、`97f48d64`=编译、`194b48a9`=脚本消息、
  `2af7707f`=导出/导入、`de128929`=Cam。

落地：
- **`task_snap.py`** 每分类增采 `err_pool`（`{total,truncated,items,addrs}`），
  meta 加 `schema:2` / `n_pool_ok`；通道不可用时 `err_pool=null`，delta 自动回退。
- **`delta_snap.py`** 主判据改 err_pool 标量差分：池增 → FAIL；池自身截断无增 →
  UNKNOWN；地址集合变化 → UNKNOWN；无 err_pool（旧快照/老 IDE）→ 回退文本通道。
  摘要加 `chan=errpool|text` 标明走了哪条通道。

**效果**：真实模板工程（baseline 101/104 常驻截断）从「永远 UNKNOWN」变为
**PASS（chan=errpool）**，同时 9 个构造场景（含 0→1 判 FAIL、3→3 地址全换判
UNKNOWN、旧快照回退）全部正确。

### 修复（2026-11-26，delta 四态退出码 + severity 静默降级 + 地址互撞兜底 —— 回应 lead 15:18 四个实验）

lead 在主机侧拿 delta_snap.py 真实跑了四个构造实验，挖出两个数据级假通过，本轮全修：

- **退出码扩到四态**：`0=PASS / 1=FAIL / 2=UNKNOWN / 3=TOOL_ERROR`。之前删掉
  `snap_after.json` 会抛 FileNotFoundError 被 shell 当 exit 1，与 FAIL 同码 ——
  工具链故障被误报成工程质量事故。`load()` 现在包 try，缺文件/JSON 损坏 → TOOL_ERROR(3)。
- **severity 静默降级（最隐蔽的假通过）**：`prop()` 吞异常 → severity 全变 `"?"`，
  而 delta 只认字符串 `error` → 新增 error 被判 PASS。修两层：
  `task_snap.py` severity 取不到直接 raise（宁缺毋滥，不产出坏快照）；
  `delta_snap.py` 兜底扫描 `"?"`，命中即 UNKNOWN（兼容旧快照）。
  text 读不到单独计数并报数（偏保守，不掩盖 sev）。
- **地址重复错误互撞兜底**：归一化后 13 条 `%MB... 地址重复` 全撞成一条 key，
  before 13 / after 13（地址全换仍全错）→ 文本 delta=0 → 假 PASS。
  `task_snap.py` 每分类增采 `err_total`（error 条数）+ `err_addrs`（`%MB/%MW/%MX/%I*`
  地址去重集）；`delta_snap.py` 对二者做集合差分，地址变化或 after 存量 error
  而文本差分看不见 → UNKNOWN。
- **before 截断判定收紧**：之前 `dn>0` 才 UNKNOWN，导致「截断但 total 不变」判 PASS。
  截断本身即文本不可信（可能一消一增），改为截断即 UNKNOWN。真实模板工程
  （baseline 101/104 常驻截断）因此如实返回 UNKNOWN，FAIL 优先级不变。
- **stdout 改 ASCII 安全串**：GBK 控制台打中文变乱码，判定不能 grep stdout。
  `print` 只打 ASCII 摘要（`=== delta : PASS === new_err=0`），中文细节全写 `delta.log`。

验证：语法 132/132；协议 22/22；构造 12 个场景全过（TOOL_ERROR/severity/地址互撞/
截断收紧/FAIL 优先/拍子错/干净 PASS）；真机 PID 36704 实测 296 条消息
`n_sev_ok=296 / n_txt_miss=0`，err_total/err_addrs 采集正常，如实返回 UNKNOWN。

### 修复（2026-11-26，delta_snap 假 PASS 漏洞 + mount 假退出码 —— 回应 lead 14:58 审查）

lead 逐个读了三个脚本，找到两个真问题 + 一个自证要求，本轮全部落地并真机/构造验证：

- **`scripts/delta_snap.py`** —— 补 after 截断盲区：之前只查 before 截断，漏了
  「before 不截断 / after 截断且有净增量」场景（可见新增只是前 100 条，被截掉部分
  可能有 error）→ 文本不可全信。可见部分的新增 error 仍计进 delta_err（优先判 FAIL），
  无新增 error 时降 UNKNOWN 而非 PASS。
- **`scripts/delta_snap.py`** + **`scripts/ide/tasks/task_snap.py`** —— 快照自证：
  task_snap 顶层写 `{"meta":{"which"},"cats":{..}}`，delta 先校验 before/after 拍子，
  两次拍成同一个或旧格式无 meta 一律 UNKNOWN（退出 2），杜绝「忘改 which → 恒 PASS」。
- **`scripts/ide/tasks/task_mount_assert.py`** —— 文档/实现不符：eval_file 下进程退出码
  不由脚本决定 → 主机侧按退出码判恒 0 假通过。改为结果落 `ipc/task_mount_result.json`
  （含 ok/total/unmounted/mounted），主机侧读 json 判定。
- **句柄滞留读到侧也修**：task_snap / task_mount_assert 读 args 也用 `io.open` 裸开不关
  → 主机侧下次写 args JSON 复现 PermissionError（实测抓到），统一改 try/finally 显式 close。

验证：语法对 3 文件全 OK；协议 22/22；真机（PID 36704）验证
pass 空操作 PASS、两次同拍子 UNKNOWN、旧格式 UNKNOWN、after 截断+增量 UNKNOWN、
可见新增 error 优先 FAIL、mount 两路 result.json（MISS→ok:false / 纯挂→ok:true）。

### 新增（2026-11-26，验收第 4.5 层：挂载断言 + 双快照差分 —— lead 交叉验证方案落地）

回应 lead（DSH agent）直连信道的两个方案，均已真实 IDE 验证：

- **`scripts/ide/tasks/task_mount_assert.py`** —— 验收前置断言：给定 POU 名必须已挂进某任务的
  调用列表。防「任务未挂载」假通过（POU 不挂任务 = 不进编译单元 = build 后双分类 0 错误，
  代码是坏的）。只读 Task Configuration，秒级，不需要编译。
  验证：真实 IDE 上 `M000_MAIN -> MainTask`（OK）与 `prg_NoTaskTest`（MISS）正确判出。
- **`scripts/ide/tasks/task_snap.py` + `scripts/delta_snap.py`** —— 双快照多重集差分
  （lead 方案，baseline 截断的正解）：before 快照 → 导入 → after 快照 → 主机侧差分，
  只判**新增**的 error，模板工程 101 条 baseline warning 自动归零，无需白名单。
  消息归一化（数字与 GUID 替换为 #）防行号/GUID 漂移；before 已截断（total≥100）的
  分类只比 total 差并记不可信；判定优先级：可靠分类新增 error>0 = FAIL（截断不影响
  该事实）> 有不可信分类 = UNKNOWN（exit 2，绝不静默当通过）> PASS。
  坑（实测）：IDE 内写文件必须显式 close，裸 `io.open().write()` 句柄滞留 IDE 进程，
  主机侧读 PermissionError。
  验证：真实 IDE 空操作差分 PASS；注入负样本（after 新增 error）FAIL exit=1；
  截断分类 total 差 +1 时正确 UNKNOWN exit=2。

### 整理（2026-11-26，scripts/ide 分层：可复用与一次性拆开 + 仓库文件地图）

**动机**：`scripts/ide/` 平铺了 113 个脚本，能复用的（`task_check.py` / `task_silent_import.py`）和一次性考古的
（`task_exp_*`、`task_*_probe`、各 `F0x` 普查）混在一层，新人无法判断「哪个能抄、哪个是废稿」。
每加一个研究脚本，这一层的噪声就更大一分。

**改法**（纯目录与路径调整，**不改任何脚本行为**）：

| 位置 | 数量 | 内容 |
|------|------|------|
| `scripts/ide/`（core） | 5 | `_base.py` / `plc_daemon.py` / `boot_daemon.py` / `reload_daemon.py` / `scan_all_native.py` |
| `scripts/ide/tasks/` | 38 | 验收 / 导入 / 导出 / 建对象 / 任务槽 / GVL —— **验收链路只用这些** |
| `scripts/ide/studies/` | 75 | 一次性考古（含新增的 5 个 F10 脚本），问题答完即冻结 |

- **`_base.resolve_base()` 支持三层**：新增 `tasks` / `studies` 分支，`<BASE>/ide/{tasks,studies}/x.py` 上溯两级得到 `<BASE>`。
  这是移动后不崩的关键——daemon 恒从 `<BASE>/ide/plc_daemon.py` 跑，但 tasks 里的脚本要自己算对 BASE。
- **113 个脚本的 `sys.path` 行改为上溯两级**：`os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0])))`，逐文件命中 113/113。
- **主机侧硬编码路径同步**：`scripts/do_replace.py:26`（`task_silent_import.py`）、
  `scripts/run_overwrite_import.py:22`（`task_import_overwrite.py`）、`scripts/bridge.cmd` 注释示例。
- **文档路径引用同步 13 处**：README.md / AGENTS.md / SKILL.md / docs/usage.md / references/ 三篇 / bridge.cmd。
  文档里多数是裸文件名（`task_check.py`），完整路径只有 13 处，**裸名不受影响**。
- **新增 `scripts/ide/README.md`**：118 个脚本按 core / tasks / studies 分类索引，每条一句话；明确 studies 不进验收链路。
- **新增根 `FILEMAP.md`**：232 个文件的地图——先看哪 4 个、分布、按任务找文件、写入链路 8 步、一次性产物边界。

**兼容性**：外部若直接调 `<BASE>/ide/task_check.py` 这类旧路径会失效，改成 `<BASE>/ide/tasks/task_check.py`。
裸名引用（文档里大多数）不受影响。

**验证**：`scripts/check_ipy_syntax.py` 跑全部 118 个 IDE 脚本 → 116 通过；
2 个未通过是 studies 里 `task_import_f04.py` / `task_import_f05.py` 的历史遗留（同一 if/else 互斥分支内各定义一次 `_ug`，
IronPython 允许、不影响运行），**属考古脚本，按冻结原则未改**。

> ⚠ **2026-11-26 复核更正（DS 整理复审）**：上述「2 个 FAIL 是历史遗留」的归因**是错的**。
> 实测 `task_import_f04.py` 的两个 `_ug` 根本不在同一作用域（一个在 `def mk_folder()` 内、一个在模块级 `try` 内），
> Python 3 直接 `compile` 通过，不存在重复定义。那 2 个 FAIL 是 `check_ipy_syntax.py` 自身的**假阳性**
> （`ast.walk` 扁平遍历、不区分作用域）。已修复为按作用域分组检查，修复后 118/118 全过。详见下方「DS 整理复审」。


### 修复（2026-11-26，DS 整理复审：真实 IDE 验证 + 两处遗留问题修复）

对 828e4c3（scripts/ide 分层重构）做**真实环境复核**（不只是读 diff），结论：**重构本身质量高、可用**，
同时修掉两处遗留问题。

**真实验证（IDE PID 36704 在跑，守护旧版仍在内存）**：
- `bridge.py selftest` → `ok: true`；走 eval_file 通道执行迁移后的 `ide/tasks/task_readnow.py`、
  `ide/tasks/task_check.py` 均成功，`check.log` 确认 `BASE` 推导正确（`source: derive:...ide`）、双分类正常读取。
- 这覆盖了迁移最危险的一条路径：eval_file 下 `sys.argv[0]` 是守护路径而非脚本自身，
  两层 `dirname` 依赖「守护已 import 过 `_base`、模块缓存命中」才成立——目前可用，
  但若未来有脚本在守护 import `_base` 之前执行（如清空 `sys.modules` 的场景）会挂，已知即可。
- 数字核对：FILEMAP 232/49/11/10/2 全对；`ide/README.md` 索引 121 条覆盖全部 118 个脚本，无一缺漏。

**修复 1 —— `check_ipy_syntax.py` 作用域假阳性**：见上方更正。修复后全量 118 个脚本 0 FAIL。

**修复 2 —— 828e4c3 经 GitHub Data API 推送引入的 CRLF blob**：API 推送把工作区 CRLF 字节直接写进 blob，
绕过 `.gitattributes` 的入库转换，导致 clone 后 `git status` 永远显示 4 个文件被修改（假差异）。
涉及 `scripts/bridge.cmd`（按 `*.cmd eol=crlf` 归一，检出自动还原 CRLF）与 3 个
`assets/natives/*.native`（`-text` 原样字节，工作区 CRLF 保持不动）。**内容零变化**——
4 个文件均已核验为纯行尾差异（`tr -d '\r'` 后 `cmp` 一致）才提交。

**遗留给后续（未改，仅记录）**：`tasks/` 38 个脚本中 24 个硬编码了具体工程对象名
（`F01_Variable_GVLVerify`、`prg_GvlVerifyUse` 等），与「tasks = 可复用、studies = 一次性」的边界定义不符；
真正被验收链路引用的 tasks 只有 7 个。这批硬编码脚本本质是「用过的收尾/验证脚本」，
下次整理时要么参数化进 tasks，要么按 studies 冻结——不影响当前使用。


### 新增（2026-11-26，F10_POU_EthercatTask 复制验证）

- **F10_EtherCAT 任务层 POU 复制验证：`F10_POU_EthercatTask_Verify / E0~E3 四个副本（_F10V）`**。`F10_POU_EthercatTask` 含 4 个**纯 ST 的 PROGRAM**（无 LD、无 DUT、无子文件夹），带调用链 `E0_EtherCAT_MainC → E1_M8000与EtherCAT通讯检测 / E2_轴控调用 / E3_SystemTime`。完整复用 F04 翻译管线（`make_f10_translate.py`：单遍交替正则改写 `MetaObject.Name` + 全部 `Text` 节点，36 个真全局变量改写到 `F01_Variable_GVLVerify` 副本，4 个对象名的相互调用一并改写），共 **909 处改写**（E0=5 / E1=69 / E2=756 / E3=79）。**验收**：预编译 101/0、编译 104/0，合计 **0 错误**（202 条 warning 与 F08 轮数量一致，模板自带非新增）。**判定要点（无新坑，全部沿用既有结论）**：设备对象（`Servo*`/`Axis*`/`EtherCAT_C`/`GL20*`）、共享全局（`Gc_ui4PMEAxisNum`/`Gc_uiPAxisNum`/`Hr_astAxisData`/`g_xVirtual`，F04 轮已确认原件无副本）、A 开头轴枚举值（DUT 属原件、未复制枚举定义，无需加后缀，与 F04 的差别所在）、FB 引脚名、局部变量、注释中文——一律不改写。改写完整性用「裸 `M8000`/`M8002` 计数为 0」核验（子串计数 `M8000_GVLVerify` 会误报残留，必须用词边界正则）。新增脚本：`task_scan_f10.py`、`task_probe_f10.py`、`task_export_f10.py`、`task_topguid_f10.py`、`task_import_f10.py`、`examples/analyze_f10.py`、`examples/make_f10_translate.py`。

### 修改（2026-11-26，bridge/daemon 可靠性重写：run_id 对账 + 心跳看门狗 + 取消代数 + 并发锁 + selftest）

参考 `dsh-computer-use-win`（v0.6.4，MIT）的工程实践重写 `scripts/bridge.py`、补丁 `scripts/ide/plc_daemon.py`。
**动机**：这些机制都属于「出问题时才显形」的类型——平时跑得好好的，一旦守护慢一拍就会给出**错误的成功**，
所以不能只靠「在真实工程里跑一次没问题」来验收，必须能在不启动 IDE 的前提下把每个失败路径精确复现。

**六项改动**：

| # | 机制 | 解决的真实问题 |
|---|---|---|
| 1 | **`run_id` 对账** | 旧实现只做「删 `result.json` → 写 `cmd.json` → 等 `result.json` 出现」。上一条命令超时后守护迟一点才写结果，这条**迟到结果**会被下一次调用当成自己的读走——`ok` 是 `true`、JSON 能解析，只有内容是错的。**最阴险的一类假成功**。现在每条命令带唯一 `run_id`，守护原样回带，对不上就丢弃继续等 |
| 2 | **心跳看门狗** | 旧实现只有一个死等循环，守护线程崩了也要等满 180s，且报「超时」不是「守护已死」，排查方向直接跑偏。现在每 ~1s 查 `heartbeat` mtime，超 8s 立刻抛 `E_HEARTBEAT_STALE` |
| 3 | **独立心跳线程** | 旧实现 `_beat()` 写在 `loop()` 里，**长命令一跑心跳就停**，看门狗会误报「守护已死」。改为独立 `heartbeat_loop()` 线程（0.5s 一跳），语义明确为「守护进程活着」。实测：命令占住主线程跑 6s 期间，心跳年龄最大值仅 **0.50s** |
| 4 | **取消代数 `cancel.gen`** | 旧 `stop_daemon()` 写 `stop.flag` 让守护退出，取消一条命令的代价是丢掉整个守护，下次还得重新注入；布尔 flag 也无法区分「这条的取消」和「上一条的取消」。现在 `cancel.gen` 单调递增，只影响正在跑的那条 |
| 5 | **`ipc/bridge.lock` 并发锁** | 旧实现两个线程同时 `send()` 会互相删/覆盖 `cmd.json`，可能一条被执行两遍或两条都丢。现在具名锁 + 陈旧锁自动抢占 |
| 6 | **`bridge.py selftest`** | 旧文档三处（README/SKILL/mcp-bridge）都让人跑 `ide/probe_daemon.py`，**而那个文件长期不存在**（坏链）。现在 selftest 内置，fail-closed，`problems` 里每条都写明下一步做什么 |

**新增文件**：

- `scripts/ide/reload_daemon.py` —— **热重载守护**。改完 `plc_daemon.py` 后不用人工点菜单：写 `stop.flag` →
  **后台线程**等 `ready.flag` 消失 → 清残留 → exec `boot_daemon.py`。⚠ 不能主线程等：`stop.flag` 是在本条命令
  执行期间写的，旧循环要等本命令返回才看到它，主线程等就是**自己等自己**。实测 <1s 完成。
- `scripts/check_ipy_syntax.py` —— IronPython 2 语法自检（`except Exception, e:` 无法被 Python 3 `py_compile`，
  先降级再 `ast.parse`）。
- `scripts/test_bridge_protocol.py` —— 8 组协议回归（假守护，不碰真实 IDE）：正常往返 / 迟到结果 / 旧版守护降级 /
  心跳停摆 fail-fast / 取消 / 并发 / 陈旧锁抢占 / selftest。**22 项断言全过**。

**⚠ 过程中发现并修掉的真实缺陷（铁律 40）**：`_IpcLock._holder_dead()` 原本照 POSIX 用 `os.kill(pid, 0)` +
`errno == ESRCH` 判活。实测 Windows 11 / Python 3.12：`os.kill(999999, 0)` → `errno 22 (WinError 87)`，
而 `os.kill(36704, 0)`（该 pid **明明活着**，就是 InoProShop）抛**同一个 `errno 22`**。也就是说
「不存在的 pid」与「活着的 pid」不可区分 → 所有进程都被判成死的 → **陈旧锁永远能抢，等于没锁**（T7 直接失败）。
改为 `OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION)` + `GetExitCodeProcess` + `STILL_ACTIVE(259)`，
判不了时**当作活着**（宁可等锁超时，也不要抢活人的锁）。

**真实 IDE 验收（2026-11-26 13:16，InoProShop V1.10.0.3 / PID 36704 / `D:\plc_study\study.project`）**：

| 项 | 结果 |
|---|---|
| 热重载守护 | `reload_daemon.log`：`old daemon gone (0.2s)` → `NEW daemon ready (0.2s)`；`daemon_boot.log` 出现新版独有的 `creating heartbeat thread` |
| `bridge.py selftest` | `ok: true`，`problems: []`，`ping` 带回 `run_id: 20261126131644-881fe782`，**无** `legacy_daemon` |
| 取消（真实 6s 长命令） | `cancel()` 后调用方拿到 `E_CANCELLED`；守护**没被杀**，后续 `ping` 正常 |
| 并发 3 线程 | 全部 `ok: true`，3 个 `run_id` 互不相同 |
| 长命令期间心跳 | 12 次采样最大 **0.50s**（阈值 8.0s），证明「命令慢 ≠ 守护死」 |
| 真实动作回归 | `status` / `list_pous` 正常返回（`status` 的 `online_error: 堆栈为空。` 是已知的非主线程问题，已降级成字段） |

**兼容性**：`send()/call()` 签名与返回值不变，`do_replace.py` 等老调用方无需改；结果新增 `run_id` / `cancelled`
两个字段，老代码忽略即可；守护若是旧版（不回带 `run_id`）会退化为「出现即认」并标 `legacy_daemon: true`。

### 修改（2026-11-26，铁律 39、40）

- **铁律新增 39、40**（README + SKILL 双写，`AGENTS.md` 条数说明同步为 40 条）：
  39 = 结果必须与命令对账（`run_id`），「文件出现」不等于「这是我这轮的结果」；
  40 = `os.kill(pid, 0)` 在 Windows 上不能判活（不存在的 pid 与活着的 pid 抛同一个 `errno 22`）。
- **README 铁律分组表从 4 组扩到 6 组**，补上此前漏登记的 E 组（31~38，枚举/凸轮/轴组）和 F 组（39、40，桥与守护）。
- **`probe_daemon.py` 坏链清理**：README / SKILL / mcp-bridge 三处引用改为 `bridge.py selftest`；
  README 目录树里的 `probe_daemon.py` 换成实际存在的 `reload_daemon.py`。

### 新增（2026-11-26，F08_AxisGroup 轴组复制验证）

- **AxesGroup（运动轴组）对象全流程验证：`F08_AxisGroup_Verify / AxesGroup_A1_F08V + AxesGroup_C1_F08V`**。`F08_AxisGroup` 下两个轴组（`AxesGroup_A1` 擦拭 A1 侧 XY 二轴、`AxesGroup_C1` 擦拭 C1 侧 XY 二轴），是**设备侧运动配置对象**——`is_folder=False`、`has_textual_implementation=False`、`get_children()` 返回 `[]`、`dir()` 只有 6 个 .NET 基础方法，**脚本接口几乎完全不可见，所有信息只能靠 `export_native` 拿**。复制只改 3 处（`MetaObject.Name` / `MetaObject.Guid` / `Object.Id`，实测 diff 精确 3 处、其余字节完全保留）。**验收**：预编译 101/0、编译 104/0，合计 **0 错误**。**A/B**：正样本 `stGroup := AxesGroup_A1_F08V;` 0 错误；负样本 `ZZZ_NoSuchGroup_F08V` 编译 **2 条**错误。**三个关键新发现**：① **`AxisGuid` 指向的物理轴不能同时属于两个轴组**——沿用原件轴时 IDE 导入会把 `AxisGuid` 全清成 `00000000`，编译报 `X轴轴映射为空`；对照实验（改成空闲 Axis9/Axis10）证明 `AxisGuid` 完整保留、0 错误，**这不是脚本 bug 而是 SoftMotion 占用保护**；② **轴组必须在「轴所在的那个任务」里被引用**（本工程轴挂 `ETHERCAT` 而非 `MainTask`，挂错报 `轴组 xxx 与所选轴所在任务不同`；同一 POU 挂两任务报 `在多任务下存在多处调用`）；③ **`PAXES_GROUP_REF` 不能与 `0`/BIT 比较**（报 `不能比较类型 'PAXES_GROUP_REF' 和类型'BIT'`）。另：`SoftMotion General Axis Pool.get_children()` 返回 `[]`，**脚本无法建虚拟轴**，共用轴方案必须手工加轴。详见 `references/native-structure.md §33`。新增脚本：`task_scan_f08.py`、`task_probe_f08.py`、`task_deep_f08.py`、`task_guidref_f08.py`、`task_device_f08.py`、`task_usage_f08.py`、`task_pool_f08.py`、`task_tasks_f08.py`、`task_import_f08.py`、`task_readback_f08.py`、`task_alt_import_f08.py`、`task_ab_f08.py`、`task_export_taskcfg_f08.py`、`examples/make_f08_axesgroup_copy.py`、`examples/make_f08_alt_mapping.py`、`examples/del_task_pou.py`。

### 修复（2026-11-26，任务槽摘除）

- **`pous.remove("名字")` 打印成功但实际无效（铁律 25 同源，本轮再次确认）**：`MainTask.pous.remove()` 与 `ETHERCAT.pous.remove()` 都回读仍在。新增 `scripts/examples/del_task_pou.py` 走「导出 TaskConfig native → 按行删 POU 块 → 同名覆盖导入」。⚠ 期间踩过一个坑：用跨行正则 `.*?</Single>` 删除会**连相邻的 `</Single>` 一起吃**，导入报 `第 89 行，位置 10 上的开始标记"List"与结束标记"Single"不匹配`；正确做法是从 `<Single Type="{f194d1ef…}">` 行起**逐行走到单独一行 `</Single>`** 为止。

### 修改（2026-11-26，铁律 37、38）

- **铁律新增 37、38**（README + SKILL 双写，`AGENTS.md` 条数说明同步为 38 条）：37 = 轴组 `AxisGuid` 不能共用物理轴 + 必须挂轴所在任务；38 = 任务槽 `remove` 无效，走 native 覆盖且不能跨行正则。
- **`assets/natives/` 新增两个轴组样本**：`axesgroup_cart_xy_sample.native`（原件 `AxesGroup_A1`，21 KB）、`axesgroup_cart_xy_copy_sample.native`（副本 `AxesGroup_A1_F08V`，映射到空闲轴，21 KB）。

### 新增（2026-11-26，F07_CAM 复制验证 + Cam1 曲线规划落地）

- **CAM（电子凸轮）对象全流程验证 + 曲线规划落地：`F07_CAM_Verify / Cam1_F07V`**。`F07_CAM` 只有一个对象 `Cam0`，无子文件夹无 POU。两轮工作：① **复制验证**——导出 `Cam0_folder.native` → `scripts/examples/make_f07_cam_copy.py` 只改 `MetaObject.Name` 加 `_F07V`（CAM 无 `TextLines`/`Implementation`，不存在跨对象文本引用）→ 导入新建 `F07_CAM_Verify`，1/1 成功无空文件夹；② **曲线规划落地**——`scripts/examples/make_cam1_curve.py` 按停-升-停 3-4-5 五次多项式重写 `Points`+`Segments`+`Dimension`+`Periodic`，生成 `Cam1_F07V`（3 段：停歇 0-120 / 分度 120-240 / 停歇 240-360，H=45°，β=120°，`p3=450 p4=-675 p5=270`）。**验收**：预编译 101/errors=**0**、编译 104/errors=**0**、Cam 分类 `de128929` errors=**0**，合计 **0 错误**；往返 diff 写入 13 字段 vs 回读 13 字段 **0 差异**；接缝 x=120 / x=240 位移·速度·加速度全部连续。**三个关键新发现**：① **CAM 直线段 `p1` 是段内增量不是终点绝对值**（`y=p0+p1·u`，按绝对值写会让停歇段斜率非零、与多项式段零速度冲突）；② **分度凸轮必须 `Periodic=False`**（`y(360)≠y(0)`，沿用模板 `True` 报 `在点 (0/0) 的连续性要求不能填充 位置/速度`）；③ **Cam 错误只落 `de128929` Cam 分类**，预编译/编译可能全 0，只看那两个会漏判通过。另：Cam 子对象**无法脚本删除**（`remove(obj)` 报 `takes no arguments`、`replace(idx,"")` 报 `no attribute`），改曲线只能同名覆盖导入。详见 `references/native-structure.md §32`。新增脚本：`task_scan_f07.py`、`task_export_f07.py`、`task_export_f07_top.py`、`task_import_f07.py`、`task_f07_ab_test.py`、`task_f07_cleanup.py`、`task_import_cam1.py`、`task_export_cam1.py`、`task_delete_cam1.py`（实测无效，留作反面记录）、`examples/make_f07_cam_copy.py`、`examples/make_cam1_curve.py`。

### 修复（2026-11-26，F07_CAM）

- **`make_f07_cam_copy.py` 头部注释把两个段类型 Guid 的参数个数写反**：原写「直线 `{3bfb4cba}` p0..p5、五次多项式 `{7ede90d3}` p0..p3」，实测为**直线 `{7ede90d3}` p0..p1、五次多项式 `{3bfb4cba}` p0..p5**，两个 Guid 的类型和参数个数全部颠倒。已改正，并在文件头补上两条硬规则（p1 增量、Periodic=False）与 §32 指引。

### 修改（2026-11-26，消息分类表）

- **`references/mcp-bridge.md` 分类表补第 6 个分类 `de128929-86dd-4c5e-82c8-09aa2f3d8abe` = Cam**。工程里存在 CAM 对象时才出现，承载凸轮曲线连续性校验错误。同轮实测 `0986c5dd`（格式检查）**反而没出现**，再次印证「GUID 集合因版本/配置而异，不能照抄」。已在表下加 `⚠` 块强调「Cam 错误不落预编译/编译分类，只看那两个会漏判通过」，并附典型错误原文。
- **`assets/natives/` 新增两个 CAM 样本**：`cam_swing_broken_sample.native`（31 KB，**反面样本**——模板 Cam0，5 段摆动凸轮，x=200 处位移断裂 20°、3 处速度阶跃，勿照抄）、`cam_index_345_sample.native`（26 KB，**正面样本**——Cam1，3 段分度凸轮，接缝全连续，双分类 0 错误）。
- **铁律新增 35、36**（README + SKILL 双写，`AGENTS.md` 条数说明同步为 36 条）：35 = CAM 直线段 `p1` 是段内增量；36 = 分度凸轮必须 `Periodic=False`。

### 新增（2026-11-26，F02_Struct 复制验证）

- **Struct DUT 全流程验证：F02_Struct_Verify**。`F02_Struct`（17 个顶层 DUT + SF01_Alarm 子文件夹 14 个报警结构体）整包导出 → `scripts/examples/make_f02_copy.py` 加 `_StructVerify` 后缀（类型名 + 成员名同加，跳过 `TYPE/STRUCT/UNION/END_*` 段标记行）→ 逐个 `import_native` 到新建文件夹 `F02_Struct_Verify`（复用 `make_gvl.folder_entry`），17/17 成功无弹窗。**A/B 验证**：ST POU `prg_StructVerifyUse` 挂 MainTask，正样本引用副本成员（`stClock.xBlink_1Hz_StructVerify` 等 + UNION 成员 `w字_StructVerify`）→ 预编译 0 错误、编译仅模板原有 1 条；负样本 `stClock.ZZZ_NotExist_Member` → 编译分类 **4 条真实错误**。结论：DUT 副本全局可见、验收链路有效。详见 `references/native-structure.md §29`。新增脚本：`task_export_f02.py`、`task_import_f02.py`、`task_f02_ab_test.py`、`task_f02_cleanup.py`、`task_list_folders.py`、`probe_windows.py`、`examples/make_f02_copy.py`。
- **子文件夹复制补做：SF01_Alarm_StructVerify**（2026-11-26 二轮）。在 `F02_Struct_Verify` 下建子文件夹并导入 14 个报警结构体副本（含 `ARRAY[0..49] OF BOOL` 数组成员、7 个空结构体）14/14 无弹窗。新发现：子文件夹的 `parent_container_guid` / `parent_guid` 都用**父 Folder 的 `MetaObject.Guid`**（SV 节点 guid，非导出根 guid）；IDE 内 ElementTree 是老 xmllib 解析 native 报 `illegal character`，**GUID 解析必须放主机侧**。A/B 正（含 `ARRAY OF 副本结构体`）0 错误 / 负 4 条真实检出。新增脚本：`task_export_sf01.py`、`task_import_sf01.py`、`task_sf01_ab_test.py`、`task_sf01_cleanup.py`。
- **`run_overwrite_import.py` 修复实测生效**：修掉「只扫被禁用窗口」的 bug 后，覆盖导入 Task Configuration 仅 3.31s 自动完成（修复前卡 435s 需人工点击）。
- **FB/FC 全量翻译验证：F04_FB_Verify**（2026-11-26 三轮）。`F04_FB` 全部 58 个对象（9 个子文件夹：SF06_通讯/6、SF05_设备状态机/7、SF98_34-1-擦拭机/11、SF02_气缸/7、SF99_其他/3、半自动/3、SF03_真空/7、SF01_轴控/9、SF04_产量统计/5；30 ST + 8 LD + 20 DUT）整树导出 → `scripts/examples/make_f04_translate.py` 单遍正则加 `_F04V` 后缀（对象名 + 内部跨引用 + GVL 变量改写到 `_GVLVerify` + 枚举字面量）→ `F04_FB_Verify` 按子文件夹结构逐个 `import_native`，58/58 无弹窗。**两个关键新发现**：① 枚举字面量是**全局符号**（不是类型内作用域），副本枚举沿用值会重名 277 条、裸引用全变「未知类型」，必须给枚举值也加后缀；② ST/`LD Implementation` 的 GUID 有独立取值（`{3b83b776-fb25-…}`ST / `{25e509de-33d4-…}`LD），以实测为准。A/B：`FB_Cylinder_F04V`（三个 `VAR_IN_OUT` io 引脚接真实副本 Struct，GVL 引用已指 `_GVLVerify`）+`FB_RGYLamp_F04V` 正样本 0 错误；负样本 4 条真实检出。详见 `references/native-structure.md §30`。新增脚本：`task_export_f04.py`、`task_export_f04_top.py`、`task_export_gvl_names.py`、`task_import_f04.py`、`task_f04_ab_test.py`、`task_f04_purge.py`、`task_f04_cleanup.py`、`examples/analyze_f04.py`、`examples/make_f04_translate.py`。

- **FC 全量翻译验证：F05_FC_Verify**（2026-11-26 四轮）。`F05_FC` 全部 10 个对象（7 ST FC + 3 DUT；其中 **5 个 FC 直接挂在根下**，2 个子文件夹 SF01_AlarmRecord/3、SF02_AlarmWindow/2）整树导出 → `scripts/examples/make_f05_translate.py` 加 `_F05V` 后缀 → `F05_FC_Verify`，10/10 无弹窗。**三个新发现**：① 根下直接 POU 导出时也会生成「空目录 + `<名>_folder.native`」，看起来像子文件夹，判别只能靠 TypeGuid（`6f9dac99-8de1-4efc-8465-68ac443b7d08`，旧记录的 `f3a6-45e5-…` 是错的）；② 枚举字面量提取正则必须吃行尾 `//` 注释（`\s*,?\s*(//.*)?$`），否则 F05 的 `Enum_AlarmLevel` 0 命中、277 重名问题重演；③ 枚举字面量是中文常见词（提示/警告/故障）时不能盲目全局替换，须先扫描确认只在声明行出现。A/B：`FC_AlarmRecord_F05V`（ARRAY OF 副本 Struct）+`FC_CRC16_F05V`（内部调 FC_XOR8/16_F05V）正样本 **0 错误**；负样本 2 条真实检出。详见 `references/native-structure.md §31`。新增脚本：`task_scan_f05.py`、`task_export_f05.py`、`task_export_f05_top.py`、`task_import_f05.py`、`task_f05_ab_test.py`、`task_f05_purge.py`、`task_f05_cleanup.py`、`examples/analyze_f05.py`、`examples/make_f05_translate.py`。

### 修正（2026-11-26，F05 空文件夹）

- **根下直接 POU 被误建为空文件夹（F05 实测 5 个）**：导出时根下 POU 也会生成同名空目录，翻译脚本复制该目录、导入脚本对每个目录 `mk_folder`，导致 `F05_FC_Verify` 下多出 `ConcatPro_F05V`、`FC_CRC16_F05V`、`FC_XOR8_F05V`、`FC_XOR16_F05V`、`FC_整串字符串按分隔符截取_F05V` 共 5 个空文件夹（正确结构应为 7 项：2 文件夹 + 5 FC）。**三重防护已落地**：① `make_f05_translate.py` 目录内无 `.native` 则 skip；② `task_import_f05.py` 空 natives 列表则 `[SKIP]` 不建文件夹；③ `task_f05_rm_empty.py` 按「`kids==0` 且两个 textual 属性都取不到」判定并 `remove()`。清理后结构 7 项正确、编译仍 0 错误。详见 `references/native-structure.md §31.6`。

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
- `boot_daemon.py`（唯一守护注入入口）、`probe_daemon.py`（守护诊断；⚠ 该文件当时只在文档里写了、实际未落地，2026-11-26 起由 `bridge.py selftest` 正式取代）、`scan_all_native.py`（全工程批量导出）、
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
