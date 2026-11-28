# 模式卡 03 · A00 骨架（工站子程序）

> 状态：**已在软件里验证**（2026-11-28）。样本 `assets/natives/prg_Stn3LoadSeq.native`（31 网络 / 1145 个 Id 全唯一 / 1.19 MB）
> 由 `scripts/examples/gen_a00_stn3.py` 生成，导入 InoProShop V1.10.0.3 编译分类 **0 错误 / 101 警告**（警告全是模板自带的枚举转换）。
> 前置阅读：`step-sequence.md`（单个步序网络的母语法）、`process-flow.md`（完整流程 + 定时/超时/中断）、`../edge-detection.md`（框的 EN 边沿）。

---

## 0. 这张卡解决什么

会写步序网络 ≠ 会写一个**工站子程序**。InoPack 模板里每个工站 POU（`A00_上料移栽`、`A01_中转移栽`…）的第 1、2、8 个网络是固定的骨架，缺了它们：

- 总控看不到本工站的步序号（HMI 上没有「当前步号 / 当前步描述 / 步序日志」）
- 单步模式、单站模式、总控启动三种放行方式全部失效（现场调试只能整段跑）
- 工位判断（有料/无料/多料/少料）没有，换工位就要重写跳转

这张卡给的是：**8 个骨架网络 + 两段式步号 + 变量容器约定**，以及从哪里克隆、怎么换符号。

---

## 1. 骨架的 8 个网络（顺序不可换）

| # | 网络 | 作用 | 来源 |
|---|------|------|------|
| 1 | 步序号记录器 | `FB_StepLogger` 实例，把每周期步号/描述/日志写给 HMI | **整块克隆** A00 net01 |
| 2 | 步序号缓存处理 | 单步 / 单站 / 总控 三路放行 `aiAutoStep := aiAutoStepBuffer` | **整块克隆** A00 net02 |
| 3 | 流程开始 | `10000 → 10`（无条件跳，只为把步号从 0 拉进流程） | 生成 |
| 4–7 | 安全自检 | `10 → 15 → 20 → 30 → 100`：逐缸复位、逐轴回安全位 | 生成 |
| 8 | 工位判断跳转 | `100`：产品状态 0/1 → 取料段 / 放料段；异常置多料/少料报警 | **整块克隆** A00 net08（换 4 个符号） |
| 9–23 | 取料段 | `1000 – 1120`，做完跳回 100 | 生成 |
| 24–31 | 放料段 | `2000 – 2060`，做完跳回 100 | 生成 |

克隆件在 `assets/natives/a00-fragments/`：`net01_step_logger.xml`（12 KB）、`net02_step_buffer.xml`（39 KB）、`net08_station_dispatch.xml`（96 KB）。
它们是 A00 导出里**原样的网络节点**，用 `split_networks.py` 从完整导出中切出来的。

---

## 2. 克隆三个网络时只换什么

### NET1 / NET2：只换工站位号

```python
s = open("net01_step_logger.xml").read().replace("STNControl[1].", "STNControl[3].")
```

两个网络里所有变量都在 `STNControl[1]` 这个结构体数组元素上，换一个前缀就整套搬到新工站。**别改结构**：NET2 的三路线由（单步模式 / 单站模式 + 本站 `xStart` 上升沿 / 非单站模式 + 总控 `xStart` 上升沿）是现场三种调试方式的全部，删一条现场就少一种。

### NET8：换 4 个上料移栽专有符号

| A00 原符号 | 换成 | 含义 |
|---|---|---|
| `Gr_stS1上料移栽工位状态.ui产品状态` | `iStationProductState` | 本工位有料/无料 |
| `G_xS1上料移载有无料检测感应` | `xMaterialAtStation` | 工位有无料检测 |
| `HAL_stStation1Alarm.x上料移栽异常多料报警` | `xAlarmOver` | 异常多料 |
| `HAL_stStation1Alarm.x上料移栽异常少料报警` | `xAlarmShort` | 异常少料 |

网络语义（照 A00 原样，不要简化）：

- 产品状态 = 0 **且** 工位无料 → `MOVE 1000`（去取料）
- 产品状态 = 1 **且**（工位无料 **或** 总控空跑 `xEmptyMode`）→ `MOVE 2000`（去放料）
- 其余组合 → 报警线圈（`(S)` 多料 / 少料）

⚠ 报警线圈在 A00 里挂在**最后一个触点的 `OutputItems`** 上（net08 实测 4 处），不是挂在 AND 框上——挂框上 IDE 只画空方块（见 `../false-pass-catalog.md` 第 9 条）。

---

## 3. 变量容器：不要再造结构体

模板已经给了 `STNControl : ARRAY[0..20] OF Struct_StationControl`（`F01_Variable`）。

| 下标 | 占用 |
|---|---|
| 0 | 总控 `F20_POU_Station0_总控` |
| 1 | 上料移栽 `A00` |
| 2 | 擦拭工站 |
| 3..20 | **空闲，新工站直接用** |

字段（新增工站会用到的一部分）：`xAutoing` / `xStart` / `xSingleStepMode` / `xSingleStationMode` / `xEmptyMode` / `aiAutoStep[0..9]` / `aiAutoStepBuffer[0..9]` / `awstrAutoDescription[0..9]` / `astAutoStepLog0..9`。

所以生成器只做一件事：把 `ldgen` 的四个语义全局指向本工站——

```python
L.AUTOING = u"STNControl[3].xAutoing"
L.STEP    = u"STNControl[3].aiAutoStep[0]"
L.BUF     = u"STNControl[3].aiAutoStepBuffer[0]"
L.DESC    = u"STNControl[3].awstrAutoDescription[0]"
```

之后 `step_net` / `step_net2` / `judge_net` / `desc_tree` / `jump_tree` / `coil_tree` 全部自动落到本工站，不用逐个改字符串。

---

## 4. 步号两段式

| 段 | 步号 | 说明 |
|---|---|---|
| 公共 | 0 / 10 / 15 / 20 / 30 | 0 待命，10–30 安全自检，100 工位判断 |
| 取料 | 1000 → 1010 → 1020 → 1025 → 1030 → 1040 → 1050 → 1060 → 1070 → 1090 → 1095 → 1100 → 1110 → 1120 | 段内 +10，条件步用 +5（`1025` 请求后伸出、`1095` 置状态） |
| 放料 | 2000 → 2010 → 2020 → 2030 → 2040 → 2050 → 2060 | 同上 |
| 收尾 | 1120 / 2060 | **无条件** `MOVE 100` 跳回工位判断 |

规则：**段首是 1000 / 2000 的整数倍，段内 +10，条件插入用 +5，段尾跳回 100**。
这样一眼能从步号看出来在哪个工位、哪个阶段——A00/A01/A02 全部照此。

---

## 5. 部署：由总控调用，**不要挂 MainTask**

工站子程序是**被总控 POU 调用**的（`F20_POU_Station0_总控` 里按工站号调 `A00`…`A0x`），它本身不进 `MainTask.pous` 列表。
（2026-11-28 用户明确：「可以不用调用到MainTask」。）

⚠ 但验证阶段必须让它进编译单元，否则 0 错误是假的：

- 要么临时 `main_task.pous.add("prg_Stn3LoadSeq")` 编一次、验完摘掉；
- 要么先让总控真的调用它再 build。

隐藏桌面实例上**只有编译分类**（无预编译分类），未挂任务的 POU 静默漏检——见 `../evidence/hidden-instance-scope/README.md`。

---

## 6. 从零生成

```bash
# 仓库自带片段 + 任意 PROGRAM 骨架
LDSKEL=assets/natives/user_fixed.native LDOUT=work/prg_Stn3LoadSeq.native \
  python scripts/examples/gen_a00_stn3.py
```

产物统计（脚本自己打印）：`networks 31 / ids 1145 / max_id 1145 / AND 84 · MOVE 59 · EQ 29 / branch 32 / pin 230`。
连续两次运行**只有对象 GUID 不同**（`Single Name="Guid"` 由 `build_doc` 每次新生成），其余逐行一致——可用来验证生成器没被改坏。

---

## 7. 验收（本次实测）

| 项 | 结果 |
|---|---|
| 隐藏桌面副本导入 → 临时挂 MainTask → build | `编译完成 -- 0 错误, 101 警告`（104 条消息） |
| 写进用户工程（`do_replace.py`，改名让位） | `import_native ok 1.51s` / `networks 31` / `saved` |
| 双分类 | 预编译 `total=101 errors=0`，编译 `total=104 errors=0` |
| 人眼 | IDE 里程序段 8 显示 EQ 门控 + 三条支路 + `(S)` 报警线圈 |

---

## 8. 坑表

| 现象 | 根因 | 正解 |
|---|---|---|
| 流程开始/跳回这类无动作步报 `'AND'需要至少'2' 个操作数` | 用 `step_net` 且动作列表为空，生成出单条件 AND | 用 `step_net2(..., unconditional=True)` |
| 夹爪检测判不出来 | 用两个独立 `step_net` 表达二选一 | `judge_net(step, [(cond, n1), (cond_neg, n2)])`，一个 BRANCH 两条 MOVE |
| 换工站后所有变量都指向 1 号工站 | 只改了声明，没改 `ldgen` 的四个语义全局 | 生成前先改 `L.AUTOING/STEP/BUF/DESC` |
| 导入后 IDE 里网络显示但线圈是空方块 | 线圈挂在功能框 `OutputItems` | 挂末触点 `OutputItems`（A00 写法）或 `NETITEM.OutputItems` |
| `import gen_loadseq` 后产物被覆盖 | 那个生成器有模块级副作用 | 只 import `ldgen`，动作框模板自己解析 |
| 切网络切出 140 字符碎片 | 字符串配对 `List2` 嵌套深度 | 用 `scripts/corpus/split_networks.py`（ElementTree） |

---

## 9. 还没验证的

- 总控 `F20` 真实调用本 POU 的联调（本次只验证了 POU 自身编译 0 错误）
- 多工站并行（`STNControl[4]`/`[5]`）同时跑
- 步序号记录器 `FB_StepLogger` 的 HMI 侧显示效果

最后更新：2026-11-28（lead）