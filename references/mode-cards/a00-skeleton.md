# 模式卡 03 · A00 骨架：把流程写进工站自动 POU 的动作槽

> 状态：**已在软件里验证**（2026-11-28，v2 按用户纠正后的容器改写）。
> 样本 `assets/natives/A04_slot4.native`（847,782 B / 22 网络 / 768 个 Id 全唯一）、骨架 `assets/natives/a04-action-skeleton.native`（186,228 B，`A04_` 的原始导出）。
> 由 `scripts/examples/gen_a04.py` 生成，导入 InoProShop V1.10.0.3 编译分类 **0 错误 / 101 警告**（警告全是模板自带的枚举转换）。
> 前置阅读：`step-sequence.md`（单个步序网络）、`process-flow.md`（延时/超时/报警/中断）、`../edge-detection.md`（框的 EN 边沿）。

---

## 0. 先选对容器（选错整件事白做）

工站流程有三种写法，只有第三种是模板的做法：

| 写法 | 结果 |
|---|---|
| 新建独立 `PROGRAM` 挂 `MainTask` | 能编译、能跑，但和模板的工站体系不接：HMI 看不到本工站步号、单步/单站模式失效、总控不知道这个工站 |
| 新建子程序、由总控调用 | 同样游离在工站体系外，还要额外接线 |
| **写进工站自动 POU 的动作槽 `A0x`** | 模板原生写法。用户原话（2026-11-28）：**「正常是将A00_4写流程，不用调用子程序，内部已经调用完成了」** |

---

## 1. 动作槽在树里的位置

```
Device
└── PLC 逻辑
    └── Application
        └── F21_POU_Station1_工站1_搬运移栽        （Folder）
            └── STN1_02_Auto                    （PRG，ST）
                ├── A00_上料移栽                  （动作，LD）
                ├── A01_中转移栽
                ├── A02_下料移栽
                ├── A03_下料翻转
                ├── A04_                          ← 第 5 个动作槽，数组下标 4
                └── … A09_
```

宿主 `STN1_02_Auto` 的 ST 体里有一整段**无条件调用**（原导出约 11875–11885 行，注释 `//____子程序调用`）：

```iecst
A00_上料移栽();
A01_中转移栽();
A02_下料移栽();
A03_下料翻转();
A04_();
A05_();
…
A09_();
```

所以动作槽天然每个周期都被调用——**不需要任何接线、不需要挂 `MainTask`**。

---

## 2. 动作对象和 `PROGRAM` 不一样

| 项 | 动作 `A0x` |
|---|---|
| TypeGuid | `8ac092e5-3128-4e26-9e7e-11016c6684f2`（ActionEntry） |
| ParentGuid | 宿主 POU 的 Guid（如 `1e1af19e-9582-40b0-975f-b4f47f49da10` = `STN1_02_Auto`） |
| EmbeddedTypeGuids | `25e509de-33d4-4447-93f8-c9e4ea381c8b`（LD） |
| `Interface` / `TextLines` | **没有** |
| 声明区 `VAR` | **没有**（只能用宿主 POU 与全局符号） |
| 改名 | **不支持**：`old.rename(u"A04__old_tmp")` 报 `名称 'A04__old_tmp' 对于本工程无效。` |
| 删除 | `old.remove()` 可用（不可撤销，回滚只能靠 `.project` 备份） |
| 槽位下标 | **动作名尾号**：`A04_` → `4` |

所以变量一律落在这套现成容器上：

```
STNControl[1].xAutoing                // 自动运行总使能
STNControl[1].aiAutoStep[4]           // 当前步（唯一状态源，只读）
STNControl[1].aiAutoStepBuffer[4]     // 下一步（跳步只写它）
STNControl[1].awstrAutoDescription[4] // 当前步描述（HMI 显示）
v_aFBStepLogger[4]                    // 步序日志实例
```

`STNControl : ARRAY[0..20] OF Struct_StationControl` 是模板 `F01_Variable` 里的现成数组（0 总控 / 1 上料移栽 / 2 擦拭 / 3..20 空闲），**不要新建结构体**。

---

## 3. `A04_` 里已经有的 6 个网络（不要重建）

| 网络名 | 作用 | 处理 |
|---|---|---|
| `Network000000_步序号记录器` | `FB_StepLogger` 实例，把步号/描述/日志送 HMI | **保留** |
| `Network000001_步序号缓存处理` | 单步 / 单站 / 总控 三路放行 `aiAutoStep := aiAutoStepBuffer` | **保留** |
| `Network000002_流程开始` | `10000 → 10` | **保留** |
| `Network000003_安全自检` | `10 → 100`，逐缸复位、逐轴回安全位 | **保留**（本项目里只做到 100 前一跳） |
| `Network000004_工位判断跳转` | `100 → 1000`（本工位直接进取料段） | **保留** |
| `Network000005_流程` | **空** | **替换成取放料步序** |

要写的只有最后这一个网络。生成时把前 5 个原样留下，把「流程」换成步序网络。

---

## 4. 生成：保留前 5 个网络，拼步序

```python
import io, re
import xml.etree.ElementTree as ET
import ldgen as L

# 只认网络节点：Type 是 Network（d9a99d73-…）的 Single
G_NET = u'<Single Type="{d9a99d73-b633-47db-b876-a752acb25871}"'

s = io.open(TPL_A04, "r", encoding="utf-8").read()
key = u'<List2 Name="NetworkList">'
i = s.find(key)
inner_start = i + len(key)
j = L.find_list2_end(s, i)                 # 深度配对，别用字符串 find 找 </List2>
inner = s[inner_start: j - len(u'</List2>')]

starts = [m.start() for m in re.finditer(re.escape(G_NET), inner)]
blocks = [inner[starts[k]: starts[k + 1] if k + 1 < len(starts) else len(inner)]
          for k in range(len(starts))]
kept = blocks[:5]                          # 只留骨架 5 个

s2 = s[:inner_start] + u"\n" + u"\n".join(kept + nets) + u"\n  " + s[j - len(u'</List2>'):]
s2 = L.renumber(s2, [0])                   # 全表 Id 重编，必须
# 再校：Id 无重复 + UniqueIdGenerator = max(Id)+1
```

生成前先把 `ldgen` 的四个语义全局指到第 4 号槽（`step_net` / `step_net2` / `judge_net` / `coil_tree` 都读它们）：

```python
L.AUTOING = u"STNControl[1].xAutoing"
L.STEP    = u"STNControl[1].aiAutoStep[4]"
L.BUF     = u"STNControl[1].aiAutoStepBuffer[4]"
L.DESC    = u"STNControl[1].awstrAutoDescription[4]"
```

---

## 5. 步序（本次样本）

| 步号 | 描述 | 动作 | 完成条件 |
|---|---|---|---|
| 1000 | 夹紧缸复位、A0 去取料位 | `FC_CylinderExe(C0,0)` + `FC_AxisAbsGo(A0,A0P_上料机取料位)` | `AND(C0.xDone, A0.o_xAbsDone)` |
| 1010 | A1 去取料位 | `FC_AxisAbsGo(A1,A1P_上料机取料位)` | `A1.o_xAbsDone` |
| 1020 | 等上料机请求取料 | — | `G_xS1上料机请求取料` |
| 1030 / 1040 / 1050 | C2 伸出 → C1 伸出 → C0 夹紧（抓料） | 三个 `FC_CylinderExe(…,1)` | 各自 `xDone` |
| 1060 / 1070 | C1 复位 → C2 缩回 | `FC_CylinderExe(…,0)` | 各自 `xDone` |
| 1080 | A0/A1 去擦拭 A1 平台 1 放料位 | 两个 `FC_AxisAbsGo` | `AND(A0.o_xAbsDone, A1.o_xAbsDone)` |
| 1090 | 等擦拭平台请求放料 | — | `G_xS2擦拭A1平台1请求上料移栽放料` |
| 1100–1140 | C2 伸出 → C1 伸出 → C0 复位（放料）→ C1 复位 → C2 缩回 | 五个 `FC_CylinderExe` | 各自 `xDone` |
| 1150 | 本工位完成 | — | 无条件 `MOVE 100` |

符号全部是模板现成的：`A0_上料移栽直线电机轴` / `A1_上料移栽R轴` / `C0_上料移载夹紧气缸` / `C1_上料移载升降气缸` / `C2_上料移载伸出气缸` / `G_astCylinder[…]` / `G_astAxis[…]`。

---

## 6. 替换动作：`remove` 旧 + `import_native` 新

```python
old = find_action(host, u"A04_")        # 宿主 POU 的直接子对象里按名字找
old.remove()
system.process_messageloop()
r = host.import_native(SRC)              # 返回 NativeImportResult
```

⚠ 两条硬约束：

1. **动作不能改名让位**。`old.rename(u"A04__old_tmp")` 直接失败（见 §2），只能 `remove()`。
2. **同名对象存在时 `import_native` 会长时间无返回**（不是卡在 `projects.open`）。顺序必须是先 remove 再 import。

---

## 7. 验收（本次实测）

| 项 | 结果 |
|---|---|
| 隐藏桌面副本（`a04_test.project`）remove → import → build | `import: ok` / `编译完成 -- 0 错误, 101 警告`（104 条消息）/ `saved` |
| 写进实时工程 `D:\plc_study\study.project`（先备份 `.project`） | 同上，0 错误 / 101 警告 / `saved` |
| 实时导出核对 | `live_a04.native` 1,108,990 B / **22 个网络节点** / 含「取料位」6 处、「擦拭A1放料位」2 处 |
| 人眼 | IDE 里 `STN1_02_Auto_A04_` 标签页程序段 16/17 显示 1090、1100 步；消息栏 0 错误 |
| 生成器可复现 | 仓库版脚本连续两次运行产物**逐字节相同**（对象 GUID 也来自模板，不经 `build_doc` 重生成） |

⚠ 设备树可能仍只显示 6 个网络（树是缓存，未刷新）——**以导出为准**，别据此判断导入失败。

---

## 8. 坑表

| 现象 | 根因 | 正解 |
|---|---|---|
| 编译 0 错误，但工程里找不到这段流程 | 写成了新建 `PROGRAM`，没进动作槽 | 改写 `A0x` 动作 |
| 改动作名报 `名称 'A04__old_tmp' 对于本工程无效。` | 动作不支持改名 | `remove()` + `import_native()` |
| `import_native` 长时间不返回 | 同名动作已存在 | 先 `remove()` 再导入 |
| 设备树里只有 6 个网络 | 树缓存未刷新 | 导出核对网络数 |
| 动作里写 `VAR` 不生效 | 动作没有声明区 | 变量用宿主 / `STNControl[1]` |
| 步号不前进、描述不更新 | 骨架网络被删掉 | 保留前 5 个网络 |

---

## 9. 还没验证的

- 总控 `F20_POU_Station0_总控` 真实调用本工站后的联调（本次只验证到动作自身 0 错误）
- 多工站并行（`STNControl[4]` / `[5]`）同时跑
- `FB_StepLogger` 在 HMI 上的显示效果

---

## 附录 A · 独立 `PROGRAM` 版（只在工站没有自动 POU 宿主时用）

`assets/natives/prg_Stn3LoadSeq.native`（1,191,815 B / 31 网络 / 1145 个 Id，生成器 `scripts/examples/gen_a00_stn3.py`）把 8 段骨架全部写进一个独立 `PROGRAM`，变量用 `STNControl[3]`，验证时需临时挂 `MainTask`（否则不进编译单元，0 错误是假通过）。

它适合：工站没有动作槽宿主、要把骨架当教学样本、或要单独调试一段流程。**模板工程里不要这么做**——会绕开工站体系。

---

最后更新：2026-11-28（lead，v2：容器改为工站 POU 的动作槽 `A0x`）