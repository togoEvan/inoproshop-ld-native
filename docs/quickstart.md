# 换电脑 / 换 AI：5 分钟冷启动

目标：一台**全新 Windows**，只装了 InoProShop 和 Python 3，拉下这个仓库就能
「生成 LD → 静默写入 → 编译判定 PASS」。本文是按实测跑通的顺序写的，
每一步都给出**怎么确认它成功了**；任一步的确认不过，后面的结论都不可信。

---

## 0. 前提（缺一件都跑不通）

| 要件 | 说明 | 怎么确认 |
|---|---|---|
| Windows | 隐藏桌面靠 `CreateDesktopW`，只有 Windows 有 | — |
| InoProShop | 实测 1.10.0.3；安装路径不必固定，`hidden_launch.py --ide=` 可指定 | 目录里存在 `CODESYS\Common\InoProShop.exe` |
| Python 3 | **主机侧**脚本用；IDE 内部的 IronPython 2.7 是 IDE 自带的，不用装 | `python -c "import sys;print(sys.version)"` |
| 一个工程副本 | 别拿用户正在编辑的工程做实验 | 见第 2 步 |

> 三个目录概念要分清：**仓库**（本文所在）、**BASE**（= `<仓库>/scripts`，桥与 IPC 的根）、
> **工程**（`.project` 文件）。BASE 默认自动从脚本位置反推，铺在奇怪位置时才需要 `PLC_MCP_BASE`。

---

## 1. 体检

```bat
python scripts\selfcheck.py
```

看 `== 结论 ==`：全绿才继续。它会查 Python 版本、12 个必需文件、`ide/tasks` 任务数、
InoProShop 安装位置、守护是否在跑、`ready.flag` / 心跳 / `ping`。
**没装 IDE 或守护没起时这里就会红**，不用等到后面才发现。

---

## 2. 起一个隐藏实例（不抢前台、不弹窗、看不见）

```bat
:: 先复制一份工程当实验体（必须复制：隐藏实例会 save()）
copy D:\plc_study\study.project D:\work\probe.project

python scripts\hidden_launch.py --project=D:\work\probe.project
```

正常输出（实测）：

```text
[hidden] desktop DSHHidden_1a2b3c4d  pid 34896
[hidden] READY +9.5s
[hidden] OPEN: {"ok": true, "application": "Application"} (+12.4s)
```

**这一步内部做的事**：`CreateDesktopW` 新建一个不可见桌面 → `CreateProcessW` 带
`STARTUPINFO.lpDesktop` 把 IDE 生到那个桌面 → 追加 `--runscript=<BASE>/ide/plc_daemon.py`
注入守护 → 等 `ipc/ready.flag` → 再用 `bridge.call("open_project")` 打开工程。

### ⚠ 头号坑：不要给 IDE 传 `--project=`

命令行打开会让**设备/库初始化**与**编译**抢跑。带 EtherCAT / CANopen 的复杂工程
（如 InoPack 模板 13MB）会冒出 **500 条「未知类型: 'Tparam_64_..._StructStatistics'」**
（500 是错误池截断上限），VERDICT 直接 FAIL —— 这是**环境假错**，不是你的代码错。
实测：同一个工程副本 `--project=` 打开 → errors=500；**空 IDE 起来 READY 后再
`open_project` → errors=0 / PASS**。`hidden_launch.py` 已经默认走后者，
`--raw-project` 才会退回旧行为（仅供复现问题）。

---

## 3. 确认守护与工程对得上

```bat
python scripts\bridge.py selftest
python scripts\bridge.py status
```

`status` 里的 `project` 必须是你第 2 步那个副本的**绝对路径**。
不是 → 有另一个守护在别的 BASE 上抢答（`selftest` 的 `base` 会露出来），
先 `hidden_launch.py --stop` 再重来。

---

## 4. 拿程序：现成样本 / 模式卡生成

| 你要什么 | 直接用 | 或改生成器 |
|---|---|---|
| 工站动作槽流程（A00 写法） | `assets/natives/A04_slot4.native` | `scripts/examples/gen_a04.py` |
| 完整工站流程（延时/超时/报警/复位/中断） | `assets/natives/prg_FlowDemo.native` | `scripts/examples/gen_flow_ld.py` |
| 步序最小样本 | `assets/natives/prg_SeqDemo.native` | `scripts/examples/gen_seq_ld.py` |
| 树形状态机 | `assets/natives/user_fixed.native` | — |
| FB 调用 / TON / S-R 线圈 | `fb_call_test` / `prg_TonTest` / `prg_CoilTest` | `gen_tontest.py` / `gen_coiltest.py` |

**别凭空造结构**：节点 GUID、槽位顺序、线圈载体都只能从样本克隆，
规则见 `references/native-structure.md`，怎么写流程见 `references/mode-cards/`。

---

## 5. 写入前过三道闸门（主机侧、秒级、不进 IDE）

```bat
python scripts\check_symbols.py  work\x.native    :: 引用的符号都在声明区/GVL 里
python scripts\check_slots.py    work\x.native    :: 框的槽数 == 参数数
python scripts\ld_logic.py       work\x.native    :: 图形拓扑 → 布尔表达式，语义对得上
```

三道都 PASS 再写。它们拦的是**编译器不报错但运行必错**的那几类（值引脚误当触点、
值输入多/少一个、线圈挂在框上只画空方块）。

---

## 6. 写入（静默，不弹框）

```bat
:: native 里有同名对象时：自动「改名让位 → import_native → 删旧 → save」
python scripts\do_replace.py work\x.native Application prg_MyFlow
```

末行 `RESULT: PASS` 才算进了树。见 `references/mcp-bridge.md` 的协议细节。
**动作槽（A0x）不能改名**，替换走 `remove()` + `import_native()`，见模式卡 03。

---

## 7. 验收（唯一可信的「写对了」证据）

```bat
python scripts\accept.py --names=prg_MyFlow
```

它做四件事：① 断言这些对象**已挂任务**（没挂 → 退出码 3 直接拒）；
② 清空「预编译 / 编译 / 导出导入」三个消息分类；③ `app.build()`；
④ 主机侧等 12s 后跑 `task_check.py` 双通道读消息。

```text
[accept] VERDICT: PASS (errors=0 warnings=200 chan=dual why=clean ...)
```

退出码：**0 PASS / 1 FAIL / 2 UNKNOWN / 3 前置不满足**。UNKNOWN 不是通过。
证据链：把挂载对象里的一处 `aiAutoStep[0]` 改成 `aiAutoStepZZ[0]` → `errors=2 / FAIL`；
改回来 → `errors=0 / PASS`（同一个隐藏实例、同一个工程）。

### ⚠ 二号坑：没挂任务的对象，编译根本不看

隐藏实例上 `build()` **只产生编译分类**（预编译分类不出现），而编译分类
**只含挂进任务调用列表的 POU**。所以「导入一个没人调用的 POU → 编译 0 错误」
是**假通过**：实测把一个 POU 的声明改错（函数体仍引用旧名）→ 导入 OK → 0 错误 PASS；
把它挂进 MainTask → 立刻 2 条错误。
命令行里已经有 `task_mount_assert.py`，`accept.py --names=` 会自动调它；
**禁止跳过这一步就说「通过了」**。

---

## 8. 收工

```bat
python scripts\hidden_launch.py --status   :: 看 pid / 桌面 / 工程
python scripts\hidden_launch.py --stop     :: 只杀自己记的 pid，绝不动用户的 IDE
```

用户的 IDE（本机常驻 PID 36704）**永不关闭、不激活、不抢焦点**。
实验都在隐藏桌面的副本上做，用户的工程只在「你确认要落地」时写，
写前 `copy` 一份 `.project` 备份。

---

## 常见失败对照

| 现象 | 真因 | 处理 |
|---|---|---|
| `500` 条 `未知类型: Tparam_*` | 用 `--project=` 直启复杂工程 | 空起 + `open_project`（第 2 步默认已是） |
| `errors=0` 但 IDE 里明显错误 | 对象没挂任务 / 消息池被清 / 读到缓存 | `accept.py --names=`；`task_check.py` 双通道 |
| `Tools not found` | 守护起在别的 BASE，`ready.flag` 写去了别处 | `bridge.py selftest` 看 `base`/`ipc`，`--stop` 重来 |
| 导入卡住 6 分钟不返回 | 同名动作/对象二次导入 | `remove()` 再 `import_native()`；外层必须超时 |
| `VERDICT: UNKNOWN` | 分类截断且双通道不一致 / 分类未注册 | 先 build + 等 12s 再看；查 `ipc/check.log` 的 `=== 通道` 行 |
| 界面卡死 | 在 IDE 脚本里 `sleep` / 轮询 | IDE 侧只读一次就返回，计时放主机侧 |
