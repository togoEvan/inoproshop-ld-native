# scripts/ide —— IDE 内 IronPython 2.7 脚本索引

这些脚本跑在 **InoProShop 进程内部**（IronPython 2.7.7 + ScriptEngine.plugin 3.5.11.10），
不是主机侧 Python 3。主机侧的 `bridge.py` / `do_replace.py` 通过 `ipc/cmd.json` 驱动 daemon，
daemon 再 `exec` 这里的脚本。

## 分段（2026-11-26 整理）

| 目录 | 数量 | 用途 | 进验收链路 |
|------|------|------|------------|
| `ide/`（本层） | 5 | 守护本体 + 路径自解析 + 全量导出 | ✅ 是 |
| `ide/tasks/` | 45 | 验收 / 导入 / 导出 / 建对象 / 任务槽 / GVL 等**可复用操作** | ✅ 是 |
| `ide/studies/` | 98 | 一次性考古脚本（探 API、探结构、A/B 对照、F0x 普查） | ❌ 否 |

本索引逐条覆盖 **tasks 46/46** 与 **studies 98/98**（2026-11-28 由 git 文件清单核对，无遗漏、无残留）。

**`studies/` 的边界**：它们是为回答某个具体问题临时写的，问题答完就冻结。
新增能力请写进 `tasks/`，不要往 `studies/` 里堆；验收链路里不要引用 `studies/`，
因为它们通常硬编码了某个工程的对象名（`prg_GvlVerifyUse`、`F08_AxisGroup_Verify`、`F10_*` 之类），换工程即失效。

## 两条代码约定（移动/新增脚本必须遵守）

1. **路径自解析行必须上溯到 `scripts/`**：
   ```python
   sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
   import _base
   BASE = _base.resolve_base()
   ```
   `tasks/` 与 `studies/` 是两层目录，所以用两个 `dirname`；本层脚本用一层。
   `_base.resolve_base()` 已支持这三种位置（`ide/`、`ide/tasks/`、`ide/studies/`）。
2. **不要 `sleep` / `process_messageloop` 轮询**：脚本跑在 IDE 主线程，会冻死界面。
   计时与重试一律放主机侧（`bridge.py` 的 `call(timeout=...)`）。

## 本层（core，5 个）

| 脚本 | 用途 |
|------|------|
| `_base.py` | 路径自解析：IDE 内读不到 shell 环境变量，靠 sys.argv[0] 反推 BASE / IPC |
| `boot_daemon.py` | 守护注入入口（唯一入口，人工在 IDE 菜单「执行脚本文件」跑本文件） |
| `plc_daemon.py` | 常驻守护主体：轮询 cmd.json 分发命令 + 独立心跳线程 |
| `reload_daemon.py` | 热重载：改完 plc_daemon.py 后用它换新，不必重启 IDE |
| `scan_all_native.py` | 批量导出全工程对象为 native（结构学习语料，只读） |

## tasks/（46 个，可复用）

| 脚本 | 用途 |
|------|------|
| `tasks/export_all.py` | IDE 内递归导出整个 active_application，每个对象一个 .native（语料来源，只读） |
| `tasks/task_allmsg_dump.py` | 全量消息转储：build 之后把所有分类里的每条消息（不论级别）都写出来 |
| `tasks/task_at_check.py` | 核对 F01_Variable_GVLVerify 下 8 个副本 GVL 是否保留了 AT 地址 |
| `tasks/task_at_scan.py` | 扫描整个 Application 里所有 AT 绝对地址（含 POU/GVL），算已用区间和空闲区间 |
| `tasks/task_build.py` | 只跑 app.build()，不读消息 —— 与 task_check.py 配对使用 |
| `tasks/task_build_check.py` | 构建一次（不 clear_messages），让编译分类出现 |
| `tasks/task_build_clean.py` | 干净验收：先 clear 两个分类 → build() → 退出，主机侧等待后读（避免把陈旧消息当本轮结果） |
| `tasks/task_check.py` | 验收：只读两个分类的消息并统计 Error / Warning，单次快照，绝不阻塞 IDE |
| `tasks/task_cleanup_final.py` | 收尾：把验证 POU 从 MainTask 调用列表摘掉并删除，只保留 F99_GVLVerify 文件夹 |
| `tasks/task_cleanup_negative.py` | 删除负样本对象（GVL_BadTest），保留 F99_GVLVerify 验证文件夹 |
| `tasks/task_cleanup_test_pou.py` | 删除临时验证 POU（prg_GvlVerifyUse），保留 F99_GVLVerify 文件夹 |
| `tasks/task_clear_io_cat.py` | 清掉「导出/导入」分类里的残留消息（「文件已经存在」这类非代码 Error） |
| `tasks/task_cmd_list.py` | 枚举 system.commands（GetEnumerator 返回 ScriptCommand 对象），反射取 guid/name/des… |
| `tasks/task_cmd_run.py` | 执行指定的 IDE 命令（按 GUID 字符串，遍历 commands 找到匹配项后 execute） |
| `tasks/task_copy_cleanup.py` | 收尾：删除验证 POU 并把 MainTask 调用列表恢复成只剩 M000_MAIN |
| `tasks/task_delete_objects.py` | 按名字删除 Application 下的对象（清理验证用负样本 POU） |
| `tasks/task_dump_only.py` | 只 dump 消息，不 build（保留导入触发的快照） |
| `tasks/task_dump_tree.py` | 递归列出 Application 下全部对象：名称 / 子对象数 / 是否疑似 Folder（空壳） |
| `tasks/task_export_fixed.py` | 导出当前工程里的 prg_StartStop（用户手改后版本），供学习其结构 |
| `tasks/task_export_gvl.py` | 按「文件夹/对象」路径导出单个对象（支持子文件夹），用于观察单对象导出的 SV 结构 |
| `tasks/task_export_gvl_names.py` | 导出 F01_Variable_GVLVerify 的 GVL 变量名 → GVLVerify 变量名映射 + F04 副本将引用的引脚类型 |
| `tasks/task_extended.py` | 任务配置与对象移动：create_task / set_task / task_info / list_tasks / move_object / remove_task，改-读回-回滚 |
| `tasks/task_export_named.py` | 通用：导出 Application 下指定名字的对象（含子对象）为 native，供往返比对 |
| `tasks/task_export_one.py` | 导出 prg_ReproStudy 到指定路径（供往返比对） |
| `tasks/task_final_verify.py` | 复核：MainTask 调用列表是否真的摘掉了验证 POU |
| `tasks/task_gvl_copy_test.py` | 验证副本 GVL 的「带后缀全局变量」是否真的可用（挂 MainTask 才参与编译） |
| `tasks/task_gvl_cross_check.py` | 交叉验证：新建一个 ST POU，代码里直接引用 GVL 里的全局变量 |
| `tasks/task_gvl_negative_check.py` | 负样本对照：把 prg_GvlVerifyUse 的 body 改成一个必然未定义的标识符 |
| `tasks/task_gvl_symbol_check.py` | 验证 GVL 变量是否真的成为「全局变量」：用多种只读 API 探测符号是否存在 |
| `tasks/task_gvl_task_test.py` | GVL 全局变量验证（正确版）：建 POU + 挂进 MainTask 调用列表 + build + dump |
| `tasks/task_import_overwrite.py` | 覆盖式导入：不改名让位，直接 import_native，遇到同名覆盖弹框由主机侧点「全部」 |
| `tasks/task_list_folders.py` | 列出 Application 下所有 F0x 开头的 Folder / GVL 及成员，用于确认 F02 内容 |
| `tasks/task_mount_assert.py` | 验收前置断言：给定 POU 名必须已挂进某任务的调用列表（不挂=不进编译单元=假通过）；结果落 `ipc/task_mount_result.json`，主机侧读 json 判定（eval_file 下退出码无意义） |
| `tasks/task_msg_text.py` | 用 get_messages(cat) 直接 dump 每个分类的全部消息文本（返回的是字符串） |
| `tasks/task_msgdump_now.py` | 只读转储当前消息、逐分类统计 severity（验证 ≥100 条时是否被截断、Error 是否真为 0） |
| `tasks/task_readback_pou.py` | 读回 prg_GvlVerifyUse 的声明/实现原文，确认 replace 是否真的写进工程 |
| `tasks/task_readnow.py` | 不清空，直接读当前 5 个分类的所有消息 |
| `tasks/task_rename_children.py` | 把某个文件夹下的子对象（GVL）批量改名，统一加后缀 |
| `tasks/task_rename_folder.py` | 把 F99_GVLVerify 重命名为 F01_Variable_GVLVerify（在软件工程里直接改名） |
| `tasks/task_rt_funcret.py` | 往返验证 prg_FuncRetTest：导出导入后的 POU，比对 Function 框结构是否保持 |
| `tasks/task_show_state.py` | 显示 MainTask 调用列表 + prg_NoTaskTest 是否存在 |
| `tasks/task_silent_import.py` | 静默导入 native：改名让位 → import_native → 同 tick 读消息 → 失败回滚 → 删旧 → 保存 |
| `tasks/task_snap.py` | 消息池快照（before/after 各一拍）→ 主机侧 delta_snap.py 差分。主判据是 **err_pool**（`get_message_objects(cat, Severity.Error)` 按完整池过滤，不受 100 条截断）；另含 meta.which 自证、err_total/err_addrs 对象级兜底；severity 读不到直接 raise（不产坏快照） |
| `tasks/task_taskcfg_read.py` | 只读：打印 Task Configuration 每个任务的 pous 列表 + Application 顶层对象名 |
| `tasks/task_tree_dump.py` | 列出 Application 下的全部对象（含 Folder/GVL），并展开 F01_Variable |
| `tasks/task_unhook_task.py` | 彻底把 prg_GvlVerifyUse 从 MainTask 调用列表摘掉（remove 传名字无效，改试索引/其它方式） |

## studies/（98 个，一次性考古）

| 脚本 | 当时要回答的问题 |
|------|------------------|

| `studies/task_ab_f08.py` | F08 轴组 A/B 验证 |
| `studies/task_alt_import_f08.py` | 把 f08_out_alt 的副本同名覆盖导入 F08_AxisGroup_Verify（对照实验） |
| `studies/task_at_ab_test.py` | A/B 对照：验证副本 GVL（保留 AT 绝对地址）里的变量是否真的全局可见 |
| `studies/task_at_cleanup.py` | 收尾：删除 prg_AtVerifyUse + 把 MainTask 调用列表恢复成只剩 M000_MAIN |
| `studies/task_build_api_probe.py` | 探测 app 的构建类方法（rebuild / clean / generate_code 等），并看它们是否真的重编译 |
| `studies/task_deep_f08.py` | F08 轴组深入探测：导出 C1、解析 A1/C1 的 Guid 引用、查工程里这些 Guid 是谁 |
| `studies/task_delete_cam1.py` | 删除 F07_CAM_Verify 下的指定子对象（默认 Cam1_F07V），为重新导入让位 |
| `studies/task_device_f08.py` | 在设备树里找轴组引用的 POU / 轴 的真实归属 |
| `studies/task_dump_verify_dirs.py` | 列出 F05_FC_Verify 与 F04_FB_Verify 下的完整结构（含子对象类型与数量） |
| `studies/task_exp_build.py` | 只调用 app.build()，不读消息 |
| `studies/task_exp_clear.py` | 决定性实验：清空消息后只做一件事，再看预编译分类里有没有 ZZZ |
| `studies/task_exp_cmd.py` | 只执行一个 IDE 命令，不读消息（避免读消息时把结果混进来） |
| `studies/task_exp_delay.py` | 测「检查程序」命令后预编译消息的到达延迟 |
| `studies/task_exp_dump.py` | 只 dump 消息分类（不执行任何命令） |
| `studies/task_exp_notask.py` | 实验：未挂任务的 POU 到底被哪些操作检查？ |
| `studies/task_exp_op.py` | 只删除 / 只导入一个对象，不做别的（避免异步命令与读消息互相干扰） |
| `studies/task_exp_poll.py` | 只读预编译分类条数（主机侧轮询用，不改任何东西） |
| `studies/task_exp_probe_editor.py` | 探测：当前 IDE 打开了哪些编辑器/文档，以及「检查程序」的作用域 |
| `studies/task_exp_probe_sev.py` | 探测消息接口的严重级别能力：能不能区分 Error / Warning |
| `studies/task_exp_task.py` | 把 POU 挂进 / 摘出 MainTask 的调用列表 |
| `studies/task_export_cam1.py` | 从 IDE 导出 Cam1_F07V 回读，验证曲线数据（Points/Segments）确实生效 |
| `studies/task_export_f01.py` | 导出 F01_Variable 文件夹（含全部子 GVL）作为备份 |
| `studies/task_export_f02.py` | 导出 F02_Struct：整文件夹 native + 逐个成员 native |
| `studies/task_export_f04.py` | 整树导出 F04_FB：每个子文件夹单独 native + 每个对象单独 native + 整包备份 |
| `studies/task_export_f04_top.py` | 导出 F04_FB_Verify 顶层文件夹 native（主机侧解析其 SV guid 后再供子文件夹用） |
| `studies/task_export_f05.py` | 整树导出 F05_FC：每个子文件夹单独 native + 每个对象单独 native + 整包备份 |
| `studies/task_export_f05_top.py` | 导出 F05_FC_Verify 顶层文件夹 native（主机侧解析其 SV guid 后再供子文件夹用） |
| `studies/task_export_f07.py` | 整树导出 F07_CAM：每个子文件夹单独 native + 每个对象单独 native + 整包备份 |
| `studies/task_export_f07_top.py` | 导出 F07_CAM_Verify 顶层文件夹 native（备份 f07_top_backup.native） |
| `studies/task_export_f10.py` | F10 第一步：导出 4 个 POU 的 native + 建 F10_POU_EthercatTask_Verify 顶层文件夹 |
| `studies/task_export_f11.py` | F11 第一步：导出 F11_POU_MainTask 全部 POU + 建 Verify 顶层文件夹 |
| `studies/task_export_f20.py` | F20 第一步：导出 F20_POU_Station0_总控 全部 POU + 建 Verify 顶层文件夹 |
| `studies/task_export_f21.py` | F21 第一步：导出 F21_POU_Station1_工站1_搬运移栽 全部 POU + 建 Verify 顶层文件夹 |
| `studies/task_export_sf01.py` | 补导出：SF01_Alarm 子文件夹的 14 个报警结构体 + F02_Struct_Verify 文件夹的 SV GUID |
| `studies/task_export_taskcfg_f08.py` | 把 prg_F08VerifyUse 从指定任务里彻底摘掉（绕开 pous.remove 无效的问题） |
| `studies/task_export_taskcfg_f11.py` | 导出 Task Configuration native（供主机侧删残留的 prg_F11VerifyUse） |
| `studies/task_export_taskcfg_f20.py` | 导出 Task Configuration native（供主机侧删残留的 prg_F20VerifyUse） |
| `studies/task_export_taskcfg_f21.py` | 导出 Task Configuration native（供主机侧删残留的 prg_F21VerifyUse） |
| `studies/task_f02_ab_test.py` | A/B 验证副本 Struct：建 ST POU prg_StructVerifyUse 挂进 MainTask，两种实现切换 |
| `studies/task_f02_cleanup.py` | 收尾：删除 prg_StructVerifyUse（任务列表已通过覆盖导入复位，不再动 pous） |
| `studies/task_f04_ab_test.py` | A/B 验证 F04 副本 FB：ST POU prg_F04VerifyUse 挂 MainTask 实例化副本 FB |
| `studies/task_f04_cleanup.py` | F04 收尾：摘测试 POU 任务槽 + 删除 prg_F04VerifyUse |
| `studies/task_f04_purge.py` | 删除 F04_FB_Verify 整个顶层文件夹（含全部子对象）+ 删除 prg_F04VerifyUse |
| `studies/task_f05_ab_test.py` | A/B 验证 F04 副本 FB：ST POU prg_F05VerifyUse 挂 MainTask 实例化副本 FB |
| `studies/task_f05_cleanup.py` | F04 收尾：摘测试 POU 任务槽 + 删除 prg_F05VerifyUse |
| `studies/task_f05_purge.py` | 删除 F05_FC_Verify 整个顶层文件夹（含全部子对象）+ 删除 prg_F05VerifyUse |
| `studies/task_f05_rm_empty.py` | 删除 F05_FC_Verify 下误建的空文件夹（无子对象、无代码的纯容器） |
| `studies/task_f07_ab_test.py` | F07 CAM A/B 验证 |
| `studies/task_f07_cleanup.py` | F04 收尾：摘测试 POU 任务槽 + 删除 prg_F07VerifyUse |
| `studies/task_f11_ab_test.py` | F11 A/B 验证：副本确实在预编译/编译作用域内 |
| `studies/task_f11_purge.py` | 清空 F11_POU_MainTask_Verify 下的全部子对象（重导入前） |
| `studies/task_f20_ab_test.py` | F20 A/B 验证：副本确实在预编译/编译作用域内 |
| `studies/task_f21_ab_test.py` | F21 A/B 验证：副本确实在预编译/编译作用域内 |
| `studies/task_force_rebuild.py` | 强制重编译：app.clean() + app.rebuild()，然后全量 dump 消息 |
| `studies/task_guidref_f08.py` | 查 F08 轴组引用的 4 个 POU Guid + 2 个 AxisGuid 在工程里对应哪个对象 |
| `studies/task_import_cam1.py` | 把 Cam1_F07V.native 导入已存在的 F07_CAM_Verify 文件夹，并回读校验 |
| `studies/task_import_f02.py` | 在 Application 下新建 F02_Struct_Verify 文件夹（复用 make_gvl 的 folder_entry） |
| `studies/task_import_f04.py` | 建 F04_FB_Verify 顶层文件夹 + 9 个 SF 子文件夹，导入 58 个副本对象 |
| `studies/task_import_f05.py` | 建 F05_FC_Verify 顶层文件夹 + 9 个 SF 子文件夹，导入 58 个副本对象 |
| `studies/task_import_f07.py` | 建 F07_CAM_Verify 顶层文件夹并导入 CAM 副本（单对象，无子文件夹） |
| `studies/task_import_f08.py` | 建 F08_AxisGroup_Verify 顶层文件夹并导入轴组副本 |
| `studies/task_import_f10.py` | F10 第三步：把 ipc/f10_out 下的 4 个翻译副本导入 F10_POU_EthercatTask_Verify 顶层文件夹 |
| `studies/task_import_f11.py` | F11 第三步：把 ipc/f11_out 下 15 个翻译副本导入 Verify 顶层文件夹 |
| `studies/task_import_f20.py` | F20 第三步：把 ipc/f20_out 下 7 个翻译副本导入 Verify 顶层文件夹 |
| `studies/task_import_f21.py` | F21 第三步：把 ipc/f21_out 下 7 个翻译副本导入 Verify 顶层文件夹 |
| `studies/task_import_sf01.py` | 在 F02_Struct_Verify 下建 SF01_Alarm_StructVerify 子文件夹，导入 14 个报警结构体副本 |
| `studies/task_list_top.py` | 列出 Application 下全部直接子对象，找 F 系列顶层文件夹（含 F20） |
| `studies/task_pool_f08.py` | 探测 SoftMotion General Axis Pool：能否新建虚拟轴、轴对象长什么样 |
| `studies/task_pou_api_probe.py` | 探测：如何在脚本里创建一个 POU（用于写一段引用 GVL 变量的代码做交叉验证） |
| `studies/task_poulist_probe.py` | 探测 ScriptPouObjectList 的增删 API（把 POU 挂进任务调用列表） |
| `studies/task_poutype_probe.py` | 探测 create_pou 需要的 PouType 枚举怎么拿 |
| `studies/task_poutype_probe2.py` | 探测 PouType 枚举的可用值（只接受 0？）+ 尝试 create_pou(name, 0) |
| `studies/task_poutype_probe3.py` | 反射查找 PouType 枚举类型，拿到枚举值后 create_pou |
| `studies/task_probe_f08.py` | 探测 F08_AxisGroup 下轴组对象的能力：属性、方法、能否导出 native |
| `studies/task_probe_f10.py` | 探测 F10 下 4 个 POU 的真实格式：ST / LD / CFC，以及声明与实现的开头 |
| `studies/task_readback_f08.py` | F08 回读验证：导出导入后的轴组，比对 13 个关键字段，并检查内部 POU Guid 是否被重建 |
| `studies/task_readback_f11.py` | F11 回读验证：导出导入后的副本比对关键字段 |
| `studies/task_scan_f04.py` | 扫描 F04_FB：列出全部子文件夹 + FB，标注实现语言（ST/LD）与对象大小 |
| `studies/task_scan_f05.py` | 扫描 F05_FC：列出全部子文件夹 + FB，标注实现语言（ST/LD）与对象大小 |
| `studies/task_scan_f07.py` | 扫描 F07_CAM：列出全部子项（含直接 POU），标注实现语言（ST/LD）与对象大小 |
| `studies/task_scan_f08.py` | 扫描 F08 文件夹：递归列出全部子项，标注类型 / TypeGuid / 实现语言 |
| `studies/task_scan_f10.py` | 扫描 F10 文件夹：递归列出全部子项，标注类型与实现语言 |
| `studies/task_scan_f11.py` | 扫描 F11 文件夹：递归列全部子项，标注类型与实现语言 |
| `studies/task_scan_f20.py` | 扫描 F20 文件夹：递归列全部子项，标注类型与实现语言 |
| `studies/task_scan_f21.py` | 扫描 F21 文件夹：递归列全部子项，标注类型与实现语言 |
| `studies/task_sf01_ab_test.py` | A/B 验证子文件夹副本：ST POU prg_Sf01VerifyUse 挂 MainTask |
| `studies/task_sf01_cleanup.py` | 收尾（SF01 轮）：删除 prg_Sf01VerifyUse + 摘任务槽 + 保存 |
| `studies/task_task_api_probe.py` | 探测 Task Configuration 的调用列表 API（用于把验证 POU 挂进任务，强制参与编译） |
| `studies/task_tasks_f08.py` | 列出 Task Configuration 下全部任务名与其 POU 列表 |
| `studies/task_topguid_f10.py` | F10 补充步骤：读取 F10_POU_EthercatTask_Verify 顶层文件夹 guid |
| `studies/task_topguid_f11.py` | 读 F11 Verify 顶层文件夹 guid → ipc/f11_top_guid.txt |
| `studies/task_topguid_f20.py` | 读 F20 Verify 顶层文件夹 guid → ipc/f20_top_guid.txt |
| `studies/task_topguid_f21.py` | 读 F21 Verify 顶层文件夹 guid → ipc/f21_top_guid.txt |
| `studies/task_unhook_f11.py` | 把 prg_F11VerifyUse 从 MainTask 彻底摘掉（remove 名字无效，须按索引再摘） |
| `studies/task_unhook_task2.py` | 彻底摘掉 MainTask 里的空槽项：试 Item(i) 后 remove(obj)，并检查最终列表 |
| `studies/task_unhook_task3.py` | 再试几种摘除空槽项的办法 |
| `studies/task_usage_f08.py` | F08 轴组用法探测：工程里轴组是怎么被 POU 引用的 + 对照实验 |
| `studies/task_verify_tc.py` | 验收 F11 收尾：确认 MainTask 的 POU 列表已不含 prg_F11VerifyUse |

## 常用入口

- 装守护：IDE 菜单 Tools → Scripting → Execute Script File → `scripts/ide/boot_daemon.py`
- 验收：主机侧 `python scripts/bridge.py eval_file path=<BASE>/ide/tasks/task_check.py`
- 静默写 POU：`python scripts/do_replace.py <native> <parent> <expect...>`（内部调 `tasks/task_silent_import.py`）
- 构建：`tasks/task_build.py` 只 build 不读消息，等 ≥10s 后用 `tasks/task_check.py` 读（**build 会清空预编译分类**）
