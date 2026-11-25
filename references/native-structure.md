# LD Native XML 结构与节点类型

## 语言 GUID（本机反射所得）

- LD（梯形图）: `29148beb-8dd2-4bb8-8b77-ab9fe196c1ba`
- ST: `cc393387-a21c-4f68-a3e3-84c36951965d`
- FBD: `c2e2244b-c806-41b4-8ad3-7a0e25ce1393`

取法：`Activator.CreateInstance(ScriptImplementationLanguages).ladder`

## 层级结构

```
NetworkList
  Network                    （一个程序段）
    NetworkItems             （段内多个梯级 NETITEM）
      NETITEM {9873c309-1f09-4ebf-9078-42d8057ef11b}
        RValue {acfc6f68-...}  AND 框 / TON 框 / 分支组（BoxType 决定）
        OutputItems             可挂多个线圈
```

`NetworkItems` 的直接子节点可以不是 NETITEM —— **EXECUTE 框（内嵌 ST）就直挂这一层**，
见下文「EXECUTE 框」一节。

## 关键节点类型

| GUID | 含义 | 要点 |
|------|------|------|
| `{9873c309-1f09-4ebf-9078-42d8057ef11b}` | NETITEM（梯级） | |
| `{acfc6f68-8e3a-4af5-bf81-3dd512095a46}` | 功能框（AND/MOVE/TON/FB/EXECUTE） | InputItems 槽位数必须 == InputParam 参数数；`BoxType` + `CallType` 决定是哪种 |
| `{9de7f100-1b87-424c-a62e-45b0cfc85ed2}` | 触点/引脚节点 | 外层 `IsContact` 决定身份：True=触点，False=值引脚 |
| `{c9b2f165-48a2-4a45-8326-3952d8a3d708}` | Operand 操作数 | 内含 Boolean/Flags/Operand/Type/IsCoil/SeriesIndex/Id；**线圈和输出引脚不带 `Name` 属性** |
| `{827b9ec2-2032-40da-9f4e-7670ca2d55a8}` | 并联分支组 | 内部 Trees 放多个支路节点，Mode=Sequential；**Trees 必须 ≥2 条，否则 IDE 绘制网络崩溃** |
| `{505bff94-4c90-4e17-ac28-b8ac69d1b9e2}` | 连接器节点（支路输出接点） | 只有 Id 一个子节点；**完整支路必须有它** |
| `{5f9848d3-568d-4cc5-9e31-8e28e9607ff1}` | 连接器（带 Flags/Input） | 功能框的 EN 槽 / 电源流入口 |
| `{b2131366-6917-4304-87a9-64c0585560a8}` | **STSnippet 容器** | EXECUTE 框的代码块；其它框此处为 `<Null/>` |
| `{3b83b776-fb25-43b8-99f2-3c507c9143fc}` | **STSnippet 内层** | 只包一个 TextDocument |
| `{f3878285-8e4f-490b-bb1b-9acbb7eb04db}` | TextDocument | 声明区与 STSnippet 共用此类型 |
| `{a5de0b0b-1cb5-4913-ac21-9d70293ec00d}` | TextLines 行 | 每行含 Id/Tag/Text |
| `{d9a99d73-b633-47db-b876-a752acb25871}` | Network 单网络容器 | |

## Operand 内部 Flags 位掩码

| 值 | 含义 | 适用 |
|----|------|------|
| 0 | 无 | 常量引脚必须为 0 |
| 1 | NOT 取反 | 触点取反（常闭）；**值引脚残留此值必报错** |
| 2 | S 置位 | 线圈置位 |
| 3 | R 复位 | 线圈复位 |

## AND 框的输入元数：至少 2 个槽

**任何 AND 框（包括每个 NETWORK 顶层 `RValue` 本身就是的那个 AND）都必须有 ≥ 2 个 `InputItems` 槽。**

单条件 rung 是高频踩坑点：

| 阶段 | 结果 |
|------|------|
| 预编译 `217bc73e` | **0 错误**（不校验元数） |
| 构建 `97f48d64` | 报 N 条 `'AND'需要至少'2' 个操作数`，N = 单条件 rung 条数 |

输出映射段（`步标志 → 输出`）、单触点置位段最容易中招。

**修法**：条件数 < 2 时补一个 `TRUE` 触点占位：

```
Operand="TRUE"  内部 Flags=0  IsContact=True
```

语义不变（`X AND TRUE = X`），图形上多一个 TRUE 常开点。

> 详细报错对照见 [precompile-errors.md §2b](precompile-errors.md)。

## MOVE 框标准结构（已验证预编译 0 错误）

```xml
<Single Type="{acfc6f68...}">   <!-- 直接挂 Network/NetworkItems -->
  <List2 Name="InputItems">
    <!-- 槽0: EN 槽 = AND 框（内含条件触点，每个触点 IsContact=True） -->
    <!-- 槽1: IN 槽 = 常量引脚（IsContact=False + 内部 Flags=0 + Type=INT + Boolean=False） -->
  </List2>
  <Single Name="InputParam">Names=[EN, IN], Types=[BOOL, INT]</Single>
  <Single Name="OutputParam">Names=[ENO, OUT], Types=[BOOL, INT]</Single>
  <Single Name="OutputItems">OUT 操作数 = 目标变量（如 iState）</Single>
</Single>
```

## 功能块（FB）调用标准结构（act04 / act90 实测，2026-11-25）

**FB 调用与 MOVE 框同属 `{acfc6f68}` 功能框，但关键字段全不一样。**

### 与 MOVE 框的差异对照

| 字段 | MOVE 框 | FB 调用 |
|------|---------|---------|
| `CallType` | `Move` | `Function` / `Program` / `FunctionBlock` |
| `BoxType` | `MOVE` | **POU 名**（`prg_EM00_Logic`、`PackMLUnitManager`、`PackMLScCmdInit`） |
| `IsBoxType` | `True` | `True`（两者相同） |
| `EN` / `ENO` | 条件槽（AND 框或常量引脚） | **`<Single Name="EN" Type="bool">True</Single>`**（纯布尔，不是图形节点） |
| `Instance.Operand` | — | `FunctionBlock` 类**必填实例名**；`Program` / `Function` 类写 `<Null Name="Operand" />` |
| `Instance.Type` | — | 实例的类型名（如 `PackMLUnitManager`）；无名实例写空串 `''` |
| `Instance.IsInstance` | — | 恒为 `True` |

`CallType` 三取值对应的图形语义：

| CallType | 图形 | 实例 | 例 |
|----------|------|------|-----|
| `Function` | FUN 框 | 无 | `PackMLScCmdInit(stScCmd := ...)` |
| `Program` | PRG 框 | 无 | `prg_EM00_Logic(uiEmID := 0)` |
| `FunctionBlock` | FB 框 | **有** | `fbPackMLManager(...)` |

### 槽位规则（核心）

```
InputItems 槽位数 == InputParam 参数个数（EN 也算一个）
  槽0      = 连接器 {5f9848d3}，Input=Null    ← EN 引脚的来源；Null = 由框自身 EN 字段决定
  槽1..n   = 参数引脚 {9de7f100}，IsContact=False
             与 InputParam **去掉 EN 之后**严格一一对应，顺序不可乱

OutputItems 长度 == OutputParam 参数个数（逐项一一对应，不是「恒 1 个 Null」）
  有 ENO 的框（EN/ENO=True）：第 0 项 = <Null />        ← 对应 ENO
  无 ENO 的框（TON，EN/ENO=False）：没有 ENO 位，Q/ET 各自一项
  已接线项 = Operand 节点 {c9b2f165}，LValue=True, IsCoil=False，Operand=目标变量
  未接线项 = <Null />
```

### ⚠ `OutputParam` 里有没有 `ENO`，由 `EN`/`ENO` 字段决定（19/19 实测）

这条之前记成「第 0 项恒为 `<Null />`（对应 ENO）」，**只对含 ENO 的框成立**。
InoPack 全部样本（54 个功能框，其中 19 个非 AND）实测规律完全一致：

| `EN` / `ENO` 字段 | `OutputParam.Names` | 含义 |
|---|---|---|
| `True` / `True` | 第一项是 `ENO`，后面才是真正输出 | Function / Program / 常规 FB / EXECUTE |
| `False` / `False` | **不含 `ENO`**，直接是真正输出 | 只有 `TON`（`['Q','ET']`） |

实测证据（19/19 全部符合，0 例外）：

```
TON              EN=False ENO=False  OutputParam=['Q','ET']                不含ENO
EXECUTE          EN=True  ENO=True   OutputParam=['ENO']                   含
PackMLConfiguer  EN=True  ENO=True   OutputParam=['ENO','']                含
HC_GetCPUInfo    EN=True  ENO=True   OutputParam=['ENO','xError']          含
prg_UN00         EN=True  ENO=True   OutputParam=['ENO']                   含
HC_MovePtpV      EN=True  ENO=True   OutputParam=['ENO']                   含
EventRecordV2    EN=True  ENO=True   OutputParam=['ENO','','xActive','xError']
EventManager     EN=True  ENO=True   OutputParam=['ENO', 8 个真输出]        含
GetOEE           EN=True  ENO=True   OutputParam=['ENO','xError','xBusy','eMessage']
```

**踩过的坑（2026-11-25）**：生成器把「第 0 项恒为 `<Null/>`」当死规矩写死，
给 TON 写 `OutputParam=['Q','ET']` 却只输出 1 个 `<Null/>`（应为 2 个）。
预编译和编译都是 0 错误、往返 diff 也 PASS，**IDE 照样接受**——
只有拿真实样本比对 `项数 vs 参数数` 才发现不一致。已修，并在 `fb_box()` 里加了
`len(out_vars) != len(out_names)` 就 `raise` 的断言。

**自检**：`OutputItems/List2` 的项数必须 == `OutputParam/Names` 的项数。
注意 `OutputItems` 是 `Single` 包 `List2`，数的是 `List2` 的子节点。
直接跑 `python scripts/check_slots.py <a.native> [b.native ...]` 即可（退出码 0/1）。

**注意 `InputParam.Names` 填的是参数名，不是操作数。**
`Names=['EN','stScCmd']`，`Types=['BOOL','sPmlSCCmd[REF]']` —— REF 形参在 Types 里
带 `[REF]` 后缀；而引脚 `Operand.Type` 写去掉后缀的实际类型（`sPmlSCCmd`）。

### 完整结构示例（FunctionBlock 类，带实例）

```
功能框 {acfc6f68}
├─ EN  = <Single Name="EN" Type="bool">True</Single>
├─ ENO = <Single Name="ENO" Type="bool">True</Single>
├─ InputItems (13 槽 = InputParam 13 个参数)
│   ├─ [0] 连接器 {5f9848d3}  Input=Null            ← EN
│   ├─ [1] 引脚 {9de7f100}    Operand=PML0.stPackMLCfg   Type=sPmlCfg     ← stCfg
│   ├─ [2] 引脚             Operand=...xRemModeReq    Type=BOOL         ← xRemModeReq
│   └─ ... 依次到第 12 个参数
├─ CallType  = FunctionBlock
├─ Instance  = {c9b2f165}  IsInstance=True  Operand=fbPackMLManager  Type=PackMLUnitManager
├─ OutputItems (13 项 = OutputParam 13 个参数)
│   ├─ [0] <Null />                                 ← ENO
│   ├─ [1] Operand=PML0.stStat.stModeCmd  Type=sPmlMode  LValue=True
│   └─ ... 依次到第 12 个输出
├─ InputParam   Names/Types 各 13 项
├─ OutputParam  Names/Types 各 13 项
├─ BoxType   = PackMLUnitManager
└─ IsBoxType = True
```

### 挂载位置

与 MOVE 框相同：直接挂 `Network/NetworkItems`，或作为分支组支路里的
`AND[FB框, 连接器{505bff94}]`。act04 网络2 就是后者（两条并联支路各一个 FB 框）。

### 已验证样本

| 文件 | 覆盖 |
|------|------|
| `ipc/act04_Interface.native` | `Program` 类（无名实例、单参数） |
| `ipc/act90_PackMLManager.native` | `FunctionBlock` 类（带实例、12 入 12 出）+ `Function` 类（REF 形参）+ MOVE 框包 FB 框 |
| `assets/natives/fb_call_test.native` | **可直接克隆的 FB 调用模板**（上述三类合并成一个 POU） |
| 生成器 `scripts/examples/make_fb_call_test.py` | 三类 CallType 各一个，全部往返一致、双分类 0 错误 |

## 挂载位置规则

MOVE 框（功能框）有两个合法位置：

1. **直接挂 `Network/NetworkItems`** —— 一个网络里多条独立梯级，每梯级一个 MOVE 框
2. **挂分支组 `{827b9ec2}` 的 `Trees`** —— 树形/并联结构

### ⚠️ 分支组里「完整支路」的标准结构（用户手改已验证，2026-11-25）

**分支组 Trees 里的支路不是裸 MOVE 框，而是「AND 框包住 [MOVE 框, 连接器]」。**

这是最关键的修正。裸 MOVE 框挂 Trees 虽然预编译能过，但 IDE 里的功能链不完整——
末端缺少连接器，后续无法继续串接，图形上也不完整。用户手工补全后的正确结构：

```
分支组 {827b9ec2}  Mode=Sequential
├─ Input: 公共前缀触点（如 TRUE，IsContact=True）
└─ Trees:
   ├─ tree 0 ─ 外层 AND 框 {acfc6f68}  BoxType=AND  CallType=And  IsBoxType=False
   │            └─ InputItems (2 槽):
   │               ├─ [0] MOVE 框 {acfc6f68}  BoxType=MOVE  CallType=Move  IsBoxType=True
   │               │      ├─ EN  = True
   │               │      ├─ ENO = True
   │               │      ├─ InputParam  Names=[EN, IN]  Types=[BOOL, INT]
   │               │      ├─ OutputParam Names=[ENO, OUT]
   │               │      ├─ InputItems (2 槽):
   │               │      │    ├─ [0] EN 槽 = AND 框（内含条件触点，至少 2 个）
   │               │      │    └─ [1] IN 槽 = 常量引脚（IsContact=False, Flags=0, Type=INT）
   │               │      └─ OutputItems: OUT 操作数（iState）
   │               └─ [1] 连接器 {505bff94-4c90-4e17-ac28-b8ac69d1b9e2}  ← 只有 Id 一个子节点
   │
   ├─ tree 1 ─ 外层 AND 框 ... (同上)
   └─ tree 2 ─ 外层 AND 框
                └─ InputItems (2 槽):
                   ├─ [0] 嵌套分支组 {827b9ec2}（继续分层，内部再放多个 MOVE 框）
                   └─ [1] 连接器 {505bff94}
```

### 三层嵌套的完整实例（实测预编译 0 错误）

用户工程 `assets/natives/user_fixed.native` 网络 2 的真实结构。
**2026-11-25 已把全部 8 条支路统一成完整形式（每条都带外层 AND + 连接器）：**

```
分支组 (3 支路, Input=TRUE 触点)
├─ tree0: AND[ MOVE(7) , CONN ]
├─ tree1: AND[ MOVE(2) , CONN ]
└─ tree2: AND[ 分支组(6 支路) , CONN ]
              ├─ tree0: AND[ MOVE(6) , CONN ]
              ├─ tree1: AND[ MOVE(8) , CONN ]
              ├─ tree2: AND[ MOVE(9) , CONN ]
              ├─ tree3: AND[ MOVE(4) , CONN ]
              ├─ tree4: AND[ MOVE(3) , CONN ]
              └─ tree5: AND[ MOVE(5) , CONN ]
```

**⚠️ 修正（2026-11-25）**：此前记录说「内层嵌套分支组的支路是裸 MOVE 框」——
那是用户**尚未改完**的中间状态。用户随后要求把 6 个内层支路也补齐，
补齐后**内层同样需要 AND + 连接器**。

**结论：无论在哪一层，分支组 Trees 里的支路都应该是「AND 框包住 [MOVE 框, 连接器]」。**
只有一种例外：分支组 `Input` 槽里的公共前缀触点（如 TRUE）是裸触点。

补齐前后的差异（可作为排查依据）：

| 状态 | 内层支路形态 | 预编译 | 图形完整性 |
|------|-------------|--------|-----------|
| 补齐前 | 裸 MOVE 框 | 0 错误 | 功能链断头，无连接器 |
| 补齐后 | AND[MOVE, CONN] | 0 错误 | 完整，可串接 |

### 为什么需要外层 AND + 连接器

- 外层 AND 框的 `InputItems` 两个槽 = 「功能框输入」+「功能框输出接线位」
- 连接器 `{505bff94}` 代表这条支路的输出接点，使支路可以继续向右串接
- 缺少它 = 功能链断头，虽然预编译不报错，但结构不完整

### 不能挂的位置

- NETITEM.OutputItems（线圈位）→ `已标识项中有一项的格式无效`
- NETITEM.RValue → 同上

其他：

- NETITEM.OutputItems 可挂**多个线圈**
- 分支组的 `Input` 槽可放一个公共前缀触点（如 `TRUE`），实现「公共条件只画一次 + 竖线分叉」

## ENO 引脚

- 功能框的 `ENO` 是一个 `Single Name="ENO" Type="bool">True` 节点，表示该框的 ENO 输出已启用/接线
- **功能链末端的框可以删掉 `ENO` 节点**（不往后连接），实测预编译 0 错误
- 中间框若需串接到下一框，保留 `ENO`

## Id 分配

- 全部唯一；`UniqueIdGenerator` 需 ≥ 最大 Id（建议 +100 余量）

## OUT 操作数

- OUT 输出操作数节点自身就是 `{c9b2f165}`（无 Operand 子层），取值用 `child(outop, "Operand")`

### 声明区（Interface/TextDocument/TextLines）

native 文件里除了图形，还有一份 POU 声明文本，位于：

```
Object
└─ Interface {a9ed5b7e-75c5-4651-af16-d2c27e98cb94}
   └─ TextDocument {f3878285-8e4f-490b-bb1b-9acbb7eb04db}
      └─ TextLines (Array)
         └─ Single {a5de0b0b-1cb5-4913-ac21-9d70293ec00d}
            ├─ Id   : long    ← 必须全表唯一、顺序递增
            ├─ Tag  : Null
            └─ Text : string  ← 一行声明源码，中文可直接写
```

**铁律：图形里引用的每一个符号，声明区必须有一行对应声明。**
`import_native` 只搬「图形 + 声明文本」，不会根据图形自动补声明；
漏声明就会在预编译阶段得到一堆 `C0046: 没有定义标识符`（每个引用点报一条）。

补声明的最小做法：

1. 克隆任意一条已有声明行节点（deepcopy）
2. 改 `Id`（新值）与 `Text`（新声明文本）
3. 插到 `END_VAR` 那一行**之前**
4. 全部插完后，把 `TextLines` 里所有 `Id` 按数组顺序从 900 重排

### 公共前缀与支路条件的去重

分支组 `{827b9ec2}` 的 `Input` 槽 = 所有支路共享的**公共前缀触点**。
因此每个支路的 EN 条件框里**不应该再重复放同样的 TRUE**，
否则图形上会看到「两个 TRUE 串联」（逻辑等价但冗余，且不符合树形画法要求）。

正确形态：

```
分支组 Input = TRUE          ← 公共前缀，只画一次
├─ tree0: AND[ MOVE( IN← AND[ xAlarm̄, xAutoMode, xInitDone, xAutoRun̄ ] ), CONN ]
├─ tree1: AND[ MOVE( IN← AND[ ... ] ), CONN ]
└─ tree2: AND[ 分支组(6 支路), CONN ]
```

错误形态（多了第二个 TRUE）：

```
├─ tree0: AND[ MOVE( IN← AND[ TRUE, xAlarm̄, ... ] ), CONN ]   ← 这个 TRUE 多余
```

## NETITEM 的 Flags 位：整级输出取反

`NETITEM.Flags`（`{668066f2}` 容器里的 `Flags` int）的 **bit 0 = 该梯级输出取反**，
图形上表现为线圈前的小圆圈 `○`。

```
<NETITEM Flags=0>  →  条件 ──────( )线圈        正常
<NETITEM Flags=1>  →  条件 ──○──( )线圈        输出取反
```

注意与 **Operand 内部 Flags bit0 = NOT**（常闭触点）区分：

| 位置 | 含义 | 图形表现 |
|------|------|---------|
| `Operand.Flags` bit0 | 该触点取反 | `\|/\|` 常闭触点 |
| `NETITEM.Flags` bit0 | 整个梯级输出取反 | 线圈前 `○` |

**典型用法**：一条条件同时驱动两个互斥输出，只画一次条件。

```
xStopped(常闭) ─┬─( ) xProduction
                └─○─( ) xManual        ← 第二个 NETITEM 的 Flags=1
```

## RValue 的类型可以是分支组本身

`NETITEM.RValue` 的 `Type` **不一定是** `{5f9848d3 RValue 容器}`：

- 条件是**单个触点/AND 框** → `RValue Type={5f9848d3}`，内部再放图形节点
- 条件是**并联分支组** → `RValue Type={827b9ec2}`（分支组），**直接**当 RValue

```
<!-- 正确：RValue 类型就是分支组 -->
<Single Name="RValue" Type="{827b9ec2}">
  <Null Name="Input" />
  <List2 Name="Trees"> ... </List2>
  <Single Name="Mode" Type="{3b9474d0}">Sequential</Single>
  <Single Name="Id" ... />
</Single>
```

在 `{5f9848d3}` 里再包一层分支组会报 **「已标识项中有一项的格式无效」**。

## ⚠ 铁律：分支组的 Trees 必须有 ≥ 2 条支路

**单支路分支组会让 IDE 绘制网络时崩溃**，而且**预编译和编译都报 0 错误**，
极易被误判为"验收通过"。

### 症状

```
程序段 2:
  在绘制该网络的时候遇到错误。
  不能显示内容。
  索引超出了数组界限。
  堆栈跟踪
    在 ...OryOpCeA00OG2UaUNhjyWGetg8LTg(IBoxTreeParallel, Point, Int32&, ...)
    在 ...Visit(IBoxTreeParallel) ...
```

即：**程序能编译、能下载、能运行，但梯形图编辑器打不开这一级网络**。

### 根因

`IBoxTreeParallel`（分支组绘制器）按「支路数 ≥ 2」计算几何位置。
`Trees` 只有 1 项时内部数组访问越界。

### 实测证据（全部用脚本枚举 `Trees` 长度）

| 文件 | 网络 | 分支组位置 | Trees 数 | IDE 绘制 |
|------|------|-----------|---------|---------|
| act03_PackMLCmd | net1~net10 | 全部 | **2** | 正常 |
| prg_PackMLCmdTest | net1~net7 | 全部 | **2** | 正常 |
| prg_FbCallTest（错版） | net1 | RValue | 2 | 正常 |
| prg_FbCallTest（错版） | **net2** | **RValue** | **1** | **崩：索引越界** |

结论：**工程里从未出现过 `Trees=1` 的分支组**，这是纯粹的非法构造。

### 正确做法

**只有 1 条支路时，不要用分支组包装**，直接把 AND 框 / 图形节点挂上去：

```
单支路（正确）                     单支路（错误）
NetworkItems                       NetworkItems
└─ AND 框 {acfc6f68}          ✗    └─ NETITEM {9873c309}
   ├─ 功能框                          └─ RValue = 分支组 {827b9ec2}
   └─ 连接器 {505bff94}                  └─ Trees = [AND 框]   ← 只有 1 项
```

参考实现（act90_PackMLManager 网络3 就是这个形态）：
`scripts/examples/make_fb_call_test.py` 的 `build_networks()`

```python
# 单支路 -> AND 框直挂，不套分支组
nets.append(network([and_box([fb_call, connector_end()])], u"注释"))

# 多支路 -> 分支组（≥2 条）可以挂在 NETITEM.RValue 里，也可以直挂
nets.append(network([branch([and_box([...]), and_box([...])])], u"注释"))
```

### 与 NETITEM/RValue 的关系

- **分支组** 本身合法，`RValue Type={827b9ec2}` 也合法（act03 全工程都这么写）
- 但 **分支组必须 ≥2 条支路**
- **单支路** 时：既不要套 `NETITEM`，也不要用 `branch()`，直接挂 AND 框

## 分支组 Input 槽的公共前缀

分支组 `Input` 槽（`<Single Name="Input" Type=...>`）放公共前缀时，有两种合法形态：

| 公共前缀内容 | `Input` 的 Type | 说明 |
|-------------|----------------|------|
| 单一分支组 | `{827b9ec2}` 分支组 | Input 本身就是分支组 |
| 分支组 + 触点（串联） | `{acfc6f68}` AND 框 | Input 是**完整** AND 框 |

**关键**：`Input` 属性必须带 `Name="Input"`。直接把 `and_box()` / `branch()` 的输出
塞进去而忘了改外层标签名，会报同样的「格式无效」错误。

```python
# 正确
inp = prefix.replace('<Single Type="', '<Single Name="Input" Type="', 1)
```

Input 若是 AND 框，必须是**完整** AND 框（含 `CallType`/`Instance`/`BoxType`/`Id`），
不能只写 `ContainsExtensibleInputs…InputItems` 的截断版本。

## 新建 POU 的完整流程（实测通过）

以 `prg_PackMLCmdTest` 为例，7 网络、预编译 0 错误：

1. 取一个**已知可导入**的 native 骨架（如 `assets/natives/user_fixed.native`）
2. 替换 `NetworkList` 内容为生成的网络（按 `<List2>` 配对扫描，**跳过自闭合标签**）
3. 替换 `TextLines` 为新的声明文本，Id 从 900 起顺序重排
   - ⚠ **必须锚定 `Interface` 再找**：`raw.find('<Array Name="TextLines"', raw.find('<Single Name="Interface"'))`
   - 一份 native 里 `TextLines` 至少两处（`Interface` 声明区 + EXECUTE 框 `STSnippet` 的 ST 代码），
     且 `NetworkList` 在文档中排在 `Interface` 之前。裸 `find` 会命中 ST 代码块，
     把声明写进 ST、真声明区留着骨架旧变量 → 预编译 40+ 条 `符号 'PROGRAM'/'BOOL' 不能识别`
     （2026-11-25 实测 48 条，详见 `precompile-errors.md` 第 8 条）
4. 改 `MetaObject/Name` 与 `MetaObject/Guid`（新 uuid4）
5. `UniqueIdGenerator` 抬到最大 Id + 200
6. `ipc/import_args.json` 写 `{"path":..., "parent":"Application", "expect":[...]}`
7. `task_silent_import.py` 静默导入（父对象 `Application`，无同名 → 不弹框）
8. `task_check.py` 验证：**预编译 `217bc73e` 和编译 `97f48d64` 两个分类错误数都必须为 0**（只跑预编译会漏掉 AND 元数这类构建期错误）
   - ⚠ 先确认 `check.log` 里列出了全部 5 个分类。**看不到分类清单 = 没真读到消息，`total=0` 无效**（假通过，见 `precompile-errors.md` 第 9 条）
9. 语义抽查声明区首行（`PROGRAM xxx` / `FUNCTION_BLOCK xxx`）——**往返 diff PASS 不能替代这一步**

可复用的生成器：`scripts/examples/make_packml_cmd_test.py`、`scripts/examples/make_ld_learn.py`（TON / EXECUTE / FB 内 LD）

---

## 定时器功能框（TON）标准结构（act05 / HC_ValveCtrl 实测，2026-11-25）

**TON 是 `{acfc6f68}` 功能框的一个特例，与普通 FB 调用有两处硬差异**：

| 字段 | 普通 FB 调用 | **TON 定时器框** |
|------|-------------|-----------------|
| `EN` / `ENO` | `<Single ... >True</Single>` | **`False`**（实测 7 处 TON 全为 False） |
| `InputItems[0]` | 恒为连接器 `{5f9848d3}` | **看挂载位置**（见下） |
| `CallType` | `FunctionBlock` | `FunctionBlock`（相同） |
| `Instance.Operand` / `Type` | 实例名 / FB 类型名 | 实例名（如 `fbActLeft`）/ **`TON`** |

### `InputItems[0]` 的两种合法形态

```
① 顶层：NETITEM.RValue 直接是 TON 框
   InputItems[0] = 连接器 {5f9848d3}   Input=Null    ← 电源流来自梯级左侧
   InputItems[1] = 值引脚 {9de7f100}   Operand="T#3S"  Type=TIME  IsContact=False

② 嵌套：TON 框挂在某个 AND 框的 InputItems 里
   InputItems[0] = 条件触点 {9de7f100}  Operand="xActiveLeft"  IsContact=True
   InputItems[1] = 值引脚 {9de7f100}   Operand="TO_TIME(rSetActTime*1000)"  Type=TIME
```

**为什么不一样**：`EN=False` 意味着这个框没有 EN 引脚，`InputItems` 的第 0 槽就退回成
**普通输入引脚**——顶层时它是「电源流连接器」，嵌套时它是第一个真实参数 `IN`。

### 槽位规则

```
InputItems  长度 == InputParam 个数（TON 固定 2 个：IN / PT）
            [0] = 连接器 或 条件触点   ← IN（BOOL）
            [1] = 值引脚               ← PT（TIME）

OutputItems 长度 == OutputParam 个数（TON 固定 2 个：Q / ET）
            [0] = <Null />             ← 对应 Q（**不是 ENO**！TON 没有 ENO 位）
            [1] = <Null /> 或 Operand   ← ET，**不带 Name 属性**，LValue=True
```

⚠ **TON 的 `OutputParam` 是 `['Q','ET']`，不含 `ENO`**，所以两项都不承担 ENO 语义。
两个输出都不接线时，两项都写 `<Null/>`（InoPack `HC_ValveCtrl` 实测 7/7 全是 `[Null, Null]`）。
别照抄「第 0 项恒为 `<Null/>` 对应 ENO」——那句只对 `EN/ENO=True` 的框成立。

`InputParam` / `OutputParam` 照常填 `Names=[IN,PT]` / `Types=[BOOL,TIME]`、
`Names=[Q,ET]` / `Types=[BOOL,TIME]`。

### 完整结构（顶层写法，实测导出）

```xml
<Single Type="{acfc6f68...}">
  <Single Name="ContainsExtensibleInputs" Type="bool">False</Single>
  <Single Name="EN"  Type="bool">False</Single>       <!-- ⚠ False -->
  <Single Name="ENO" Type="bool">False</Single>       <!-- ⚠ False -->
  <Single Name="ProvidesSTSnippet" Type="bool">False</Single>
  <Flags ... Flags=0 />
  <Null Name="InputFlags" />
  <List2 Name="InputItems">
    <Single Type="{5f9848d3}">   <!-- 槽0：连接器 -->
      <Flags .../> <Null Name="Input"/> <Id/>
    </Single>
    <Single Type="{9de7f100}">   <!-- 槽1：PT 值引脚 -->
      <Operand ... Operand="T#3S" Type="TIME" .../>
      <IsContact>False</IsContact> <Id/>
    </Single>
  </List2>
  <CallType>FunctionBlock</CallType>
  <Instance ... Operand="fbDelay" Type="TON" IsInstance=True />
  <OutputItems><List2>
    <Null/>                                        <!-- ENO -->
    <Operand LValue=True IsCoil=False Operand="" /> <!-- ET，无 Name 属性 -->
  </List2></OutputItems>
  <InputParam>  Names=[IN,PT]    Types=[BOOL,TIME] </InputParam>
  <OutputParam> Names=[Q,ET]     Types=[BOOL,TIME] </OutputParam>
  <BoxType>TON</BoxType>
  <Null Name="STSnippet" />
  <IsBoxType>True</IsBoxType>
</Single>
```

**输出引脚可以不接线**：实测 `HC_ValveCtrl` 里 6 个 TON 的 `Q`/`ET` 全空
（`Operand=""`），预编译 0 错误、编译 0 错误。要读 `ET` 就在 EXECUTE 块里写
`fbAlarmLeft.ET`（模板正是这么做的）。

参考实现：`scripts/examples/make_ld_learn.py` 的 `ton_box()`。

---

## EXECUTE 框：LD 内嵌 ST 代码块（HC_ValveCtrl 网络9 实测，2026-11-25）

**这是 LD 里直接嵌一段 ST 的官方写法**，`references/` 之前完全没有记载。

| 字段 | 值 | 说明 |
|------|-----|------|
| `BoxType` | `EXECUTE` | |
| `CallType` | **`None`** | ⚠ 全新取值，不是 `And`/`Move`/`Function`/`FunctionBlock` |
| `ProvidesSTSnippet` | **`True`** | 唯一会为 True 的框类型 |
| `EN` / `ENO` | `True` / `True` | |
| `STSnippet` | **非 Null** | 代码在这里；其它框都是 `<Null Name="STSnippet" />` |
| `InputItems` | 1 槽（连接器 `{5f9848d3}`） | |
| `OutputItems` | 1 项（`<Null/>`） | |
| `InputParam` / `OutputParam` | `[EN]/[BOOL]` / `[ENO]/[BOOL]` | |

### 挂载位置

**直接挂 `Network/NetworkItems`，不套 NETITEM、不套分支组**（实测网络9 只有一个子节点）：

```
Network
  NetworkItems
    Box {acfc6f68} BoxType=EXECUTE    ← 就这一层
```

### STSnippet 三层结构

```
STSnippet {b2131366}
└─ STSnippet {3b83b776}
   └─ TextDocument {f3878285}
      └─ TextLines {a5de0b0b}  ← 每行一个 Single，含 Id/Tag/Text
├─ STSnippetWidth  (int，如 496)
├─ STSnippetHeight (int，如 400)
└─ Id
```

**代码行写法与声明区完全一样**：每行 `<Single Type="{a5de0b0b}">`，内含
`Id`（全局唯一）、`<Null Name="Tag"/>`、`Text`。ST 里的换行靠「一行一个 Text」表达，
`Text` 内部不写 `\n`；制表符可以直接写 `\t`；`&quot;` 等实体由 XML 层负责转义。

### 完整结构（实测导出）

```xml
<Single Type="{acfc6f68...}">
  <ContainsExtensibleInputs>False</ContainsExtensibleInputs>
  <EN  Type="bool">True</EN>
  <ENO Type="bool">True</ENO>
  <ProvidesSTSnippet Type="bool">True</ProvidesSTSnippet>   <!-- ⚠ True -->
  <Flags .../>
  <Null Name="InputFlags" />
  <List2 Name="InputItems">
    <Single Type="{5f9848d3}"><Flags/><Null Name="Input"/><Id/></Single>
  </List2>
  <CallType>None</CallType>                                  <!-- ⚠ None -->
  <Instance ...><Null Name="Operand"/><Type/></Instance>
  <OutputItems><List2><Null/></List2></OutputItems>
  <InputParam> [EN]/[BOOL] </InputParam>
  <OutputParam>[ENO]/[BOOL]</OutputParam>
  <BoxType>EXECUTE</BoxType>
  <Single Name="STSnippet" Type="{b2131366}">                <!-- ⚠ 非 Null -->
    <Single Name="STSnippet" Type="{3b83b776}">
      <Single Name="TextDocument" Type="{f3878285}">
        <Array Name="TextLines" Type="{a5de0b0b}">
          <Single Type="{a5de0b0b}"><Id/><Null Name="Tag"/><Text>//注释</Text></Single>
          <Single Type="{a5de0b0b}"><Id/><Null Name="Tag"/><Text>IF x THEN</Text></Single>
          ...
        </Array>
      </Single>
    </Single>
    <STSnippetWidth>496</STSnippetWidth>
    <STSnippetHeight>400</STSnippetHeight>
    <Id/>
  </Single>
  <IsBoxType>True</IsBoxType>
</Single>
```

**EXECUTE 里能引用的东西**：本 POU 的局部变量、输入/输出形参、**同一网络里其它功能框的实例**
（模板用 `fbAlarmLeft.ET` 读 TON 的已过时间）。因此「TON 算时间 + EXECUTE 里做判断/赋值」
是很自然的搭配，可以避开 LD 里画复杂比较的麻烦。

参考实现：`scripts/examples/make_ld_learn.py` 的 `execute_box()`。

---

## FUNCTION_BLOCK 里的 LD 写法（HC_ValveCtrl 实测，2026-11-25）

**结论：FB 内部的 LD 与 PROGRAM 内部的 LD 在 native 层完全同构，没有任何额外字段。**

`HC_ValveCtrl` 是 `FUNCTION_BLOCK`，它的 native 与 PROGRAM 骨架逐节点对照：

| 项 | PROGRAM | FUNCTION_BLOCK |
|----|---------|----------------|
| `MetaObject/TypeGuid` | `6f9dac99-8de1-4efc-8465-68ac443b7d08` | **完全相同** |
| `EmbeddedTypeGuids` | `[a9ed5b7e, 25e509de]` | **完全相同** |
| `Object/SpecialFunc` | `None` | `None` |
| `Object/POULevel` | `Standard` | `Standard` |
| `Implementation/DefaultViewMode` | `Ld` | `Ld` |
| 网络 / 分支组 / 功能框结构 | — | **完全相同** |

**唯一区别在声明区文本**：首行写 `FUNCTION_BLOCK <名字>` 而不是 `PROGRAM <名字>`，
并按需用 `VAR_INPUT` / `VAR_OUTPUT` / `VAR_IN_OUT` / `VAR` 分段。

```iecst
FUNCTION_BLOCK HC_ValveCtrl
VAR_INPUT
    xCmdLeft  : BOOL;
    rSetActTime : REAL;
END_VAR
VAR_OUTPUT
    xActiveLeft : BOOL;
    rActTimeLeft : REAL;
END_VAR
VAR
    fbActLeft : TON;      // FB 内部也能有实例
END_VAR
```

**实践含义**：想写 FB 里的 LD，**直接把 PROGRAM 的生成流程照搬**，只改声明区首行即可。
不需要改 TypeGuid、不需要额外字段。实测 `fb_LdLearnTest`（FUNCTION_BLOCK + TON + EXECUTE）
导入成功、双分类 0 错误、往返结构一致。

参考实现：`scripts/examples/make_ld_learn.py` 的 `build_pou()`（`DECL_FB` 与 `DECL_PRG` 只差声明文本）。

---

## ⚠ 线圈 / 输出引脚的 Operand 不带 `Name` 属性（实测证伪）

生成器里最容易写错的一处。`{c9b2f165}` Operand 节点的 `Name` 属性**分两种**：

| 位置 | 是否带 `Name` | 实测 |
|------|--------------|------|
| 触点 / 值引脚内部的 Operand | **带** `Name="Operand"` | `user_fixed.native` |
| 功能框 `Instance` | **带** `Name="Instance"` | `user_fixed.native` |
| **线圈**（`NETITEM.OutputItems`） | **不带**（`<Single Type="{c9b2f165}">`） | `user_fixed.native`、`fb_call_test.native` |
| **功能框输出引脚接线目标** | **不带** | `fb_call_test.native`（`xScInitOk`） |

**症状**：多写了 `Name="Operand"` 时，预编译 0 错误、编译 0 错误、图形显示正常——
**但导出往返会不一致**：IDE 导入时静默抹掉这个属性。只有逐节点 diff 才能发现。

**自检**：导入后再导出，与源文件做结构 diff，`Operand` 节点的 `Name` 属性对不上就是这个问题。

**对的是什么**：`coil()` / `out_operand()` 生成的 Operand 一律 `name=None`。
