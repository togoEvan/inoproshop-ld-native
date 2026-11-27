# 模式卡 02 · 完整工站流程（步序 + 延时 + 超时 + 报警 + 复位 + 中断）

> 状态：**已实验验证**（2026-11-27，InoProShop V1.10.0.3；隐藏桌面实例与用户工程各编译一次 = `0 错误, 101 警告`，101 条为模板固件既有警告）
> 修订：**v2（18:25–18:26）按用户两条规范重写** —— ① BOOL 量一律用线圈（S/R），禁用 MOVE；② 每条路末尾必须是线圈或功能框，不许空梯级。v1 的 37 网络版本作废。
> 母本：`D:/plc_study/study.project`（InoPack 包装模板升级副本），骨架克隆自 `A00_上料移栽`
> 成品：`assets/natives/prg_FlowDemo.native`（723,466 B / 35 网络 / 822 个 Id / 34 个声明变量）
> 生成器：`scripts/examples/gen_flow_ld.py`（依赖同目录 `ldgen.py`）

## 0. 这张卡解决什么

模式卡 01 只给了「一步一网络」的骨架，遇到真实工站会缺四件事：**延时怎么给、卡住怎么报警、报警后怎么复位、操作工扳到手动怎么立刻停下**。
这张卡把六件套补齐，并给出可直接跑的生成代码与四道验收。它对应的判断是：「你现在可以写流程了吗」——可以，前提是全套都在软件里编译过、且有负样本对照。

## 1. 能力边界（先看这个，避免误用）

| 能做 | 证据 |
| --- | --- |
| 步序推进 / 等待信号 / 分支跳转 | 35 网络，`0 错误` |
| 延时（TON，`t#500ms` / `t#3s`） | 6 个 TON 实例，全部被编译器接受 |
| 每步超时 + 报警码 | 3 个 3s 超时器 → 步 99，`iErrCode` 记步号 |
| 报警复位 | 步 99 判 `xReset` 上升 → 清报警、清码、回 0 |
| 手动/安全链中断 | 2 个中断网络放末尾，7 个输出每周期强制 FALSE |
| 计数（良品/不良） | ADD 框 EN 边沿，停几个周期都只 +1 |
| HMI 步描述 | `awstrAutoDescription` 每步写一次 WSTRING |

| 不能 / 未验证 | 原因 |
| --- | --- |
| 轴运动（`MC_*` / `HMC_*`） | 必须在轴控 FB 内部用 ST 写，LD 只放调用封装 FB |
| 通讯（TCP / Modbus） | 模板已有现成 FB，本卡未纳入 |
| 配方 / 变量数组批量 | 语法可用，未做实验对照 |
| 真机运行行为 | 没有目标 PLC，只到「编译通过 + 结构自检 + 离线仿真」 |

## 2. 结构配方（35 个网络的固定排布）

| 段 | 网络 | 内容 | 为什么必须在这个位置 |
| --- | --- | --- | --- |
| 提交 | 1 | `aiAutoStep := aiAutoStepBuffer` | 所有网络先读旧步号、只写缓冲，最后统一提交；否则同周期内后面网络会看到新步号 |
| 辅助位 | 2–5 | `bSafeStart` / `bNeedLoad` / `bNeedClamp` / `bNeedEject` | 把「本步 + 未到位」压成一个触点，主流程网络少一层比较框 |
| 计时 | 6–11 | 3 个 3s 超时 TON + 3 个保持 TON（500/300/500ms） | 必须在主流程之前：先算出超时标志，主流程才能在同一周期内跳走 |
| 主流程 | 12–26 | 0 待命 → 10 上料 → 15 保持 → 20 压紧 → 25 保持 → 30 检测 → 40 判定 →（良 50 → 55 → 90）/（不良 60 → 65 → 70 → 75 → 90）→ 99 报警 | 每个网络固定三梯级：写描述 → **线圈组**（BOOL 动作用 S/R）→ 写下一步；判定用 `judge_net`（一个比较框分出两条跳步） |
| 报警 | 主流程内（步 99） | 步 99：置位线圈 `xAlarm`，等 `xReset` 上升 → 回 0 | 报警步必须能自锁，否则复位后立刻又落回超时 |
| 复位 | 27–28 | 27：`xReset` 常闭 → 复位线圈 `xAlarm`；28：`iErrCode := 0`（MOVE INT） | 独立网络，避免与步 99 抢写同一变量 |
| 超时 | 29–31 | 3 个 `BRANCH{超时触点}`：`iErrCode := 步号` / `aiAutoStepBuffer := 99` | 两条都是 **MOVE 到 INT 变量**（数据量，合法）；**不许用空梯级凑 BRANCH 的 2 个树**，见 §2.5 |
| 中断 | 32–35 | 手动/安全断各两个网络：`abort_coils_net`（7 个复位线圈）+ `abort_clear_net`（清步序） | 必须最后且每周期无条件：本周期前面置的输出要能被撤掉 |

顺序铁律三条：**提交在最前、计时在主流程之前、中断在最后**。

## 2.5 BOOL 量一律用线圈，禁用 MOVE（用户规范）

用户原话（2026-11-27）：「1、BOOL量不要用move」「2、有些路最末尾没用线圈和功能块」。

| 目标变量类型 | 正确写法 | 错误写法（v1 犯过的） |
| --- | --- | --- |
| BOOL | 线圈：普通 `( )` / 置位 `(S)` / 复位 `(R)` | `MOVE TRUE → xOut` |
| INT / DINT / WORD | MOVE 框 | 线圈（编译器不认） |
| WSTRING | MOVE 框 | 同上 |
| 步序跳转 | MOVE 到 `aiAutoStepBuffer` | 直接写 `aiAutoStep` |

三种线圈的语义与 native 编码：

| 线圈 | 语义 | `Operand.Flags.Flags` |
| --- | --- | --- |
| 普通线圈 `( )` | 条件成立为 TRUE，不成立为 FALSE | 0 |
| 置位线圈 `(S)` | 条件成立置 TRUE，之后保持 | 2 |
| 复位线圈 `(R)` | 条件成立置 FALSE，之后保持 | 3 |

`ldgen.py`：`coil(var)` / `set_coil(var)` / `reset_coil(var)` 返回线圈操作数，**必须挂在 `netitem()` 的 `OutputItems` 上**（不能挂 `and_box`，见坑表最后一条）。

**一个梯级挂多个线圈是合法的**（单独验证过：`prg_CoilTest`，3 个并联线圈 S/R/普通 + 1 个单线圈网络，导入 + 挂 MainTask + build = 0 错误）。
所以「伸出时同时撤另一路」写成
`netitem(step_gate(10), [set_coil(xLoadExt), reset_coil(xLoadRet)])`
即可，不必拆成两个网络。

第二条规范的实操含义：`BRANCH` 的每棵树结尾要么落到线圈、要么落到框（MOVE / ADD / TON），**不许只有 `connector + outconn` 的空梯级**。
v1 用空梯级把 `BRANCH` 凑到 2 棵树，被用户否决；正解是该梯级填上真正要做的事（例如超时的第二条 MOVE），或者干脆不要这个 `BRANCH`。

注意区分：`MOVE` / `ADD` 框 `OutputItems` 里的输出连接器（`outconn`）是框的 ENO 连线，**不算空梯级**；违规的只有「整棵树里除连接器外什么都没有」。

## 3. TON 的真实结构（本卡最重要的新知识）

从母本 `A00_上料移栽` 里切出第一个 TON 框（字符区间 876005..887472，11,467 字符）逐字段对出来的结论：

- **`InputItems` 只有 2 个槽（IN、PT），没有 EN 槽** —— 这点和 MOVE / ADD 不同，照 MOVE 的 3 槽写法会多给一个 EN，导入后图形上会多出一个悬空引脚。
- `InputFlags` 是 `<Null Name="InputFlags" />`（单元素），不是 List2。
- `OutputItems` 是 2 个元素：`[Q, ET]`；Q 不接线时写 `<Null />`，ET 不接线时写一个 `Operand` 空值、`Type=TIME`。
- `InputParam = [IN, PT]` / `[BOOL, TIME]`；`OutputParam = [Q, ET]` / `[BOOL, TIME]`。
- `Instance` 是独立的 Operand 容器：`Operand=实例名`、`Type=TON`、`IsInstance=True`（不是普通操作数）。
- 框头 `EN=False`、`ENO=False`（TON 不用 EN）。
- 该 TON 在母本里位于 `BRANCH` 的 Trees 中，说明框可以作为分支梯级；但**不要把 TON 放进门控分支**（见下节第 1 条）。

`ldgen.py` 对应构造函数：

    ton_box(inst, in_item, pt_text, q_var=None, et_var=None)

用法：`ton_box(u"fbTLoad", eq_box(value_pin(STEP, u"INT"), value_pin(u"10", u"INT")), u"t#3s", u"bLoadTimeout")`

## 4. 三个必须踩对的点（错了就静默错，编译不一定报）

### ① TON 必须每周期执行，不能放进 BRANCH 门控

门控分支不导通时框根本不执行，`ET` / `Q` 保持上一次的值 → 第二次进同一步时定时器已经计满，延时形同不存在、超时器立刻跳闸。
编译 0 错误、单次走查也看不出来，只有跑第二轮才暴露。

正解：TON 单独一个网络，`IN` 直接吃比较框（`aiAutoStep = N`），离开本步 `IN=FALSE` 自动复位，进入本步从 0 开始计。

### ② 一次性动作挂在框的 EN 引脚上（`InputFlags[0].Flags=16`）

上一版我在触点把 `Flags` 改成 2 想当作上升沿 —— IDE 原样收下、编译 0 错误、导出回来还是 2，但**图形上没有边沿标记，也不产生边沿语义**（详见 `references/edge-detection.md`）。
正解是框的第一项 `InputFlags`：`Flags=16` 表示该输入引脚启用边沿检测，图形上 EN 引脚外侧会多一个向上的箭头。

### ③ 中断网络放最后且每周期无条件执行

不加边沿、不做门控。同时写 `aiAutoStep := 0` 和 `aiAutoStepBuffer := 0`，否则下一周期网络 1 会把缓冲区里的旧步号又提交回来。
中断时不报警、计数不回滚（计数已经 +1 的成品不能撤回）。

## 5. 从零生成

    import sys
    sys.path.insert(0, r"<仓库>/scripts/examples")
    import ldgen as L
    L.SKEL = r"<一个已验证的 PRG native，作骨架>"

    nets = [L.buf_commit_net()]
    # 计时：每步一个 TON，单独成网络，IN 直接吃比较框（不能放进 BRANCH 门控）
    nets.append(L.ton_net(u"fbTLoad",
                          L.eq_box(L.value_pin(L.STEP, u"INT"), L.value_pin(u"10", u"INT")),
                          u"t#3s", u"取料超时"))
    # 主流程：写描述 → 线圈组（S/R） → 写下一步
    nets.append(L.step_net2(10, u"上料伸出",
                            [L.set_coil(u"xLoadExt"), L.reset_coil(u"xLoadRet")],
                            15, done_contact=L.contact(u"xLoadAtPos")))
    # 判定：一个比较框分出两条跳步（末尾都是 MOVE → 合规）
    nets.append(L.judge_net(40, u"判定",
                            [(L.contact(u"xScanOK"), 50),
                             (L.contact(u"xScanOK", neg=True), 60)]))
    # 超时：两条 MOVE（INT），不写空梯级
    nets.append(L.timeout_net(L.contact(u"fbTLoad.Q"), 10, u"取料超时报警"))
    # 中断放最后、每周期无条件
    nets.append(L.abort_coils_net(L.contact(u"xManualMode"),
                                  [L.reset_coil(u"xLoadExt"), L.reset_coil(u"xLoadRet")],
                                  u"手动中断-撤输出"))
    L.build_doc(L.SKEL, u"prg_FlowDemo", DECL, nets, r"<输出路径>.native")

完整可跑版本见 `scripts/examples/gen_flow_ld.py`（生成 → 自检 → 打印结构计数 → 写文件）。

## 6. 验收链（四道，缺一道就可能假通过）

1. **结构自检**：网络数、Id 全唯一、各类框计数、`InputFlags=(16,...)` 的出现次数、触点 `Flags=2` 必须为 0。
2. **符号表**：`check_symbols.py` 跑一遍，所有操作数必须在声明区或全局表里有定义（TON 的 Q 写成未声明变量时**编译器不报错**，只有这道能抓）。
3. **真机 build**：隐藏桌面实例导入 → 挂进 MainTask（没挂就不进编译单元，0 错误是假通过）→ build → 读编译分类，必须看到「编译完成 -- 0 错误」。
4. **负样本对照**：改动一处 → 编译器必须报错。证明它真在编这个对象、0 错误不是缓存。

本次实测数据：

| 项 | 结果 |
| --- | --- |
| 结构 | 35 网络 / 806 个 Id 全唯一 max=806 / AND 48 · MOVE 43 · EQ 21 · ADD 2 · TON 6 · 线圈 45（普通 4 / S 10 / R 31） |
| MOVE 目标类型 | INT 28 + WSTRING(49) 15，**BOOL 0 个**（符合 §2.5） |
| 符号 | 34 个声明变量，235 个操作数去掉 74 个常量后全部有定义 → PASS |
| build（隐藏实例） | `97f48d64` 共 104 条：开始构建 → 代码典型化 → `编译完成 -- 0 错误, 101 警告` |
| build（用户工程） | 导入 35 网络 → 挂 MainTask → `97f48d64 n=104 err=0 warn=101`（101 条模板既有警告） |
| 图形（人眼） | 用户在 IDE 里确认：程序段 2 三缸安全链 → 线圈 `bSafeStart`；程序段 3 EQ → 线圈 `bNeedLoad`；分支内 `(S) xLoadExt` / `(R) xLoadRet` 两个线圈并列正常（v2 之前是空方块） |
| 负样本 | v1 改一处操作数 → 报 2 条错误（见坑表最后两行） |

## 7. 坑表（都有原文）

| 现象 | 真正原因 | 正解 |
| --- | --- | --- |
| `'AND'需要至少'2' 个操作数`（3 条） | 用 `coil_net([eq_box(...)])` 只有一个条件，AND 框只有 1 个输入槽 | 要么补第二个条件，要么去掉这层 AND 直接把 EQ 结果接到用它的框的 EN |
| build 只报 3 条 AND，没报 3 个未定义变量 | TON 的 `Q` 输出到未声明变量，**编译器不校验** | `check_symbols.py` 必须单独跑 |
| 导入抛 `已标识项中有一项的格式无效。` | 负样本只改了 `Operand` 的文本、没换 Guid/名，IDE 在解析阶段就拒绝 | 负样本必须换 `Guid` 与对象名；且这种负样本只能证明「编译器在编新对象」，不能证明语义错误被捕获 |
| 导入后构建报 `没有定义标识符'prg_FlowDemoNeg'` `需要程序名、函数或功能块实例替代 'prg_FlowDemoNeg'` | 上一条的连带结果：对象没进工程，但任务列表里已经被 `pous.add` 过 | 挂任务前先确认 `found=True` |
| 同名对象已存在时 `import_native` **卡死 85 秒以上、无返回无报错** | 副本工程里已有同名 `prg_FlowDemo`，IDE 在处理同名导入时进入内部等待 | 导入前先 `o.remove()` 掉同名对象并 `process_messageloop()`；写真实工程用「改名让位」法 |
| 用户看图后指出「有些路最末尾没用线圈和功能块」 | v1 用 `connector + outconn` 空梯级把 `BRANCH` 凑到 2 棵树 | 每棵树结尾必须是线圈或框（见 §2.5）；超时那条改成第二条 MOVE |
| 用户截图指出「程序段 2 末尾还是一个空方块」 | 线圈挂在 `AND` 框（`G_BOX`）的 `OutputItems` 上 —— IDE 只在 NETITEM 或触点 PIN 的 `OutputItems` 里认线圈，挂在框上画成一个空占位（编译照样 0 错误） | 用 `netitem(条件项, [线圈...])` 包一层：A00 实测线圈挂 NETITEM 15 处、挂触点 PIN 5 处、挂 BOX **0** 处 |

## 8. 还没验证的

- **语义级负样本**：想造「逻辑写错但语法正确」的样本，必须改结构化节点（比如把 `EQ` 的两个操作数互换）而不是改文本，否则 import 直接拒绝。
- **真机运行**：没有目标 PLC，步序的实际时序（扫描周期抖动、外部信号抖动）未测。
- **中断与超时同时发生**的优先级：本卡让中断赢（放最后写），但没有专门造这个并发场景。

---

最后更新：2026-11-27 18:52（lead，v3 修线圈载体：线圈必须挂 NETITEM.OutputItems，挂 AND 框上 IDE 只画空方块）