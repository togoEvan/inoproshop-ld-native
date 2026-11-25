# Changelog

本项目的所有重要变更都记录在此文件。

格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### 修复
- **`git push` 报 `Failed to connect to github.com:443 after 21000 ms`，实为 DNS 污染**（2026-11-25 实测）。本机 DNS 把 `github.com` 解析到 `20.6.7.17`（不可达），但真实 IP `20.205.243.166:443` 直连正常，凭据 `git credential fill` 也能正常返回 `username=Tang-zhi-l`。极易被误判成"网络断了"或"凭据失效"而反复重试。修复：`sync.ps1` 推送前依次 TCP 探测候选 IP（`20.205.243.166` / `20.27.177.113` / `140.82.113.4`）的 443 端口，用 `git -c http.curloptResolve=github.com:443:<ip>` 钉住第一个可达地址；全部不可达才回退系统 DNS。用**候选列表 + 探测**而非硬编码单 IP，因为 GitHub 的 IP 会变
- `references/mcp-bridge.md`「换环境必查」从 6 项扩到 7 项，新增「GitHub DNS 是否被污染」判别行；并新增「DNS 污染」小节（症状原文、三步判别命令、`curloptResolve` 修复法、IP 会变所以要用候选列表）
- `docs/iteration.md` 新增 §5.5「DNS 污染」：与 §5.4「为什么不弹凭据窗口了」并列，明确区分「凭据问题」和「DNS 问题」两种都表现为 push 失败的场景

### 修改
- **库更新规则从「遇新坑必回写」升级为「四类触发」**。原来只笼统说"遇到新坑要回写"，容易漏记。现明确为四类，每类都规定了**触发信号 / 落到哪个文件 / 必带什么证据**：①**没见过的格式**（新 GUID、层级、属性组合、槽位排布）→ `native-structure.md` + `assets/natives/` 样本 + `scripts/examples/` 生成器，须附双分类 0 错误与往返一致；②**Bug**（脚本报错 / IDE 崩 / 导入失败 / 验收漏报）→ `precompile-errors.md` 或直接修 `scripts/`，须附报错原文与复现步骤；③**吃过的亏**（理解错、结论被证伪）→ 提炼成铁律（README + SKILL 双写），须写清「错在哪 / 对的是什么 / 怎么自检」；④**新配置**（换机器 / IDE 版本 / 路径 / 凭据）→ `mcp-bridge.md` 环境要点，须附一条能直接跑的自检命令。四处同步改写：`SKILL.md`「更新规则」、`AGENTS.md` §6、`docs/iteration.md` §2.1、`README.md`「贡献 / 迭代」
- `references/mcp-bridge.md`「环境要点」新增**换环境必查的自检表**（BASE 解析 / IPC 目录 / daemon 存活 / IDE 进程与工程 / IronPython 语法 / Git 凭据 / GitHub DNS），每项给出可直接执行的命令与失效表现
- `docs/iteration.md` §1 改动分类表：验证要求从「预编译 0 错误」统一改为「**双分类 0 错误**」；新增「环境配置」类；样本类补「被证伪的旧样本必须替换而非仅追加」；并加注「双分类 0 错误 ≠ 图形没问题」的实测案例（单支路分支组）
- `docs/iteration.md` §2 标准流程补第 ⑨ 步（重新打包 `.skill` 并同步本机技能目录），并新增 §2.1「回写四类触发」对表

### 修复（分支组渲染）
- **分支组 `Trees` 只有 1 条支路会让 IDE 绘制网络时崩溃**（用户截图报「在绘制该网络的时候遇到错误 / 不能显示内容 / 索引超出了数组界限」，堆栈在 `IBoxTreeParallel`）。`make_fb_call_test.py` 首版给只有一条 FB 调用的网络套了「单支路分支组 + NETITEM.RValue」，**预编译 0 错误、编译 0 错误，但梯形图编辑器打不开这一级网络**。脚本枚举全部样本后确认：act03_PackMLCmd 的 10 个网络、prg_PackMLCmdTest 的 7 个网络，所有分支组 `Trees` 都是 2，工程里从未出现过 `Trees=1`。修法：单支路时**不用 `branch()`、不套 `NETITEM`**，直接把 AND 框挂 `NetworkItems`（照 act90_PackMLManager 网络3）。改后重新导入，导出结构与实测样本一致，预编译 0 + 编译 0，程序段 2 正常显示
- `scripts/examples/make_fb_call_test.py`：`build_networks()` 改为「多支路 → 分支组直挂；单支路 → AND 框直挂」；`netitem_rvalue()` 标记为**已弃用**并在 docstring 写明踩坑原因，防止后来者照抄

### 新增
- `references/native-structure.md` 新增「⚠ 铁律：分支组的 Trees 必须有 ≥ 2 条支路」一节：症状（绘制错误原文 + 堆栈特征）、根因（`IBoxTreeParallel` 按 ≥2 计算几何）、4 行实测证据表（哪些文件哪些网络 Trees=2 / =1 及绘制结果）、正确与错误结构对照图、参考实现指向 `make_fb_call_test.py` 的 `build_networks()`。并在「关键节点类型」表的分支组一行加上「Trees 必须 ≥2」约束
- **功能块（FB）调用的 native 结构**（act04_Interface + act90_PackMLManager 实测）。FB 框与 MOVE 框同属 `{acfc6f68}`，但 `CallType` 为 `Function`/`Program`/`FunctionBlock`、`BoxType` 填 POU 名、`EN`/`ENO` 是纯 `<Single Type="bool">True</Single>`（不是条件槽）、`Instance.Operand` 只有 `FunctionBlock` 类才填实例名。槽位规则：**`InputItems` 槽位数 == `InputParam` 参数个数（EN 算一个），槽0 恒为连接器 `{5f9848d3}` 且 `Input=Null`，槽1..n 与去掉 EN 后的参数严格一一对应；`OutputItems` 长度 == `OutputParam` 个数，第 0 项恒为 `<Null />`（对应 ENO）**。另记 `InputParam.Names` 填参数名而非操作数、REF 形参在 Types 里带 `[REF]` 后缀
- **`scripts/examples/make_fb_call_test.py`：FB 调用生成器**。三类 `CallType` 各生成一个调用（`Function` 的 `PackMLScCmdInit`、`Program` 的 `prg_EM00_Logic`、`FunctionBlock` 的 `PackMLUnitManager` 带实例 12 入 12 出），全部用本 POU 局部变量、不依赖工程其它对象。实测静默导入成功、导出往返结构与源完全一致、**预编译 0 错误 + 编译 0 错误**
- `references/native-structure.md` 新增「功能块（FB）调用标准结构」一节：与 MOVE 框的 8 项差异对照表、三类 CallType 语义、槽位规则、完整 13 槽结构示例、已验证样本清单
- `scripts/start_daemon.cmd`：给**已经开着的** IDE 注入守护的一键入口。用 UIA `InvokePattern` 点「工具 → 脚本 → 执行脚本文件」，不移动鼠标、不抢键盘焦点、不激活窗口；注入完自检 `ipc/ready.flag` 并打印 `[OK]`/`[FAIL]`
- `scripts/bridge.cmd`：命令行调用入口，按 `PLC_PYTHON` → `py -3` → `python` 顺序挑一个真能跑的 Python 3，避开 Windows 应用商店那个 0 字节的 `python.exe` 存根
- **`scripts/examples/make_packml_cmd_test.py`：从零生成一个完整 LD POU 的可复用生成器**。以 `assets/natives/user_fixed.native` 为骨架，生成 7 网络 PackML 命令层测试程序 `prg_PackMLCmdTest`（模式切换 + Start/Stop/Abort/Clear/Reset/Hold），实测静默导入成功、**预编译 0 错误 0 警告**。脚本内含 `contact/coil/and_box/branch/netitem/network` 全套节点构造函数，可直接改造成任意 POU 生成器
- `references/native-structure.md` 新增 4 节：**NETITEM.Flags 整级输出取反**、**RValue 类型可以是分支组本身**、**分支组 Input 槽公共前缀的两种合法形态**、**新建 POU 的完整 8 步流程**
- `scripts/pack_skill.py`：打包 `.skill` 分发件。文件清单严格取自 `git ls-files`，只打 `SKILL.md` + `references/` + `scripts/` + `assets/`，保证包里永远是已提交版本，不会混入本地改动或已删除的旧文件
- `references/precompile-errors.md` 第 6、7 类问题：C0046 批量未定义标识符、两个 TRUE 串联
- `references/precompile-errors.md` 第 2b 类问题：单条件 rung 的顶层 AND 只有 1 个输入——**预编译 0 错误，构建却报 N 条 `'AND'需要至少'2' 个操作数`**
- `references/mcp-bridge.md`「textual_* 接口不可用时的退路」：用户手工启动的 IDE 实例里对象全是 `ExtendedObject[IScriptObject]`，文本接口失效（`list_pous` 恒 0、`get_pou` 报 POU not found），只能 `export_native` 读、`import_native` 写
- `references/native-structure.md`「声明区（TextLines）结构」与「公共前缀与支路条件去重」两节
- `scripts/examples/make_fix45.py`：补声明 + 删多余 TRUE 的修复脚本
- **分支组「完整支路」标准结构**（用户手改已验证）：外层 AND 框包住 `[MOVE 框, 连接器 {505bff94}]`；**任何一层（含嵌套分支组内部）都适用**
- `scripts/examples/make_full8.py`：把裸 MOVE 支路批量包装成完整支路的生成脚本

### 修改
- `assets/natives/user_fixed.native` 更新为**修复后最终版**：8 支路完整结构（3 顶层 + 内层 6）+ 声明区齐全，预编译 0 错误 0 警告；并在文档中标记为树形结构**首选克隆模板**
- **全部脚本去掉硬编码的用户目录 + 路径自解析**：新增 `scripts/ide/_base.py` 统一路径解析——**环境变量对 IDE 内脚本无效**（daemon 跑在 IDE 进程内，继承的是 IDE 启动那一刻的环境，实测恒为 `None`），且含中文的路径经 `subprocess` 环境变量传给 IDE 会按 GBK 解码损坏。解析优先级改为：`scripts/ide/xxx.py → scripts/` 自身路径反推（`sys.argv[0]` 走 Windows UTF-16 命令行，中文无损，**最可靠**）> `<BASE>/base_path.txt`(手工兜底) > 环境变量(仅 `launch_ide_daemon.py` 启动且路径真实存在时) > `D:\plc_mcp`。`bridge.py` / `do_replace.py` 用同一套规则。日志打印 `BASE = ... (source: ...)` 便于排错
- `README.md`：目录结构补全到实际文件（含 `scripts/examples/`、`sync.cmd`、各 `task_*.py` 用途）；铁律表新增第 9 条；「已验证的合法模式」补公共前缀去重与声明区
- `SKILL.md`：`assets/natives/` 与 `scripts/` 表格按实际用途重排；铁律新增第 9 条；合法模式补两条
- `docs/usage.md`：目录约定补全实际文件；快速排错索引补 §6 与 §7
- `docs/iteration.md`：新增 §5.4「为什么不弹凭据窗口了」，记录 `helper-selector` 弹窗根因与 `wincred` 方案
- `README.md`：快速开始补「IDE 已开着」的一键注入（`start_daemon.cmd`）与 `bridge.cmd`；路径解析表补 IPC 目录优先级**与它和 BASE 解析顺序不同的原因**（IDE 继承旧环境变量导致 ready.flag 写错目录）；目录结构补两个新脚本
- `references/mcp-bridge.md`：修正 `bridge.py` 的 PowerShell 示例（原引号不匹配、路径末尾多一个 `/`），改为推荐 Python 调用 + 正确的 CLI 转义写法
- `references/native-structure.md`：重写「挂载位置规则」，补完整支路结构图与补齐前后对照表
- `.gitignore` / `.gitattributes`：注释从「一句话标签」改写为「为什么 + 挡什么 + 自检命令」。`.gitignore` 补充 gitignore 只对未跟踪文件生效、`git check-ignore -v` 自检、凭据已提交需吊销并清历史的说明；`.gitattributes` 补充跨平台换行根因、`git check-attr` 自检、`*.native` 为何按二进制处理。规则内容本身未变
- `task_silent_import.py`：全局递归 `find_named`/`walk` 替换为 `find_child()`——只在目标父对象（Application）的**直接子对象**里用 `get_children()` 过滤查找，符 README 铁律「禁止全局 find_named」，避免误命中 Task Configuration 里的同名调用对象
- **验收标准从「只看预编译」改为「预编译 + 编译双分类」（库内容整理）**。原先 4 处文档（README/SKILL/AGENTS/usage）都写着「编译分类永远 0 错误，拿它验收等于没验收」，但实测证伪：单条件 rung 的顶层 AND 只有 1 个输入槽时，预编译 0 错误而构建报 N 条 `'AND'需要至少'2' 个操作数`。现在统一为「预编译 `217bc73e` 抓结构错误 + 编译 `97f48d64` 抓语义错误，两者都必须为 0」
- **`scripts/ide/task_check.py` 加 `app.build()`**：原先只执行「检查程序」，不触发构建，导致只在构建期报的错误永远读不到（上面那个矛盾的结构性根源）。现在先「检查程序」再 `build()`，末尾输出 `=== 验收结论 : 通过/不通过 (合计 N 错误) ===`。实测 check 4.42s + build 4.03s，结论正确
- **`references/native-structure.md` 新增「AND 框的输入元数：至少 2 个槽」一节**：原来只在 `precompile-errors.md §2b` 记了症状，结构文档没有对应规则。现补「任何 AND 框（含 NETWORK 顶层 `RValue` 的那个）都要 ≥2 个 `InputItems` 槽，单条件补 `TRUE`」并交叉引用 §2b
- **`references/precompile-errors.md` 消息分类表重写**：删掉「编译分类永远 0 错误、不能当验收」的错误结论，改为「两个分类抓不同错误，缺一不可」
- **`docs/usage.md` §3 验收规范重写**：3.1 改为双分类标准 + 对照表；3.2 输出示例补编译分类与验收结论行；3.3「什么不算验收」补「只看预编译」与「只看编译」两条对称项；§6 禁止事项「用编译分类验收」改为「只看单一分类验收」
- **`AGENTS.md` §2 验收标准重写**：补两分类对照表与实测案例；铁律条数从「8 条」修正为「10 条」
- **`README.md`**：铁律表新增第 10 条（AND 至少 2 个输入槽）；`precompile-errors.md` 描述从「7 类」修正为「8 类」；目录结构补 `make_packml_cmd_test.py`
- **`SKILL.md`**：铁律新增第 10 条；`examples/make_*.py` 说明改为如实描述（`make_full8`/`make_fix45` 读环境变量，`make_packml_cmd_test` 用相对路径）
- **清理失效引用**：`docs/usage.md` 失败排查表引用的 `inspect_native.py` 仓库里不存在，改为实际可用的「与样本逐层标签 diff」做法；`references/native-structure.md` 引用的 `task_precompile.py` 不存在，改为 `task_check.py`

### 修复（早期）
- **PLC_PRG 12 段状态机首版构建报 6 条 `'AND'需要至少'2' 个操作数`**：生成器给单条件 rung
  （上电初始化、进入急停、4 段输出映射）只 append 了 1 个输入槽，AND 框退化成单操作数。
  已改为条件数 < 2 时自动补 `TRUE` 触点；修复后预编译 0 错误、编译 0 错误（仅 CmpLog 库警告）
- **同步时弹「选择凭据助手」窗口**：Git for Windows 的系统级配置是 `credential.helper=helper-selector`，
  每次联网都会弹窗。`sync.ps1` 现在会自动把仓库级凭据助手设为 `wincred`（纯命令行读 Windows 凭据管理器，零弹窗），
  并强制 `GIT_TERMINAL_PROMPT=0` + `GCM_INTERACTIVE=never`；凭据失效时直接报错而不是弹窗等待
- **C0046 批量未定义标识符**（45 个错误的真实根因）：native 只搬「图形 + 声明文本」，图形引用的符号必须在 `Interface/TextDocument/TextLines` 里逐行声明；漏声明 = 每个引用点报一条错误。已为 `prg_StartStop` 补全 8 个状态机变量声明，45 → 0
- **两个 TRUE 串联**：分支组 `Input` 已有公共前缀 TRUE 时，支路 EN 条件框里不要再放 TRUE。已删除 8 条支路里多余的 TRUE
- **修正认知**：裸 MOVE 框挂分支组 Trees 虽预编译 0 错误，但功能链断头、图形不完整；任何层级都需外层 AND + 连接器包装
- `SKILL.md` / `README.md`：修正「内层是裸 MOVE 框」的表述——那是用户未改完的中间状态
- **`plc_daemon.py` 加载即崩（NameError: a_import_native）**：`ACTIONS` 字典引用了在它之后才定义的 `a_import_native` 函数，前向引用导致模块级加载失败、daemon 永远起不来。已把 `a_import_native` 移到 `ACTIONS` 之前
- **daemon 日志文件被锁导致整个守护崩死**：`daemon.log` 被上一个实例的句柄锁住时，`io.open` 抛异常直接中断 daemon 启动。已改为 `_open_log()`：打不开 `daemon.log` 就用带时间戳的日志名降级，绝不让日志问题拖垮守护
- **`task_check.py` 读预编译报 category null**：`get_message_objects` 不能传字符串/GUID 分类，需先枚举 `get_message_categories()` 按 GUID 匹配到分类对象再取消息。已改 `_objs_by_guid`
- **守护 `ready.flag` 写到旧目录、新版永远等不到就绪**（2026-11-25 部署实测）：IDE 进程会继承「启动它的环境」里的 `PLC_MCP_IPC`（实测指向旧工作区 `D:\小艺Work工作空间\20261123160323\plc_mcp\ipc`），而 `_base.resolve_ipc()` 原来环境变量优先，导致 `plc_daemon.py` 把 `ready.flag` / 心跳 / 日志全写进旧目录，`bridge.start_daemon()` 傻等 30 秒后报「守护进程未就绪」。已改为 `<BASE>/ipc` 优先、环境变量仅在该目录不存在时兜底

### 删除
- `docs/github-新手操作手册.md` —— 一次性的对话式操作记录，不属于工具文档
- `scripts/ide/task_cleanup4.py` —— 硬编码了某个具体工程的 POU 白名单，无法复用

## [1.0.0] - 2026-11-24

### 新增
- 首次发布：LD native 结构知识（节点 GUID、槽位规则、挂载位置）
- 预编译错误对照表（5 类错误 → 根因 → 修复）
- MCP 文件 IPC 桥（`bridge.py` + `plc_daemon.py`）
- 静默导入（改名让位法，不弹确认框）
- 预编译检查脚本（`task_check.py`，读 `217bc73e` 分类）
- 4 份已验证 native 克隆模板

### 修复
- **根因定位**：值输入引脚（IN 槽）`IsContact` 必须为 `False`；从触点模板克隆残留 `True` 是预编译报
  `不允许对类型 'SINT' 进行 'NOT' 操作` 的根本原因（此前 4 个单变量实验排除了触点写法、
  EN 槽内容、BoxType、CallType）
