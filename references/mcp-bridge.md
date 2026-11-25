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
| 3 | **daemon 存活** | `python bridge.py ping` | 无 `{"ok":true,"pong":true}` |
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

## 常用诊断脚本（ide/ 目录）

| 脚本 | 用途 |
|------|------|
| task_check.py | 执行「检查程序」+ 读预编译/编译分类 → ipc/check.log（**验收必用**） |
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

**排错顺序**（别乱猜）：`python scripts/ide/probe_daemon.py` → 看第 2 段「候选 BASE」哪个心跳是新的、
第 3 段 `bridge` 用的是哪个，两者不一致就是挂错目录；全都没心跳就是没注入。

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
  **不要硬编码中文标签**——GUID 集合因版本/配置而异，名称才是稳定语义。
- ⚠ `Guid` 是 `script_engine.Guid`（.NET 类型），不是 Python 内建——裸写 `Guid("{...}")` 会静默 `NameError`

## system.commands

- 索引 91 ≈「检查程序」（tokens=project/buildactiveapp，触发预编译）
- 索引 102 ≈「检查所有对象」（tokens=project/checkall）
- 命令有 `execute()` 方法

## 其他铁律

- 不动鼠标、不抢焦点、不关闭 IDE
- 中文注释需字节级完好（native 用 UTF-8 写出）
- 每次改动后：执行检查 → 读预编译分类 → 导出读回校验
