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

## bridge.py 调用（PowerShell 下注意引号）

```powershell
# eval_file 需要 JSON 参数（PowerShell 转义写法）：
& python.exe bridge.py eval_file '{\"path\": \"D://...//task_check.py/"}'
```

## 常用诊断脚本（ide/ 目录）

| 脚本 | 用途 |
|------|------|
| task_check.py | 执行「检查程序」+ 读预编译/编译分类 → ipc/check.log |
| task_readnow.py | 不清空直接读当前 5 个分类 → ipc/readnow.log |
| task_allmsgs.py | 带分类读取全部消息 |
| task_silent_import.py | 静默导入核心 |

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
