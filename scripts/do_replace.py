# -*- coding: utf-8 -*-
"""静默替换工程内的 native 对象（绝不弹确认框）。

原理：InoProShop 的 import_native(path) 只有 1 个路径参数时，遇到同名对象会弹
模态「是否替换」对话框。这里改为「先把旧对象改名让位 -> 再导入 -> 删旧对象」，
导入瞬间不存在同名冲突，因此完全不弹框。实测 0.9 秒完成。

用法:
    python do_replace.py <native文件绝对路径> [父对象名] [关键词1,关键词2,...]

示例:
    python do_replace.py work\\out_2cyl.native prg_EM01_Logic "afbCylCtrl[1],IO.xCylActive2"
"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bridge

BASE = bridge.BASE
IPC = bridge.IPC
ARGS = os.path.join(IPC, "import_args.json")
LOG = os.path.join(IPC, "silent_import.log")
TASK = os.path.join(BASE, "ide", "tasks", "task_silent_import.py")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    src = os.path.abspath(sys.argv[1])
    parent = sys.argv[2] if len(sys.argv) > 2 else "prg_EM01_Logic"
    expect = []
    if len(sys.argv) > 3:
        expect = [x.strip() for x in sys.argv[3].split(",") if x.strip()]

    if not os.path.exists(src):
        print(json.dumps({"ok": False, "error": "file not found: %s" % src}, ensure_ascii=False))
        sys.exit(2)

    payload = {"path": src, "parent": parent, "expect": expect}
    tmp = ARGS + ".tmp"
    with io.open(tmp, "w", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False))
    os.replace(tmp, ARGS)

    try:
        os.remove(LOG)
    except OSError:
        pass

    r = bridge.call("eval_file", timeout=180, path=TASK)
    if not r.get("ok"):
        print(json.dumps(r, ensure_ascii=False, indent=2))
        sys.exit(3)

    log = ""
    if os.path.exists(LOG):
        with io.open(LOG, "r", encoding="utf-8") as f:
            log = f.read()
    print(log)


if __name__ == "__main__":
    main()
