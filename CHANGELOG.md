# Changelog

本项目的所有重要变更都记录在此文件。

格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

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
