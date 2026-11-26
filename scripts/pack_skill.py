# -*- coding: utf-8 -*-
# @py3
"""打包 .skill 分发件。

只打 SKILL.md / references/ / scripts/ / assets/，且文件清单严格取自
`git ls-files`——保证包里永远是**已提交并推送的版本**，不会混入
本地未提交的改动或已被删除的旧文件。

用法：
    python scripts/pack_skill.py [输出路径]

默认输出：仓库同级目录的 inoproshop-ld-native.skill
"""
import os
import subprocess
import sys
import zipfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL_NAME = "inoproshop-ld-native"
DEFAULT_OUT = os.path.join(os.path.dirname(REPO), SKILL_NAME + ".skill")

# 只打这四类内容；docs/、AGENTS.md、sync.ps1 等仓库专属文件不进包
KEEP_DIRS = ("references", "scripts", "assets")
KEEP_ROOT_FILES = ("SKILL.md",)


def git_files():
    out = subprocess.check_output(
        ["git", "ls-files"], cwd=REPO
    ).decode("utf-8").splitlines()
    keep = []
    for f in out:
        if f in KEEP_ROOT_FILES:
            keep.append(f)
        elif f.split("/")[0] in KEEP_DIRS:
            keep.append(f)
    return sorted(keep)


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_OUT

    files = git_files()
    if not files:
        print("ERROR: git ls-files 没有返回任何可打包文件")
        return 1

    if os.path.exists(out):
        os.remove(out)

    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            src = os.path.join(REPO, f)
            if not os.path.exists(src):
                print("ERROR: 文件缺失 %s" % src)
                return 2
            z.write(src, "%s/%s" % (SKILL_NAME, f))

    print("打包完成: %s" % out)
    print("  文件数: %d" % len(files))
    print("  大小:   %.1f KB" % (os.path.getsize(out) / 1024.0))
    for f in files:
        print("    %s" % f)
    return 0


if __name__ == "__main__":
    sys.exit(main())
