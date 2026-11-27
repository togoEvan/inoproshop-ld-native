# 边沿检测：LD 内建的上升沿在哪一格

> 结论先行：InoProShop 的梯形图**有内建边沿检测**，位置在**功能框的第 0 个输入引脚（EN）**，
> 编码是 `InputFlags[0].Flags = 16` + `Fixed = True`。
> 触点没有边沿语义；不需要为它写 `R_TRIG` / `F_TRIG`，也不需要手搓「本周步号 ≠ 上周期步号」的比较网络。

本文替代两个旧结论：

1. `references/native-structure.md` §18 曾写「触点 Flags 值域仅 0/1，无 P/N 边沿形态，边沿要用 R_TRIG/F_TRIG FB」——**边沿是内建的，位置在框上**。
2. 同文件 §③ 曾把 `InputFlags` 里的 `16` 解释为「该引脚是电源流引脚」——**它表示「该引脚启用边沿检测」**；普通框的 EN 引脚并不带 16。

---

## 1. 三种做法对比

| 做法 | 怎么写 | 结论 |
|---|---|---|
| ① 手搓比较网络 | 存「上周期步号」，本周期比较，反相后串在 EN 前（4~8 个网络） | 能跑，但网络量翻倍，且必须排在主流程之前，顺序错就失效 |
| ② 触点 `Operand.Flags.Flags=2` | 把触点 Flags 改成 2 | **无效**。IDE 会接受并原样保留，导入 0 错误、导出往返也保住，但它不产生边沿。 |
| ③ 框 `InputFlags[0].Flags=16` | 框的第 0 个输入引脚 flags 写 16 | **正解**。IDE 图形上给 EN 引脚加边沿标记，语义就是「该框只在上升沿执行一次」。 |

②的教训值得单列：**「导入成功 + 编译 0 错误 + 导出保真」三条合起来仍可能什么都没发生**——
IDE 只是把一个它不解释的位形原样存着。这类验证必须有一个「行为对照」或「用户工整样本」兜底，
否则就是自己造样本、自己验证的循环论证。

---

## 2. 结构长什么样

### MOVE（EN + IN，两引脚）

```xml
<List2 Name="InputFlags">
  <Single Type="{668066f2-6069-46b3-8962-8db8d13d7db2}">   <!-- EN 引脚 -->
    <Single Name="Extensible" Type="bool">False</Single>
    <Single Name="Fixed" Type="bool">True</Single>      <!-- 带边沿时 Fixed 也是 True -->
    <Single Name="Flags" Type="int">16</Single>
  </Single>
  <Single Type="{668066f2-...}">                          <!-- IN 引脚 -->
    <Single Name="Extensible" Type="bool">False</Single>
    <Single Name="Fixed" Type="bool">False</Single>
    <Single Name="Flags" Type="int">0</Single>
  </Single>
</List2>
```

### 三条硬规则

1. **项数 = 输入引脚数**，不是随便写的长度。MOVE 两项 `(16,0)`、ADD 三项 `(16,0,0)`、`FC_CylinderExe` 四引脚 `(16,0,0,0)`。
2. **只有第 0 项（EN）会被解释**，其余固定 0。目前没有见过非第 0 项非 0 的样本。
3. **`<Null Name="InputFlags" />` = 无边沿、每周期执行**。这是绝大多数框的默认形态，
   所以「我的框全都 Null」等价于「我的所有副作用框都在每周期执行」。

### 对照：普通 MOVE 与带边沿的 MOVE

```text
普通 MOVE : InputFlags = <Null/>                       ← 每周期执行
带边沿 MOVE: InputFlags = List2[(16,True), (0,False)]   ← 只在该引脚上升沿执行
```

同一 POU 里两种 MOVE 共存，是本节最硬的证据：**差异只可能来自用户是否加了边沿**。

---

## 3. 生成器写法

生成 native 时按框的引脚数写 flags 块：

```python
G_PINFLAGS = "{668066f2-6069-46b3-8962-8db8d13d7db2}"

def input_flags(n_pins, edge=False):
    if not edge:
        return '<Null Name="InputFlags" />'
    items = []
    for i in range(n_pins):
        items.append(
            '<Single Type="%s"><Single Name="Extensible" Type="bool">False</Single>'
            '<Single Name="Fixed" Type="bool">%s</Single>'
            '<Single Name="Flags" Type="int">%d</Single></Single>'
            % (G_PINFLAGS, "True" if i == 0 else "False", 16 if i == 0 else 0))
    return '<List2 Name="InputFlags">' + "".join(items) + '</List2>'
```

生成后自检：统计 `Flags=16` 的**处数应等于「你要加边沿的动作数」**。
例如状态机里只有 3 处一次性动作（启动、良品计数、不良计数），就应当恰好 3 处；
多出来说明有框被误加了边沿，少一处说明漏了。

---

## 4. 证据链（2026-11-27 实测）

| # | 步骤 | 结果 |
|---|---|---|
| ① | 用户在 IDE 里手工挂一个「上升沿 + MOVE」网络 | 该网络**没有触点**，母线直连 MOVE 的 EN；MOVE 的 `InputFlags=(16,0)`，同 POU 其它 MOVE 全是 `Null` |
| ② | 语料普查（46 个 .native） | `InputFlags` 非空只有 `(16,0,0)` 152 处、`(16,0,0,0)` 142 处，全是「引脚数项、第 0 项 16」 |
| ③ | 隐藏桌面实例导入 + 挂 MainTask + build | `编译完成 -- 0 错误, 1 警告`（真编译，三条消息齐全） |
| ④ | 导出往返（`if_after.native`） | 14 网络 / 497,753 B，`InputFlags` 三处 `(16,0,0)`×2 + `(16,0)`×1 全部保住 |
| ⑤ | 落地真实工程 | 静默导入 1.78 s / 14 网络 / saved；预编译 0 错误 / 编译 0 错误 |

### 负样本怎么做（这条很重要）

要证明「边沿真的生效」，负样本**不能只把 flags 改回 Null 就完事**——那只是回到旧形态，
编译器不会报错，两张都是 0 错误。有效的做法是二选一：

- **行为仿真**：按周期推进状态机，断言「该步停留 N 个周期，计数只 +1」；
- **图形确认**：人在 IDE 里看 EN 引脚上有没有那个边沿标记（隐藏桌面实例看不到图形，必须借人眼）。

---

## 5. 判据与坑

1. **上电 / 复位后，信号必须先出现一次 FALSE 才能触发**。所有边沿都是这样，不是缺陷；
   但要在声明区注释里写清楚，否则现场会报「第一次按没反应」。
2. **不是所有框都需要边沿**。只有「执行一次会产生副作用」的框才加：计数（ADD）、赋值（MOVE）、
   触发型 FB 调用（Execute 类）。纯逻辑框（AND / EQ / 比较）加了反而会让逻辑丢掉一个周期。
3. **边沿与「步门控」是两件事**，不要互相替代：
   - 步门控（`EQ(step, N)`）决定「这一步要不要跑」；
   - 边沿决定「即使一直在这一步，也只跑一次」。
   两个都要有：少了门控会在别的步乱跑，少了边沿会在同一步跑 N 次。
4. **不要用触点 Flags 模拟边沿**（做法②）。它会静默成功，是典型的假通过。

---

## 6. 尚未验证

- 边沿是否只对第 0 个输入引脚有效：目前所有样本都只在 EN 上，其余引脚 0。
- 除 MOVE / ADD / Function 调用 / `FC_CylinderExe` 外，TON、比较框、BRANCH 能否挂边沿：无样本。
- 下降沿（`Fixed`/`Flags` 的另一取值）是否存在：未探测到，需要用户手工挂一个下降沿样本才能反推。

---

## 7. 相关

- 结构字段全量：`references/native-structure.md` §③（InputFlags）、§18（触点 Flags）
- 假通过案例：`references/false-pass-catalog.md`
- 零打扰写入链路：`references/mcp-bridge.md`
