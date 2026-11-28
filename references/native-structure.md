# LD Native XML 结构与节点类型

> **阅读路径**：先看 §1~§4 摸清基础（GUID / 层级 / 节点类型 / 位掩码），
> 再按要画的元素跳到对应章节。带 ⚠ 的章节是踩过坑、有实测纠正的，**必读**。

## 目录

**基础**
- §1 语言 GUID（本机反射所得）
- §2 层级结构
- §3 关键节点类型
- §4 Operand 内部 Flags 位掩码

**元素标准结构**
- §5 单条件 rung：不要 AND 框，触点直挂 RValue ⚠
- §6 MOVE 框标准结构
- §7 功能框容器不对称规律 + MOVE 三形态
- §8 FUNCTION 调用框（CallType=Function）
- §9 功能块（FB）调用标准结构
- §10 挂载位置规则
- §11 ENO 引脚
- §12 Id 分配
- §13 OUT 操作数
- §14 NETITEM 的 Flags 位：整级输出取反
- §15 RValue 的类型可以是分支组本身
- §16 RValue 容器的完整值域
- §17 真实业务工程的全量结构普查（解析别人的工程先读这节）
- §18 触点取反位掩码与网络级字段
- §19 LD 文档级转换标志字段群
- §20 ⚠ 铁律：分支组的 Trees 必须有 ≥ 2 条支路
- §21 分支组 Input 槽的公共前缀
- §22 新建 POU 的完整流程
- §23 定时器功能框（TON）标准结构
- §24 EXECUTE 框：LD 内嵌 ST 代码块
- §25 FUNCTION_BLOCK 里的 LD 写法
- §26 ⚠ 线圈 / 输出引脚的 Operand 不带 Name 属性
- §27 轴控指令（HC_MovePtpV / HC_MovePtpR）
- §28 GVL（全局变量列表）与 Folder 的 native 结构

## 1 语言 GUID（本机反射所得）

- LD（梯形图）: `29148beb-8dd2-4bb8-8b77-ab9fe196c1ba`
- ST: `cc393387-a21c-4f68-a3e3-84c36951965d`
- FBD: `c2e2244b-c806-41b4-8ad3-7a0e25ce1393`

取法：`Activator.CreateInstance(ScriptImplementationLanguages).ladder`

## 2 层级结构

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

## 3 关键节点类型

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

## 4 Operand 内部 Flags 位掩码

| 值 | 含义 | 适用 |
|----|------|------|
| 0 | 无 | 常量引脚必须为 0 |
| 1 | NOT 取反 | 触点取反（常闭）；**值引脚残留此值必报错** |
| 2 | S 置位 | 线圈置位 |
| 3 | R 复位 | 线圈复位 |

## 5 单条件 rung：**不要 AND 框**，触点直挂 RValue（2026-11-25 实测纠正）

⚠ **本节曾写错，现已实测纠正。** 旧结论是「单条件必须补一个 TRUE 触点占位」，用户看图形后指出「TRUE 常开一直接通，相当于没加，多此一举」——**用户是对的**，正确做法是压根不建 AND 框。

### 三方对照实测（prg_SlotTest / prg_BareContactTest）

| 写法 | XML 形态 | 预编译 `217bc73e` 结果 |
|------|----------|------------------------|
| 2 槽 AND | `RValue=AND[触点, TRUE]` | ✅ 0 错误（模板既有写法，可用但不必要） |
| **1 槽 AND** | `RValue=AND[触点]` | ❌ `'AND'需要至少'2' 个操作数` + `检测到不一致元素 (不正确的输入序列)` |
| **裸触点直挂** | `RValue=触点{9de7f100}` | ✅ **0 错误**，往返导出结构完全保留 |

### 结论

- 「AND 框必须 ≥2 槽」约束的是**框**，不是 rung。
- 单条件 rung **不应该有框**：把触点节点直接作为 `NETITEM.RValue`。
- `RValue` 的合法值域实测为三种：功能框 `{acfc6f68}`、分支组 `{827b9ec2}`、连接器 `{5f9848d3}`，**外加裸触点 `{9de7f100}`**（此前误记为「RValue 不能是裸触点」）。

### 生成器写法

```python
# ✅ 正确：单条件直挂触点
netitem_box_rvalue(contact(u"xCond"), [coil(u"xOut")])

# ❌ 错误：1 槽 AND 框（预编译直接报错）
netitem_box_rvalue(and_box([contact(u"xCond")]), [coil(u"xOut")])

# ⚠ 可用但冗余：2 槽 AND + TRUE 占位（模板自带 70 处，但没必要学）
netitem_box_rvalue(and_box([contact(u"xCond"), contact(u"TRUE")]), [coil(u"xOut")])
```

> `netitem_box_rvalue` 只做「把第一个 `<Single Type="` 改成 `<Single Name="RValue" Type="`」，与节点类型无关，因此传触点也能用。

### 多条件 rung

条件 ≥2 时仍用 AND 框（`and_box([...])`），这是模板 429 个网络的主流形态（2 槽 18 处、4 槽 4 处、5 槽 6 处、6 槽 4 处、7 槽 2 处）。

> 详细报错对照见 [precompile-errors.md §2b](precompile-errors.md)。

## 6 MOVE 框标准结构（已验证预编译 0 错误）

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

## 7 功能框容器不对称规律 + MOVE 三形态（2026-11-25 全工程 126 个 POU 实测）

用 `scripts/ide/scan_all_native.py` 一键导出全工程所有对象后全量统计，得到两条**容器形态铁律**：

| 容器 | 形态 | 证据量 |
|---|---|---|
| `InputItems` | **`<List2 Name="InputItems">` 直接挂在框下**（框的直接子节点） | 全部 CallType × 557 个框 |
| `OutputItems` | **`<Single Name="OutputItems"><List2 Name="OutputItems">…</List2></Single>`**（Single 包一层 List2） | 全部 CallType × 557 个框 |

**两者不对称是常态，不是笔误**——解析时若用同一段代码取两者，会把 MOVE 的 InputItems 数成 0（实测踩坑：先按 `Single>List2` 解析，MOVE 的 EN+IN 两槽被数成 0 槽，还误判文档写错了）。

### MOVE 框的三种合法形态

| 形态 | InputParam.Names | InputItems 内容 | 出处 |
|---|---|---|---|
| **标准**（自己生成用这种） | `[EN, IN]` | 2 槽：槽0=AND 框（或触点），槽1=IN 值引脚 | 用户手改验证、模板导出 133 处 |
| **多槽触点链** | `[EN, IN]` | 6~8 槽：槽0=TRUE 触点，槽1..N-2=条件触点（EN 直接串联，无显式 AND 框），槽末=IN 常量（如 `7`） | `dump_155228.native` 段2 状态机（Id=60263） |
| **嵌套框接 EN** | `[EN]`（**只有 1 个参数，无 IN！**） | 2 槽：槽0=**另一个功能框**（如 `PackMLUnitManager`，13 槽 FB），槽1=IN 值引脚（如 `PML0.stCmd.stSc`） | `scan_063_Main.native`（Id=591，7 处） |

**⚠ 豁免规则（check_slots 必须放行）**：`InputParam=['EN']` 但 `InputItems` 有 2 槽——槽 0 是嵌套框 `{acfc6f68}` 时，前一个框的 ENO 输出直接作为本框的 EN 输入（EN/ENO 链式调用）。同理**多槽触点链形态**（槽 0 是触点、槽 > 2、末槽是 IN 常量）也合法。这两种 IDE 原生形态下「输入槽 == InputParam 数」断言**不成立是正常的**，否则 IDE 模板原生 POU 全部误报。

### 批量导出全工程（scan_all_native.py，2026-11-25 新增）

`scripts/ide/scan_all_native.py`（IDE 内 eval_file 执行）：递归遍历
`proj.active_application` 全部后代对象，凡能 `export_native` 的都导出为
`<IPC>/scan_<序号>_<名字>.native`，空壳（<200 字节，folder 等）自动删除。
本次实测导出 **126 个对象**（含 Library Manager / Symbols / Trace 等工程级对象）。

用途：①学习时**批量扫描未知 BoxType**（`glob('scan_*.native')` 一把梭）；
②回归对比（新生成结构与模板原生 POU 同场跑 check_slots）。

## 8 FUNCTION 调用框（CallType=Function，2026-11-25 全工程实测）

**函数（有返回值）在 LD 里的调用框**，全工程 35 处（EtcStatusV2 / EventRecordV2 /
PackMLSCCmdSum / PackMLConfiguer / PackMLScCmdInit）。与 FB 框的关键差异：

- **核心规律：`OutputItems[i]` 与 `OutputParam.Names[i]` 严格按索引一一对应**（35/35 实测）
- `[0]` ↔ `ENO`：未接 ENO 线时为 `<Null/>`
- `[1]` ↔ **`OutputParam.Names` 索引 1 恒为空字符串**（35/35）＝**函数返回值槽**，
  `Types[1]` 是返回类型（如 BOOL）。接住返回值＝在 `[1]` 放操作数
  （`Operand=xScInitOk`、`LValue=True`）——已在 `prg_FbCallTest`（自建 POU）实测验证
- `[2..]` ↔ 其余 `VAR_OUTPUT` 参数
- **Instance.Operand 必须是 `<Null/>`**（三态规律，同 Action/Program）
- **`InputItems` 槽位数 == `InputParam` 参数个数**（35/35 等长，含 EN 槽——与 FB 框一致，
  槽0=连接器、槽1..n=参数引脚）。⚠ 教训：统计时若用 `find("Single[@Name='InputItems']")`
  解析会**踩容器不对称坑**——InputItems 是 `List2` 直接挂、不在 `Single` 里，
  find 不到返回 0，会得出「恒为空」的**错误结论**（实测翻过车，复核后已修正）
- 未接线的输出槽写 `<Null/>`，接线的写 `Operand` 操作数（`LValue=True`）
- **端到端验证（prg_FuncRetTest，2026-11-25）**：生成器 `examples/make_func_return_test.py`
  生成两个 Function 框（PackMLScCmdInit 最简形态 + PackMLSCCmdSum 带 VAR_OUTPUT 尾参），
  导入后**双分类 0 错误**，往返导出结构保持：`[0]=Null(ENO)`、`[1]=返回值变量`、`[2]=VAR_OUTPUT`，
  索引严格一一对应
- ⚠ **REF 形参类型不可当本地声明用**：`PackMLSCCmdSum` 的 `stSum` 形参类型是
  `sUnitScCmd[REF]`，但本 POU 声明 `stSumTest : sUnitScCmd` 会预编译报
  「没有定义标识符」——`sUnitScCmd` 不是简单可见名。照模板 `act90_ScCmd` 的接法
  **直接接工程全局实例成员**（`PML0.stCmd.stSc`），不要自己声明局部变量
  （`PML0` 是全局实例，check_symbols 需加 `PLC_GLOBAL_SYMBOLS=Master,PML0` 白名单）

## 9 功能块（FB）调用标准结构（act04 / act90 实测，2026-11-25）

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

## 10 挂载位置规则

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
- **线圈的载体只有两种**：NETITEM（`{9873c309}`）的 `OutputItems`，或触点 PIN（`{9de7f100}`）的 `OutputItems`。**挂到功能框（`{acfc6f68}`，如 AND 框）的 `OutputItems` 上，IDE 只画一个空占位小方块**，预编译 / 编译仍然是 0 错误（2026-11-27 实测；A00 语料分布：NETITEM 15 处 / 触点 PIN 5 处 / 功能框 0 处）。生成器用 `netitem(条件, [线圈...])` 包一层。
- 分支组的 `Input` 槽可放一个公共前缀触点（如 `TRUE`），实现「公共条件只画一次 + 竖线分叉」

## 11 ENO 引脚

- 功能框的 `ENO` 是一个 `Single Name="ENO" Type="bool">True` 节点，表示该框的 ENO 输出已启用/接线
- **功能链末端的框可以删掉 `ENO` 节点**（不往后连接），实测预编译 0 错误
- 中间框若需串接到下一框，保留 `ENO`

## 12 Id 分配

- 全部唯一；`UniqueIdGenerator` 需 ≥ 最大 Id（建议 +100 余量）

## 13 OUT 操作数

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

## 14 NETITEM 的 Flags 位：整级输出取反

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

## 15 RValue 的类型可以是分支组本身

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

## 16 RValue 容器的完整值域（2026-11-25 全工程 127 对象扫描）

NETITEM 的 `RValue` 字段首节点形态统计（143 处，全工程实测）：

| RValue 首节点形态 | 处数 | 含义 |
|---|---|---|
| `Null` | 69 | 空条件（占位） |
| 功能框 `{acfc6f68}` | 52 | AND 框/其他框直接当条件 |
| 容器 `{5f9848d3}`（内含分支组/连接器 EN、ENO、Input） | ~17 | 单条件容器（分支组时见下） |
| 分支组 `{827b9ec2}` 作为容器 Input | 6 | 分支组嵌进容器 |
| 触点 `{9de7f100}` 作为容器 Input | 4 | 单触点直接当条件 |

**要点**：功能框是最常见的 RValue 形态（52 处）——NETITEM 条件直接放 AND/比较框，
不一定先包 `{5f9848d3}` 容器。生成时保持现有「AND 框当 RValue」写法即可。

## 17 真实业务工程的全量结构普查（2026-11-25「除油倒盘-擦拭机-PLCV20261124」实测）

前面各节来自小样本 + 手写骨架。本节是对一个**真实产线工程**（403 对象 / 400 个
export entry / 5804 个功能框 / 940 个分支组）逐字段统计的结果，用来校正「小样本
推出来的一般规律」。**遇到与本节冲突的旧结论，以本节为准。**

复现脚本：`scripts/examples/make_repro_study.py`（生成 `prg_ReproStudy`，9 个网络，
实测预编译 0 错误、编译无新增错误、往返导出结构签名逐行一致）。

### ① NetworkItems 的直接子节点：分支组是主流，不是 NETITEM

| NetworkItems 直接子节点 | 网络数 |
|---|---|
| **分支组 `{827b9ec2}`** | **679** |
| 空（无内容） | 540 |
| AND 框 | 55 |
| FB 调用框（FB_StepLogger 等） | 20+ |
| **NETITEM** | **仅 18** |
| MOVE 框 | 11 |
| EXECUTE 框 | 4 |

**结论：真实程序里 `NetworkItems → 分支组 → Trees` 才是主结构**，`NETITEM` 直挂只是
少数写法（18/1330）。生成复杂逻辑时优先用「分支组 + Trees」，不要把一切都塞进 NETITEM。

### ② 分支组 `{827b9ec2}` 的完整字段

```
Single {827b9ec2}            ← 注意：Input 有 Name 属性，不能漏写
  ├─ Input     : 可为 <Null/> 或任意图形节点（触点/比较框/AND/TON/嵌套分支组）
  ├─ List2 Trees : 2~17 条（实测分布：2 条 462、3 条 341、4 条 99、5 条 24、
  │                6 条 21、9 条 21、7/8 条各 6、10 条 7、17 条 3）
  ├─ Mode      : 恒为 "Sequential"（990/990，无第二种取值）
  └─ Id
```

- **`Mode` 只有 `Sequential`**：不要发明 `Parallel` 等值。
- **`Trees` 长度 ≥ 2**（与「分支组必须 ≥2 支路」铁律一致）。
- **`Input` 实测取值分布**：`EQ` 614、`PIN` 191、`AND` 49、`Null` 45、`BRANCH` 37、
  `GT` 16、`TON` 13、`GE` 13、`LT` 11、`FIND` 1 —— 比较框当公共前缀最常见。
- **`Trees` 元素类型**：可以是 `NETITEM`、`AND` 框、`PIN`（裸触点）、嵌套 `BRANCH`。
  最常见组合是 `[AND, AND]`（222）、`[AND, AND, AND]`（218）、`[AND, NETITEM]`（55）。

### ③ `InputFlags`：只有部分框是 `List2`，其余是 `Null`

这是旧文档完全没记的字段。统计（按 BoxType）：

| BoxType | InputFlags 形态 | 处数 |
|---|---|---|
| FC_AxisAbsGo | `List2`（长度 = 槽数） | 500 |
| FC_CylinderExe | `List2` | 236 |
| **ADD** | **`List2`** | 24（另有 6 处 `Null`） |
| **LE** | **`List2`** | 13（另有 4 处 `Null`） |
| AND / MOVE / EQ / GT / LT / GE / TON / EXECUTE / 全部 FB_xxx | `Null` | — |

`List2` 每项是一个 Flags 块（`Extensible/Fixed/Flags`）。**ADD 实测值**：

```
InputFlags = [ (Flags=16, Fixed=True), (Flags=0, Fixed=False), (Flags=0, Fixed=False) ]
```

**⚠ 修正旧结论（2026-11-27 二次修正）**：

- 第一次修正推翻了「`Flags=16` = S/R 线圈专用」：NETITEM 级 `Flags=0` 的 S/R 线圈有
  306 处（置位 179 + 复位 127），`Flags=16` 只有 7 处。**与 S/R 线圈无关。**
- 但当时把 16 解释成「该引脚是电源流引脚」**也是错的**。决定性证据来自用户手工操作：
  同一个 POU 里普通 MOVE 的 `InputFlags` 是 `<Null/>`，用户在 EN 上点了一下「边沿检测」
  之后同一个 MOVE 变成 `InputFlags=[(Flags=16, Fixed=True), (Flags=0, Fixed=False)]`
  ——**唯一变量就是边沿**。
- 正确含义：**`InputFlags[i].Flags = 16` = 第 i 个输入引脚启用了边沿检测**（梯形图里画成
  引脚上的 `↑`）。`Fixed=True` 是随之而来的（该引脚不再可固定为常通）。

**因此：框的边沿不是靠触点实现的，而是靠框自己的 `InputFlags`。**
完整规则、XML 形态、生成函数与验证链见 [`edge-detection.md`](edge-detection.md)。

### ④ 比较框（EQ/NE/GT/LT/GE/LE）：3 槽，但 InputParam 只有 1 个名字

```
InputParam  = Names=['EN']  Types=['BOOL']
OutputParam = Names=['']    Types=['BOOL']
InputItems  = 3 槽  ← 槽0=EN 触点，槽1=左操作数，槽2=右操作数
OutputItems = 1 项（<Null/>）
EN=True  ENO=False  IsBoxType=True  CallType=Eq/Ne/Gt/Lt/Ge/Le
Instance.Operand = <Null/>
```

**⚠ 不要按 `len(InputItems) == len(InputParam)` 校验比较框**——模板里 `InputParam`
只有 1 个名字却有 3 个槽。`check_slots.py` 对比较框要放行。

**比较框可以嵌套比较框**：`LT` 的槽0 可以是 `GE` 框（实测 32 处 `['BOX:GE','PIN','PIN']`）。
此时槽0 不是触点而是框。

### ⑤ `{505bff94}` 空占位的真实位置

```
<Single Type="{505bff94-4c90-4e17-ac28-b8ac69d1b9e2}" Method="IArchivable">
  <Single Name="Id" Type="long">###</Single>
</Single>
```

- **只出现在 `List2/InputItems` 的槽位 1（共 2 槽）**，紧跟一个功能框
  （MOVE / FC_AxisAbsGo / FC_CylinderExe / EXECUTE / ADD / TON / DELETE / FB_xxx）。
- 2205 处，形态恒定（只有 `Id` 一个子节点，**没有 Flags、没有 Name 属性**）。
- **⚠ 旧结论「分支组 Trees 内 1908 处」未经核实**：本轮只确认了 AND 框 InputItems 槽1
  这一种位置。分支组内的出现需另行验证，不要照抄。

### ⑥ `Instance.Operand` 与 `Instance.Type` 必须成对正确

| 框类 | Instance.Operand | Instance.Type |
|---|---|---|
| FunctionBlock（TON / FB_xxx） | `<Single Type="string">实例名</Single>` | `<Single Type="string">TON</Single>`（= BoxType） |
| 其余全部（AND/MOVE/EQ/GT/LT/GE/ADD/EXECUTE/FC_xxx/FIND/DELETE） | `<Null/>` | `<Single Type="string"></Single>`（空） |

**⚠ 血泪教训（本轮实测）**：给 TON 写 `Instance.Type` 为空时，`import_native` 抛
**「已标识项中有一项的格式无效。」**，并且该错误是**模态弹窗**——它会阻塞 IDE 主线程，
守护进程心跳停止、`bridge.py` 全部超时。必须人工点掉「确定」才能恢复。
**造 FB 类框时 `Instance.Type` 必须填 BoxType 名。**

### ⑦ 框级 `Flags.Fixed` 的真实分布

| 框 | Fixed |
|---|---|
| AND | False（恒定） |
| TON | **两种都有**（True 27 / False 20，均合法） |
| MOVE / 比较框 / ADD | True |
| Action / Function / FB / Program | True |

**⚠ 修正旧结论**：旧文档写「TON 是仅有的两个 Fixed=False 的框之一」。实测 TON
True/False 各占一半，**不存在「必须 False」**。取 True 不会多画空引脚，更安全。

### ⑧ TON 框实测（47 处）

```
CallType=FunctionBlock  EN=False  ENO=False
Instance.Operand = 实例名（TON_0 / TON_1 / ... 全部有值）
Instance.Type    = "TON"
InputParam  = ['IN','PT']   Types=['BOOL','TIME']
OutputParam = ['Q','ET']    Types=['BOOL','TIME']   ← 没有 ENO
InputItems  = 2 槽（IN 的电源流 + PT 时间值）
OutputItems = 2 项，未接线时两项都是 <Null/>
```

**⚠ TON 的 OutputItems 不能套「第 0 项恒为 ENO 空位」**——它压根没有 ENO 参数。

### ⑨ ADD / MOVE 实测字段

```
ADD : CallType=Add  EN=True ENO=True IsBoxType=True Fixed=True
      InputParam=['EN']  OutputParam=['ENO','']
      InputItems=[CONN, PIN, PIN]  OutputItems=[Null, OPERAND]
      InputFlags=List2[(16,True),(0,False),(0,False)]

MOVE: CallType=Move EN=True ENO=True IsBoxType=True Fixed=True
      InputParam=['EN']  OutputParam=['ENO','']
      InputItems=[CONN, PIN]  OutputItems=[Null, OPERAND]
      InputFlags=Null
```

### ⑩ `Implementation` 的 TypeGuid

`Implementation` 节点的 `Type` **属性**（不是子元素文本）区分实现语言：

| TypeGuid | 语言 | 处数 |
|---|---|---|
| `{3b83b776-fb25-43b8-99f2-3c507c9143fc}` | ST 文本实现 | 88 |
| `{25e509de-...}` | LD 网络列表实现 | 52 |

### ⑪ POU 对象的 TypeGuid 语义表（`MetaObject` 的 `TypeGuid` 字段）

| TypeGuid 前 8 位 | 含义 | 数量 |
|---|---|---|
| `b53c14ea` | Network 占位 | 159 |
| `6f9dac99` | FUNCTION_BLOCK | 85 |
| `2db5746d` | Struct / Enum | 54 |
| `8ac092e5` | PROGRAM / ACTION | 46 |
| `738bea1e` | Folder | 24 |
| `c3fc9989` | Check 函数 | 9 |
| `ffbfa93a` | GVL | 8 |
| `98a2708a` | Task（MainTask/ETHERCAT） | 2 |
| `ad3ae438` | AxesGroup | 2 |
| `f7aa3620` | Trace | 2 |

### ⑫ 导出 XML 的真实层级（解析别人工程时必读）

```
ExportFile
 └ StructuredView
    └ Single
       └ List2 (EntryList)
          └ Single (一个 entry)
             ├ Single Name="Name"      ← 对象名
             ├ Single Name="Object"    ← ★对象本体在这里（不是标签名 "Object"！）
             └ Single Name="MetaObject"
                └ Single Name="TypeGuid"  ← ★对象类型 GUID 在这里
```

**⚠ 两个极易踩的读取 bug**（本轮修正了 4 个旧扫描脚本）：
1. **`Object` 是 `Name` 属性值，不是标签名**。`root.iter('Object')` 永远取不到东西。
2. **`InputItems` 本身就是 `<List2>`**（取槽直接 `list(node)`）；
   **`OutputItems` 是 `<Single>` 里再包一层 `<List2>`**（要先找子 `List2`）。
   容器不对称，读的时候必须分别处理。
3. `NETITEM` 节点**没有 `Name` 属性**，只能按 `Type="{9873c309...}"` 识别。
4. `Flags` 是 `<Single Name="Flags">` 里再嵌 `<Single Name="Flags" Type="int">N`
   —— **取数值要取两层**。

## 18 触点取反位掩码与网络级字段（2026-11-25 全工程实测补充）

- **触点 `Operand.Flags.Flags` 值域 = 0 / 1 / 16**（1295 处 =0 正开、62 处 =1 常闭取反、
  29 处 =16 电源流引脚）——**没有边沿语义**。旧版这里写的「值域仅 0/1」与「边沿检测要用
  R_TRIG/F_TRIG FB」**两句都不成立**：触点 Flags 还有 16；边沿是框内建能力（见上文 §③ 与
  [`edge-detection.md`](edge-detection.md)），不需要 R_TRIG/F_TRIG，也不要用触点去模拟。
  把触点 Flags 改成 2 时 IDE **不报错、原样保留**，但图形上没有边沿、行为上也不产生边沿
  ——这是最隐蔽的一类写错（详见该文「误区二」）。
- **网络级 `Connectors` / `ILLines` 恒空**（429 个网络全空）——LD 生成时写空 List2 即可，
  不要往里塞东西（这两者是 FBD/IL 视图的残留字段）
- **值引脚常量类型**：`IsContact=False` 的引脚 `Type` 可为 BOOL/UINT/INT/TIME/
  RTS_SYSTIMEDATE/结构体名等（306 处 BOOL 最常见）；`Boolean` 字段：BOOL 常量 True 时
  为 True（307 处），其余为 False——生成常量引脚时 BOOL 用 `Boolean=True`，
  数值/时间型用 `Boolean=False` + `Type=INT/UINT/TIME`

## 19 LD 文档级转换标志字段群（2026-11-25 全工程实测）

每个 LD `NetworkList` 所在的文档节点（`{25e509de...}` Implementation 容器内）还带
一批**转换标志字段**（127 对象 × 恒定值；`user_fixed.native` 骨架已含，生成器不用管）：

| 字段 | 恒定值 | 含义推测 |
|---|---|---|
| `DefaultViewMode` | `Ld` | 默认视图 LD |
| `CodesysLDConverted` / `CodesysLDConverted1` | `True` | CODESYS LD 转换标志 |
| `AssigmentToBranched` / `BoxWithoutInputsConverted` / `_executeIdsRepaired` / `DemuxToParalleled` | `True` | 各类拓扑修复标志 |
| `BoxTreeSymbolInfoUpdated` | `False` | 符号信息更新标志 |
| `ValidIds` | `True` | Id 有效性 |
| `BranchCounter` | `0` | 分支计数器 |
| `NetworkListComment` | 空 | 网络列表注释 |

**生成新 POU 不需要写这些字段**——骨架 `user_fixed.native` 已带，改 NetworkList/TextLines
时不碰它们。列在这里是为了：读别人工程时知道这些字段是**文档级元数据**，别当网络内容解析。

## 20 ⚠ 铁律：分支组的 Trees 必须有 ≥ 2 条支路

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

## 21 分支组 Input 槽的公共前缀

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

## 22 新建 POU 的完整流程（实测通过）

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

## 23 定时器功能框（TON）标准结构（act05 / HC_ValveCtrl 实测，2026-11-25）

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

## 24 EXECUTE 框：LD 内嵌 ST 代码块（HC_ValveCtrl 网络9 实测，2026-11-25）

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

## 25 FUNCTION_BLOCK 里的 LD 写法（HC_ValveCtrl 实测，2026-11-25）

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

## 26 ⚠ 线圈 / 输出引脚的 Operand 不带 `Name` 属性（实测证伪）

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

---

## 27 轴控指令（InoPack HC_MovePtpV / HC_MovePtpR 实测，2026-11-25）

InoPack 模板的轴控封装是**两层结构**：

```
① 轴控 FB（HC_MovePtpV / HC_MovePtpR）—— 内部用 ST 写，8~9 个 action 各管一种运动
② 调用点（act0_Ptp）—— 用 LD 里的功能框调 ①
```

**轴控指令（MC_Power / MC_MoveAbsolute / MC_MoveRelative / MC_Stop / MC_Halt /
MC_SetPosition / MC_Reset / HMC_MoveVelocity / HMC_MoveJog / HMC_Home）全部写在
FB 内部的 ST 里**，LD 里只出现「调用封装好的 FB」这一个框。所以 LD native 里
**没有 MC_xxx 的功能框**——想在 LD 里画运动指令框是走不通的。

### 两种轴类型（虚轴 vs 实轴）

| 封装 FB | 轴变量类型 | 用途 |
|---|---|---|
| `HC_MovePtpV` | `AXIS_REF_SM3` | **虚轴**点位控制（仿真/无实驱） |
| `HC_MovePtpR` | `AXIS_REF_ETC_DS402_CS` | **实轴**点位控制（EtherCAT DS402 伺服） |

两个 FB 的接口形态一致，区别在轴类型和实轴多出来的 `Servo : ETCSlave` 引脚、
`actHome` / `actHalt` / `Srch` 三个额外 action。

### `HC_MovePtpV` 声明区（可直接抄的骨架）

```pascal
FUNCTION_BLOCK HC_MovePtpV
VAR_INPUT
    {attribute 'hide'}
    wsName:         WSTRING := "";        // 伺服名称
    {attribute 'hide'}
    xSafety:        BOOL := TRUE;         // TRUE = 安全条件满足
    xCondition :    BOOL;                 // TRUE = 动作条件满足
END_VAR
VAR_OUTPUT
END_VAR
VAR_IN_OUT
    stInfo :        HC_sPtpInfo;          // PLC 数据接口（命令 + 状态）
    VirtualAxis:    AXIS_REF_SM3;         // 轴引用（VAR_IN_OUT，不是 VAR）
END_VAR
VAR
    fbSetPosition:  MC_SetPosition;
    fbRelative:     MC_MoveRelative;
    fbPower:        MC_Power;
    fbStop:         MC_Stop;
    fbReset:        MC_Reset;
    fbAbsolute:     MC_MoveAbsolute;
    fbVelocity:     HMC_MoveVelocity;
    fbJog:          HMC_MoveJog;
    fSetVel  :      LREAL;
    fSetAcc  :      LREAL;
    fSetDec  :      LREAL;
    fSetJerk :      LREAL;
    fSetMaxDec :    LREAL;
    fSetMaxJerk :   LREAL;
    xPtpCond :      BOOL;                 // 运动条件满足
END_VAR
```

**要点**：
- 轴引用必须放 `VAR_IN_OUT`（`AXIS_REF_SM3` 是结构体，放 `VAR_INPUT` 会复制一份，指令不动真实轴）
- 每个运动指令一个**独立的 FB 实例**（`fbPower` / `fbStop` / ... 各自一个），不能共用一个
- 实轴版 `HC_MovePtpR` 用 `ARRAY [0..1] OF MC_MoveAbsolute` 这类**实例数组**，支持双通道（示教 + 定位并行）

### 8 个轴控指令的标准调用写法（ST，全部带形参）

模板一律用「实例名(形参 := 值, 输出 => 变量);」的**标准形参调用**，不用赋值方式。

```pascal
// ① 使能 —— MC_Power（注意是 bRegulatorOn / bDriveStart 两个 BOOL，不是 Enable）
fbPower(
    Axis:=              VirtualAxis,
    Enable:=            TRUE,
    bRegulatorOn:=      stInfo.xCmdPwr,
    bDriveStart:=       stInfo.xCmdPwr,
    Status=>            stInfo.xStsPwrDone,
    Error=>             stInfo.xStsPwrError);

// ② 快速停止 —— MC_Stop（Deceleration / Jerk 是必填）
fbStop(
    Axis:=              VirtualAxis,
    Execute:=           stInfo.xCmdStop OR (NOT xPtpCond AND stInfo.xStsPtpActive),
    Deceleration:=      fSetMaxDec,
    Jerk:=              fSetMaxJerk,
    Done=>              stInfo.xStsStopDone,
    Error=>             stInfo.xStsStopError,
    Busy=>              stInfo.xStsStopBusy);

// ③ 绝对定位 —— MC_MoveAbsolute（Direction 用 MC_Direction 枚举）
fbAbsolute(
    Axis:=              VirtualAxis,
    Execute:=           stInfo.xCmdAbs,
    Position:=          stInfo.fSetPos,
    Velocity:=          fSetVel,
    Acceleration:=      fSetAcc,
    Deceleration:=      fSetDec,
    Jerk:=              fSetJerk,
    Direction:=         stInfo.eSetDir,
    CommandAborted=>    stInfo.xStsAbsAborted,
    Error=>             stInfo.xStsAbsError,
    Busy=>              stInfo.xStsAbsBusy,
    Done=>              stInfo.xStsAbsDone);

// ④ 相对定位 —— MC_MoveRelative（Distance 而不是 Position）
fbRelative(
    Axis:=              VirtualAxis,
    Execute:=           stInfo.xCmdRel,
    Distance:=          stInfo.fSetDist,
    Velocity:=          fSetVel,
    Acceleration:=      fSetAcc,
    Deceleration:=      fSetDec,
    Jerk:=              fSetJerk,
    CommandAborted=>    stInfo.xStsRelAborted,
    Error=>             stInfo.xStsRelError,
    Busy=>              stInfo.xStsRelBusy,
    Done=>              stInfo.xStsRelDone);

// ⑤ 设置轴位置 —— MC_SetPosition（Mode=FALSE 表示相对当前位置偏移）
fbSetPosition(
    Axis:=              VirtualAxis,
    Execute:=           stInfo.xCmdSetPos,
    Position:=          stInfo.fSetHPos,
    Mode:=              FALSE,
    Error=>             stInfo.xStsSetPosError,
    Busy=>              stInfo.xStsSetPosBusy,
    Done=>              stInfo.xStsSetPosDone);

// ⑥ 故障复位 —— MC_Reset（Execute 要防抖：已 Done/Error 且轴仍故障时才允许再次触发）
fbReset(
    Axis:=              VirtualAxis,
    Execute:=           stInfo.xCmdReset AND NOT ((fbReset.Done OR fbReset.Error)
                            AND (VirtualAxis.nAxisState=1)),
    Error=>             stInfo.xStsResetError,
    Busy=>              stInfo.xStsResetBusy,
    Done=>              stInfo.xStsResetDone);

// ⑦ 恒速 —— HMC_MoveVelocity（汇川扩展，形参是小写 f 开头，不是标准 MC 的大写）
fbVelocity(
    Axis:=              VirtualAxis,
    xEnable:=           stInfo.xCmdVel OR fbVelocity.xBusy,
    fVelocity:=         fSetVel,
    fAcceleration:=     fSetAcc,
    fDeceleration:=     fSetDec,
    fJerk:=             fSetJerk,
    eDirection:=        stInfo.eSetDir,
    xAborted=>          stInfo.xStsVelAborted,
    xError=>            stInfo.xStsVelError,
    xBusy=>             stInfo.xStsVelBusy,
    xInVelocity=>       stInfo.xStsVelDone);

// ⑧ 点动 —— HMC_MoveJog（汇川扩展，正/反两个 BOOL 同时给）
fbJog(
    Axis:=              VirtualAxis,
    xJogForward:=       stInfo.xCmdJogFor,
    xJogBackward:=      stInfo.xCmdJogBack,
    fVelocity:=         fSetVel,
    fAcceleration:=     fSetAcc,
    fDeceleration:=     fSetDec,
    fJerk:=             fSetJerk,
    xAborted=>          stInfo.xStsJogAborted,
    xBusy=>             stInfo.xStsJogBusy,
    xError=>            stInfo.xStsJogError);
```

**关键差异（标准 MC vs 汇川 HMC）**：

| 指令 | 形参风格 | 差异 |
|---|---|---|
| `MC_Power` | 大写 `Enable/bRegulatorOn/bDriveStart` | 标准库 |
| `MC_MoveAbsolute` / `MC_MoveRelative` / `MC_Stop` / `MC_Halt` / `MC_SetPosition` / `MC_Reset` | 大写 `Axis/Execute/Velocity/...` | 标准库，输出 `Done/Error/Busy/CommandAborted` |
| `HMC_MoveVelocity` | **小写** `xEnable/fVelocity/fAcceleration/...` | 汇川扩展，输出 `xBusy/xError/xInVelocity/xAborted` |
| `HMC_MoveJog` | **小写** `xJogForward/xJogBackward/fVelocity/...` | 汇川扩展，无 `Execute`，靠两个 BOOL 电平控制 |
| `HMC_Home` | 小写 `xHomeType/uiHomeMode/fHmoeVelocity/...` | 注意模板里 `fHmoeVelocity` 是**拼写错误**（原样如此），照抄才不会编译报错 |

⚠ **`HMC_Home` 的形参名 `fHmoeVelocity` 是 InoPack 的原始拼写错误**（Home 拼成 Hmoe）。
这是库里的真实名字，不是笔误——写 `fHomeVelocity` 会编译报错。

### 错误码统一收集

每个指令后面都跟一段错误码归集，模板统一写到 `stInfo.eStsFbErrorID`（类型 `HMC_ERROR`）：

```pascal
IF stInfo.xStsAbsError THEN
    stInfo.eStsFbErrorID := UINT_TO_DWORD(fbAbsolute.ErrorID);
END_IF
```

注意标准 MC 的 `ErrorID` 是 `UINT`，要 `UINT_TO_DWORD` 转；`HMC_` 系列的 `eErrorID`
本身已是 `HMC_ERROR` 类型，直接赋（`fbVelocity.eErrorID`），不用转。

### 轴状态读法（不靠指令，直接读轴结构体）

```pascal
stInfo.fStsAxisPos      := VirtualAxis.fSetPosition;      // 实时位置
stInfo.fStsAxisVel      := VirtualAxis.fSetVelocity;      // 实时速度
stInfo.fStsAxisTrq      := VirtualAxis.fActTorque;        // 实时力矩
stInfo.xStsAxisBusy     := VirtualAxis.nAxisState > 3
                           OR (VirtualAxis.nAxisState = 2 AND VirtualAxis.fSetVelocity <> 0);
stInfo.xStsAxisStandstill := VirtualAxis.nAxisState = 3
                           OR (VirtualAxis.nAxisState = 2 AND VirtualAxis.fSetVelocity = 0);
stInfo.xStsAxisError    := VirtualAxis.nAxisState = 1;    // 1 = 故障
stInfo.eStsAxisState    := VirtualAxis.nAxisState;        // SMC_AXIS_STATE 枚举
stInfo.pStsAxis         := ADR(VirtualAxis);              // 轴指针（POINTER TO AXIS_REF_SM3）
```

`nAxisState` 取值：`1`=故障、`2`=待机/静止、`3`=停止、`>3`=运行中。

### 轴控 FB 在 LD 里的调用写法（act0_Ptp 实测）

```
BoxType      = HC_MovePtpV
CallType     = FunctionBlock
Instance.Operand = fbPtpV[0]              ← FB 实例（数组元素）
Instance.Type    = HC_MovePtpV

InputParam.Names = ['EN', 'xCondition', 'stInfo', 'VirtualAxis']
InputParam.Types = ['BOOL', 'BOOL', 'HC_sPtpInfo[REF]', 'AXIS_REF_SM3[REF]']
                    ↑ REF 形参在 Types 里带 [REF] 后缀

InputItems (4 槽 = 4 个参数)
  [0] 连接器 {5f9848d3}  Input=Null        ← EN
  [1] 引脚 {9de7f100}    Operand='IO.xEmergencyStop'   Type=BOOL
  [2] 引脚               Operand='EM0.astPtpV[0]'      Type=HC_sPtpInfo
  [3] 引脚               Operand='Master'              Type=AXIS_REF_SM3

OutputParam.Names = ['ENO']   OutputItems = 1 项 <Null/>
EN = True   ENO = True
```

**关键**：`AXIS_REF_SM3[REF]` 引脚的操作数直接写**轴名**（`Master`），
`Type` 写 `AXIS_REF_SM3`（去掉 `[REF]` 后缀）。引脚 `IsContact=False`。

### `CallType = Action`（全新取值，本轮首次发现）

调用 POU 内的 action 时用这个 CallType：

```
BoxType   = act0_Ptp        ← action 的名字
CallType  = Action          ← 之前只记录过 And/Function/Program/FunctionBlock/None
EN/ENO    = True / True
InputParam.Names  = ['EN']
InputParam.Types  = ['BOOL']
InputItems        = 1 槽（连接器）
OutputParam.Names = ['ENO']
OutputItems       = 1 项 <Null/>
Instance.Operand  = <Null/>   ← ⚠ 必须是 Null，不是空 Single！
Instance.Type     = ''        ← 类型名是空串（<Single Name="Type" Type="string" />）
IsBoxType         = True
```

**⚠⚠ `Action` 调用的 `Instance.Operand` 必须是 `<Null Name="Operand" />`。**

> **纠正错误结论（2026-11-25）**：本文原写「Action 的 `Instance.Operand` 是空字符串
> `<Single Name="Operand" Type="string"></Single>`，不是 `<Null/>`」——**这是错的**。
> 该结论是从「自己导入后再导出的文件」里反推出来的，属于**循环论证**：IDE 把自己
> 写进去的空 `<Single>` 原样导出，于是"验证"通过，实际从没对照过真实模板。
> 对照 InoPack 真实模板的 **16 个 Action 框，全部是 `<Null Name="Operand" />`**。
>
> **写错的现象**：IDE 会在该框**上方多画一个红框的、可填写参数的小方框**。
> 用户两次反馈：「正常调用没有这个小方块」「actAbs_NOPE 上面还是有小方框可以
> 填写参数」——后一句是关键，`actAbs_NOPE` 是故意写的**不存在的** BoxType，它也
> 有方框，说明方框与 BoxType 合法性、与 `Flags.Fixed` **都无关**，纯粹是
> `Operand` 节点形态问题。

**`Instance.Operand` 三态规律（按 `CallType` 决定，0 例外）**：

| CallType | `Instance.Operand` | 说明 |
|---|---|---|
| `FunctionBlock` | `<Single Type="string">实例名</Single>` | 如 `fbPtpV[0]`、`afbCylCtrl[0]` |
| `Action` | `<Null Name="Operand" />` | 只有 EN/ENO |
| `Function` | `<Null Name="Operand" />` | 无实例 |
| `Program` | `<Null Name="Operand" />` | 无实例 |
| `And` | `<Null Name="Operand" />` | |
| `Move` | `<Null Name="Operand" />` | |

**只有 FB 才需要实例名**，其余一律 `Null`。写成空 `<Single>` 就会多画一个小方框，
而**预编译、编译、往返 diff 三关全部通过**——只能靠人眼看图形或静态断言发现。

### 轴控数据结构

| 结构 | 作用 | 关键字段 |
|---|---|---|
| `HC_sPtpInfo` | **PLC 侧**命令 + 状态（程序用） | `xCmdPwr/xCmdAbs/xCmdRel/xCmdJogFor...` 命令；`fSetPos/fSetVel/fSetAcc/fSetDec/fSetJerk/eSetDir` 参数；`xStsAbsDone/xStsAbsBusy/xStsAbsError` 状态；`eStsFbErrorID : HMC_ERROR`；`pStsAxis : POINTER TO AXIS_REF_SM3` |
| `HC_sPtpMan` | **HMI 侧**命令 + 参数（触摸屏用） | 含示教数组 `arAbsPos/arAbsVel`、`wCmdAbsSave/wCmdAbsTch` 等 |
| `HC_sPtpHold` | 保持型数据 | 掉电保持的轴参数 |
| `HC_sFumInfo` | 功能块状态 | |

**分工**：`stInfo`（`HC_sPtpInfo`）给 PLC 程序用，`stHMI`（`HC_sPtpMan`）给 HMI 用，
两者在 action 里做转换。这样 HMI 改参数不影响 PLC 逻辑层。

### ⚠ 实轴版的双实例切换（避坑）

`HC_MovePtpR` 的 `actAbs` 用两个实例交替，切换顺序按 Busy 决定：

```pascal
IF fbAbsolute[1].Busy THEN
    fbAbsolute[0](Axis:= RealAxis);
    fbAbsolute[1](Axis:= RealAxis);
ELSE
    fbAbsolute[1](Axis:= RealAxis);
    fbAbsolute[0](Axis:= RealAxis);
END_IF
```

**为什么**：汇川的圆弧/定位指令**不支持对同一实例重复触发**——同一实例连着调两次
Execute，第二次会被忽略或直接 Done。用双实例交替可以让第二次运动在第一次还在
Busy 时就排队。这正是 AM521 蚊香形螺旋插补里踩到的同一个坑。

### 与本仓库其它章节的关系

- 轴控 FB 是普通 `FUNCTION_BLOCK`，所以「`FUNCTION_BLOCK` 里的 LD 写法」一节全部适用
- 轴控 FB 内部用 **ST**（不是 LD），所以它的实现部分落在 `Implementation` 的 `TextLines` 里，
  和「EXECUTE 框内嵌 ST」用的是**同一个 `TextLines` 节点类型**——这也正是
  「改声明区必须锚定 `Interface`」那条铁律的由来（一份 native 里 `TextLines` 有多处）
- 轴控 FB 在 LD 里的调用框是常规 `CallType=FunctionBlock`，槽位规则同「功能块（FB）调用标准结构」

## 28 GVL（全局变量列表）与 Folder 的 native 结构（2026-11-25 实测，1319 行 / 8 个 GVL）

### 对象层级

```
ExportFile
└─ StructuredView  (Guid = 导出根 SV Guid)
   └─ Single
      └─ List2                      (EntryList)
         └─ Single (entry)          (一个 entry = 一个对象)
            ├─ Single Name="IsRoot"
            ├─ Single Name="MetaObject"   → Guid / ParentGuid / Name / Properties / TypeGuid / EmbeddedTypeGuids / Timestamp
            ├─ Single Name="Object"       → 对象本体（GVL 的声明在这里）
            ├─ Single Name="ParentSVNodeGuid"
            ├─ Array  Name="Path"
            └─ Single Name="Index"
```

⚠ `root.iter("Object")` **找不到对象**——`Object` 是 `Single` 的 `Name` **属性值**，
不是标签名。必须遍历 entry 再按 `Name` 属性取子节点。

### GVL 本体

```
Object (Type = {ffbfa93a-…})
└─ Single Name="Interface"
   └─ Single Name="TextDocument"
      └─ Array Name="TextLines"
         └─ Single   (每行)
            ├─ Single Name="Text" Type="string"    ← 声明原文，保留 tab/空格
            └─ Single Name="Id"   Type="int"       ← GVL 内独立递增序列
```

- **没有 `NetworkList`，没有 `Implementation`**（那是 POU 才有的）
- 一个 GVL 内可以有**多段** `VAR_GLOBAL … END_VAR`
- `PERSISTENT RETAIN` 和 `RETAIN PERSISTENT` **两种顺序都真实存在**，不要当成笔误
- `Object.NetVarProperties` = `<Null/>`；`AddAttributeSubsequent` / `ParameterList` = `<Single Type="bool">False</Single>`
- `MetaObject.EmbeddedTypeGuids` = `Array[a9ed5b7e]` 单元素；**Folder 的是 `<Null/>`**

### Folder 的四条 GUID 关系铁律

| # | 字段 | 取值 |
|---|---|---|
| ① | `MetaObject.Properties` 字典 | **Key = 导出根 SV Guid**，**Value = 父容器 guid**（内层 `ParentObjects` 的 Key 又是导出根 SV Guid，Value 是父容器 guid） |
| ② | `ParentSVNodeGuid` | = `ParentObjects` 的 Value |
| ③ | `MetaObject.ParentGuid` | **祖父** guid：直属 Application 的 Folder → 全零；Folder 的子对象 → Application 的 SV 节点 `2fb5ae21-…` |
| ④ | `Object.StructuredViewGuid`（Folder） | = **导出根 SV Guid**（不是自身 guid） |
| ⑤ | `IsRoot` | **被导出的 Folder 自身 `IsRoot=True`**，其余 entry 一律 `False` |

### 花括号铁律（写错就报「格式无效」）

- 节点 **`Type="…"` 属性**带 `{…}`
- **`Type="System.Guid"` 的文本值不带 `{}`**
- `Properties` 字典的 `<Value><Single Type="{829a18f2-…}">` **属性带** `{}`

### AT 绝对地址（`AT %MBxxxx`）三条硬规矩

1. **`AT %MBxxxx` 是绝对物理地址**。把 GVL 复制一份、变量名加后缀、地址原样保留 →
   编译报 **13 条「地址重复」**：`"Hr_xBuzzerShield_GVLVerify"地址重复(重复地址范围为：%MB131076~%MB131076)`。
2. 副本要带地址，必须**整体平移到空闲区间**。实测 `MB +311228 / MW +2000` 后
   50 个地址与原件重叠 **0**，A/B 对照正样本 0 错误、负样本 2 条。
   已用区间与空闲起点可用 `scripts/ide/tasks/task_at_scan.py` 扫出来。
3. 正则要吃 **`AT%MW1000` 这种无空格写法**：`(\s+AT\s*%\S+)?`，`\s*` 不是 `\s+`。
   第一版写 `\s+` 导致 `PLC_Common` 有 6 行没被识别。

### IDE 会自动改写 RETAIN 段（不是 bug）

导入回导后，`PERSISTENT RETAIN` / `RETAIN PERSISTENT` 段的变量被 IDE 补上绝对地址
并规范化字面量：

```
Gv_xSaved    :BOOL :=TRUE;   →  Gv_xSaved AT %MB131099 : BOOL := TRUE;
Gv_diTotal   :DINT :=0;      →  Gv_diTotal AT %MB149512 : DINT := DINT#0;
Gv_xRetain2  :BOOL;          →  Gv_xRetain2 AT %MB146918 : BOOL;
```

普通 `VAR_GLOBAL` 段和 `VAR_GLOBAL CONSTANT` 段**不被改写**。
⇒ **含 RETAIN 段的 GVL 无法「往返逐字节一致」**，只能逐字段比对类型/名字。
（上一轮 `F01_Variable` 8 个 GVL 重建时能字节级一致，是因为那次保留了原地址、
且原文件本来就是 IDE 已改写过的形态。）

### POU 参与编译的前提（2026-11-26 二次修正）

**两个消息分类的作用域不同**，这是理解「为什么 build 干净但 IDE 里报错」的关键：

| 分类 | GUID | 作用域 |
|---|---|---|
| 预编译 | `217bc73e-759b-4a3c-bfa1-991c938a6541` | **`build()` 阶段覆盖 Application 下全部 POU**，与是否挂任务**无关** |
| 编译 | `97f48d64-a2a3-4856-b640-75c046e37ea9` | **只含挂进任务调用列表的 POU** |

实测（负样本 `prg_NoTaskTest` 里 `xOut := ZZZ_NotExist_Symbol;`；
每次先 `clear_messages` 逐分类清空，再做**单一动作**，主机侧等 ≥10s 后独立读）：

| 动作（清空后单独执行） | 预编译 ZZZ | 编译 ZZZ |
|---|---|---|
| 什么都不做（对照） | 0 | 0 |
| 菜单「检查程序」`ab02b3c3` | **0**（不产生任何消息） | 0 |
| `import_native` 导入 POU | 0 | 0 |
| `app.build()`（POU **未挂**任务） | **1** | 0 |
| `app.build()`（POU **已挂** MainTask） | **1** | **2** |
| 删除 POU 后（对照） | 0 | 0 |

⇒ **结论**：
1. **预编译分类的报错来自 `app.build()`**，不是菜单「检查程序」。用户点「检查程序」
   看到报错，是因为该菜单触发了构建/检查，消息由构建阶段写入；消息留在分类里不会消失。
2. **菜单「检查程序」本身是只读的**，不产生任何消息，**不能用于验收**。
3. **预编译覆盖全部 POU**（含未挂任务的），**编译只覆盖挂进任务的**。
   所以「build 的编译分类干净」不能说明未挂任务的 POU 没问题。

⚠ **环境差异（2026-11-28 实测，隐藏桌面实例）**：上面第 3 条只在**交互式 IDE**（用户自己
打开工程、消息分类已注册）成立。用 `HiddenLaunch.exe` + `--runscript` 起的隐藏实例上，
`app.build()` 之后**只出现编译分类 `97f48d64`，预编译分类 `217bc73e` 从头到尾不出现**，
未挂任务的 POU **一条消息都不产生**：

| 动作 | 97f48d64 | 217bc73e | 未挂 POU 的 ZZZ 命中 |
|---|---|---|---|
| 导入 A、B，都不挂任务 → build（28s） | n=104 err=0 | 分类不存在 | A=0 / B=0 |
| 把 B 挂进 MainTask → build（9s） | n=106 err=**2** | 分类不存在 | B=2 / A=0 |
| 再把 A 也挂进 MainTask → build | n=108 err=**4** | 分类不存在 | A=2 / B=2 |

⇒ **隐藏实例不做预编译语义检查，只做编译**。所以隐藏实例上的验收**必须先把目标 POU
挂进 MainTask 再 build**（`scripts/ide/tasks/task_mount_assert.py` 就是这道前置断言），
否则漏检是静默的（0 错误、0 消息）。证据：`references/evidence/hidden-instance-scope/README.md`。

要让 POU 真正参与构建：

```python
main_task = <Application / "Task Configuration" / "MainTask">
main_task.pous.add("POU名")      # ScriptPouObjectList.add(str)
```

⚠ **预编译消息是异步补齐的**。`system.clear_messages(cat)`（**必须传分类参数**，
无参调用报 `takes exactly 1 argument (0 given)`）后立刻读是 0 条，
**约 10 秒**后才补齐到 101 条；清空后空闲 20s 仍是 0 条（不会自行恢复）。
所以「清空 + 单一动作 + 等待 + 读」的判定实验，等待必须放主机侧 Python
（IDE 脚本里 sleep 会冻死界面）。**等待不足会造成假阴性**——本轮曾因只等 10s 而漏读。

`app.create_pou` 的第 2 个参数必须是 CLR 枚举
`_3S.CoDeSys.ScriptEngine.BasicFunctionality.PouType`（反射取后 `System.Enum.Parse`），
传字符串报 `expected PouType, got str`，传数字报 `Cannot convert numeric value`。

## 29 Struct DUT 的 native 结构（2026-11-26 实测，F02_Struct / 17 个顶层 DUT + SF01_Alarm 子文件夹 14 个）

### 与 GVL 的同构关系

Struct DUT（TypeGuid `2db5746d-d284-4425-9f7f-2663a34b0ebc`）与 GVL 高度同构：

| 项 | GVL（`ffbfa93a`） | Struct DUT（`2db5746d`） |
|---|---|---|
| 声明载体 | `Object > Interface > TextDocument > TextLines` | 同左 |
| `Object` 直属子节点 | `Interface` + `NetVarProperties` + `AddAttributeSubsequent` + `ParameterList` | **只有 `Interface` + `UniqueIdGenerator`（单 string）** |
| `EmbeddedTypeGuids` | `Array[a9ed5b7e]` 单元素 | 同左（`Array[a9ed5b7e]` 单元素） |
| 声明语法 | `VAR_GLOBAL … END_VAR`（可多段） | `TYPE 名 : STRUCT … END_STRUCT END_TYPE`（UNION 同理 `UNION … END_UNION`） |
| 绝对地址 | `AT %MBxxxx` 写在声明行 | 不占内存地址，**无 AT 问题** |

### ⚠ 类型名写在声明文本里（与 GVL 的最大差异）

GVL 只有「变量名」；DUT 的**类型名**写在声明首行 `TYPE Struct_Clock :`。
复制 DUT 时必须**同时改两处**，只改 `MetaObject.Name` 不改声明首行会导致类型名对不上：

```
MetaObject.Name                 : Struct_Clock_StructVerify
TextLines[0] : TYPE Struct_Clock_StructVerify :     ← 必须一起改
```

成员行与 GVL 变量行同构（`标识符 : 类型;//注释`），跳过 `TYPE/STRUCT/UNION/END_*` 段标记行。

### 实测记录（F02_Struct_Verify，2026-11-26）

- 复制 17 个顶层 DUT（加 `_StructVerify` 后缀，成员名同加后缀）→ 逐个 `import_native` 到新建文件夹，17/17 成功，无一弹窗（无同名冲突时 import 不弹框）
- 新建 Folder `F02_Struct_Verify` 复用 `make_gvl.folder_entry`（ParentGuid 全零、EmbeddedTypeGuids `<Null/>`）成功
- **A/B 验证**：ST POU `prg_StructVerifyUse`（挂 MainTask）正样本引用副本成员 `stClock.xBlink_1Hz_StructVerify` 等 → 预编译 0 错误、编译仅模板原有 1 条 `E3_SystemTime`；负样本 `stClock.ZZZ_NotExist_Member` → 编译分类 **4 条真实错误**（`不是'STRUCT_CLOCK_STRUCTVERIFY'的成员` ×2、无效赋值目标、类型转换）⇒ 正样本 0 错误不是假通过
- ⚠ 负样本报错信息里结构体名被 IDE 大写成 `STRUCT_CLOCK_STRUCTVERIFY`，grep 判定时大小写不敏感

### 子文件夹的复制（SF01_Alarm_StructVerify，2026-11-26 二轮补做）

在 `F02_Struct_Verify` 下建**子文件夹** `SF01_Alarm_StructVerify`（14 个报警结构体副本），与顶层 Folder 的差异：

| 项 | 顶层 Folder（挂 Application） | 子文件夹（挂 Folder 下） |
|---|---|---|
| `folder_entry.parent_container_guid` | Application 的 SV 节点 guid | **父 Folder 的 SV 节点 guid**（即父 Folder entry 的 `MetaObject.Guid`） |
| `folder_entry.parent_guid` | 全零（`00000000-…`） | 父 Folder 的 SV 节点 guid（不再是全零） |
| `path_parts` | `[Device, PLC 逻辑, Application]` | `[Device, PLC 逻辑, Application, F02_Struct_Verify]`（含父文件夹名） |

⚠ 父 Folder 的 SV 节点 guid 取法：把父 Folder `export_native` 出来，**主机侧**解析——
`StructuredView Guid` 是**导出根** guid（每次导出 fresh 生成，不能当 parent 用），
`MetaObject.Guid`（Name=父文件夹名的那个 entry）才是它的 SV 节点 guid。
**解析必须放主机侧**：IDE 内的 ElementTree 是老 xmllib，解析 native 报
`illegal character in content`。

实测：14 个报警结构体（含 `ARRAY[0..49] OF BOOL` 数组成员、7 个空结构体）副本
导入 14/14 无弹窗；正样本含 `ARRAY[0..2] OF 副本结构体` 及其成员访问 0 错误；
负样本 `stTips.ZZZ_NotExist` → 编译分类 4 条真实检出（同顶层轮）。

## 30 FB/FC 全量翻译验证（2026-11-26 实测，F04_FB / 58 个对象）

`F04_FB` 全部 58 个对象（9 个子文件夹：SF06_通讯、SF05_设备状态机、SF98_34-1-擦拭机、
SF02_气缸、SF99_其他、半自动、SF03_真空、SF01_轴控、SF04_产量统计）整树导出 →
`scripts/examples/make_f04_translate.py` 单遍正则加 `_F04V` 后缀 →
`F04_FB_Verify` 按子文件夹结构逐个 `import_native`，58/58 无弹窗。

### 30.1 对象构成与实现语言

- 30 个 ST FB/FC、8 个 LD FB、20 个 DUT（Struct/Enum），实现语言从
  `Single Name="Implementation" Type` 判定（`{3b83b776-fb25-43b8-99f2-3c507c9143fc}`=ST、
  `{25e509de-33d4-4447-93f8-c9e4ea381c8b}`=LD；**注意此二 GUID 与常见记录不同，
  以此为准**）。DUT 无 `Implementation` 节点。
- 58 个对象里 14 个有内部引用（FB 引用同文件夹 Struct/Enum 类型、FB 互相引用），
  全部成功改写；跨引用最密的是 `FB_RGYLamp_F04V → FB_Alarm_Buzzer/FB_InitializingAndAutoing_Buzzer`、
  多个标定 FB → `FC_AxisAbsGo`、`FB_Cylinder_F04V → Struct0_Cylinder_F04V/Struct1/Struct2`。

### 30.2 ⚠ 枚举字面量进全局命名空间（277 条重名的根因）

- IEC 枚举的字面量值（`A1_上料移栽R轴:=1,`）**不是**作用域限定在类型内的符号，
  而是**全局符号**。副本枚举若沿用原件字面量，会与原件/全局符号**重名**：
  实测 277 条「符号'xxx'存在重名」+ 所有裸引用（如 `VAR i_axisIndex : INT; i_axisIndex:=A1_上料移栽R轴`）
  全变「未知类型: 'xxx'」。**修法：枚举值也要加 `_F04V` 后缀**（从 DUT 声明里
  用 `^\s*\w+:=数字,` 行提取 `name:=` 前的名字加入改写表）。改后预编译 101 errors=0。
- 改写表优先级：内部对象名 ∪ GVL 变量名 ∪ 枚举字面量；单遍 `(?<![A-Za-z0-9_])(name)(?![A-Za-z0-9_])`
  交替合并（长名先排防前缀误伤）。中文不属于 `[A-Za-z0-9_]`，中文名边界天然成立。

### 30.3 A/B 验证（验收链路完整）

- 正样本：ST POU `prg_F04VerifyUse` 实例化 `FB_Cylinder_F04V`（`VAR_IN_OUT` 三个 io 引脚全接真实副本
  Struct，`io_stHMICylinder` 已自动改引 `Struct1_HMI_Cylinder_F04V`）+ `FB_RGYLamp_F04V()` →
  build 后预编译 0 错误、编译仅模板基线 1 条（E3_SystemTime，非 F04 错）。
- 负样本：`fbCyl.ZZZ_NotExist_Pin := TRUE;` → 编译分类 **4 条真实错误**
  （`'ZZZ_NotExist_Pin' 不是'FB_CYLINDER_F04V'的成员` ×2 + 无效赋值目标 + 类型转换）。
- ⚠ 空槽会让整个编译中止（total 从 105 掉到 37），导致负样本假阴性——验收前必须先复位 TaskConfig。

### 30.4 GVL 引用改写到 `_GVLVerify`

用户要求新 FB 引脚/逻辑引用之前验证过的 `F01_Variable_GVLVerify` 副本变量。
`make_f04_translate.py` 读取 `F01_Variable_GVLVerify` 8 个 GVL 的 687 个变量名，
把 FB 体内的 `Gv_xxx` 改写到 `Gv_xxx_GVLVerify`（实测 FB_Cylinder 副本 16 处、全树 851 处改写）。
`VAR_IN_OUT io_stHMICylinder : Struct1_HMI_Cylinder_F04V` 这类**类型引用**走「内部名 → 副本类型」
改写，而 `H_astAlarmRecord_GVLVerify` 这类**变量引用**走 GVL 映射，两条链并行不冲突。

## 31 FC 全量翻译验证（2026-11-26 实测，F05_FC / 10 个对象）

`F05_FC` 结构比 F04 多一种形态：**7 个 ST FC + 3 个 DUT，其中 5 个 FC 直接挂在
`F05_FC` 根下**（不是子文件夹），2 个子文件夹（`SF01_AlarmRecord` 3 个对象、
`SF02_AlarmWindow` 2 个对象）。整树导出 → `make_f05_translate.py` 加 `_F05V` →
`F05_FC_Verify`，10/10 无弹窗。

### 31.1 ⚠ 根下直接 POU 与「子文件夹」在导出时长得一样

导出脚本用 `kids()` 判断，根下直接 FC 也会生成一个空目录 + `<名>_folder.native`，
**看起来像子文件夹，其实是 POU**。判别唯一可靠依据是 native 里的
`Single Name="TypeGuid"` = `6f9dac99-8de1-4efc-8465-68ac443b7d08`（FB/FC 类）；
真 Folder 是 `738bea1e-…`。⚠ 之前记录的 `6f9dac99-f3a6-45e5-…` 是错的，以此为准。

### 31.2 ⚠ 枚举字面量的提取正则要吃行尾注释

`Enum_AlarmLevel` 的声明是 `\t提示\t\t:= 1,//仅在触摸屏显示用`——字面量后面跟
`//` 注释。原正则 `^\s*(\w+)\s*:=\s*-?\d+\s*,?\s*$` 匹配不到（F05 实测 0 命中，
会导致 277 重名问题重演）。必须放宽为 `...\s*,?\s*(//.*)?$`。
另注意最后一个字面量可能**无逗号**（`严重故障\t:= 4//...`），`(//.*)?` 同时覆盖。

### 31.3 枚举字面量的中文词不能盲目全局替换

`Enum_AlarmLevel` 的字面量是 `None / 提示 / 警告 / 故障 / 严重故障`——`提示`、`警告`、
`故障` 是极常见中文词，纯文本全局替换会改坏注释和字符串。**安全前提**：先扫描
这些字面量在每个对象里的全部出现位置，确认只在枚举声明行出现，再加后缀。
F05 实测仅出现在 `Enum_AlarmLevel` 与 `Struct_AlarmRecord` 的声明行，替换安全。

### 31.4 根下 POU 的导入清单必须在主机侧预生成

IDE 内 `xml.etree` 是老 xmllib，解析含中文/特殊字符的 native 直接抛
`illegal character in content`（§29 已记录）。所以「根下哪些是 POU」的判定
**不能放 IDE 脚本里**：主机侧预生成 `ipc/f05_root_pous.txt` 清单，
IDE 脚本只读清单逐个 `import_native`。

### 31.5 A/B 验证

- 正样本：`prg_F05VerifyUse` 调用 `FC_AlarmRecord_F05V`（`io_astAlarmRecord` 传
  `ARRAY[0..99] OF Struct_AlarmRecord_F05V`，测副本 Struct 引用链）+ `FC_CRC16_F05V`
  （内部调 `FC_XOR8_F05V`/`FC_XOR16_F05V`，测 FC 互相调用链）→
  **预编译 0 / 编译 0，合计 0 错误**（比 F04 更干净，连 E3_SystemTime 基线都没有）。
- 负样本：多传一个不存在的引脚 → 编译 **2 条真实错误**
  （`函数 'FC_AlarmRecord_F05V' 需要'2'个输入` + `没有定义标识符'ZZZ_NotExist_Pin'`）。

### 31.6 ⚠ 根下直接 POU 会被误建为空文件夹（实际踩到）

§31.1 记录了「根下直接 POU 导出时也生成空目录」，但**导出/翻译/导入三个脚本
如果都只按目录遍历，就会真的在工程里建出空文件夹**。F05 实测多建了 **5 个**：
`ConcatPro_F05V`、`FC_CRC16_F05V`、`FC_XOR8_F05V`、`FC_XOR16_F05V`、
`FC_整串字符串按分隔符截取_F05V`。

链路：导出生成 `ipc/f05/<名>/`（空目录）→ 翻译在 `ipc/f05_out/<名>/` 又建一份
→ 导入遍历目录时对每个目录调 `mk_folder` → 工程里多 5 个空文件夹。

**三重防护（已在脚本中落地）**：
1. `make_f05_translate.py`：目录内无 `.native` 直接 `skip`；
2. `task_import_f05.py`：`natives` 列表为空则 `[SKIP]`，不调 `mk_folder`；
3. 事后清理 `task_f05_rm_empty.py`：判定 `kids==0` 且 `textual_declaration` /
   `textual_implementation` 都取不到 → 纯容器 → `remove()`。

**判别空 Folder 的可靠方法**：`len(kids(o)) == 0` 且两个 textual 属性都抛异常或
返回 `None`。真正的 POU 即使 `kids==0` 也一定能取到 `textual_declaration`。
空文件夹不影响编译（实测删前删后都是 0 错误），但会污染工程结构。

## 32 CAM（电子凸轮）对象结构与曲线规划（2026-11-26 实测，F07_CAM / Cam0 + Cam1）

`F07_CAM` 只有一个对象 `Cam0`，**没有子文件夹、没有 POU**。CAM 是与 FB/FC/DUT
完全不同的对象类别，最容易踩的坑是**它没有文本层**——不能"翻译"，曲线内容只能改结构化数值。

### 32.1 TypeGuid 与 Object 的 8 个子节点

```
TypeGuid = fea841a8-cb28-421c-8d22-c7226c528b66   （CAM）
```

`Object` 下固定 8 个子节点：

| 节点 | 类型 | 说明 |
|---|---|---|
| `Name` | string | **内部类型名，固定 `"Cam"`，复制时不改** |
| `Dimension` | `{d33a766f-2682-46e4-9246-c08c4c59ed7e}` | `dMasterStart/End`、`dSlaveStart/End` 四个 double |
| `Periodic` | bool | 是否周期闭合，见 §32.3 |
| `Period` | double | 周期，通常 = `dMasterEnd - dMasterStart` |
| `Points` | ArrayList | 控制点列表，见 §32.2 |
| `Segments` | ArrayList | 段列表，见 §32.2 |
| `ContinuityRequirements` | uint | 位掩码，`7` = 位置\|速度\|加速度 全要连续 |
| `TappetTracks` | ArrayList | 从轴轨迹（凸轮开关） |
| `Properties` | `{93a11fef-b03d-42c0-9d96-0fa7e7e17d3f}` | 杂项 |

**⚠ 没有 `TextLines`、没有 `Implementation`** —— 这是与 FB/FC/DUT 最本质的区别。
所以：
- 「翻译副本」= 只改 `MetaObject.Name`（不存在跨对象文本引用）
- 「改曲线」= 只能改 `Points` / `Segments` / `Dimension` / `Periodic` 的结构化数值

### 32.2 Points 与 Segments 的字段与 Guid

**控制点**（`Points` 列表元素 / 段内 `cp0`/`cp1`）Type = `{33af5b4b-b53e-4699-8a38-5b974f57f906}`，10 个字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `X` / `Y` | double | 主轴 / 从轴位置 |
| `V` / `A` / `J` | double | 速度 / 加速度 / 跃度 |
| `XEditable` / `YEditable` / `VEditable` / `AEditable` / `JEditable` | bool | 该分量是否允许 IDE 自动填充 |

**段**（`Segments` 列表元素）：

| Guid | 类型 | 标量参数 |
|---|---|---|
| `{7ede90d3-c635-4970-9884-6cb82027dc11}` | **直线** | `p0`, `p1` |
| `{3bfb4cba-336c-4ed3-b189-88789dd9592e}` | **五次多项式** | `p0`..`p5` |
| `{67de258b-9885-4c31-a492-832de2bedf9c}` | TappetTrack | `ID` + `Tappets` |
| `{fbd51b6b-9635-464d-bc11-0f5ed14d3246}` | Tappet | `x` + `PositivePass`/`NegativePass` |
| `{11f0881c-b6c6-44b5-ba5b-24d4e91af48a}` | Pass | `Type`(int)，1=正 / 2=负 |

⚠ **每段必须自带 `cp0` / `cp1` 两个端点副本**，值须与相邻段一致。
`Points` 与 `Segments` 是**两套独立数据，必须同步改**，只改一套 IDE 会显示错位。

### 32.3 ⚠ 铁律：直线段 `p1` 是段内增量，不是终点绝对值

直线段的 y 表达式是：

```
y(u) = p0 + p1 · u        （u = 段内归一化位置 0..1）
```

即 `p0` = 起点 y，**`p1` = `y1 - y0`（段内增量）**。

模板 Cam0 三段实测反解（这是判定依据，不是推测）：

| 段 | p0 | p1 | y(0) | y(1) | cp0.Y → cp1.Y | 吻合 |
|---|---|---|---|---|---|---|
| 段1 | 0 | 0 | 0 | 0 | 0 → 0 | ✓ |
| 段3 | 20 | 80 | 20 | 100 | 20 → 100 | ✓ |
| 段5 | 0 | 0 | 0 | 0 | 0 → 0 | ✓ |

**踩过的坑**：按「p0=起点、p1=终点」写停歇段 `p0=45 p1=45`，实际算出 `y(1)=90`、
段内斜率 45，与相邻多项式段的零速度冲突，Cam 分类报：

```
在点 (240/45) 的连续性要求不能填充 速度
```

**自检口诀（两条都成立才对）**：

```
p0      == cp0.Y
p0 + p1 == cp1.Y
```

### 32.4 ⚠ 铁律：分度凸轮必须 `Periodic=False`

- **摆动凸轮**（一周期回到原点，如模板 Cam0 的 0→0）：`y(360) == y(0)` → `Periodic=True`
- **分度凸轮**（每周期从轴累进 H，如 Cam1 的 0→45）：`y(360) == y(0) + H` → **必须 `Periodic=False`**

沿用模板的 `True` 会报：

```
在点 (0/0) 的连续性要求不能填充 位置
在点 (0/0) 的连续性要求不能填充 速度
```

**自检**：算 `y(360) - y(0)`，≠ 0 就必须 `False`。

### 32.5 凸轮曲线规划方法

#### 32.5.1 无量纲峰值系数是选型的唯一客观依据

```
Vmax = Cv · H / T
Amax = Ca · H / T²
Jmax = Cj · H / T³
```

其中 `H` = 分度行程，`T` = 分度段时长 = `β/360 × 60/n`（β=分度角，n=主轴 rpm）。

| 规律 | Cv | Ca | Cj | 特点 | 适用 |
|---|---|---|---|---|---|
| 等加速等减速 | 2.000 | 4.000 | ∞ | 加速度阶跃 | 低速重载 |
| 余弦加速度 | 1.571 | 4.932 | ∞ | 起止 A≠0 | 中低速 |
| 正弦加速度（摆线） | 2.000 | 6.283 | 39.5 | 全程最平滑 | 高速分度 |
| **3-4-5 五次多项式** | **1.875** | **5.774** | **60.0** | 起止 V=A=0 | **通用推荐** |
| 4-5-6-7 多项式 | 2.188 | 7.513 | 52.5 | 更高阶平滑 | 超高速 |
| 修正正弦 | 1.760 | 5.528 | 69.5 | Cv 最小 | 高速轻载 |
| 修正梯形 | 2.000 | 4.888 | 61.4 | Ca 较低 | 中速中载 |

⚠ **数据可信度**：前 5 行的 Cv/Ca/Cj 由解析式数值微分**实测校验**（误差 < 0.1%），可直接引用。
后 2 行（修正正弦 / 修正梯形）的分段公式版本多、易写错，**仅引《机械设计手册》系数、未绘波形**，
只用于横向比较量级，**不作为计算依据**。

#### 32.5.2 为什么推荐 3-4-5 五次多项式

1. **起止 V=0、A=0**，与两侧停歇段（直线，V=0）天然 C¹/C² 连续，接缝零冲击。
   摆线 / 修正正弦端部**速度不为 0**，需专门做匹配。
2. Ca=5.774 居中：比摆线低 8%，比修正正弦高 4.4%。
3. **实现最简**：CAM 已有 `{3bfb4cba}` 五次多项式段类型，只需填 p3/p4/p5 三个系数，**无需插点表**。
4. 改造现有 CAM 对象成本最低（段数从 5 降到 3）。

#### 32.5.3 停-升-停标准系数（可直接抄）

```
H = 360 / N_STATION          每工位行程
β = 分度角（deg）
T = β/360 × 60/n             分度段时长（s）

段1 直线        x[ 0            → (360-β)/2 ]    p0=0    p1=0
段2 五次多项式  x[ (360-β)/2    → (360+β)/2 ]    p0=p1=p2=0
                                                  p3=10H  p4=-15H  p5=6H
段3 直线        x[ (360+β)/2    → 360       ]    p0=H    p1=0
```

**三重校验**（三个都必须为 0 / H）：

```
p3 + p4 + p5 = 10H - 15H + 6H = H         末值正确
y'(1)  = 3p3 - 4p4 + 5p5      = 0         末端速度 0
y''(1) = 6p3 - 12p4 + 20p5    = 0         末端加速度 0
```

Cam1 实例（8 工位，H=45，β=120）：`p3=450, p4=-675, p5=270`，
实测 `Vmax=253.1 °/s`、`Amax=2338.5 °/s²`、`Jmax=72900 °/s³`（n=60 rpm）。

#### 32.5.4 落地前校核清单（10 项）

| # | 校核项 | 判据 |
|---|---|---|
| 1 | 位移单调 | 分度段 y 严格单调递增 |
| 2 | 位置连续 | 段接缝 y 相等 |
| 3 | 速度连续 | 段接缝 V 相等 |
| 4 | 加速度连续 | 段接缝 A 相等 |
| 5 | 周期闭合 | `y(360)-y(0)` 决定 `Periodic` 取值（§32.4） |
| 6 | 峰值加速度 | `Amax ≤` 从轴许用加速度 |
| 7 | 峰值转矩 | `M = J_load · Amax_rad / η ≤` 电机峰值 / 1.5 |
| 8 | 跃度 | `Jmax ≤` 机械许用（≤ 1e5 °/s³ 属温和） |
| 9 | 压力角 | 仅实体凸轮涉及，α_max ≤ 30°~45°；电子凸轮不涉及 |
| 10 | 与 Dimension 一致 | Points/Segments 的 x 落在 `[dMasterStart, dMasterEnd]` |

#### 32.5.5 ⚠ 模板 Cam0 是反面样本（实测缺陷，勿照抄）

`F07_CAM / Cam0` 是 5 段摆动曲线，**不是可用工艺曲线**：

| 接缝 x | 位移 | 斜率 dy/dx | 结论 |
|---|---|---|---|
| 100 | 0→0 ✅ | **0→1.0 ✗** | 速度阶跃（停歇→起步） |
| 120 | 20→20 ✅ | **1.0→0.75 ✗** | 速度阶跃（多项式→直线） |
| 200 | **80→100 ✗** | **0.75→0 ✗** | **位移断裂 20°** |
| 250 | 0→0 ✅ | 0→0 ✅ | 正常 |

- 最致命：x=200 处段3 直线算到 80、段4 从 100 起，**直接跳变 20°**，IDE 报曲线不连续。
- 另 5 段里 3 段是**纯直线（等速）**，两端速度突变 → 加速度理论无穷大 → 冲击、异响、丢步。
- 位移非单调（0→20→80→100→0），一周期回到原点 → 是**摆动**凸轮，不是分度凸轮。

> 注意：段4 的五次多项式系数**本身是自洽的**（y(0)=100、y(1)=0、两端斜率匹配），
> 问题出在段3 的终点值 80 与它起点 100 对不上。不要误判成「多项式系数写错」。

#### 32.5.6 与 §27 轴控的关系

CAM 是「主从同步」的运动控制方式，与 §27 的点位控制互补：

| 章节 | 场景 | 典型指令 |
|---|---|---|
| §27 | 单轴 / 轴组定位 | `MC_MoveAbsolute`、`MC_MoveRelative`、`MC_MoveVelocity` |
| §32 | 主轴-从轴电子凸轮耦合 | `MC_CamIn`（引用 CAM 对象）、`MC_CamOut` |

POU 里引用 CAM 的写法（本轮 A/B 正样本，双分类 0 错误通过）：

```pascal
VAR
    refCam : MC_CAM_REF;
    fbCamIn : MC_CamIn;
END_VAR

refCam := Cam1_F07V;
fbCamIn(Master := Master, Slave := Slave, CamTableID := refCam);
```

### 32.6 ⚠ Cam 子对象无法用脚本删除，只能同名覆盖导入

三种写法全部失败（2026-11-26 实测）：

| 写法 | 报错原文 |
|---|---|
| `top.remove(obj)` | `remove() takes no arguments (1 given)` |
| `top.replace(idx, "")` | `'ScriptObject' object has no attribute 'replace'` |
| `t.pous.remove(idx)`（POU 列表那套） | Cam 文件夹没有 `pous` 属性 |

**唯一可行**：把改好的 native 用**同名** `import_native` 再导一次，返回
`NativeImportResult.ok` 且原对象被正确覆盖（实测 `Periodic`、`Points`、`Segments` 全部更新）。

与铁律 25（POU 任务槽 `remove` 留 `Name=""` 空槽）属同类 API 局限，但 Cam 更彻底——
**根本没有删除入口**。

### 32.7 导入验证结果（Cam1_F07V）

| 分类 | total | errors |
|---|---|---|
| 预编译 `217bc73e` | 101 | **0** |
| 编译 `97f48d64` | 104 | **0** |
| Cam `de128929` | — | **0** |

往返 diff：写入 13 个字段 vs 回读 13 个字段，**0 缺失 / 0 差异**。

⚠ 注意：本轮曲线出错时（`Periodic=True` 与 p1 写错），**错误只落在 `de128929` Cam 分类**，
预编译 101/0、编译 104/0 全是 0 —— **只看这两个分类会漏判通过**。详见 `mcp-bridge.md` 分类表。

## 33 AxesGroup（运动轴组）对象结构与复制（2026-11-26 实测，F08_AxisGroup）

`F08_AxisGroup` 下有两个轴组：`AxesGroup_A1`（擦拭 A1 侧 XY 二轴）、`AxesGroup_C1`（擦拭 C1 侧 XY 二轴）。
轴组是与 FB/FC/DUT/CAM 都不同的**设备侧运动配置对象**。

### 33.1 对象能力（探测结果）

| 探测项 | 结果 |
|---|---|
| `TypeGuid` | `ad3ae438-9dc8-4473-b82c-f59e508baec4` |
| `is_folder` | `False` |
| `has_textual_implementation` | `False` |
| `textual_declaration` / `textual_implementation` | `AttributeError`（**没有文本层**） |
| `get_children()` | `[]`（**没有子对象**） |
| `type_guid` | `AttributeError`（**没有该属性**，只能从导出的 native 里读） |
| `guid` | 有（`ScriptObject.guid`） |
| `dir()` | 只有 `Equals/GetHashCode/GetType/MemberwiseClone/ReferenceEquals/ToString` |

**结论**：脚本接口对轴组几乎完全不可见，**所有信息只能靠 `export_native` 拿到**。
这与 CAM（§32）一样属于「结构化对象」，但比 CAM 更封闭——CAM 至少有 `Name/Periodic/Points` 等可读属性路径。

### 33.2 native 结构（`Object` 下的字段）

```
<Object Type="{ad3ae438-...}">
  <Id>                        uint，同文件夹内递增（A1=0, C1=1）
  <Type>                      CART_XY（笛卡尔 XY 二轴；其它值未实测）
  <AxisMappingCollection>
    <AxisMappings>            4 个槽（固定 4，未用的填 00000000）
      <AxisGuid>              指向 Device/ETHERCAT_C/ServoXX/AxisXX 的 guid
      <Description>           组内轴名（A1/A2/A3/A4）
      <ZeroingIndex>          int
  <WorkspaceConfig>
    <PositionConfig>          MaxVelocity/MaxAcceleration/MaxDeceleration/MaxJerk/UnitTyp
    <AttitudeConfig>          同上（姿态轴，单位「度」）
  <ReadInputsPouGuid>         ⚠ 轴组内部自动生成的 4 个 POU
  <WriteOutputsPouGuid>       ⚠ 全工程树里都找不到，脚本不可见
  <InitPouGuid>               ⚠
  <gvlPouGuid>                ⚠ 唯一例外：导入后不被改写（见 33.5）
  <PositionDimensionType>     Metre
  <AttitudeDimensionType>     Degrees
  <UserMasterDimensionType>   Position
  <AltitudeHeightL0> / <BigArmBoomLengthL1> / <SmallArmBoomLengthL2>     机器人学参数
  <CurveType>                 T
  <ContinuousPathEnable> / <SavingsLength> / <ForwardLookingLength> /
  <ForwardLookingAccuracy>    前瞻配置
  <StBaseX..C> / <StPartX..C> / <StToolX..C>                            基坐标 / 工件 / 工具
  <StPartCoordinateSystemModels> / <StToolCoordinateSystemModels>       Part1..Part10 各 10 组
  <AxisSettingEnable>         bool
```

`AxisGuid` 实测归属（从设备树解析）：

| 轴组 | 槽位 | AxisGuid | 真实对象 |
|---|---|---|---|
| A1 | 0 | `2b9e1a51-…` | `Device/ETHERCAT_C/Servo7_擦拭A1侧X轴/Axis7_擦拭A1侧X轴` |
| A1 | 1 | `39176bc8-…` | `Device/ETHERCAT_C/Servo8_擦拭A1侧Y轴/Axis8_擦拭A1侧Y轴` |
| C1 | 0 | `abafabd0-…` | `Device/ETHERCAT_C/Servo15_擦拭C1侧X轴/Axis15_擦拭C1侧X轴` |
| C1 | 1 | `d9285e5b-…` | `Device/ETHERCAT_C/Servo16_擦拭C1侧Y轴/Axis16_擦拭C1侧Y轴` |

### 33.3 ⚠ 铁律：复制轴组必须换 `MetaObject.Guid` 和 `Object.Id`，但不能沿用被占用的 AxisGuid

复制只需改三处（实测 diff 精确为 3 处，其余字节完全保留）：

| 字段 | 原件 A1 | 副本 |
|---|---|---|
| `MetaObject.Name` | `AxesGroup_A1` | `AxesGroup_A1_F08V` |
| `MetaObject.Guid` | `d7035b48-…` | 新 guid（不换则导入冲突） |
| `Object.Id` | `0` | 新值（同文件夹内不能重复） |

**`AxisGuid` 与 4 个内部 POU Guid 原样保留，但结果不同**：

- **AxisGuid 会被 IDE 清空成 `00000000`**（若原轴已被原轴组占用）
- 内部 POU Guid（`ReadInputs`/`WriteOutputs`/`Init`）会被 IDE 重写为新值 —— 正常
- `gvlPouGuid` 保持不变

**根因（实测对照实验确认）**：SoftMotion 物理轴**不能同时属于两个轴组**。
把副本的 `AxisGuid` 改成空闲轴（Axis9/Axis10）后重新导入，**AxisGuid 完整保留、0 错误**。
所以「清空」不是脚本 bug，是 IDE 的占用保护。

**判定方法**：复制前先确认目标轴没被其它轴组占用。工程树里 `SoftMotion General Axis Pool` 是空的，
说明本工程的轴全在 `Device/ETHERCAT_C/ServoXX/` 下，且已被原轴组绑定。

**若确实要两个组共用同一批轴**：做不到。必须先建独立轴（本工程 Axis Pool 为空、
`pool.get_children()` 返回 `[]`，脚本无法建虚拟轴，只能手工在 IDE 里加），再让副本映射过去。

### 33.4 ⚠ 铁律：轴组必须在「轴所在的那个任务」里被引用

实测报错原文：

```
轴组 AxesGroup_A1_F08V 与所选轴所在任务不同: 不能再在任务 MainTask 中被引用
```

本工程轴挂在 `ETHERCAT` 任务下（8 ms，优先级 0），所以引用轴组的 POU 必须也挂 `ETHERCAT`。
`MainTask`（20 ms）里引用会直接报错。

**并且同一 POU 不能同时挂两个任务**，否则报：

```
程序 prg_F08VerifyUse 在多任务下存在多处调用，可能会产生不符合预期的结果
```

### 33.5 任务槽摘除：`pous.remove()` 依然无效（铁律 25 的同类问题）

实测 `main_task.pous.remove("名字")` **日志打印成功、回读仍在**，与铁律 25 完全同源。
唯一可靠做法（`scripts/examples/del_task_pou.py`）：

1. `export_native([taskConfig], out, True)` 导出 Task Configuration
2. 主机侧按「行」删除 `<Single Type="{f194d1ef-7376-42ce-a729-4a5485a97a46}">` … `</Single>` 块
3. `run_overwrite_import.py` 同名覆盖导入（弹框自动点「全部(A)」→「确定」两步）

⚠ **不能用跨行正则 `.*?</Single>`** —— 会连相邻的 `</Single>` 一起吃，导入报
`第 89 行，位置 10 上的开始标记"List"与结束标记"Single"不匹配`。
必须从 `<Single Type="{f194d1ef…}">` 行起，逐行走到**单独一行 `</Single>`** 为止。

### 33.6 POU 里引用轴组的正确写法

工程里已有的写法（`M010_插补控制`，实测可编译）：

```pascal
VAR
    io_stAxesGroup : PAXES_GROUP_REF;
END_VAR

io_stAxesGroup := AxesGroup_A1;
```

⚠ **不要写 `stGroup <> 0` 做非空判断**，实测报：

```
不能比较类型 'PAXES_GROUP_REF' 和类型'BIT'
```

`PAXES_GROUP_REF` 是指针类型，不能与整型/BIT 比较。

### 33.7 导入验证结果（F08_AxisGroup_Verify）

| 分类 | total | errors |
|---|---|---|
| 预编译 `217bc73e` | 101 | **0** |
| 编译 `97f48d64` | 104 | **0** |
| 合计 | — | **0** |

**A/B 验证**：
- 正样本 `stGroup := AxesGroup_A1_F08V;` → 预编译 0 / 编译 0
- 负样本 `stGroup := ZZZ_NoSuchGroup_F08V;` → 编译 **2 条**错误：
  `不能将类型 '未知类型: 'ZZZ_NoSuchGroup_F08V'' 转换为类型'PAXES_GROUP_REF'`
  `没有定义标识符'ZZZ_NoSuchGroup_F08V'`

**往返 diff（映射到空闲轴后）**：13 个 Guid 字段全部一致，仅 `Timestamp`、`Id`（IDE 重排为 2）、
`ParentSVNodeGuid`（改指向 Verify 文件夹）三处由 IDE 更新，均属预期。

### 33.8 与 §27 / §32 的关系

| 章节 | 对象 | 层级 | 有无文本层 | 复制方式 |
|---|---|---|---|---|
| §27 | 单轴轴控 | POU 代码 | 有 | 翻译改写 |
| §32 | CAM 电子凸轮 | Application 下 | 无 | 只改 Name |
| §33 | AxesGroup 轴组 | Application 下 | 无 | 改 Name + Guid + Id，AxisGuid 需目标轴空闲 |
