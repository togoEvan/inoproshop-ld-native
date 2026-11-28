# Changelog

本项目的所有重要变更都记录在此文件。

格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### 新增（2026-11-28 拉取即用：隐藏启动器 + 一条命令验收 + 冷启动文档）

- **目标**：换电脑 / 换 AI 拉下仓库就能直接做项目，不再依赖本机 `D:\plc_mcp` 的历史状态。
- **新增 `scripts/hidden_launch.py`**（纯 ctypes，无 .NET）：`CreateDesktopW` 建不可见桌面 → `CreateProcessW` 带 `STARTUPINFO.lpDesktop` 起 IDE → `--runscript=<BASE>/ide/plc_daemon.py` 注入守护 → 等 `ipc/ready.flag` → **再用 `bridge.call("open_project")` 打开工程**；`--status` / `--stop` 只处理自己记的 pid。实测无工程 READY **+9.5s**、带工程 OPEN **+12.4s**，全程无可见窗口。
- **发现并封掉 `--project=` 陷阱**：命令行打开复杂工程会与设备/库初始化抢跑，InoPack 13MB 模板编译冒出 **500 条「未知类型: `Tparam_64_..._StructStatistics`」**（500 = 错误池截断）→ FAIL；同一副本改「空起 + `open_project`」→ **errors=0 / PASS**（小工程 655KB 的 `未命名1.project` 不受影响，所以容易误判成代码问题）。`hidden_launch.py` 默认走正解，`--raw-project` 才复现旧行为；已写入 SKILL 铁律 **52**。
- **修 `ide/tasks/task_check.py` 的隐性单通道 bug**：脚本从未 `import System`，`_find_sev_type()` 里的 `NameError` 被 `except` 吞掉 → 日志常驻「找不到 Severity 枚举」→ 双通道退化成单通道 → 只要消息池截断就判 `UNKNOWN`（导出/导入/预编译三类一出现必 UNKNOWN，假阴性）。修法：补 `import System`；候选类型加 `_3S.CoDeSys.Core.Messages.Severity, Core`（程序集 `Core`，成员 `FatalError/Error/Warning/Information/Text` = 1/2/4/8/16，`Enum.Parse` 区分大小写），新增 `SEV_ALIAS` 逐个候选重试。修后日志：`=== 通道 : dual tested=2 exact=4 visible=0 mismatch=0 ===`。
- **`ide/tasks/task_build_clean.py` 重写**：清「预编译 `217bc73e` / 编译 `97f48d64` / 导出导入 `2af7707f`」三个分类后再 build；带闸门 `PLC_MCP_HIDDEN=1`（由 `hidden_launch.py` 注入）或 `PLC_MCP_ALLOW_CLEAR=1` 才清，否则只 build 不清——**清用户面板的消息等于打扰**。
- **新增 `scripts/accept.py`**：一条命令验收 = `--names=` 断言挂载（`task_mount_assert`，没挂直接退出码 3）→ 干净 build → 主机侧等 12s → `task_check` 双通道 → 打印 `VERDICT:` 与前 10 条错误；退出码 0 PASS / 1 FAIL / 2 UNKNOWN / 3 前置失败。
- **新增 `scripts/selfcheck.py`**：换机体检（Python 版本 / 12 个必需文件 / `ide/tasks` 任务数 / InoProShop 安装路径 / 守护心跳 / `ping` / `--project=` 是否存在），逐项 PASS-FAIL 并给下一步提示。
- **新增 `docs/quickstart.md`**：换电脑 8 步（体检 → 隐藏实例 → 确认守护 → 拿程序 → 三闸门 → 写入 → 验收 → 收工）+ 两个「能让结论整体翻转」的坑 + 常见失败对照表；README 的「60 秒上手」换成指向它的 7 行速查。
- **验收闭环实证**（隐藏实例副本）：把挂载对象 `prg_Stn3LoadSeq` 里一处 `STNControl[3].aiAutoStep[0]` 改成 `aiAutoStepZZ[0]` → 静默导入 OK → `errors=2 / VERDICT: FAIL`；导入回原文件 → `errors=0 / PASS`。另把 `prg_CoilTest` 副本的声明改错（函数体仍引用旧名）→ 导入 OK → **0 错误 PASS**，挂进 MainTask 后立刻 2 条错误 —— 复证「未挂任务不进编译单元」。
- 计数：126 → **130** 个文件 / 3.6MB（+hidden_launch、accept、selfcheck、quickstart；`ide/tasks` 保持 47）；铁律 51 → **52** 条。


### 整理（2026-11-28 精简仓库：313 → 126 个文件，6.4MB → 3.6MB）

- **目的**：库是给 AI 读的，不是供考古的。删一次性探针与原始日志，只保留「能直接生成 → 能验证 → 能写入」的闭环。
- **删除**：`scripts/ide/studies/` 98 个、`references/evidence/` 47 个原始日志、`scripts/examples/` 一次性探针 27 个、`assets/natives/` 16 份重复或历史样本（含 `prg_Stn3LoadSeq.native` 1.1MB、`a00-fragments/` 5 个片段）。清单与恢复方式见 `ARCHIVE.md`。
- **改写**：README 从 29KB 缩成门面 + 速查（51 条铁律唯一权威版在 `SKILL.md`，不再双写）；FILEMAP 按新结构重写；本文件只留 11-27 之后的结构性变更。
- **保留**：4 张模式卡（步序 / 流程 / 动作槽 / 边沿）、10 份克隆样本、14 个生成器、47 个可复用 IDE 任务、20 个主机脚本、11 篇参考正文。
### 修正（2026-11-28 模式卡 03 v2：流程写进工站 POU 的动作槽 `A04_`，不是独立 PROGRAM）

- **容器结论纠正**：v1 把工站流程写成独立 `PROGRAM`（`prg_Stn3LoadSeq`，31 网络）再由总控调用，是错的。用户 2026-11-28 原话：
  **「正常是将A00_4写流程，不用调用子程序，内部已经调用完成了」** —— 流程应直接写进工站自动 POU（`STN1_02_Auto`）的动作槽 `A0x`（如 `A04_`，数组下标 4），
  宿主 ST 体里已有一整段无条件调用 `A00_上料移栽()`…`A09_()`（原导出约 11875–11885 行，注释 `//____子程序调用`），不需要任何接线、也不需要挂任务。
- 动作对象的事实（实测）：`ActionEntry`（TypeGuid `8ac092e5-3128-4e26-9e7e-11016c6684f2`）、`EmbeddedTypeGuids` 是 LD、**没有 `Interface`/`TextLines`、没有声明区**，只能用宿主与全局符号；
  **不支持改名**（`old.rename(u"A04__old_tmp")` 报 `名称 'A04__old_tmp' 对于本工程无效。`），替换只能 `old.remove()` + `import_native()`；同名动作存在时 `import_native` 会长时间无返回。
- 动作自带 6 个骨架网络（`Network000000_步序号记录器` … `Network000005_流程`，最后一个空），写流程只需**保留前 5 个、替换空的「流程」**。
- 新增 `assets/natives/A04_slot4.native`（847,782 B / 22 网络 / 768 个 Id 全唯一 / AND 58 · MOVE 39 · EQ 19 · BRANCH 21）：工位 4 的取放料流程（1000–1150 步）。
- 新增 `assets/natives/a04-action-skeleton.native`（186,228 B）：`A04_` 的原始导出，当生成器的输入骨架。
- 新增 `scripts/examples/gen_a04.py`：读骨架 → 保留前 5 个网络 → 拼 16 个步序网络 → `renumber` 重编 Id；`LDTPL` / `LDOUT` 可覆盖输入输出。
  可复现性自检：与样本**逐字节相同**（对象 GUID 来自模板，不经 `build_doc` 重生成）。
- 实测（InoProShop V1.10.0.3）：隐藏桌面副本 `remove → import_native ok → build` 得 `编译完成 -- 0 错误, 101 警告`；
  写进 13MB 实时工程 `D:\plc_study\study.project` 同样 0 错误 / 101 警告 / `saved`，实时导出核对为 **22 个网络节点**（1,108,990 B，含「取料位」6 处、「擦拭A1放料位」2 处），IDE 程序段 16/17 人眼确认。
- 文档同步：`references/mode-cards/a00-skeleton.md` 重写为动作槽版本（§0 三种写法对比 / §1 树位置 / §2 动作对象特征 / §3 现成 6 网络 / §4 生成 / §5 步序 / §6 替换 / §7 验收 / §8 坑表），
  独立 `PROGRAM` 版降为附录 A；README/SKILL 铁律 51 改为「写进动作槽 `A0x`，不新建子程序、不挂 `MainTask`」；`FILEMAP.md` / `scripts/examples/README.md` / 目录树同步（文件数 310 → 313，assets 24 → 26，examples 39 → 40）。
### 新增（2026-11-28 模式卡 03 v1：A00 工站骨架 + 可克隆片段 + 生成器）⚠ 容器结论已被下面的 v2 修正

- 新增 `references/mode-cards/a00-skeleton.md`（8.5KB）：工站子程序的 A00 骨架配方 —— 8 段网络顺序、三个可整块克隆的网络（NET1 步序号记录器 / NET2 步序号缓存处理 / NET8 工位判断）、
  克隆时只换 `STNControl[1].` → `STNControl[n].` 与 NET8 的 4 个专有符号、变量容器 `STNControl[0..20]`（0 总控 / 1 上料移栽 / 2 擦拭 / 3..20 空闲）、取放料两段式步号（1000 段 / 2000 段，段内 +10，条件步 +5，段尾无条件回 100）。
- 新增 `assets/natives/a00-fragments/`（5 个 A00 原样片段，共 177KB）：`net01_step_logger.xml` / `net02_step_buffer.xml` / `net08_station_dispatch.xml` / `fc_cylinderexe.xml` / `fc_axisabsgo.xml`。
  前三个是网络节点，后两个是功能框模板（按文档顺序替换 `Single Name="Operand" Type="string"` 的文本即可复用，不用手搭框）。
- 新增 `scripts/examples/gen_a00_stn3.py`（仓库版）：按上述骨架生成 31 网络样本，读 `assets/natives/a00-fragments/`，骨架走 `LDSKEL`、输出走 `LDOUT`。
  可复现性自检：连跑两次产物**只有对象 GUID 不同**（`Single Name="Guid"` 由 `build_doc` 每次新生成），其余 22915 行逐行一致。
- 新增 `assets/natives/prg_Stn3LoadSeq.native`（1.19MB / 31 网络 / 1145 个 Id 全唯一 / AND 84 · MOVE 59 · EQ 29 · BRANCH 32）。
- 新增 `scripts/corpus/split_networks.py`：按 `List2 Name="NetworkList"` 的子元素切网络（ElementTree）。字符串配对标签深度实测会把每块截成 140 字符，不要用字符串切。
- README/SKILL 新增铁律 51：**工站子程序由总控 POU 调用，不挂 `MainTask`**（模板里 `F20_POU_Station0_总控` 按工站号调 A00/A01…，2026-11-28 用户明确「可以不用调用到MainTask」）；
  ⚠ 同时写明验证阶段必须临时挂一次或用总控真实调用，否则「未挂任务不进编译单元」会让 0 错误变成假通过。
- 实测（InoProShop V1.10.0.3）：隐藏桌面副本导入 → 临时挂 `MainTask` → build `编译完成 -- 0 错误, 101 警告`；
  写进 13MB 真实工程 `import_native ok 1.51s / networks 31 / saved`，双分类 预编译 `total=101 errors=0`、编译 `total=104 errors=0`；IDE 里程序段 8 显示 EQ 门控 + 三条支路 + `(S)` 报警线圈。
- `FILEMAP.md` / `README.md` 目录树 / 铁律组表同步（文件数 301 → 310，assets 18 → 24，examples 38 → 39，corpus 4 → 5）。
### 新增（2026-11-28 第 3 件：写入锁 task_setpou + 守护 deadline / uncertain latch）

- 新增 `scripts/ide/tasks/task_setpou.py`：带乐观锁的 POU 源码写入。写前 `sha256(decl + '\x00' + impl)` 与 `expect_hash` 比对，
  不符抛 `STALE_WRITE` 且**一个字都不写**；写完读回逐字比对（`READBACK_MISMATCH`），失败把 decl/impl 逆序 `replace` 回旧值 + `save()`，
  结果里报 `rolled_back`。参数 `<BASE>/ipc/setpou_args.json`，结果用 `### RESULT_JSON ###` 包裹。
- `scripts/ide/plc_daemon.py` 新增两件事：① bridge 传的 `deadline`（float 秒）已过期 → 回 `expired:true` 且**不执行**（排队过久的命令宁可丢弃也不双重执行）；
  ② 执行结果含 `timeout` 时写 `ipc/uncertain.json` latch，latch 存在时除 `ping` / `ack_uncertain` / `stop` 外一律拒绝（回 `uncertain:true, need_ack:true`），`ack_uncertain` 删 latch 解锁。
- `scripts/bridge.py` 新增 `E_UNCERTAIN`，`send()` 自动补 `deadline = now + timeout - 2`，收到 `uncertain` 结果抛 `E_UNCERTAIN`（带 `need_ack:true`）。
- `scripts/ide/boot_daemon.py`：判心跳陈旧时把 `uncertain.json` 一并清掉（否则 IDE 崩溃留下的 latch 会把后续所有命令锁死）。
- **修复**：`eval_file` 里被执行的脚本 `__name__` 是 `__eval__`，`if __name__ == '__main__'` 守卫会导致「函数全定义完就结束、返回 ok 但什么都没做」；
  同时 `eval_file` 现在临时改写 `sys.argv[0]`，让 `_base` 按被执行脚本自身路径推导 BASE（此前会沿守护脚本路径算）。
- 实测（1.10.0.3 隐藏桌面实例，副本 `test.project`，不碰用户工程）：`FC_XOR8` 错哈希 → `STALE_WRITE`（未写、`rolled_back:ok`）→ 正确哈希写入 `saved:true`、`hash_after` 变化、读回带新注释 →
  再用旧哈希 → 再次 `STALE_WRITE`（乐观锁生效）；带过期 `deadline` 的 ping 回 `expired:true`；写 `uncertain.json` 后 `get_decl` 抛 `E_UNCERTAIN`、`ping` 正常、`ack_uncertain` 后恢复。
- README/SKILL 新增铁律 50；`references/mcp-bridge.md` 新增「写入锁与未知结果」一节；`FILEMAP.md` 与 `scripts/ide/README.md` 同步。
### 新增（2026-11-28 第 2 件：任务配置与对象移动 task_extended.py）

- 新增 `scripts/ide/tasks/task_extended.py`：6 个操作 `create_task` / `set_task` / `task_info` / `list_tasks` / `move_object` / `remove_task`，
  统一「改 → 逐字段读回 → 失败回滚」，参数走 `<BASE>/ipc/ext_args.json`，结果用 `### RESULT_JSON ###` 包裹。
- 实测（1.10.0.3 隐藏桌面实例，副本 `tc4_test.project`，不碰用户工程）：建任务 20ms/优先级 5 → 改 50ms/6 → 关工程重开仍是 50/6；
  `prg_SeqDemo` 移进 `F05_FC` 再移回 `Application`，重开后位置正确；移动 `Task Configuration`（受保护）与不存在的对象被明确拒绝；`remove_task` 生效。
- 三条 API 真相：`dir()` 对 .NET 包装对象不可信（接口方法一个都看不见）；`KindOfTask` 按名字反射取不到类型，要用已有任务的 `kind_of_task` 当枚举值；
  移动没有 `get_parent()`，且 `get_children()` 每次返回新包装实例导致 `is` 比较恒假 —— 结果只能靠名字列表核对。
- README/SKILL 新增铁律 49；`references/mcp-bridge.md` 新增「任务配置与对象移动」一节；`FILEMAP.md` 与 `scripts/ide/README.md` 同步。
### 新增（2026-11-28 task_check v4：双通道交叉校验 + 按 severity 分档判定）

- **问题**：v3 只读可见通道 `get_message_objects(cat)`。单分类最多回传 **100** 条、错误池 **500** 条，超了截断少报；
  再叠加「错误数与上一轮一样」这类假干净，0 错误根本不可证。
- **两个通道**：通道 1 = 全量（截断少报）；通道 2 = `get_message_objects(cat, Severity.Error / FatalError)`，
  1.10 实测按**完整池**过滤（`all=540 / Error=502`、各 severity 相加等于 all，灌 1300 个未定义标识符时 Error 恰 500 实体 + 1 提示行），
  截断后仍精确。inoproshop-mcp 在 CODESYS SP19 上实测过相反行为（2 错误只回 1 条 warning、0 错误），所以必须两边对。
- **计数规则**：取两通道**较大值** —— 过滤通道坏（少报）不能把已有错误洗成 0；可见通道被截断（少报）由过滤补。
- **交叉校验**：未截断分类要求两通道相等，不等标 `cross=BAD` → `UNKNOWN`；已截断分类只做单向校验（过滤 ≥ 可见）标 `cross=GE`。
- **分类按需注册**：刚打开、从没 build 过的工程 `cats=0`（隐藏实例实测）→ 先 `app.build()` + `process_messageloop()` 各一次再枚举，仍空才判 `UNKNOWN`，绝不当 0 错误。
- **判定顺序**：无编译分类 → `UNKNOWN`；未知 severity → `UNKNOWN`；错误 > 0 → `FAIL`；通道冲突 → `UNKNOWN`；通用消息截断且无过滤通道 → `UNKNOWN`；否则 `PASS`。
  末行 `VERDICT: PASS|FAIL|UNKNOWN (errors=... chan=dual|dual-unchecked|mismatch|all why=...)`，**`UNKNOWN` 不是通过**。
- **实测（隐藏桌面副本，2026-11-28 14:25–14:26，全程 75 秒）**：A 干净工程 `PASS errors=0 warnings=100 chan=dual-unchecked built=True`；
  B 挂一个引用未定义标识符的 POU `FAIL errors=2 chan=dual`（导入导出 0==0 cross=OK）；
  C 灌 1300 个未定义标识符 `total=605 errors=500 warnings=100 filter=500 cross=GE trunc=1/1/0` → `FAIL`，
  同时实证错误池 500 上限、警告池 100 上限。
- 文件：`scripts/ide/tasks/task_check.py`（v4，保留 tasks/ 布局的两级上溯与动态分类名）、`references/mcp-bridge.md`（双通道与上限一节）、
  `README.md` / `SKILL.md`（铁律 48）、本 CHANGELOG。
### 修复（2026-11-28 库内容审计：5 处纠错 + 隐藏实例作用域实测）

- **审计口径**：拉全库 **21** 个 md/txt（含 AGENTS / README / SKILL / FILEMAP / CHANGELOG / docs / references 全部 / 三个 scripts README），
  正则扫 13 类可疑模式（电源流 / 触点 `Flags=2` / 值域 / `R_TRIG` / `InputFlags` / `IsCoil` / `create_pou` / `CallType=Action` /
  `clear_messages` / `get_messages` / `get_symbols` / `get_name` / 旧数字）。**已纠正过的三处**（Flags=16 不是「电源流引脚」、
  触点值域是 0/1/16 且无边沿语义、边沿要用 `InputFlags[0]=16`）与 `CallType=Action` 的 `Instance.Operand` 必须 `<Null/>`，**确认无需再改**。
- **`references/native-structure.md`**：线圈段补「**合法载体只有两种** —— NETITEM.OutputItems 或触点 PIN 的 OutputItems；
  挂到功能框（`G_BOX` `acfc6f68`）上 IDE 只画**空占位小方块**，编译仍 0 错误」。附 A00 语料父节点分布（NETITEM **15** / 触点 PIN **5** / 功能框 **0**）。
- **`references/mcp-bridge.md`**：消息对象属性行补「属性名必须**小写**（`GetType().GetProperty('severity')` 反射取）；
  写 `Severity` / `Text` 会静默 `None` → **err=0 假通过**；取不到就 `raise`，不要当成 0 条」。
- **`README.md` / `SKILL.md` 铁律 18**：补第三条「**导入失败的原因不看编译分类，看 `194b48a9` 脚本消息的新增 Error**」。
- **`README.md` / `SKILL.md` 铁律 47**：补「`clear_messages` 是**进程级**，同一 IDE 里别的守护/脚本的消息会被一起清掉，与他人共用实例时不要清」。
- **新增 `references/evidence/hidden-instance-scope/README.md`** + 铁律 24 补**环境差异**：`HiddenLaunch` + `--runscript` 起的隐藏实例上，
  `app.build()` 之后**只注册编译分类 `97f48d64`，预编译 `217bc73e` 不存在**，未挂任务的 POU **一条消息都不产生**。
  实测（A/B 两个引用未定义标识符的样本）：都不挂任务 → `n=104 err=0`；B 挂上 → `n=106 err=2`（只有 B）；A 也挂上 → `n=108 err=4`。
  ⇒ **隐藏实例验收必须先挂 MainTask 再 build**（`task_mount_assert.py` 是前置断言），不能指望预编译兜底。
- **`scripts/examples/README.md`**：标题改「native 生成器（38 个 + 本索引）」。
- **`FILEMAP.md`**：文件数 296 → **299**、`references/` 56 → **57**，新增 evidence 段。
### 整理（2026-11-28，目录索引补齐 + 文档数字对齐 + 铁律修重号）

- **新增 `scripts/README.md`**：scripts/ 根 **19** 个主机侧脚本分五组索引（桥与守护 5 / 导入 3 / 自检闸门 5 / 消息差分 2 / 打包与诊断 4），
  并写明「为什么根目录保持平铺」——这些路径在 README / SKILL / AGENTS / docs / 模式卡里被引用了上百次，移动的收益不抵破坏引用。
- **新增 `scripts/examples/README.md`**：**38** 个生成器分三类——可复用库/模板生成器 5（`ldgen.py` + 4 个 `gen_*`）、
  已验证结构样本生成器 13、一次性 F0x 考古 20；每类给了判断标准与「能不能改」。
- **补齐 `scripts/ide/README.md`**：分段表改 **core 5 / tasks 45 / studies 98**；索引从 tasks 40 条、studies 75 条补到 **45/45 与 98/98**
  （新增 5 个 task 条目、23 个 study 条目），并标注「由 git 文件清单核对，无遗漏无残留」。
- **`README.md`**：铁律条数 40 → **47**（数字早已过期，表格实际就是 47 条）。**修重号**：A 段原 25 / 26 → **45 / 46**
  （消息截断阈值、判导入成败三条）、F 段原 41 → **47**（build 是增量编译）——此前分别与 D 段 25/26、B 段 41 撞号。
  补上缺失的 **E. 枚举 / POU / 凸轮 / 轴组** 小节标题（31–38 原混在 D 段表格里）；目录树 tasks 38 → 45、studies 75 → 98，
  并挂上两个新索引；修 `references/` 树里两个 `└──` 的排版错误。
- **`SKILL.md`**：条数 40 → 47；补 **45 / 46**（消息截断、判导入成败）、**41**（线圈只能挂 NETITEM）、
  **31–34**（枚举字面量是全局符号、POU TypeGuid、Implementation GUID、根下 POU 误建空文件夹）的简版；F 段 41 → 47。
- **`FILEMAP.md`**：232 → **296** 个文件；`ide/README.md` 118 → **149**；分布表 scripts 根 14 → 19、ide core 5 → 6、
  tasks 38 → 45、studies 75 → 98、examples 32 → 38、corpus 5 → 4（`export_all.py` 实际在 `tasks/`）。
- **`docs/usage.md`**：目录树 tasks 38 → 45、studies 75 → 98。
- **刻意不改**：`CHANGELOG.md` 里的历史数字（118 / 38 / 75 / 232）按「历史记录保持真实」保留；
  `scripts/examples/` 里 20 个一次性脚本**不移动**——移动会同步破坏 CHANGELOG 与文档里的路径引用，收益低。

**验证**：三个索引条目数分别等于 19 / 45 / 98 / 38；README 铁律编号 1–47 唯一无重复（脚本扫描列表行与表格行求并集 = 47 个不同编号）；
FILEMAP 分布表各行相加 = 296（10 + 2 + 56 + 19 + 6 + 45 + 4 + 98 + 38 + 18）。
### 新增（2026-11-27 v4，LD 语料普查：把整个模板变成可统计的语料 + 五件工具）

- **references/corpus/inopack-template-survey.md** —— 模板普查结论：713 个导出文件 / 320.2 MB /
  去重 470 个对象（**LD 61、ST 192、无实现 217**）/ 58 个原生 LD POU / **2171 个网络 / 7495 个框 / 127 种网络形状**。
  含 24 种 BoxType×CallType 全表（AND 4401、MOVE 2347、EQ 1315、FC_AxisAbsGo 950、FC_CylinderExe 378、TON 107 ...），
  槽数规律表、InputFlags 表，以及 A00 的步序母语法。
- **references/corpus/ld-network-shapes.md** —— Top 25 网络形状表（781 个空网络、163 例 branch+EQ+FC_AxisAbsGo+MOVE ...）
  + 58 个 POU 的画像（网络数 / 形状种类 / 平均框数）。写新工序时先查这张表照抄拓扑，不要发明形状。
- **references/corpus/toolchain.md** —— 语料工具链的用法：六个环境变量（LD_BASE / LD_RAW / LD_PROJ / LD_INDEX /
  LD_SHAPES / LD_EXPORT_LOG）、四步流程、实测产出与五条坑（导出目录别放工程里、export_native 偶发卡死、
  IronPython 必须显式 close 否则句柄滞留）。
- **scripts/corpus/**（主机 Python 3）：index_native.py（对象索引）、scan_forms.py（框型统计）、
  parse_net.py（网络形状）、ld_dump.py（单网络结构树）。**scripts/ide/tasks/export_all.py**（IDE 内 IP2）
  递归导出整个 active_application，每个对象一个 .native。
- **assets/natives/prg_TonTest.native**（16,743 B / 2 网络 / 21 Id 全唯一）与 **prg_CoilTest.native**（15,382 B / 2 网络 / 20 Id）：
  两个最小样本**用修好的 NETITEM 载体重新生成**（旧版把线圈挂在 AND 框上，属错误载体，未入库）。
  隐藏实例实测（逐个独立副本）：导入 ok → 挂 MainTask → build → 97f48d64 = 0 错误, 101 警告（101 条为模板既有的枚举转换警告）；
  导出往返：prg_TonTest 2 网络 / NETITEM 1 / 线圈 1 / TON 1 / 21 Id 全唯一，prg_CoilTest NETITEM 2 / 线圈 4（S/R/普通守恒）。
- **scripts/examples/gen_tontest.py / gen_coiltest.py**：上面两个样本的生成器。
- **references/false-pass-catalog.md** 扩成「九种假象」：新增第 9 条「线圈挂错父节点，界面只画空方块」
  （编译通过、静态检查全过，唯一发现方式是人眼看图形）。

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


### 归档（2026-11-26 及更早，共 35 段）

F02 / F05 / F07 / F08 / F10 / F11 / F20 / F21 的整树复制验证、bridge/daemon 可靠性重写（run_id 对账 / 心跳 / 取消代数 / 并发锁）、消息判据三次修正（截断阈值 → 独立 Error 池 → 双通道交叉校验）、scripts/ide 分层、覆盖确认框、@py3 语法标记、第五层验收等 —— 结论已并入铁律与 `references/`，逐条原文见 git 历史 `014a4ab` 的 `CHANGELOG.md`。
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
