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
        RValue {acfc6f68-...}  AND 框（BoxType="AND", CallType="And", IsBoxType="False"）
        OutputItems             可挂多个线圈
```

## 关键节点类型

| GUID | 含义 | 要点 |
|------|------|------|
| `{9873c309-1f09-4ebf-9078-42d8057ef11b}` | NETITEM（梯级） | |
| `{acfc6f68-8e3a-4af5-bf81-3dd512095a46}` | 功能框（AND/MOVE 等） | InputItems 槽位数必须 == InputParam 参数数 |
| `{9de7f100-1b87-424c-a62e-45b0cfc85ed2}` | 触点/引脚节点 | 外层 `IsContact` 决定身份：True=触点，False=值引脚 |
| `{c9b2f165-48a2-4a45-8326-3952d8a3d708}` | Operand 操作数 | 内含 Boolean/Flags/Operand/Type/IsCoil/SeriesIndex/Id |
| `{827b9ec2-2032-40da-9f4e-7670ca2d55a8}` | 并联分支组 | 内部 Trees 放多个支路节点，Mode=Sequential |
| `{505bff94-4c90-4e17-ac28-b8ac69d1b9e2}` | 连接器节点（支路输出接点） | 只有 Id 一个子节点；**完整支路必须有它** |
| `{5f9848d3-568d-4cc5-9e31-8e28e9607ff1}` | 连接器（带 Flags/Input） | |
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
4. 改 `MetaObject/Name` 与 `MetaObject/Guid`（新 uuid4）
5. `UniqueIdGenerator` 抬到最大 Id + 200
6. `ipc/import_args.json` 写 `{"path":..., "parent":"Application", "expect":[...]}`
7. `task_silent_import.py` 静默导入（父对象 `Application`，无同名 → 不弹框）
8. `task_check.py` 验证：**预编译 `217bc73e` 和编译 `97f48d64` 两个分类错误数都必须为 0**（只跑预编译会漏掉 AND 元数这类构建期错误）

可复用的生成器：`scripts/examples/make_packml_cmd_test.py`
