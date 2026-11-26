# 证据：「不挂任务是否参与编译」六场景对照

日期：2026-11-26
工程：`D:\plc_study\study.project`（InoProShop V1.10.0.3，真实产线工程副本）
负样本 POU：`prg_NoTaskTest`

```
PROGRAM prg_NoTaskTest
VAR
    xOut : BOOL;
    iOut : INT;
END_VAR
// 负样本：引用不存在的标识符
xOut := ZZZ_NotExist_Symbol;
iOut := 0;
```

## 实验方法

关键在**排除消息残留干扰**。做法：

1. `system.clear_messages(cat)` 逐分类清空（**必须传分类参数**，无参调用报
   `takes exactly 1 argument (0 given)`）。
2. 只做**一个**动作（`app.build()` / 「检查程序」命令 / 什么都不做）。
3. 等待放在**主机侧 Python**（`sleep 20~25`），IDE 脚本里绝不 sleep（会冻死界面）。
4. 用独立脚本 `task_exp_dump.py` 只读消息，统计 `ZZZ_NotExist_Symbol` 命中数。

对照组 C3/C4 证明：清空后空闲 20s 仍是 0 条，**消息不会自行恢复**，
所以「清空 + 单一动作 + 等 20s + 读」的归因是可靠的。

## 结果（2026-11-26 二次复测后修正）

> ⚠ **第一轮结论有误，已修正**。第一轮把「预编译出现 ZZZ」归因给菜单「检查程序」，
> 但当时实验里「检查程序」前后夹了 `build`，消息实际来自 `build`。二次复测
> （每次 `clear` → **单一动作** → 主机侧等 ≥10s → 独立读）结果如下：

| 动作（清空后单独执行） | 预编译 `217bc73e` | 编译 `97f48d64` |
|---|---|---|
| 什么都不做（对照） | 0 条 / ZZZ **0** | 0 条 / ZZZ 0 |
| 菜单「检查程序」`ab02b3c3` | 0 条 / ZZZ **0** | 0 条 / ZZZ 0 |
| `import_native` 导入 POU | 101 条 / ZZZ **0** | 0 条 / ZZZ 0 |
| `app.build()`（POU **未挂**任务） | 101 条 / ZZZ **1** | 105 条 / ZZZ **0** |
| `app.build()`（POU **已挂** MainTask） | 101 条 / ZZZ **1** | 106 条 / ZZZ **2** |
| 删除 POU 后（对照） | 0 条 / ZZZ 0 | 0 条 / ZZZ 0 |

对应证据：`R18.*`（clear → 检查程序，ZZZ 0）、`R19.*`（clear → build，ZZZ 1）、
`R20.*`（clear → 检查程序 → build，只有 build 那步出 ZZZ）、`R21.*`（clear → import，ZZZ 0）。
第一轮的 `C1`~`C7`、`E2`~`E6` 日志保留备查，但**结论以本表为准**。
新增脚本：`task_exp_poll.py`（只读两分类条数与 ZZZ 命中）、`task_exp_delay.py`（命令后立即读，测延迟）。

编译分类 ZZZ 命中 2 时的两条原文：

```
不能将类型 '未知类型: 'ZZZ_NotExist_Symbol'' 转换为类型'BOOL'
没有定义标识符'ZZZ_NotExist_Symbol'
```

预编译分类 ZZZ 命中 1 时的原文：

```
没有定义标识符'ZZZ_NotExist_Symbol'
```

## 结论

**两个消息分类的作用域不同，且写入者不同。**

1. **预编译 `217bc73e`** 在 `app.build()` 阶段覆盖 **Application 下全部 POU**
   （含未挂任务的）。它的消息由 `import_native` 和 `app.build()` 写入。
2. **编译 `97f48d64`** 只含**挂进任务调用列表**的 POU。
3. **菜单「检查程序」是只读的**，不产生任何消息，**不能用于验收**。
   用户点「检查程序」看到报错，是因为该动作触发了构建/检查，消息由构建阶段写入；
   消息留在分类里不会消失，看起来像「检查程序产生的」。

**验收必须两个分类都看，且必须用 `app.build()`**：
- 只看编译分类 → 漏掉未挂任务 POU 的语法错误（假通过）
- 只看预编译分类 → 漏掉构建期错误（类型转换、`E3_SystemTime` 多任务冲突等）

## 附带的时序发现

预编译消息是**异步补齐**的：

- `clear_messages(cat)` 后**立刻**读 → 0 条
- 5 秒后 → 101 条
- 清空后**空闲** 20s（不做任何动作）→ 仍是 0 条（不自行恢复）

所以判定实验的等待必须放主机侧；在 IDE 脚本里 sleep/轮询会冻死界面
（用户曾两次反馈「软件卡死」）。

## 踩坑记录

- `E4_check_withPOU`：等待只给了 10s，读到的预编译是 101 条但 ZZZ 命中 0 ——
  **消息还没补齐完**。延长到 20s 后（`E5_check_again`）命中 1。
  ⇒ 等待时长不足会造成**假阴性**，比假阳性更危险。
- 早期 `task_notask_verify.py` 在同一个 IDE 脚本里 build 后立刻读，结果同样不可靠。
- `system.clear_messages()` 无参调用在 InoProShop 1.10 会抛
  `TypeError: clear_messages() takes exactly 1 argument (0 given)`，必须逐分类传。

## 相关脚本

`scripts/ide/` 下：

| 脚本 | 作用 |
|---|---|
| `task_exp_clear.py` | 清空全部消息分类 + 执行单一动作（build / 检查程序 / 什么都不做） |
| `task_exp_dump.py` | 只 dump 全部分类，统计 ZZZ 命中 |
| `task_exp_cmd.py` | 按 GUID 只执行一个 IDE 命令 |
| `task_exp_build.py` | 只调用 `app.build()` |
| `task_exp_op.py` | 只删除 / 只导入一个对象 |
| `task_exp_task.py` | 把 POU 挂进 / 摘出任务调用列表 |
| `task_exp_notask.py` | 早期合并版实验（保留备查） |

参数统一走 `scripts/ipc/exp_args.json`，日志落 `scripts/ipc/exp/`。
