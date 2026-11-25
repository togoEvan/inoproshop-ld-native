# MCP 桥与 InoProShop 脚本命令

## 架构

```
bridge.py（本地客户端，文件队列 IPC）
   → ide/plc_daemon.py（IDE 内守护，主线程分发 system.execute_on_primary_thread(callable, False)）
   → do_replace.py（静默导入便捷入口）
```

## 环境要点

- InoProShop = CODESYS V3.5 SP11 基础，IronPython 2.7 脚本引擎
- 全局对象：`projects` / `online` / `system`
- 脚本内用 IronPython 2 语法（`print` 无括号、`except Exception, e`、`unicode()`）

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

## 找对象（勿用全局 find_named）

- 全局 `find_named` 会递归命中 Task Configuration 里的调用对象
- 正确：`proj.active_application.get_children()` 过滤直接子对象

## 读消息（铁律）

- `system.get_messages()` → 返回字符串数组（DeprecationWarning），**不可用**
- `system.get_message_objects(category_guid)` → 返回 ScriptMessage 对象，**唯一正确方式**
- 消息对象属性：`severity` / `text` / `object.get_name()` / `position`

## system.commands

- 索引 91 ≈「检查程序」（tokens=project/buildactiveapp，触发预编译）
- 索引 102 ≈「检查所有对象」（tokens=project/checkall）
- 命令有 `execute()` 方法

## 其他铁律

- 不动鼠标、不抢焦点、不关闭 IDE
- 中文注释需字节级完好（native 用 UTF-8 写出）
- 每次改动后：执行检查 → 读预编译分类 → 导出读回校验
