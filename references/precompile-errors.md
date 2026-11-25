# 预编译错误对照表

## 消息分类 GUID（验收要读两个分类）

| 分类 | GUID | 说明 |
|------|------|------|
| 预编译 | `217bc73e-759b-4a3c-bfa1-991c938a6541` | 结构错误：槽位不符、IsContact 错、声明缺失、红框 |
| 编译 | `97f48d64-a2a3-4856-b640-75c046e37ea9` | 语义错误：如 `'AND'需要至少'2' 个操作数` |
| 脚本消息 | `194b48a9-ab51-43ae-b9a9-51d3edaaddf3` | |
| 导出/导入 | `2af7707f-6167-4a76-a40e-430967be0f18` | |
| 库管理器 | `56a60174-4139-411b-86c7-df0da1cfc088` | |

⚠️ **两个分类抓不同的错误，缺一不可。** 只跑「检查程序」只看预编译，会漏掉只在 `build()` 阶段报的错（见 §2b）。`task_check.py` 已同时跑两者。

## 错误 → 根因 → 修复

### 1. `不允许对类型 'SINT' 进行 'NOT' 操作`

- **根因**：值输入引脚（IN 槽）从触点模板克隆，残留 `IsContact=True` 和/或内部 `Flags=1`（NOT 标志），IDE 对 INT 常量做触点取反逻辑
- **修复**：IN 槽位节点 `IsContact=False` + Operand 内部 `Flags/Flags=0`、`Fixed=False`
- **特征**：每个 MOVE 框恰好 1 个错误；与触点写法、EN 槽内容、BoxType/CallType/IsBoxType 全无关（4 个受控实验证明）

### 2. AND 框报"需要至少 2 操作数"

- **根因**：AND 框 InputItems 里只放了 1 个触点
- **修复**：AND 框至少 2 个触点；单条件时补一个 TRUE 触点

### 2b. 一个 rung 只有一个条件时，顶层 AND 只有 1 个输入

- **症状**：`检查程序`（预编译 `217bc73e`）**0 错误**，但构建（编译 `97f48d64`）报 N 条
  `'AND'需要至少'2' 个操作数`，N = 单条件 rung 的条数。输出映射段（`步标志 -> 输出`）、
  单触点置位段最容易中招
- **根因**：每个 NETWORK 的 `RValue` 本身就是 AND 框，`InputItems` 槽位数 = 输入数。
  生成脚本按「条件个数」append 槽位时，单条件 rung 只剩 1 个槽
- **修复**：条件数 < 2 时补一个 `TRUE` 触点（`Operand=TRUE`、内部 `Flags=0`、`IsContact=True`）。
  语义不变，图形上多一个 TRUE 常开点
- **教训**：预编译 0 错误 ≠ 能构建。交付前预编译、编译两个分类都要读一遍

### 3. IDE 红框（画面红框+红波浪线）

- **根因 A**：功能框 InputItems 槽位数 != InputParam 参数数（如 6 触点塞进 [EN, IN] 2 槽）
- **根因 B**：IN 引脚 `Type=BOOL`（应为 INT）或 `Boolean=True`
- **修复**：槽位数严格对齐；常量引脚 `Type=INT` + `Boolean=False`

### 4. `已标识项中有一项的格式无效`

- **根因**：MOVE 框挂错位置（NETITEM.OutputItems 或 NETITEM.RValue）
- **修复**：MOVE 框直接挂 `Network/NetworkItems`

### 4b. `在绘制该网络的时候遇到错误 / 不能显示内容 / 索引超出了数组界限`

- **特征**：**预编译 0 错误、编译 0 错误**，但梯形图编辑器打开该程序段时弹出红色错误条，
  梯形图区域一片空白，`堆栈跟踪` 里能看到 `IBoxTreeParallel`（`...Visit(IBoxTreeParallel)`）。
  程序本身能编译、能下载、能运行，只是**编辑器画不出来**。
- **根因**：分支组 `{827b9ec2}` 的 `Trees` 只有 **1 条**支路。IDE 的分支组绘制器
  `IBoxTreeParallel` 按「≥2 条支路」计算几何位置，单支路时内部数组越界。
- **为什么双分类验收抓不到**：这是**纯图形渲染**问题，不参与预编译也不参与构建。
- **修复**：单支路时**不要用 `branch()`、不要套 `NETITEM`**，直接把 AND 框挂 `NetworkItems`。
  参考 `scripts/examples/make_fb_call_test.py` 的 `build_networks()`（网络2 就是单支路直挂）。
- **自检**：枚举所有分支组的 `Trees` 长度，任何一处为 1 都是隐患。

```python
# 扫描全部网络，找出 Trees < 2 的分支组
for e in root.iter():
    if e.tag == 'Single' and (e.get('Type') or '').startswith('{827b9ec2'):
        trees = [c for c in e if c.get('Name') == 'Trees'][0]
        if len(list(trees)) < 2:
            print('BAD branch: Trees =', len(list(trees)))
```

### 5. 预编译分类读出来是 0 但其实有错（假象）

- **根因**：`system.clear_messages()` 清空后，预编译由 IDE 后台**异步**填充，立即读会漏
- **修复**：执行「检查程序」命令（`system.commands` 里 name=="检查程序"，tokens=project/buildactiveapp，索引约 91）后 `process_messageloop()` + 短等待再读；或直接读当前消息（不 clear）

### 6. `C0046: 没有定义标识符'xxx'`（批量几十个）

- **根因**：native 里的 `Interface/TextDocument/TextLines` 声明区**只写了起保停 3 个变量**，
  但梯形图逻辑引用了状态机的 8 个变量（`iState` / `xAlarm` / `xAutoMode` / `xInitDone` /
  `xAutoRun` / `xIniting` / `xStopClear` / `xStepMode`）。
  **native 导入只搬图形和声明，不会替你补声明**——图形引用了什么，声明区就必须手写什么。
- **特征**：错误条数 = 各未声明标识符在图中引用次数之和。例：8+8+8+8+4+4+3+2 = **45**。
  一个标识符出现几次就报几次，所以条数往往远大于变量个数。
- **修复**：在 `TextLines` 的 `VAR ... END_VAR` 之间补声明行。
  - 克隆已有行的 `<Single Type="{a5de0b0b-1cb5-4913-ac21-9d70293ec00d}">` 节点，
    改 `Id` 与 `Text`，插到 `END_VAR` 之前。
  - **`Id` 必须全表唯一且顺序递增**：插完后按数组顺序从 900 重排一遍最省事。
  - `Text` 是纯字符串，中文注释字节级完好，无需转义。
- **教训**：改完图形一定要**先核对声明区**再导入，否则必然收获一堆 C0046。

### 7. 图形上出现「两个 TRUE 串联」

- **根因**：分支组 `{827b9ec2}` 的 `Input` 槽已经放了公共前缀 `TRUE` 触点，
  而每个支路的 EN 条件 AND 框里又放了一个 `TRUE`。
  逻辑上 `TRUE AND TRUE` 不影响结果（预编译也是 0 错误），但图形冗余、不符合「公共前缀只画一次」的要求。
- **修复**：删掉每个 EN 条件 AND 框 `InputItems` 里的第一个 `TRUE` 引脚（`Operand=="TRUE"` 且内部 `Flags==0`），
  **保留**分支组 `Input` 的公共 `TRUE`。删除后条件框至少还要剩 2 个操作数（否则补回）。
- **注意**：只删 `BoxType=="MOVE"` 框的 `InputItems[0]` 那个 AND 框里的 TRUE；
  别去动分支组 `Input`，也别动 `NetworkItems` 层的 AND。

### 8. 一次性 40+ 条 `符号 'PROGRAM'/'FUNCTION_BLOCK'/'BOOL' 不能识别` + `应该用';' 替换'...'`

> 2026-11-25 实测：预编译 **48 条 Error**，全部集中在新建的 `prg_LdLearnTest` / `fb_LdLearnTest` 两个 POU。

- **症状**：报错文本长这样（每个声明行炸 2~3 条）：
  ```
  [Error] 符号'FUNCTION_BLOCK' 不能识别                    (number=9)
  [Error] 应该用';' 替换'fb_LdLearnTest'                   (number=189)
  [Error] 符号'VAR_INPUT' 不能识别                          (number=9)
  [Error] 符号'BOOL' 不能识别                              (number=9)
  [Error] POU应以';'结尾                                   (number=190)
  [Error] 没有定义标识符'fbDelay'                           (number=46)
  ```
  伴随一批 `[Warning] 标签 'XTIMERIN' 未被引用`（number=118）。
- **根因**：**POU 声明被写进了 EXECUTE 框的 ST 代码块，真正的 `Interface` 声明区还留着骨架的旧变量。**
  生成脚本改声明区时用了裸 `find`：
  ```python
  p2 = raw.find('<Array Name="TextLines"')   # ✗ 错
  ```
  一份 native 里 `TextLines` 至少两处：`Interface` 下的 POU 声明区，和 EXECUTE 框 `STSnippet` 里的 ST 代码。
  而 `List2[NetworkList]` 在文档里排在 `Interface` **之前**，所以只要网络里有 EXECUTE 框，
  第一个 `TextLines` 就是 ST 代码块 → 声明被塞进 ST，ST 代码被覆盖成 `PROGRAM xxx / VAR ...`。
  编译器于是把 `PROGRAM`/`FUNCTION_BLOCK`/`BOOL` 当普通标识符解析，逐行炸。
- **修复**：锚定 `Interface` 之后再找：
  ```python
  p2 = raw.find('<Array Name="TextLines"', raw.find('<Single Name="Interface"'))
  ```
- **自检（必做，往返 diff 查不出来）**：
  ```python
  a = s.find('<Single Name="Interface"')
  p = s.find('<Array Name="TextLines"', a)
  print(re.findall(r'Name="Text" Type="string">(.*?)</Single>', s[p:s.find('</Array>', p)], re.S)[:3])
  # 期望第一行是 'PROGRAM prg_Xxx' 或 'FUNCTION_BLOCK fb_Xxx'
  ```
  ⚠ **往返 diff PASS 不代表对**：源文件错时 IDE 原样保留，`rt_diff` 照样 `diffs=0`。

### 9. 验收脚本报 `total=0 errors=0` 并判「通过」，但 IDE 里明明有 48 条 Error

> 2026-11-25 实测：这是**验收脚本自己的 bug**，比第 8 条更危险——它会让错误静默通过。

- **症状**：`check.log` 输出
  ```
  === 预编译 : total=0 errors=0 ===
  === 编译 : total=3 errors=0 ===
  === 验收结论 : 通过 ===
  ```
  但用 `task_allmsgs.py` 全分类 dump 出来，预编译分类 `count=69`（含 48 条 Error）。
- **根因**：`get_message_objects` 要传**分类对象**而不是 GUID 字符串。按 GUID 匹配分类时写成：
  ```python
  for c in list(system.get_message_categories()):
      try:
          if unicode(c) == guid:
              return list(system.get_message_objects(c))
      except Exception:
          continue
  return []          # ✗ 匹配不到就返回空 → 被当成「0 错误」
  ```
  `except Exception: continue` 把「读失败」和「没匹配上」全吞了，`return []` 再把它伪装成干净。
- **修复**：**匹配不到必须抛错**，并先打印全部分类便于核对：
  ```python
  cats = list(system.get_message_categories())
  for c in cats:
      L(u"  cat %s" % unicode(c))
  def _objs_by_guid(guid):
      for c in cats:
          if unicode(c) == guid:
              return list(system.get_message_objects(c))   # 失败就让它抛
      raise RuntimeError(u"消息分类 %s 未找到，不得当作 0 错误" % guid)
  ```
- **教训**：验收脚本**宁可崩，也不能把「读不到」当成「没错误」**。
  正常 `check.log` 里应该能看到 5 个分类全部列出；看不到分类清单 = 没真读到，结论无效。

## 编译分类的可忽略警告

- `[Warning] 未加载库(CmpLog)...` —— 库未加载警告，与逻辑无关，可忽略

---

## ⚠ 编译器查不出来的结构错误（不报错，但结构是错的）

下面这些**不会**产生任何 Error 或 Warning，双分类 0 错误、往返 diff 也 PASS，
只能靠「与真实样本逐字段比对」发现。列在这里是因为它们的危害和报错一样大——
错误结构会被 IDE 静默接受并原样导出，下次谁照抄谁错。

### A. `TON` 的 `OutputItems` 少写一项

- **错在哪**：把「`OutputItems` 第 0 项恒为 `<Null/>`（对应 ENO）」当死规矩，
  给 TON 写 `OutputParam=['Q','ET']` 却只输出 1 个 `<Null/>`
- **对的是什么**：`TON` 的 `EN`/`ENO` 都是 `False`，`OutputParam` **不含 ENO**，
  是 `['Q','ET']` 两项；两个输出都不接线就写 **两个** `<Null/>`
  （InoPack `HC_ValveCtrl` 7 处 TON 全是 `[Null, Null]`）
- **规律**（19/19 样本 0 例外）：
  | `EN`/`ENO` | `OutputParam.Names` |
  |---|---|
  | `True`/`True` | 第一项 `ENO`，之后才是真输出 |
  | `False`/`False` | **不含 `ENO`**，直接是真输出（只有 TON） |
- **怎么自检**：数 `OutputItems/List2` 的子节点数，必须 == `OutputParam/Names` 项数。
  注意 `OutputItems` 是 `Single` 包 `List2`，别数错层（数外层恒得 1，会误判成一致）
- **已修**：`scripts/examples/make_ld_learn.py` 的 `fb_box()` 加了
  `len(out_vars) != len(out_names)` 就 `raise ValueError` 的断言，写错立刻崩

### B. `AND` 框被误套功能框规则

- **错在哪**：以为所有 `{acfc6f68}` 都有 `EN`/`ENO` bool 值和 `InputParam` 参数名
- **对的是什么**：
  - `AND` 的 `EN`/`ENO` 是 **`<Null Name="EN" />`**（不是 `<Single Type="bool">`）
  - `AND` 的 `InputParam`/`OutputParam` 是**空 `List2`**（`Names`/`Types` 都空）
  - 所以「槽位数 == 参数数」对 `AND` **不适用**——它按条件个数自由伸缩，但**至少 2 槽**
  - `AND` 的 `IsBoxType=False`；功能框是 `True`
- **怎么自检**：按 `BoxType` 分支处理，别用一套模板套所有 `{acfc6f68}`