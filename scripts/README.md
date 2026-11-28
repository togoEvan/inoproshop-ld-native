# scripts/ —— 主机侧脚本索引

这里的脚本跑在**主机侧 Python 3**（Windows）。IDE 内部的 IronPython 2.7 脚本见 [`ide/README.md`](ide/README.md)。
两者通过 `ipc/` 目录里的文件通信：主机侧写 `cmd.json`，守护读、执行、写 `result.json`。

## 为什么根目录平铺（而不是按功能分目录）

`scripts/check_slots.py`、`scripts/do_replace.py` 这类路径在 **README / SKILL.md / AGENTS.md / docs/ / CHANGELOG / 各模式卡 / 外部 AI 的部署脚本**里被引用了上百次。
移动它们的代价是同步改几十份文档、并且让所有已部署的旧副本失效；收益只是目录好看一点。
所以**根目录保持平铺，靠这份索引分类**。新增主机侧脚本仍放根，并在下表登记一行。

## 五组（19 个）

| 组 | 个数 | 脚本 |
|----|------|------|
| 桥与守护 | 5 | `bridge.py` / `bridge.cmd` / `launch_ide_daemon.py` / `ide_trigger.ps1` / `start_daemon.cmd` |
| 导入 | 3 | `do_replace.py` / `run_overwrite_import.py` / `click_overwrite_all.py` |
| 自检闸门 | 5 | `check_slots.py` / `check_symbols.py` / `check_valpin.py` / `ld_logic.py` / `check_ipy_syntax.py` |
| 消息差分 | 2 | `delta_snap.py` / `run_build_check.py` |
| 打包与诊断 | 4 | `pack_skill.py` / `sync_skill_dir.py` / `probe_windows.py` / `test_bridge_protocol.py` |

## 桥与守护（5）

| 脚本 | 用途 |
|------|------|
| `bridge.py` | IPC 客户端：`ping` / `eval_file` / `selftest`；每条命令带 `run_id` 与迟到结果对账 |
| `bridge.cmd` | 命令行包装，自动挑一个能跑的 Python 3（避开应用商店 0 字节存根） |
| `launch_ide_daemon.py` | 启动 IDE（可带 `--project=`）并注入守护，子进程继承 `PLC_MCP_BASE` |
| `ide_trigger.ps1` | 早先的 UIA 触发注入脚本；⚠ **对 InoProShop 无效**（菜单自绘，UIA 拿不到 MenuBar），保留仅作诊断 |
| `start_daemon.cmd` | 同上，已失效；正确入口是 IDE 菜单 → 执行 `ide/boot_daemon.py` |

## 导入（3）

| 脚本 | 用途 |
|------|------|
| `do_replace.py` | 静默写入入口：改名让位 → `import_native` → 同 tick 读消息 → 失败回滚 → 删旧 → 保存；末行打 `RESULT: PASS/FAIL` |
| `run_overwrite_import.py` | 同名覆盖导入（Task Configuration 这类不能改名的对象），内部调 `click_overwrite_all.py` |
| `click_overwrite_all.py` | 覆盖确认框的两步点击（先「全部(&A)」再「&确定」）；只点第一步会一直阻塞 |

## 自检闸门（5，全部在主机侧、秒级、不进 IDE）

| 脚本 | 拦截什么 |
|------|----------|
| `check_slots.py` | 框的 `InputItems` 槽数 vs `InputParam` 数（含比较框 / MOVE / 算术框的豁免规则）+ Operand 三态断言 |
| `check_symbols.py` | 网络里引用的每个符号是否都出现在声明区（含 GVL 全局量） |
| `check_valpin.py` | 非 BOOL 引脚的 `IsContact` 必须 `False`（编译链查不出的第五类假通过） |
| `ld_logic.py` | 图形拓扑 → 布尔表达式 → DNF 规范化比对；含 S/R 与 NETITEM 载体判定 |
| `check_ipy_syntax.py` | 语法门禁：按文件头 `@py3` / `@ipy2` 标记分流，py3 文件不降级（否则 `except Exception, e:` 会被放过） |

## 消息差分（2）

| 脚本 | 用途 |
|------|------|
| `delta_snap.py` | 读 IDE 里的 `snap_before.json` / `snap_after.json` 做多重集差分，四态退出码 0 PASS / 1 FAIL / 2 UNKNOWN / 3 TOOL_ERROR |
| `run_build_check.py` | 构建 + 读消息的一条龙脚本（内部复用 `click_overwrite_all.py` 处理确认框） |

## 打包与诊断（4）

| 脚本 | 用途 |
|------|------|
| `pack_skill.py` | 打包 `.skill` 分发件（清单取自 `git ls-files`） |
| `sync_skill_dir.py` | 把仓库内容同步到本机已安装的 skill 目录 |
| `probe_windows.py` | 列出可见的 IDE 顶层窗口 / 标题 / PID，排查「守护挂在哪个实例」 |
| `test_bridge_protocol.py` | IPC 协议回归测试（假守护，不碰真实 IDE） |

## 常用命令

```
python scripts\bridge.py selftest                 # 一次给出 base / ipc / ide_running / heartbeat / ping
python scripts\do_replace.py work\x.native Application prg_StartStop   # 静默写入
python scripts\check_symbols.py work\x.native     # 导入前的符号闸门
python scripts\check_ipy_syntax.py scripts/ide    # 改完 IDE 脚本必跑
```

## 维护约定

1. 新增主机侧脚本 → 放 `scripts/` 根，并在上表登记用途一句话。
2. 新增 IDE 内脚本 → 放 `scripts/ide/tasks/`，见 `ide/README.md`；一次性探针不进库。
3. 自检闸门的规则改动必须拿真实工程回归一遍（铁律 22：校验脚本本身也会误报）。