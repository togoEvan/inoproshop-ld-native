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
- **修复**：AND 框至少 2 个触点；**但单条件时不要建 AND 框**，让触点直挂 `NETITEM.RValue`
  （见 §2b，2026-11-25 实测纠正）

### 2b. 一个 rung 只有一个条件时，顶层 AND 只有 1 个输入

- **症状**：`检查程序`（预编译 `217bc73e`）**0 错误**，但构建（编译 `97f48d64`）报 N 条
  `'AND'需要至少'2' 个操作数`，N = 单条件 rung 的条数。输出映射段（`步标志 -> 输出`）、
  单触点置位段最容易中招
- **根因**：每个 NETWORK 的 `RValue` 本身就是 AND 框，`InputItems` 槽位数 = 输入数。
  生成脚本按「条件个数」append 槽位时，单条件 rung 只剩 1 个槽
- **修复（2026-11-25 实测纠正，旧结论作废）**：条件数 < 2 时**不要建 AND 框**，
  把触点节点直接作为 `NETITEM.RValue`。
  - 旧结论是「补一个 `TRUE` 触点占位」，用户看图形后指出「TRUE 常开一直接通，相当于没加，
    多此一举」——用户是对的。TRUE 占位只是绕过 1 槽报错，不是正解。
  - 三方对照实测（`prg_SlotTest` / `prg_BareContactTest`）：

    | 写法 | 结果 |
    |------|------|
    | 2 槽 AND `AND[触点, TRUE]` | ✅ 0 错误（可用但冗余） |
    | 1 槽 AND `AND[触点]` | ❌ `'AND'需要至少'2' 个操作数` + `检测到不一致元素 (不正确的输入序列)` |
    | 裸触点直挂 RValue | ✅ **0 错误**，往返导出结构完全保留 |

  - 即「AND ≥2 槽」约束的是**框**，单条件压根不该有框。
- **教训**：预编译 0 错误 ≠ 能构建。交付前预编译、编译两个分类都要读一遍。
  另：文档里凡是「必须补占位」这类绕行修法，都要追问一句「不绕行能不能直接不建这个东西」

### 3. IDE 红框（画面红框+红波浪线）

- **根因 A**：功能框 InputItems 槽位数 != InputParam 参数数（如 6 触点塞进 [EN, IN] 2 槽）
- **根因 B**：IN 引脚 `Type=BOOL`（应为 INT）或 `Boolean=True`
- **修复**：槽位数严格对齐；常量引脚 `Type=INT` + `Boolean=False`

### 4. `已标识项中有一项的格式无效`

**这是本轮（2026-11-25）最需要记住的一条：它是模态弹窗，会把 IDE 冻死。**

- **根因（实测两种）**：
  1. MOVE 框挂错位置（NETITEM.OutputItems 或 NETITEM.RValue）
     → 修复：MOVE 框直接挂 `Network/NetworkItems`
  2. **FB 类框（TON / FB_xxx）的 `Instance.Type` 为空**
     → 修复：`Instance.Type` 必须填 BoxType 名（如 `TON`），
       `Instance.Operand` 填实例名。见 `native-structure.md` ⑥。
- **为什么这条特别危险**：`import_native` 抛出该异常时 IDE 会弹**模态对话框**
  「已标识项中有一项的格式无效。」，主线程被阻塞：
  - 守护进程心跳停止（`ipc/heartbeat` 不再更新）
  - `bridge.py` 所有命令 180s 超时，看起来像「API 挂了」
  - `task_silent_import.py` 的日志停在 `children before:`，没有 FATAL 行
    （因为主线程卡在弹窗，Python 侧写不进去）
- **判断方法**（不用看屏幕）：枚举该 PID 的可见窗口，若主窗口
  `IsWindowEnabled=False`，且另有一个窗口挂着 `确定` 按钮 + Static 文本
  「已标识项中有一项的格式无效。」，就是被模态框卡住了。
- **解除方法**：`SendMessage(hButton, BM_CLICK=0x00F5, 0, 0)` 点掉「确定」，
  主线程立刻恢复，心跳重启。
- **预防**：`ET.parse()` 只能验 XML 合法性，**验不出这种语义错误**。真正的预防是
  「FunctionBlock 类必须有实例名 + `Instance.Type` 填 BoxType 名」，见生成器
  `make_repro_study.py::generic_box(instance=...)`。

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
### C. 网络注释里的 `<` `>` 未转义 → 凭空多出 XML 子节点

**现象**：预编译 0 错误、编译 0 错误、**导入完全正常**，但往返 diff 报
`节点数不同` + 「从 #275 起整段错位」+ `total structural diffs: 55`。

**根因**：网络注释是直接拼进 XML 文本节点的：

```xml
<Single Name="Comment" Type="string">// 网络2：CallType=Action —— 不是 <Null/></Single>
```

XML 解析器看到 `<Null/>` 就当成**真实子节点**，于是这个 Network 的
`Comment` 下多了一个 `Null` 节点，节点数 363 → 362（dst 少 1，因为
IDE 重新导出时把非法子节点丢掉了）。

**错在哪**：`make_ld_learn.network()` 直接把 `comment` 变量拼进模板，
没有做 XML 转义。

**对的是什么**：所有塞进 XML 文本节点的自由文本都必须转义：

```python
def xml_text(s):
    return (s.replace(u"&", u"&amp;")
             .replace(u"<", u"&lt;")
             .replace(u">", u"&gt;"))
```

`network()` 的 `comment`、`textlines_block()` 的每一行（声明区 + ST 代码）
都要过 `xml_text()`。**注意函数定义顺序**：`xml_text` 必须在
`textlines_block` 之前定义，否则模块级调用会 `NameError`。

**怎么自检**：
1. 生成后 `grep` 注释行，确认 `<` 已变成 `&lt;`
2. `rt_diff.py` 报「节点数不同 + 整段错位」时，**先看错位那一处的父节点名**——
   是 `Comment` / `Text` / `Title` / `Label` 这类文本节点，就 100% 是转义问题
3. 不要一看到 diff FAIL 就去改结构，先排除「自己的 XML 不合法」

**为什么不报编译错**：IDE 导入时把多出来的 `Null` 当垃圾丢掉了，
注释文本本身没丢，功能完全正常。**只有往返 diff 能发现**（而且报的是错位，
不是直白的「注释有问题」）。

---

## 类型 D：IDE 图形异常（不报错，但画错）

### D-1 框上方多出一个「可填写参数的小方框」

**现象**：LD 网络里的 Action 调用框（`CallType=Action`）上方，多画出一个
**红框的、内部空白、可以填参数**的小方框。正常调用没有这个方块。

**错在哪**：`Instance/Operand` 写成了空的 `<Single>`：

```xml
<!-- ❌ 错：IDE 把它当成「一个可填写的操作数槽」画出来 -->
<Single Name="Operand" Type="string" />
```

**对的是什么**：按 `CallType` 分三态，只有 FB 才需要实例名：

```xml
<!-- FunctionBlock：写实例名 -->
<Single Name="Operand" Type="string">fbPtpV[0]</Single>

<!-- Action / Function / Program / And / Move：一律 Null -->
<Null Name="Operand" />
```

全量统计（16 个真实 Action 框 + 各类型样本）：Action→`Null`、Function→`Null`、
Program→`Null`、And→`Null`、Move→`Null`、FunctionBlock→`Single(实例名)`，0 例外。

**排查过程（记下来，别再走弯路）**：
1. 第一轮误判为框级 `Flags.Fixed` 问题（`Fixed=False` → 多画占位框）。改了
   `Fixed=True` 后用户反馈**小方框还在**。
2. 用户第二句是关键线索：「**actAbs_NOPE 上面还是有小方框可以填写参数**」——
   `actAbs_NOPE` 是故意写的**不存在的** BoxType，它也有方框，说明方框与
   BoxType 合法性无关、与 `Fixed` 也无关。
3. 于是做「真实模板 Action 框 vs 我生成的 Action 框」**全字段 diff**，
   唯一差异就是 `Operand` 的 `Null` vs 空 `Single`。

**怎么自检**（一行命令）：

```python
# 遍历 native，所有非 FunctionBlock 的框，Operand 必须是 Null
for e in walk(root):
    if e.get('Type') != G_BOX:
        continue
    ct = txt(e, 'CallType')
    op = get(get(e, 'Instance'), 'Operand')
    if ct != 'FunctionBlock' and op.tag != 'Null':
        print('BAD', ct, txt(e, 'BoxType'))
```

**为什么不报编译错**：空 `Single` 是完全合法的 XML，语义上等价于「未填写」，
编译器不管图形怎么画。**预编译、编译、往返 diff 三关全部通过**，只有人眼看图形
才能发现——所以生成器里必须用上面的断言自查。

**附带教训（循环论证）**：最初「Action 的 Operand 是空字符串不是 Null」这个
结论，是从**自己导入后再导出的文件**里反推出来的——IDE 把自己写进去的空
`Single` 原样导出，于是"验证"通过。**自己验证自己 = 没验证**。正确做法是
拿**真实模板**（InoPack 导出的原始文件）当基准做 diff。

---

## 类型 E：验收链路本身失效（最坑的一类）

### E-1 所有编译命令都走缓存，报 0 错误

**现象**：工程里放一个必然报错的 POU（如 `BoxType=actAbs_NOPE`），
执行任何编译命令都报 0 错误、0 警告。

**实测结果（2026-11-25，逐个命令验证）**：

| 命令 | 预编译分类 | 编译分类 |
|---|---|---|
| 清理 | 0 条 | 「此应用程序是最新的」 |
| 重新编译 | 0 条 | 「此应用程序是最新的」 |
| （旧）编译 | 0 条 | 「此应用程序是最新的」 |
| （旧）重新编译 | 0 条 | 真跑构建，「编译完成 0 错误」 |
| 检查所有对象 | 0 条 | 真跑构建，0 错误 |
| 运行静态分析 | 0 条 | 真跑构建，0 错误 |
| 生成代码 | 0 条 | 「此应用程序是最新的」 |
| 生成二进制文件 | 0 条 | 真跑构建，0 错误 |
| 编译 | 0 条 | 「此应用程序是最新的」 |

**结论**：**没有任何一条编译命令能替代「导入触发的自动检查」**。
预编译消息只在 `import_native()` 那一刻产生。

**对的做法**：

1. `do_replace.py` 导入
2. 主机侧 `time.sleep(1.5)`（**不在 IDE 里**）
3. 调 `task_check.py` **读一次快照**，看 `check.log`

**三个必踩的坑**：

- **绝不能 `clear_messages`**：消息是导入时产生的，清掉就永久消失，
  后续任何编译都不会重算。
- **不要用「声明改一个字符再改回」强制变脏**：实测无效，照样读 0 条。
- **不要在 IDE 脚本里 `sleep` / 轮询**：IDE 脚本跑在主线程，会把界面**冻死**
  （用户原话：「你在等待的时候软件卡死了」「还是卡死」）。计时重试放主机侧。

### E-2 负样本造错了，误判为「验收链路失效」

**现象**：造负样本 `actAbs_ZZZ` 导入后编译 0 错误，以为验收脚本坏了，
折腾一轮排查。

**错在哪**：用 `s.replace('>actAbs<', '>actAbs_ZZZ<')` 一次替换了两处——
`BoxType` **和** action Entry 的 `Name`。于是 `actAbs_ZZZ` 变成一个
**真实存在的合法 action**，编译 0 错误是**正确结果**。

**对的是什么**：只替换 `BoxType` 那一处：

```python
old = u'<Single Name="BoxType" Type="string">actAbs</Single>'
assert s.count(old) == 1
s = s.replace(old, u'<Single Name="BoxType" Type="string">actAbs_NOPE</Single>')
```

Entry 的 `Name` 保持 `actAbs`，这样才是「调用了一个不存在的 action」。

**怎么自检**：改完立刻 `grep -c` 数两处：

```
grep -c "actAbs_NOPE"            → 1（只有 BoxType）
grep -c 'Name="Name" Type="string">actAbs<'  → 1（Entry 名没动）
```

**元教训**：反向验证是唯一能证明验收链路有效的手段，但**负样本本身必须造对**。
负样本报错 ≠ 链路正常；负样本报 0 错误时，先怀疑样本，再怀疑链路。

## 类型 F：编译分类根本不存在（2026-11-25 新踩）

### F-1 打开一个**从未构建过**的工程，`97f48d64` 分类不存在

- **症状**：`task_check.py` 抛
  `RuntimeError: 消息分类 ?(97f48d64-a2a3-4856-b640-75c046e37ea9) 不存在，不得当作 0 错误`
- **根因**：消息分类是**惰性创建**的。新打开的工程、或从未执行过构建的工程，
  运行时只暴露 2 个分类（预编译 `217bc73e` + 导出/导入 `2af7707f`）。
  编译分类要等第一次 `app.build()` 之后才出现。
- **正确做法**：先用 `scripts/ide/task_build_check.py` 跑一次 `build()`（**不 clear_messages**），
  再读双分类。实测构建后分类数从 2 变 3，编译分类出现。
- **⚠ 不要**因为分类不存在就 `return 0` 当通过——那正是本仓库反复强调的「假通过」。

### F-2 真实工程构建后剩下的错误不一定是你的错

实测「除油倒盘-擦拭机-PLCV20261124」构建后编译分类剩 1 条：

```
[Error] M000_MAIN | 程序 E3_SystemTime 在多任务下存在多处调用，可能会产生不符合预期的结果
```

这是**模板工程自带的**（`E3_SystemTime` 被 MainTask 与 ETHERCAT 同时调用），
与新建 POU 无关。**判断方法**：在日志里 `grep 你新建的 POU 名`，为 0 即与本次改动无关。
预编译分类同期是 `errors=0 warnings=101`，101 条全是模板自带的
`ENUM1_CYLINDERNAME → UINT 隐含转换` 警告。

**结论表述要诚实**：应写「预编译 0 错误；编译仅剩模板原有的 1 条 E3_SystemTime 多任务错误，
新增 POU 无任何错误」，而不是笼统说「双分类 0 错误」。
