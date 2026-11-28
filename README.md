# inoproshop-ld-native

> 汇川 InoProShop（CODESYS V3.5 SP11 系）中型 PLC **梯形图 native XML 直接生成 + 静默写入**的工具包与实测知识库。
> 只追两件事：**快速写出能编过的流程**，**写入时不抢前台、不动用户的鼠标和窗口**。

[冷启动](docs/quickstart.md) · [铁律全文](SKILL.md) · [文件地图](FILEMAP.md) · [使用规范](docs/usage.md) · [迭代流程](docs/iteration.md) · [精简说明](ARCHIVE.md)

---

## 5 分钟冷启动（换电脑 / 换 AI 都走这条）

```text
0) 前提      Windows + InoProShop（实测 1.10.0.3）+ Python 3（只有主机侧脚本用它）
1) 体检      python scripts\selfcheck.py                       → 全绿再往下
2) 起隐藏实例 python scripts\hidden_launch.py --project=<工程副本>   → READY + OPEN，看不见窗口
3) 拿程序    从 assets/natives/ 挑样本，或按 references/mode-cards/ 用 scripts/examples/ 生成
4) 三道闸门  check_symbols.py / check_slots.py / ld_logic.py   → 都 PASS 才算结构可写
5) 写入      python scripts\do_replace.py x.native <父对象> "关键字"   → 末行 RESULT: PASS
6) 验收      python scripts\accept.py --names=<对象>             → 退出码 0 = VERDICT: PASS
7) 收工      python scripts\hidden_launch.py --stop              → 只杀自己起的 pid
```

**验收谓词**：预编译 `217bc73e` 0 错误 **且** 编译 `97f48d64` 0 错误 **且** 两个分类都没被 500 / 100 条截断。
隐藏实例上 `build()` 只产生编译分类，而编译只含**挂进任务调用列表**的 POU ——
「导入一个没人调用的 POU，编译 0 错误」是假通过，所以验收前必须 `task_mount_assert`。

**两个会让结论整体翻转的坑**（详细对照表见 `docs/quickstart.md`）：
1. **别给 IDE 传 `--project=`**：命令行打开与设备/库初始化抢跑，带 EtherCAT 的复杂工程会冒出
   500 条「未知类型: Tparam_*」；空起 + `open_project` 才是 0 错误。
2. **没挂任务的对象编译不可见**：`accept.py --names=` 会先断言挂载，没挂直接退出码 3。

## 目录（130 个文件 / 3.6MB，原 313 个 / 6.4MB）

```text
AGENTS.md            AI 入口：回写规则 / 什么时候记文档
SKILL.md             铁律 1–52 全文（唯一权威版本）
FILEMAP.md           我要做什么 → 去哪找
ARCHIVE.md           精简删了什么 + 怎么从 git 历史取回
docs/quickstart.md   换电脑 / 换 AI 的冷启动 8 步 + 失败对照表
docs/usage.md        长期使用规范（工程约定、编码要求）
docs/iteration.md    迭代流程 / CHANGELOG 规范 / 同步与发版
references/          11 篇：结构真相 5 篇 + 模式卡 3 张 + 语料普查 3 篇
scripts/             22 个主机侧脚本（生成、校验、写入、验收、自检、bridge 客户端）
  ide/               6 个守护与索引（IronPython 2）
  ide/tasks/         47 个 IDE 内单次任务（导出 / 导入 / 编译 / 消息 / 挂载断言）
  corpus/            5 个语料工具（全量索引、网络切分、形状统计、逻辑闸门）
  examples/          14 个生成器（模板 6 + 结构样本 6 + 任务槽工具 1 + 索引）
assets/natives/      10 份已验证样本（克隆源，别凭空造结构）
```

## 先读这三份

| 文件 | 解决什么 |
|---|---|
| `SKILL.md` | 52 条铁律：验收口径、结构合法性、挂载、任务配置、桥与脚本卫生 |
| `references/native-structure.md` | 字段级真相：节点 GUID、槽位规则、线圈 / 边沿 / 树的正确载体 |
| `references/false-pass-catalog.md` | 假通过目录：什么样的「0 错误」不可信、怎么反证 |

## 速查（编号见 SKILL.md，这里只放最常踩的）

- 写入默认走**隐藏桌面实例**；用户的 IDE 进程（本机 PID 36704）永不关闭、不激活。
- 写前备份 `.project`；导入后必须**同 tick 读消息**，跨 tick 的消息不算数。
- 线圈只能挂 `NETITEM.OutputItems` 或触点的 `OutputItems`；挂功能框上只画空方块（编译仍 0 错误）。
- 上升沿在**框的第 0 个输入引脚** `InputFlags[0].Flags=16`，不在触点（触点 Flags=2 会被原样保留但不产生边沿）。
- TON 必须单独成网络、每周期执行，不能塞进 BRANCH 门控。
- BOOL 赋值用 S/R 线圈；MOVE 只给 INT / WSTRING；空梯级必须删掉。
- 工站流程写进动作槽 `A0x`（宿主 `STN1_02_Auto` 的 ST 体已无条件调用），不新建子程序、不挂 MainTask。
- 动作不能改名：替换 = `remove()` + `import_native()`；同名对象已存在时导入会长时间无返回。
- IDE 脚本内不许 `sleep` / `process_messageloop` 轮询（会冻死界面），计时放主机侧。
- 消息属性名必须小写（`severity` / `text`）；`severity` 过滤作用在完整池，可见池会被截断。
- 只有 `import_native` 那一刻的编译消息是真实的；菜单里的检查 / 编译命令多数走缓存。
- 结构对了不等于逻辑对了：生成器产物还要过 `ld_logic.py` 与符号闸门。

## 已经放弃的路径（别重试）

- `--noUI` 启动：1.10 在 `InoObjectManager.OnProjectLoaded` 空引用崩溃。
- 用 `--project=` 直接打开复杂工程：与设备/库初始化抢跑，编译冒出 500 条 `未知类型: Tparam_*`（空起 + `open_project` 才对）。
- 直接 `CreateProcess` 起 IDE 再注入：会抢前台；零干扰只走 `scripts/hidden_launch.py`（纯 ctypes `CreateDesktopW`，不需要 .NET）。
- 通过菜单命令拿编译错误：8 条命令全走缓存，预编译分类 0 条。
- 在 IDE 脚本里 sleep 轮询消息：界面冻死。
- 把流程写成独立 PROGRAM 再让总控调用：A00 模板的宿主已经调用动作槽，另开 POU 会重复执行。

## 贡献 / 迭代

改这个库之前读 `AGENTS.md`：新增结构知识、修 bug、吃过的亏、环境变更各有固定的回写位置与验收证据。
代码改动必须过 `check_ipy_syntax.py`（IronPython 2 语法自检）；主机脚本用 `python -m py_compile`，或用 `test_bridge_protocol.py` 跑 IPC 协议回归。
