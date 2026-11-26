# 使用规范

本文件是**操作层面的规范**：环境怎么配、文件怎么命名、验收怎么算、什么不许做。
结构知识见 `references/`，协作契约见 `AGENTS.md`。

---

## 1. 环境要求

| 项 | 要求 |
|----|------|
| 操作系统 | Windows 10 / 11 |
| IDE | 汇川 InoProShop（CODESYS V3.5 SP11 系），**工程必须已打开** |
| 桥接客户端 | Python 3.7+（只用标准库：`json` / `os` / `time` / `subprocess`） |
| IDE 内脚本 | IronPython 2.7（IDE 自带，`except Exception, e:` 是**合法**语法） |
| 工作目录 | 需可写，含 `ipc/`、`ide/` 两个子目录 |

### 环境变量

> ⚠️ **重要：IDE 内脚本读不到你在 shell 里设的环境变量。**
> daemon 跑在 InoProShop 进程内，继承的是 IDE 启动那一刻的环境。
> 实测在 IDE 内执行 `os.environ.get("PLC_MCP_BASE")` 恒为 `None`。

| 变量 | 含义 | 对谁生效 |
|------|------|----------|
| `PLC_MCP_BASE` | 工作根目录（含 `ipc/`、`ide/`） | 本地 Python 脚本 + **仅当 IDE 由 `launch_ide_daemon.py` 启动时**才对 IDE 内脚本生效 |
| `PLC_MCP_IPC` | daemon 的 IPC 目录（`cmd.json` / `result.json`） | 同上 |
| `INOPROSHOP_EXE` | `InoProShop.exe` 完整路径 | 仅 `launch_ide_daemon.py` |
| `PLC_PROJECT` | 工程文件路径 | 仅 `launch_ide_daemon.py` |

**所以不要靠环境变量部署。** 路径按下面顺序自动解析（`scripts/ide/_base.py` 与 `scripts/bridge.py` 用同一套规则）：

| 优先级 | 来源 | 说明 |
|--------|------|------|
| 1 | 环境变量 `PLC_MCP_BASE` | 仅 `launch_ide_daemon.py` 启动 IDE 时有效 |
| 2 | `<BASE>/base_path.txt` 第一行 | 手工兜底 |
| 3 | 从脚本自身路径反推 `scripts/ide/x.py → scripts/` | **默认，铺好文件即可用** |
| 4 | `D:\plc_mcp` | 最后兜底 |

`ipc/check.log`、`ipc/daemon_boot.log` 第一行会打印实际解析结果：

```
BASE = D:\plc_mcp (source: derive:D:\plc_mcp\ide)
```

看到 `source: fallback` 就是自动解析失败，写个 `base_path.txt` 即可。

---

## 2. 目录约定

```
<BASE>/
├── bridge.py                 # IPC 客户端（Python 3）
├── do_replace.py             # 静默导入入口
├── launch_ide_daemon.py      # 启动 IDE + 注入
├── ide_trigger.ps1           # UIA 触发 daemon 注入
├── ipc/                      # daemon 与客户端交换区
│   ├── cmd.json              # 客户端 → daemon
│   ├── result.json           # daemon → 客户端
│   ├── check.log             # 预编译检查结果
│   ├── silent_import.log     # 导入过程日志
│   └── <唯一名>.native       # 导出快照
├── ide/                      # IDE 内 IronPython 脚本
│   ├── _base.py              # 路径自解析（IDE 内环境变量无效，靠它定位）
│   ├── boot_daemon.py        # 守护注入入口（人工点菜单执行本文件）
│   ├── reload_daemon.py      # 热重载守护（改完 plc_daemon.py 后用它换新）
│   ├── plc_daemon.py         # 守护进程（loop + 独立心跳线程）
│   ├── task_check.py         # 预编译检查（验收必用）
│   ├── task_silent_import.py # 静默导入核心
│   ├── task_readnow.py       # 读全部消息
│   └── task_export_fixed.py  # 导出指定 POU
├── check_ipy_syntax.py       # IronPython 2 语法自检（改动 ide/*.py 后必跑）
├── test_bridge_protocol.py   # IPC 协议回归（假守护，不碰真实 IDE）
├── base_path.txt             # 可选：手工指定 BASE（第 2 优先级）
└── work/                     # 生成的 native（可 gitignore）
```

### 文件命名

| 类型 | 规则 | 示例 |
|------|------|------|
| 生成的 native | `<POU名>_<用途>.native` | `prg_StartStop_tree.native` |
| 导出快照 | `silent_after_<HHMMSS>.native` | `silent_after_162043.native` |
| 诊断日志 | `ipc/<用途>.log` | `ipc/check.log` |

**导出文件名必须每次唯一**，否则 IDE 会弹覆盖确认框，无人值守场景直接卡死。

---

## 3. 验收规范

### 3.1 唯一验收标准

```
预编译分类 217bc73e-759b-4a3c-bfa1-991c938a6541 错误数 == 0
且
编译分类   97f48d64-a2a3-4856-b640-75c046e37ea9 错误数 == 0
```

两个分类抓不同的错误，缺一不可：

| 分类 | 抓什么 | 典型错误 |
|------|--------|----------|
| 预编译 `217bc73e` | 结构错误 | 槽位数不符、`IsContact` 错、`C0046` 声明缺失、红框 |
| 编译 `97f48d64` | 语义错误 | `'AND'需要至少'2' 个操作数`（单条件 rung 只给 1 个槽） |

**只读预编译会漏掉编译分类的错误**（2026-11-25 实测：预编译 0，构建报 N 条 AND 操作数不足）。

### 3.2 验收步骤

```python
# 经桥在 IDE 内执行检查脚本（内部跑 app.build()，再读两个分类）
import bridge
bridge.call("eval_file", path=r"<BASE>/ide/task_check.py", timeout=120)
```

然后读 `<BASE>/ipc/check.log`，必须有：

```
=== 预编译 : total=0 errors=0 ===
=== 编译 : total=3 errors=0 ===
=== 验收结论 : 通过 (预编译+编译合计 0 错误) ===
```

### 3.3 什么不算验收

- ❌ 只看预编译分类 0 错误（漏掉 AND 元数这类只在构建阶段报的错）
- ❌ 只看编译分类 0 错误（漏掉槽位/声明这类结构错）
- ❌ IDE 画面看起来没红框（红框可能延迟渲染）
- ❌ 导入返回 `ok`（只代表 XML 解析成功，不代表语义正确）
- ❌ 用户没说报错（用户可能还没看）

### 3.4 可忽略的警告

```
[Warning] 未加载库(CmpLog)，将会导致高效数组越界/除零诊断日志不能输出
```

与逻辑无关，不阻塞验收。

---

## 4. 生成 native 的规范

### 4.1 必须克隆，不许手写

从 `assets/natives/` 选最接近的样本，用 `xml.etree.ElementTree` 读入后**克隆节点**再改值。

手写 GUID、手写字段顺序、手写节点层级 → 几乎必然踩坑。

### 4.2 Id 分配

- 所有 `Id` 必须全局唯一
- `UniqueIdGenerator` ≥ 当前最大 Id，建议留 +100 以上余量
- 每次生成时整体 +N 偏移，避免与工程内已有 Id 冲突

### 4.3 常见改值点

| 目标 | 改哪里 |
|------|--------|
| 触点变量名 | `Operand/Operand` 文本 |
| 触点常开/常闭 | `Operand/Flags/Flags`：`0`=常开，`1`=常闭 |
| 线圈置位/复位 | `Operand/Flags/Flags`：`2`=S，`3`=R |
| 常量值（如 MOVE 的 IN） | `Operand/Operand` 文本 + `Type=INT` + `Boolean=False` + 内部 `Flags=0` |
| 输出目标（如 MOVE 的 OUT） | `OutputItems` 里操作数的 `Operand` 文本 |

### 4.4 中文注释

`Network/Comment` 节点写中文说明。写入时用 UTF-8，`ElementTree.write(..., encoding="utf-8", xml_declaration=True)`。**写完要验证字节级完好**（读回比对）。

---

## 5. 静默导入规范

```powershell
python scripts\do_replace.py <native绝对路径> Application <目标POU名>
```

内部流程（改名让位法）：

1. 旧对象改名 `prg_X → prg_X_old_tmp`
2. `import_native(新文件)` —— 此刻无同名冲突，不弹框
3. 导出新对象到唯一文件名，校验大小与网络数
4. 删除 `prg_X_old_tmp`
5. 保存工程

全程约 2 秒。日志在 `ipc/silent_import.log`。

### 失败排查

| 现象 | 原因 | 处理 |
|------|------|------|
| `import_native` 抛 `已标识项中有一项的格式无效` | 节点挂错位置，或层级多/少一层 | 见 `references/precompile-errors.md` §4；把生成文件与 `assets/natives/` 里最接近的样本做逐层标签对比 |
| 导入后对象不存在 | 名称不匹配 | 检查 native 里 `MetaObject/Name` |
| 弹了确认框 | 导出文件名重复 | 换唯一文件名重试 |
| 桥超时 | daemon 未注入或 IDE 忙 | 重新跑 `launch_ide_daemon.py` |
| 预编译 0 但构建报 AND 操作数不足 | 单条件 rung 顶层 AND 只有 1 个槽 | 见 `references/precompile-errors.md` §2b；补一个 `TRUE` 触点 |

**结构对比怎么做**：把生成文件和你克隆的样本各导出一份，按 `Name` 属性提取标签序列做 diff，能快速定位多一层/少一层。`scripts/examples/make_packml_cmd_test.py` 里有可复用的配对扫描函数（注意跳过自闭合标签，否则深度永远配不平）。

---

## 6. 禁止事项

| 禁止 | 替代方案 |
|------|----------|
| `SetCursorPos` / `mouse_event` / `SetForegroundWindow` | 文件 IPC + PostMessage |
| 关闭 / 重启 IDE | daemon 常驻，静默操作 |
| 弹窗让用户确认导入/替换 | 改名让位法 + 唯一文件名 |
| 只看单一分类验收 | 预编译 + 编译两个分类都读 |
| 手写 native GUID | 从 `assets/natives/` 克隆 |
| 全局 `find_named` | `app.get_children()` 过滤直接子对象 |
| `system.get_messages()` | `system.get_message_objects(category_guid)` |
| 长阻塞轮询 | 分离启动 + 短轮询（≤3s 间隔，总超时明确） |
| 用 Python 3 的 `ast` 校验 `ide/*.py` | 它们是 IronPython 2 语法，会报假错 |

---

## 7. 快速排错索引

| 报错 | 查这里 |
|------|--------|
| `不允许对类型 'SINT' 进行 'NOT' 操作` | `references/precompile-errors.md` §1 |
| AND 框「需要至少 2 操作数」 | `references/precompile-errors.md` §2 |
| IDE 红框 | `references/precompile-errors.md` §3 |
| `已标识项中有一项的格式无效` | `references/precompile-errors.md` §4 |
| 预编译读出 0 但实际有错 | `references/precompile-errors.md` §5 |
| `C0046: 没有定义标识符'xxx'`（一次几十个） | `references/precompile-errors.md` §6（声明区漏声明） |
| 图形上两个 `TRUE` 串联 | `references/precompile-errors.md` §7（公共前缀重复） |
| 桥连不上 | `references/mcp-bridge.md` |
