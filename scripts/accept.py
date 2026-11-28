# -*- coding: utf-8 -*-
# @py3
"""一条命令验收：挂载断言(可选) → 干净 build → 等消息落地 → 双通道判定。

为什么要有这一步：
  写入成功 ≠ 代码正确。`import_native` 只保证对象进树，
  编译错误要等 build 后从「预编译 / 编译」消息分类里读；
  而 `app.build()` 是增量的，旧消息会被当成本轮结果（假通过）。
  所以验收 = 清三个分类 → build → 主机侧等待 → task_check 双通道读。

用法：
  python accept.py                              # 只 build + 判定
  python accept.py --names=prg_A,prg_B           # 先断言这些对象已挂任务（防「未挂任务不进编译」假通过）
  python accept.py --wait=15                    # 改等待秒数（默认 12）
  python accept.py --no-build                   # 只读当前快照，不重新 build

退出码：0 PASS / 1 FAIL / 2 UNKNOWN / 3 环境或前置条件不满足
"""
import io
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bridge  # noqa: E402

IPC = os.path.join(HERE, "ipc")
TASKS = os.path.join(HERE, "ide", "tasks")
VERDICT_EXIT = {"PASS": 0, "FAIL": 1, "UNKNOWN": 2}


def arg(argv, key, default=None):
    pref = "--" + key
    for i, a in enumerate(argv):
        if a == pref and i + 1 < len(argv):
            return argv[i + 1]
        if a.startswith(pref + "="):
            return a.split("=", 1)[1]
    return default


def has(argv, key):
    return ("--" + key) in argv


def run_task(name, timeout=600):
    r = bridge.call("eval_file", path=os.path.join(TASKS, name), timeout=timeout)
    return r


def read_log(name, tail=0):
    p = os.path.join(IPC, name)
    if not os.path.exists(p):
        return ""
    with io.open(p, "r", encoding="utf-8", errors="replace") as f:
        s = f.read()
    return s[-tail:] if tail else s


def mount_assert(names):
    """断言对象已挂任务：未挂 = 不进编译单元 = 0 错误是假通过。"""
    args = os.path.join(IPC, "task_mount_args.json")
    with io.open(args, "w", encoding="utf-8") as f:
        f.write(json.dumps({"names": names}, ensure_ascii=False))
    run_task("task_mount_assert.py", timeout=180)
    p = os.path.join(IPC, "task_mount_result.json")
    if not os.path.exists(p):
        print("[accept] 挂载断言没产出 result.json，按失败处理")
        return False, {}
    with io.open(p, "r", encoding="utf-8") as f:
        res = json.loads(f.read())
    return bool(res.get("ok")), res


def main():
    names = [x.strip() for x in (arg(sys.argv, "names") or "").split(",") if x.strip()]
    wait_s = int(arg(sys.argv, "wait") or 12)

    # 0) 守护在不在、工程开没开
    st = bridge.call("status", timeout=30)
    if not st.get("ok"):
        print("[accept] 守护/工程不可用：%s" % json.dumps(st, ensure_ascii=False)[:300])
        return 3
    print("[accept] 工程 = %s" % (st.get("project") or "?"))

    # 1) 挂载断言
    if names:
        ok, res = mount_assert(names)
        if not ok:
            print("[accept] 挂载断言失败：%s" % json.dumps(res, ensure_ascii=False)[:500])
            print("[accept] 说明：这些对象不在任何任务的调用列表里，编译不会看它们。")
            print("         用 A0x 动作槽/任务挂载把流程接进调用树，或去掉 --names 自行确认。")
            return 3
        print("[accept] 挂载断言通过：%s" % ", ".join(names))

    if not has(sys.argv, "no-build"):
        print("[accept] 干净 build（清 预编译/编译/导出导入 三个分类）…")
        run_task("task_build_clean.py", timeout=600)
        blog = read_log("build_clean.log")
        print("         " + (blog.strip().splitlines()[-2] if blog.strip() else "(无日志)"))
        time.sleep(wait_s)

    print("[accept] 读消息并判定…")
    run_task("task_check.py", timeout=600)
    log = read_log("check.log")
    lines = log.splitlines()
    verdict_line = ""
    for ln in lines:
        if ln.startswith("VERDICT:"):
            verdict_line = ln
    if not verdict_line:
        print("[accept] 没有 VERDICT 行，按 UNKNOWN 处理；check.log 尾部：")
        print("\n".join(lines[-15:]))
        return 2

    verdict = verdict_line.split()[1]
    print("[accept] " + verdict_line)
    errs = [ln for ln in lines if ln.strip().startswith("[error]") or ln.strip().startswith("[fatalerror]")]
    for ln in errs[:10]:
        print("         " + ln.strip()[:200])
    if len(errs) > 10:
        print("         … 另有 %d 条错误，见 ipc/check.log" % (len(errs) - 10))
    print("[accept] 完整日志：%s" % os.path.join(IPC, "check.log"))
    return VERDICT_EXIT.get(verdict, 2)


if __name__ == "__main__":
    sys.exit(main())
