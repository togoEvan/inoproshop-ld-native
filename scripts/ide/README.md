# scripts/ide —— IDE 内 IronPython 2.7 脚本索引

这些脚本跑在 **InoProShop 进程内部**（IronPython 2.7.7 + ScriptEngine.plugin 3.5.11.10），
不是主机侧 Python 3。主机侧的 `bridge.py` / `do_replace.py` 通过 `ipc/cmd.json` 驱动 daemon，
daemon 再 `exec` 这里的脚本。

## 分段（2026-11-26 整理）

| 目录 | 数量 | 用途 | 进验收链路 |
|------|------|------|------------|
| `ide/`（本层） | 5 个脚本 + 本索引 | 守护本体 + 路径自解析 + 全量导出 | ✅ 是 |
| `ide/tasks/` | 47 | 验收 / 导入 / 导出 / 建对象 / 任务槽 / GVL 等**可复用操作** | ✅ 是 |

本索引逐条覆盖 **tasks 47/47**（2026-11-28 精简后由 git 文件清单核对，无遗漏、无残留）。

**一次性探针的边界**：只为回答某个具体问题临时写的脚本不进库（放本地 `work/`）。
它们通常硬编码某个工程的对象名（`prg_GvlVerifyUse`、`F08_AxisGroup_Verify` 之类），换工程即失效；
结论要留下，就把结论写进 `references/`，不要留脚本。新增能力一律写进 `tasks/`。

## 两条代码约定（移动/新增脚本必须遵守）

1. **路径自解析行必须上溯到 `scripts/`**：
   ```python
   sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
   import _base
   BASE = _base.resolve_base()
   ```
   `tasks/` 是第二层目录，所以用两个 `dirname`；本层脚本用一层。
   `_base.resolve_base()` 支持 `ide/` 与 `ide/tasks/` 两种位置。
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

## tasks/（47 个，可复用）

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
| `tasks/task_setpou.py` | **带乐观锁写 POU**：`sha256(decl + \x00 + impl)` 对 `expect_hash`，不符抛 `STALE_WRITE` 一个字不写；写完读回逐字比对（`READBACK_MISMATCH`），失败逆序回滚 + save。参数 `ipc/setpou_args.json`，结果 `setpou_result.json` + `setpou.log` |
| `tasks/task_snap.py` | 消息池快照（before/after 各一拍）→ 主机侧 delta_snap.py 差分。主判据是 **err_pool**（`get_message_objects(cat, Severity.Error)` 按完整池过滤，不受 100 条截断）；另含 meta.which 自证、err_total/err_addrs 对象级兜底；severity 读不到直接 raise（不产坏快照） |
| `tasks/task_taskcfg_read.py` | 只读：打印 Task Configuration 每个任务的 pous 列表 + Application 顶层对象名 |
| `tasks/task_tree_dump.py` | 列出 Application 下的全部对象（含 Folder/GVL），并展开 F01_Variable |
| `tasks/task_unhook_task.py` | 彻底把 prg_GvlVerifyUse 从 MainTask 调用列表摘掉（remove 传名字无效，改试索引/其它方式） |

## 常用入口

- 装守护：IDE 菜单 Tools → Scripting → Execute Script File → `scripts/ide/boot_daemon.py`
- 验收：主机侧 `python scripts/bridge.py eval_file path=<BASE>/ide/tasks/task_check.py`
- 静默写 POU：`python scripts/do_replace.py <native> <parent> <expect...>`（内部调 `tasks/task_silent_import.py`）
- 构建：`tasks/task_build.py` 只 build 不读消息，等 ≥10s 后用 `tasks/task_check.py` 读（**build 会清空预编译分类**）
