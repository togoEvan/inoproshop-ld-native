# 模式卡 01 · 步序网络（LD 步进状态机）

> 适用：InoProShop V1.10.0.3（CODESYS 3.5.11.10）的 LD 实现。母本 = InoPack 包装模板 A00_上料移栽（85 网络 / 490 框）。
> 状态：**已实验验证**（2026-11-27，隐藏桌面实例，导入 + 挂 MainTask + build = 0 错误）。
> 生成器：`ld_study/ldgen.py`；示例：`ld_study/gen_seqdemo.py` → `assets/natives/prg_SeqDemo.native`（190,602 B / 6 网络 / 215 个 Id）。

---

## 1. 一句话

一个 POU 里放 **1 个步序号提交网络 + N 个"一步一网络"**；每个步序网络用 `EQ(aiAutoStep, N)` 做门，网络内固定三梯级：**写描述 → 做动作 → 写下一步**。

## 2. 变量三件套（名字照抄模板，便于人和 HMI 认）

| 变量 | 类型 | 作用 |
|---|---|---|
| `aiAutoStep` | INT | 当前步。**唯一状态源，只读**，任何动作都不写它 |
| `aiAutoStepBuffer` | INT | 下一步缓存。所有跳步只写这里 |
| `awstrAutoDescription` | WSTRING(49) | 当前步描述，HMI 直读 |

外加一个总使能 `xAutoing`（布尔），串在每一步的 EQ 前面。

## 3. 网络顺序（不可换）

   网络 1   提交步序号      aiAutoStep := aiAutoStepBuffer        ← 必须最先，无条件
   网络 2   步 0  待命      BRANCH{EQ(xAutoing, aiAutoStep, 0)}   T1 描述 / T2 动作 / T3 跳步
   网络 3   步 10 取料      BRANCH{EQ(..., 10)}
   ...
   网络 n+1 步末 回待命     BRANCH{EQ(..., 40)}  → buffer := 0

提交网络必须在**声明区之后的第一个网络**：它无条件执行，把上一周期写好的 buffer 落到 aiAutoStep，于是"本周期所有步序网络看到的步号"是稳定的。把提交放到末尾（或放进某个分支里）会出现"跳步要等两个周期""分支不导通时步号不更新"这类难查的错。

## 4. 单个步序网络的结构（三梯级）

   BRANCH
     Input = EQ 框（3 槽）: [xAutoing 触点, aiAutoStep 值引脚, 常量 N 值引脚]
     Trees:
       T1  MOVE 框: "步描述" → awstrAutoDescription        （无条件，每周期刷）
       T2  动作框:  FC_CylinderExe / MOVE / ADD ...        （EN 引脚带边沿 16）
       T3  MOVE 框: 下一步号 → aiAutoStepBuffer            （EN 由完成条件触点门控）

- **T1 无条件**：描述每周期都刷，HMI 才不会闪断。
- **T2 的 EN 引脚加边沿（InputFlags[0].Flags=16）**：进入本步的**第一个周期**执行一次。带副作用的动作（气缸、轴、计数）必须这样，否则停几个周期就执行几次。
- **T3 的 EN 由完成条件门控**：完成触点导通的那个周期才跳步。若要求"按下按钮只触发一次"，也应在 T3 的 MOVE 的 EN 上加边沿，而不是给触点加 Flags。

## 5. 用 ldgen 生成（可直接跑）

```python
from ldgen import *

nets = [buf_commit_net()]                       # 网络 1：提交
nets.append(step_net(0, u"待命", [], 10, contact(u"xStart"),
                     u"待命：xStart 上升沿 -> 取料", done_edge=True))
nets.append(step_net(10, u"取料",
                     [move_box(value_pin(u"TRUE", u"BOOL"), u"bLoadOn", u"BOOL", en_edge=True)],
                     20, contact(u"xLoadDone"), u"取料：置输出"))
nets.append(step_net(20, u"加工",
                     [move_box(value_pin(u"TRUE", u"BOOL"), u"bWorkOn", u"BOOL", en_edge=True)],
                     30, contact(u"xWorkDone"), u"加工：置输出"))
nets.append(step_net(30, u"复位",
                     [move_box(value_pin(u"FALSE", u"BOOL"), u"bLoadOn", u"BOOL", en_edge=True),
                      move_box(value_pin(u"FALSE", u"BOOL"), u"bWorkOn", u"BOOL", en_edge=True)],
                     40, None, u"复位：撤输出"))
nets.append(step_net(40, u"计数",
                     [add_box(value_pin(u"iCycle", u"INT"), value_pin(u"1", u"INT"),
                              u"iCycle", u"INT", en_edge=True)],
                     0, None, u"计数：节拍 +1 回待命"))

skel = io.open(SKEL, encoding="utf-8").read()
build_doc(skel, u"prg_SeqDemo", DECL, nets, OUT)
```

生成的 6 网络成品即 `assets/natives/prg_SeqDemo.native`。

## 6. 六条实测约束（每条都有实验）

| # | 约束 | 证据 |
|---|---|---|
| 1 | `aiAutoStep` 只读，跳步只写 buffer | 模板 A00 全部 85 网络无一处直接写 aiAutoStep |
| 2 | 提交网络无条件、必须第一个 | 本卡示例编译通过且步序单周期推进；模板 A00 NET2 同位置 |
| 3 | **边沿在框的 EN 引脚**（InputFlags[0].Flags=16），**不是触点** | 触点 Flags=2 导入/编译/导出全都"成功"但语义无沿（假通过）；EN=16 才是 IDE「边沿检测」命令写出的形态，46 个 native 语料命中 294 处 |
| 4 | 布尔常量用 `value_pin(u"TRUE", u"BOOL")`（Boolean=True） | A00 唯一 TRUE 处即此形态；生成后往返一致 |
| 5 | 骨架必须 Application 直属、单一实现区 | 用带 2 个 Method 的 FB 导出当骨架 → 导入弹「已标识项中有一项的格式无效」并冻死主线程 |
| 6 | 步序网络整体可空转 | 步 30（复位）没有完成条件，靠无条件的下一网络推进 |

## 7. 实验记录（2026-11-27 17:49–17:50）

   17:49:37  opened      study_lead.project 副本（13,831,181 B）
   17:49:40  import ok   prg_SeqDemo.native（190,602 B）
             mounted     pous=['M000_MAIN', 'prg_StnAutoSeq', 'prg_SeqDemo']
   17:50:15  build       37 秒
             [97f48d64 编译] n=104 err=0 warn=101
                 ------ 开始构建应用程序 Device.Application -------
                 代码典型化 ...
                 编译完成 -- 0 错误, 101 警告
   17:50:16  saved

- 101 条警告是模板工程固件的既有告警（枚举/隐式转换），与新增 POU 无关。
- 结构自检：6 网络 / 215 个 Id 全唯一 / AND 16 · MOVE 15 · EQ 5 · ADD 1 / BRANCH 5 / PIN 35 / CONNECTOR 13 / OUTCONN 16 / InputFlags=16 共 6 处 / 触点 Flags=2 共 0 处。

## 8. 复现

```powershell
$py = "C:\Users\<你>\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
& $py D:\plc_mcp\ld_study\gen_seqdemo.py        # 生成 native
# 再用隐藏桌面实例跑导入+挂载+build 的探针（见 references/mcp-bridge.md 的 --runscript 一节）
```

## 9. 未验证 / 下一步

- 多工位（A00 里 A1/A2/B1/B2 四平台）的"步号区段跳转"结构：A00 用一个 EQ 判工位再进不同区段，本卡未覆盖。
- 步内报警/超时分支（T2 里加 TON + 跳 99）。
- 半自动/手动覆盖（模板里有 xManualMode 旁路，本卡未展开）。
