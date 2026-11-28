# InoPack 包装模板 LD 语料普查（InoProShop 1.10）

> 用途：想按真实产线工程的写法写 LD 时，先查这份普查，知道模板里到底有哪些框、哪些形状、哪些槽位数——**不要凭想象造结构**。
> 本文件的数据全部由 `scripts/corpus/` 下的工具从真实工程导出的 713 个 `.native` 里统计得出，可复现。

## 0. 语料规模

| 项 | 值 |
|---|---|
| 母本工程 | InoPack 包装 PLC 模板程序 V1.0.0.4（1.87 MB）在 InoProShop 1.10 里打开并升级后的副本，13.8 MB |
| 导出 | 713 个 `.native` / 320.2 MB（递归导出 `active_application` 全部后代，每个对象一个文件） |
| 去重后对象 | **470** |
| 实现语言 | LD **61**（模板原生 58 + 测试对象 3）、ST 192、无实现 217 |
| LD 规模 | **2171 个网络 / 7495 个框 / 127 种网络形状 / 24 种框** |

## 1. 模板原生 LD POU（按网络数，Top 20）

| # | 网络 | 框 | 文件 KB | 名称 |
|---|---|---|---|---|
| 1 | 430 | 2218 | 20104 | SF98_34-1-擦拭机 |
| 2 | 125 | 905 | 7613 | A01_中转移栽 |
| 3 | 119 | 799 | 6862 | FB_擦拭模组 |
| 4 | 119 | 799 | 6863 | FB_擦拭模组_F04V |
| 5 | 101 | 596 | 5454 | FB_擦拭模组_半自动 |
| 6 | 101 | 596 | 5456 | FB_擦拭模组_半自动_F04V |
| 7 | 97 | 638 | 5329 | A02_下料移栽 |
| 8 | 85 | 490 | 4099 | **A00_上料移栽**（步序母语法的取样对象） |
| 9 | 81 | 345 | 3161 | FB_擦拭模组_半自动更改擦拭方式 |
| 10 | 81 | 345 | 3162 | FB_擦拭模组_半自动更改擦拭方式_F04V |
| 11 | 50 | 203 | 1935 | FB_擦拭模组_半自动_插补 |
| 12 | 50 | 203 | 1936 | FB_擦拭模组_半自动_插补_F04V |
| 13 | 35 | 154 | 1293 | A03_下料翻转 |
| 14 | 35 | 46 | 443 | FB_擦拭上下料平台 |
| 15 | 35 | 46 | 443 | FB_擦拭上下料平台_F04V |
| 16 | 32 | 145 | 1336 | FB_无尘布机构 |
| 17 | 32 | 145 | 1337 | FB_无尘布机构_F04V |
| 18 | 29 | 213 | 2008 | A00_翻转半自动 |
| 19–26 | 29 | 12 | 207 | A00/A02/A04/A06/A08/A10/A12/A14_擦拭XX模组擦拭半自动（8 个几乎相同的薄壳） |
| 27 | 27 | 427 | 4272 | A17_擦拭模组一键点检半自动 |
| 28 | 20 | 172 | 1589 | A16_下料移栽取料半自动 |

后 30 个都是 2–16 网络的小 POU（`A05_擦拭C1模组换布半自动` 等 3 网络的换布小流程、`ReConect` 8 网络、`FB_Honeywell` 2 网络）。

**规律**：真正干活的逻辑集中在 20 个大 POU；站级程序（A00–A20）要么是 85–125 网络的完整工序，要么是 3–29 网络的薄壳（只调 FB）。

## 2. 24 种框词汇表（BoxType 与 CallType 必成对）

| BoxType | CallType | 次数 | 出现在几个 POU |
|---|---|---|---|
| AND | And | 4401 | 58 |
| MOVE | Move | 2347 | 55 |
| EQ | Eq | 1315 | 28 |
| FC_AxisAbsGo | Function | 950 | 20 |
| FC_CylinderExe | Function | 378 | 20 |
| GT | Gt | 185 | 17 |
| LT | Lt | 125 | 12 |
| TON | FunctionBlock | 107 | 13 |
| GE | Ge | 107 | 8 |
| ADD | Add | 76 | 16 |
| EXECUTE | None | 65 | 14 |
| LE | Le | 43 | 13 |
| FB_StepLogger | FunctionBlock | 18 | 18 |
| FB_擦拭上下料平台 / FB_半自动_无尘布机构 / FB_擦拭模组_半自动 / FB_擦拭模组 / FB_无尘布机构 / FB_无尘布机构按钮控制 | FunctionBlock | 各 8 | 8 |
| NE | Ne | 6 | 3 |
| FB_TCPIPClient | FunctionBlock | 3 | 3 |
| FIND / DELETE | Function | 各 3 | 3 |
| FB_擦拭模组_半自动_插补 | FunctionBlock | 2 | 2 |

24 种里 **只有 BoxType 的 0 种、只有 CallType 的 0 种**——两者永远同时出现，缺一即非法。

## 3. InputItems 槽数规律

| 框 | 槽数 | 次数 | 读法 |
|---|---|---|---|
| And | 2 | 4174 | 最省形态：两个输入（**单条件不许建 AND 框**） |
| Move | 2 | 2347 | EN + IN |
| Eq / Gt / Lt / Ge / Le / Ne | 3 | 1315 / 185 / 125 / 107 / 43 / 6 | EN + 两个操作数 |
| Function（FC_AxisAbsGo 等） | 4 或 3 | 953 / 381 | EN + 参数，最后一个是返回值槽 |
| TON | 2 | 107 | **IN + PT，没有 EN 槽** |
| ADD | 3 | 76 | EN + 两个操作数 |
| EXECUTE | 1 | 65 | 只有 EN |
| FunctionBlock（自定义 FB） | 2–36 | 186 | 与 FB 入参个数一致 |
| And 多槽 | 3–9 | 109 / 63 / 21 / 18 / 13 / 2 / 1 | 多条件串联（最多 9） |

## 4. InputFlags（框输入的边沿位）

只有两类框用过：

| 框 | 第 0 项 Flags | 次数 |
|---|---|---|
| Function（FC_AxisAbsGo / FC_CylinderExe） | **16** | 1328 |
| Add | **16** | 66 |
| Le | 0 | 39（`<List2>` 存在但第 0 项 0，等于没边沿） |
| 其余全部 | `<Null/>` | — |

含义见 `references/edge-detection.md`：**`InputFlags` 第 0 项 `Flags=16` + `Fixed=True` 就是「该框的 EN 引脚启用上升沿」，即这块框只在 EN 由 FALSE→TRUE 那一拍执行一次。**

## 5. 网络形状（详见 `ld-network-shapes.md`）

- 2171 个网络里 **781 个没有图形**（纯注释/占位），占 36%；
- 有图的网络里 **分支（BRANCH）主导**：`branch:1 || EQ:1+FC_AxisAbsGo:2+MOVE:2` 出现 163 次，前 5 名全是「EQ 门控 + 动作框 + MOVE 下一步」；
- 形状种类 127 种，但 Top 25 覆盖绝大多数网络。

## 6. 步序母语法（A00_上料移栽 实测）

每个步序网络的骨架（Network 4 起的标准形态）：

```
BRANCH
  Input = EQ { InputItems = [xAutoing 触点, aiAutoStep, 10000] }
  Trees =
    T1: MOVE  描述字面量 -> awstrAutoDescription
    T2: 动作框（FC_AxisAbsGo / FC_CylinderExe / TON ...，EN 带 InputFlags 16）
    T3: MOVE  下一步号 -> aiAutoStepBuffer
```

配套约定：

1. 第 1 个网络提交步号（`aiAutoStep := aiAutoStepBuffer`），其余网络只写 buffer；
2. 每个工序段前有注释网络（`*无料取料流程*` / `*有料放料流程*`）；
3. 每段内部按步号递增，跳步永远写 buffer，所以本周期读到的 `aiAutoStep` 恒为旧值（单轨状态机，见模式卡 01）。

## 7. 复现这份普查

```
scripts/ide/tasks/export_all.py            # IDE 内跑（IronPython），不走主机侧 bridge
python scripts/corpus/index_native.py      # raw/*.native -> index.json + LD/ST 清单
python scripts/corpus/scan_forms.py        # BoxType/CallType/槽数/InputFlags 统计
python scripts/corpus/parse_net.py         # 网络形状统计 -> net_shapes.json
python scripts/corpus/ld_dump.py <native>  # 单个 POU 的结构树
```

详见 `references/corpus/toolchain.md`。

---

数据来源：2026-11-27 对 `D:/plc_study/study.project`（InoPack 模板 1.10 副本）的 713 文件全量导出；原始统计脚本与中间产物在 `scripts/corpus/`。
