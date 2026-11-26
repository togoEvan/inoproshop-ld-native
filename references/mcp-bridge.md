# MCP 桥与 InoProShop 脚本命令

## 架构

```
bridge.py（本地客户端，文件队列 IPC）
   → ide/plc_daemon.py（IDE 内守护，主线程分发 system.execute_on_primary_thread(callable, False)）
   → do_replace.py（静默导入便捷入口）
```

**命令防重复执行（领取-改名机制，学自 inoproshop-mcp，2026-11-25）**：
daemon 轮询发现 `cmd.json` 后，先**原子改名为 `running.json`** 再读取执行。改名成功即视为「领取」，之后无论执行正常/异常/崩溃，文件都不再叫 `cmd.json`，绝不会被二次领取。旧机制（mtime+size 签名判重）在签名比较失败或执行中途崩溃时可能把同一命令执行两遍——对写入类命令是实打实的事故。写方 `bridge.py` 本就是原子写（`.tmp` + `os.replace`），与领取-改名配合，端到端恰好一次。

## 环境要点

- InoProShop = CODESYS V3.5 SP11 基础，IronPython 2.7 脚本引擎
- 全局对象：`projects` / `online` / `system`
- 脚本内用 IronPython 2 语法（`print` 无括号、`except Exception, e`、`unicode()`）

### ⚠ IronPython 里 `except Exception` 兜不住的三类异常（2026-11-25 实测，血亏）

**`SystemExit`、`KeyboardInterrupt`、`SystemError` 都不继承 `Exception`，只继承 `BaseException`。**

这意味着 `except Exception:` 拦不住它们，异常会一路穿透到宿主。在守护进程里这是致命的：

| 场景 | 表现 | 根因 |
|---|---|---|
| 重复注入 daemon | 注入后 **0.7 秒内心跳停摆**，`bridge` 全部超时；`daemon_boot.log` 里只有一行 `skip: another daemon alive`，**完全看不出是异常穿透** | `_acquire_instance()` 判定「已有实例存活」时 `raise SystemExit`；`loop()` 的命令执行层只写了 `except Exception`，`SystemExit` 穿过它、穿过 `exec`，**把整个轮询线程干掉** |
| `status` 命令 | 整个 `status` 返回 `{"ok": false, "error": "堆栈为空。"}`，工程路径等本来能拿到的信息全丢 | `online.create_online_application(app)` 在**非主线程**调用抛 `SystemError("堆栈为空。")`；`execute_on_primary_thread` 失败时 fallback inline 到后台线程，于是必然触发 |
| 任何 `eval_file` 被执行的脚本 | 宿主守护跟着一起死 | 同上，脚本里任何 `raise SystemExit` / `sys.exit()` 都会穿透 |

**规则**：
1. 守护循环（`plc_daemon.loop()`）的循环体和命令执行层**必须兜 `BaseException`**，且要单独 `except SystemExit` 记一行日志，否则排查时看不到任何线索。
2. 「附加信息」类调用（在线状态、网关列表等）**单独 try 并降级成字段**（如 `online_error`），绝不能让整个命令失败。
3. 用 `eval_file` 跑任何脚本前先想一遍：它会不会 `sys.exit()`。

### 换环境时必查的 6 项（新配置触发点）

换机器 / 换 IDE 版本 / 换工程路径 / 换凭据方式后，逐项跑下面的自检命令，**不要凭"我这边能用"下结论**。

| # | 项 | 自检命令 | 失效表现 |
|---|---|---------|---------|
| 1 | **BASE 路径解析** | 跑 `task_check.py`，看 `ipc/check.log` 第一行 `BASE = ... (source: ...)` | source 是 `fallback` 说明推导失败，会用 `D:\plc_mcp` |
| 2 | **IPC 目录**（与 BASE 可能不同） | `ls ipc/ready.flag ipc/heartbeat` | ready.flag 写在旧目录 → bridge 傻等 30s 报"守护未就绪" |
| 3 | **daemon 存活** | `python bridge.py selftest` | `ok` 不是 `true`；`problems` 里会直接写明下一步该做什么 |
| 4 | **IDE 进程与工程** | `Get-Process InoProShop` + 日志里的 `project = ...` | 无进程 / 工程路径对不上 |
| 5 | **IronPython 语法** | 新增 `ide/*.py` 后先 `eval_file` 试跑一次 | `except Exception, e` 被 Python 3 化会直接 SyntaxError |
| 6 | **Git 凭据** | `printf "protocol=https\nhost=github.com\n\n" \| git credential fill` | 弹「选择凭据助手」窗口 = 被 `helper-selector` 接管 |

**新增配置项时**：除了在这里加一行，还要在 `scripts/ide/_base.py` 顶部注释写清解析优先级，并在 `docs/iteration.md` §7 补同步步骤。

### 导出 API 签名（本机 SP11 实测，2026-11-25）

学自 `tkucic/codesys_workflow_automation` 的 `codesysBulker.saveAndExport`。用 `fn.__doc__` 反射拿到本机真实重载：

```python
# PLCopenXML（可带 declarations_as_plaintext）
proj.export_xml(objects, path=..., recursive=True,
                export_folder_structure=True,
                declarations_as_plaintext=True)
# native XML（CODESYS 自有格式，注意参数名是 destination 不是 path）
proj.export_native(objects=..., destination=..., recursive=True,
                   one_file_per_subtree=False,
                   profile_name=None, reporter=None)
```

两者在本机都 `hasattr == True`，`import_xml` / `import_native` 同样存在。
**用途**：`export_native` 可整工程一次性导出（免去逐个 POU 导出），
`export_xml` 的 PLCopenXML 是跨平台通用格式，可用于与其它工具交换。
⚠ 反射签名时 `fn.Overloads` 在 IronPython 下 `len()` 会报错，直接读 `fn.__doc__` 更可靠。

## 静默导入（改名让位法）

```
do_replace.py <native文件> <父对象名> "关键字过滤"
# 例：do_replace.py work\startstop_state3.native Application "prg_StartStop"
```

流程：旧对象改名 `prg_X_old_tmp` → `parent.import_native(path, None, handler)` → 删旧对象 → `proj.save()`
- 导入前校验用导出文件**每轮唯一命名**（`silent_after_HHMMSS.native`），否则弹覆盖确认框
- 1.8 秒左右完成

## bridge.py 调用

推荐用 Python 直接调用（不用跟 PowerShell 的引号转义搏斗）：

```python
import bridge
r = bridge.call("eval_file", timeout=180, path=r"D:\plc_mcp\ide\task_check.py")
print(r)          # {"ok": true, "done": true}
```

也可以走 CLI，第二个参数是 JSON：

```powershell
python bridge.py eval_file '{\"path\": \"D:\\\\plc_mcp\\\\ide\\\\task_check.py\"}'
```

> PowerShell 里 JSON 的每个双引号都要反斜杠转义，反斜杠本身还要再转义一层，
> 所以路径写成 `\\\\`。这就是上面推荐用 Python 调用的原因。
> ⚠ bash heredoc 写 JSON 同样会吃反斜杠（`\\` 变 `//`），路径参数请用 `python -c` 或
> 直接写 `.py` 文件传参，别用 heredoc 拼 JSON。

### 结果与命令对账：`run_id`（2026-11-26）

每条命令由 `bridge.send()` 自动补一个唯一 `run_id`（`时间戳-8位hex`），守护写回结果时原样带回。`bridge` 只认 `run_id` 相同的那份结果，**迟到结果一律丢弃继续等**。

- 结果 dict 里多两个字段：`run_id`、`cancelled`（老代码忽略即可）。
- 守护是旧版（不回带 `run_id`）时，`bridge` 退化为「`result.json` 出现即认」，并在返回值里标 `legacy_daemon: true` —— 能用，但失去对账保护。
- **看到 `legacy_daemon: true` 就该重新注入守护**（见下面「热重载」一节）。

### 心跳看门狗（2026-11-26）

守护有**两个线程**：`loop()`（轮询命令）+ `heartbeat_loop()`（每 0.5s 写 `heartbeat`）。
心跳线程独立，所以「命令执行慢」不会让心跳停 —— 这正是「守护活着但命令慢」与「守护已死」能区分开的原因。

`bridge.send()` 轮询期间每 ~1s 检查一次 `heartbeat` 的 mtime，超过 `HEARTBEAT_STALE = 8.0s` 立刻抛 `E_HEARTBEAT_STALE`（**不等满 timeout**），并清掉 `cmd.json` 免得守护复活后补跑一条过期命令。

> ⚠ 实测（2026-11-26）：命令占住 IDE 主线程跑 6s 期间，心跳年龄最大值仅 **0.50s**。旧实现把 `_beat()` 写在 `loop()` 里，长命令一跑心跳就停，看门狗会误报「守护已死」——独立线程就是为了消除这个假报警。

### 取消：`cancel.gen` 不是 `stop.flag`（2026-11-26）

| | `cancel()` | `stop_daemon()` |
|---|---|---|
| 语义 | 取消**当前正在跑的那条命令** | 让守护**退出** |
| 落盘 | `ipc/cancel.gen`（单调递增整数） | `ipc/stop.flag` |
| 后续命令 | 天然不受影响 | 下次调用要重新注入 |

守护在**执行前**和**执行后**各读一次代数，与命令携带的 `cancel_gen_at_send` 比对：变了就标 `cancelled=True` 并尽快收尾。实测真实 IDE：`cancel()` 后 1.2s 内调用方拿到 `E_CANCELLED`，守护**没被杀**，后续 `ping` 正常。

### 并发：`ipc/bridge.lock`

`bridge.send()` 用「原子创建 + 内容带 pid/ts」的锁文件串行化写 `cmd.json`，陈旧锁（持有者已死）自动抢占。实测 3 线程并发 `call()` 全部成功且 `run_id` 互不相同。

⚠ **陈旧锁判活的 Windows 坑**（铁律 40）：`os.kill(pid, 0)` 在 Windows 上对**不存在的 pid** 和**活着的 pid** 抛的是同一个 `errno 22`，按 `ESRCH` 判活会让所有进程都判成死的（锁等于失效）。`bridge._pid_alive()` 改用 `OpenProcess` + `GetExitCodeProcess`，判不了时**当作活着**。

### 自检：`python bridge.py selftest`

一次给出可诊断快照，**fail-closed**（任何一项失败都显式列进 `problems`）：

```bash
python bridge.py selftest
```

```json
{
  "ok": true,
  "base": "...\\inoproshop-ld-native\\scripts",
  "ipc_writable": true,
  "ide_running": true,
  "ready_flag": true,
  "heartbeat_age": 0.04,
  "ping": {"run_id": "20261126131644-881fe782", "cancelled": false,
           "ok": true, "pong": true, "time": "13:16:44"},
  "cancel_gen": 0,
  "problems": []
}
```

`problems` 里每条都带「下一步该干什么」。这取代了旧文档里引用的 `probe_daemon.py`（那个文件**长期不存在**，README/SKILL/mcp-bridge 三处引用都是坏链）。

### 热重载守护（改完 `plc_daemon.py` 后）

改了守护代码，IDE 里跑的还是旧代码（脚本已 exec 完）。不用人工点菜单，让旧守护帮你换：

```python
import bridge
bridge.call("eval_file", timeout=60,
            path=r"<BASE>\ide\reload_daemon.py")
```

`reload_daemon.py` 的做法：写 `stop.flag` → 起**后台线程**等 `ready.flag` 消失 → 清残留 → exec `boot_daemon.py` 起新守护。
⚠ 不能在主线程等 —— `stop.flag` 是在本条命令执行期间写的，旧循环要等本命令返回才看到它，主线程等就是自己等自己（死锁）。
实测耗时 < 1s，`daemon_boot.log` 会出现新版独有的 `creating heartbeat thread`。

## 常用诊断脚本（ide/ 目录）

| 脚本 | 用途 |
|------|------|
| task_check.py | `app.build()` + 读预编译/编译分类 → ipc/check.log（**验收必用**） |
| task_readnow.py | 不清空直接读当前 5 个分类 → ipc/readnow.log（排查异步消息） |
| task_export_fixed.py | 导出工程内指定 POU → ipc/user_fixed.native（学结构用） |
| task_silent_import.py | 静默导入核心（由 do_replace.py 调用，一般不直接跑） |

## textual_* 接口不可用时的退路（实测）

用户手工启动的 IDE 实例里，`get_children()` 拿到的对象全是 `ExtendedObject[IScriptObject]`，
**没有** `textual_declaration` / `textual_implementation` 属性
（`has_textual_declaration` / `has_textual_implementation` 恒为 False，直接访问抛
`'ExtendedObject[IScriptObject]' object has no attribute 'textual_implementation'`）。
此时 `a_get_pou` / `a_get_decl` / `a_list_pous` 全部失效
（`list_pous` 返回 `count=0`，`get_pou` 返回 `POU not found`）——**不是工程坏了，别去修工程**。

退路：

- **读**：`pou.export_native(path)` 导出 XML，再用 Python 侧解析 `TextLines`（声明区）与
  `NetworkList`（12 段图形），逐段还原「条件串 + S/R 线圈」做校验
- **写**：照旧用 `import_native`（不依赖文本接口）
- 需要文本编辑能力时，改用 `--desktop` 隐藏桌面启动的实例（那里文本接口正常）

## 守护注入：为什么只能人工点菜单（2026-11-25 实测）

`ide_trigger.ps1` / `start_daemon.cmd` 走 UIA `InvokePattern` 去点「工具 → 脚本 → 执行脚本文件...」，
**在 InoProShop 上根本不可能成功**。实测证据：

```
root class = WindowsForms10.Window.8.app.0.13965fa_r6_ad1
Descendants 里 ControlType.MenuBar   数量 = 0
Descendants 里 ControlType.MenuItem  数量 = 0
Win32 GetMenu(hwnd) = 0
按 Alt 激活菜单后，顶层窗口只多出 tooltips_class32 和 SysShadow，没有弹出菜单窗口
```

菜单栏是**自绘**的（画在 `SandBarDock` 的子窗口上，不对 UIA 暴露控件树），所以任何
`FindByName("Tools")` / `FindByName("工具")` 都返回 None —— **改语言没用，放弃 UIA**。

**唯一入口**：IDE 里人工点一次
`工具 → 脚本 → 执行脚本文件... → 选 <BASE>\ide\boot_daemon.py`

`boot_daemon.py` 相对「直接选 `plc_daemon.py`」多做的事：

| 做的事 | 为什么必须 |
|---|---|
| 自解析 IDE 目录（`PLC_IDE_DIR` > `sys.argv[0]` > 已加载 `plc_daemon.__file__`，优先选同时含 `boot_daemon.py` 与 `plc_daemon.py` 的目录） | 通过 `eval_file` 通道执行时 `sys.argv[0]` 仍是旧守护的路径，会推导到错误的 BASE |
| 强制改写 `sys.argv[0]` 为 `<BASE>/ide/plc_daemon.py` | `_base.resolve_base()` 最高优先级是「从 `sys.argv[0]` 反推」。IDE 里执行过别处的 daemon 后，`sys.argv[0]` 固定成旧路径，守护把 `ready.flag` 写进旧目录 → `bridge` 误判「未启动」→ 转去点菜单 → 报 `Tools not found` |
| 检查心跳年龄，超过 8s 就清理 `heartbeat`/`instance.lock`/`daemon.pid`/`ready.flag`/`cmd.json`/`running.json`/`result.json` | `_acquire_instance()` 只看心跳 mtime，上一次守护异常退出或 IDE 重开时心跳文件还留着，新实例会误判「已有实例」直接 `SystemExit` |
| 把 exec 命名空间钉到 `sys._plc_mcp_keep` | 命名空间被回收 → `_logf` 关闭、线程对象被 GC → 守护静默死掉（症状：`daemon.log` 0 字节、没有 `heartbeat`） |
| 单独 `except SystemExit` | 见上一节。重复注入时不掀掉正在跑的线程 |
| 显式注入 `projects` / `online` / `system` | 用 `import plc_daemon` 加载时这三个名字不在模块命名空间里，`a_eval_file` 自己会 `NameError` |

**排错顺序**（别乱猜）：先 `python scripts/bridge.py selftest` —— 它一次给出 `base`/`ipc`/`ide_running`/`ready_flag`/`heartbeat_age`/`ping`/`cancel_gen` 和逐条 `problems`，并明确告诉你「守护没注入」还是「守护挂了」。`base` 与 `ipc` 对不上就是挂错目录（换机部署最常见）；`heartbeat_age` 大就是守护线程死了；`ping` 带 `legacy_daemon` 就是守护是旧版。

## 找对象（勿用全局 find_named）

- 全局 `find_named` 会递归命中 Task Configuration 里的调用对象
- 正确：`proj.active_application.get_children()` 过滤直接子对象

## 读消息（铁律）

- `system.get_messages()` → 返回字符串数组（DeprecationWarning），**不可用**
- `system.get_message_objects(category_guid)` → 返回 ScriptMessage 对象，**唯一正确方式**
- 消息对象属性：`severity` / `text` / `object.get_name()` / `position`
- **动态枚举全部分类，不要只读硬编码的几个**（学自 inoproshop-mcp，2026-11-25）：
  `system.get_message_categories()` 先枚举运行时暴露的**每一个**分类，全量扫描。
  大工程里编译错误会落到已知分类之外的分类（Library Manager、POU 专属、工程树等），
  只读预编译 `217bc73e` + 编译 `97f48d64` 会漏。本机 SP11 实测暴露 5 个分类
  （含脚本 `194b48a9` 和导入导出 `2af7707f`）；**`220493a1`（Additional code checks）
  本机不存在**——GUID 集合因版本/配置而异，不能照抄外部项目的分类清单。`task_check.py` 已按此实现：
  三个基础分类（预编译/编译/格式检查）缺一即 `raise`；其余分类（含已知的 `220493a1`）
  存在才读、计入合计。
- **分类名称用 `system.get_message_category_description(cat)` 动态取**（实测可用，
  学自 `Wayan123/multi-plc-agent`）。本机 SP11 实测返回中文，直接解决了「5 个分类里
  2 个 GUID 不明身份」的问题：
  | GUID | 名称 |
  |---|---|
  | `97f48d64-a2a3-4856-b640-75c046e37ea9` | 编译 |
  | `217bc73e-759b-4a3c-bfa1-991c938a6541` | 预编译 |
  | `0986c5dd-ca06-40a7-94e5-bf42de3dfd91` | 格式检查 |
  | `2af7707f-6167-4a76-a40e-430967be0f18` | 导出/导入 |
  | `194b48a9-ab51-43ae-b9a9-51d3edaaddf3` | 脚本消息 |
  | `de128929-86dd-4c5e-82c8-09aa2f3d8abe` | **Cam**（2026-11-26 新增） |
  **不要硬编码中文标签**——GUID 集合因版本/配置而异，名称才是稳定语义。
- ⚠ **`de128929` = Cam 分类（2026-11-26 实测新增）**：工程里存在 CAM（电子凸轮）对象时才出现，
  承载凸轮曲线的连续性校验错误。**这类错误不会落进预编译 `217bc73e` 或编译 `97f48d64`**——
  实测 Cam 曲线错误时，预编译 101 条 / **errors=0**、编译 104 条 / **errors=0**，
  错误只出现在 Cam 分类。**只读那两个分类会漏判通过**，必须动态枚举全部分类。
  同轮实测 `0986c5dd`（格式检查）**反而没出现**，再次印证「GUID 集合因版本/配置而异」。
  典型 Cam 错误原文：`Cam | 在点 (240/45) 的连续性要求不能填充 速度`。
  曲线写法规则见 `native-structure.md §32`。
- ⚠ `Guid` 是 `script_engine.Guid`（.NET 类型），不是 Python 内建——裸写 `Guid("{...}")` 会静默 `NameError`

## system.commands

- 索引 91 ≈「检查程序」（tokens=project/buildactiveapp）—— ⚠ 2026-11-26 实测该命令**不产生任何消息**，只读，不能用于验收；验收走 `app.build()`
- 索引 102 ≈「检查所有对象」（tokens=project/checkall）
- 命令有 `execute()` 方法

## 其他铁律

- 不动鼠标、不抢焦点、不关闭 IDE
- 中文注释需字节级完好（native 用 UTF-8 写出）
- 每次改动后：执行检查 → 读预编译分类 → 导出读回校验
