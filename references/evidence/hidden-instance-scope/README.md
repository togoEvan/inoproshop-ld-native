# 证据：隐藏桌面实例上「未挂任务的 POU 是否参与构建」

日期：2026-11-28 10:33–10:36
环境：`HiddenLaunch.exe`（CreateDesktopW 隐藏桌面）+ `InoProShop.exe --profile=InoProShop(V1.10.0.3) --runscript=<脚本>`，
工程副本 `D:/plc_mcp/work/_hidden/notask2_test.project`（由 `D:/plc_study/study.project` 复制，13.8MB → 12.5MB 保存后），
全程零桌面输入、零前台窗口。

## 为什么重测

`references/evidence/notask-scope/README.md` 的结论（预编译覆盖全部 POU、编译只覆盖挂任务的 POU）是在
**用户交互式 IDE**（消息分类已注册、预编译基线 101 条）上测的。而在隐藏桌面实例上，
`app.build()` 之后**预编译分类根本不存在**，同样的写法会得出完全不同的结论。
两者不矛盾，但必须写清「在哪测的」，否则按老结论在隐藏实例上验收会**静默漏检**。

## 样本

`prg_NoTaskA` / `prg_NoTaskB`（各 8434 B，1 网络，`ldgen.py` 生成，新 GUID），声明只写 `xOutA` / `xOutB`，
实现各引一个不存在的标识符：

```
PROGRAM prg_NoTaskA
VAR
    xOutA : BOOL;
END_VAR
xOutA := ZZZ_NotExist_A;
```

## 第一轮（probeNoTask.py → probeNoTask.log，10:33:26–10:34:31）

1. 打开副本，导入 A、B（都成功）。
2. `app.build()`，A、B **都不挂任务**，耗时 28s。
3. 把 B 挂进 MainTask，`app.build()`，耗时 9s。

```
---- build-1 都不挂 10:34:21
  [2af7707f] n=1 err=0  hitA=0 hitB=0
  [97f48d64] n=104 err=0  hitA=0 hitB=0
  pous after = ['M000_MAIN','prg_StnAutoSeq','prg_SeqDemo','prg_FlowDemo','prg_NoTaskB']
---- build-2 A未挂 B已挂 10:34:30
  [2af7707f] n=1 err=0  hitA=0 hitB=0
  [97f48d64] n=106 err=2  hitA=0 hitB=2
      * Error | 不能将类型 '未知类型: 'ZZZ_NotExist_B'' 转换为类型'BOOL'
      * Error | 没有定义标识符'ZZZ_NotExist_B' 
```

⇒ **全程没有 `217bc73e` 分类**（只有 `2af7707f` 导出/导入 与 `97f48d64` 编译）。
未挂任务的 A 一条消息都没有；B 一挂上，两条错误立刻出现。

## 第二轮（probeNoTask2.py → probeNoTask2.log，10:35:59–10:36:54）

同一副本（B 已挂、A 未挂），验证「分类是否存在」与「补挂 A」：

```
---- open 后（未做任何动作） cats=0
  cat list = []
--- 执行「检查程序」ab02b3c3  → [cmd] not found（该 GUID 在 1.10 的命令表里不存在，勿再引用）
--- app.build()  10:36:15 → 10:36:43
---- build 之后 cats=1
  [97f48d64] n=106 err=2 hitA=0 hitB=2
  cat list = ['97f48d64']
--- build-3（把 A 也挂进 MainTask）10:36:44 → 10:36:52
---- build-3 A与B都挂
  [97f48d64] n=108 err=4 hitA=2 hitB=2
      * Error | 没有定义标识符'ZZZ_NotExist_A' 
      * Error | 不能将类型 '未知类型: 'ZZZ_NotExist_A'' 转换为类型'BOOL'
```

⇒ 清空后 open 时 **0 个分类**；build 后 **只有编译分类**；预编译分类从头到尾没有出现过。

## 结论

| 环境 | 预编译 `217bc73e` | 编译 `97f48d64` | 未挂任务 POU 的错误出现在哪 |
|---|---|---|---|
| 交互式 IDE（用户工程） | build 后 101 条，覆盖全部 POU | 只含挂任务的 POU | 预编译（1 条，无类型错） |
| 隐藏桌面实例（本证据） | **分类不存在** | 只含挂任务的 POU | **哪里都不出现（静默漏检）** |

1. **隐藏实例上，未挂任务的 POU 完全不参与构建，也不产生任何消息。** 只导入不挂任务 → build 报 0 错误，
   并不代表 POU 写对了。
2. **隐藏实例的验收必须先把目标 POU 挂进 MainTask 再 build。** 这道前置断言在
   `scripts/ide/tasks/task_mount_assert.py`（挂载失败直接 FAIL，而不是等编译结果）。
3. **不要指望「预编译兜底」**：隐藏实例上预编译分类不注册，`clear_messages(217bc73e)` 之类会直接失败。
4. 交互式 IDE 上两条结论依然成立（预编译覆盖全部 POU），所以两套验收流程都要写清环境。

## 复现

```
$env:__COMPAT_LAYER='RunAsInvoker'
& '<HiddenLaunch.exe>' '<InoProShop.exe>' '--profile=InoProShop(V1.10.0.3)' `
    '--runscript=D:/plc_mcp/work/_hidden/probeNoTask2.py' '--timeout-ms=200000'
```

脚本跑完 IDE 不退出，靠 `--timeout-ms` 收；日志写在脚本内的绝对路径。
