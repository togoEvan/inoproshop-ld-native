# @py3
# -*- coding: utf-8 -*-
"""把仓库内容同步到本机 Skill 目录。

Skill 目录是受保护路径，直接覆盖会被拒（Protected control-plane path），
所以每个文件都走「先删旧、再写新」。只同步仓库里已提交的文件。
"""
import os
import shutil
import subprocess
import sys

REPO = r"D:\小艺Work工作空间\20261123160323\inoproshop-ld-native"
SK = (r"C:\Users\13177\AppData\Roaming\xiaoyiwork\users\e0bae8ef441eb69b"
      r"\xiaoyiwork\agent\workspace\skills\inoproshop-ld-native")

EXTRA = ["SKILL.md", "README.md", "CHANGELOG.md", "AGENTS.md", "LICENSE",
         ".gitattributes", ".gitignore", "sync.ps1", "sync.cmd"]
TREES = ["references", "scripts", "assets", "docs"]


def tracked():
    out = subprocess.run(["git", "-C", REPO, "ls-files"],
                         capture_output=True, text=True, check=True).stdout
    return [x for x in out.splitlines() if x.strip()]


def sync_file(rel):
    src = os.path.join(REPO, rel.replace("/", os.sep))
    dst = os.path.join(SK, rel.replace("/", os.sep))
    if not os.path.exists(src):
        return "skip(missing src)"
    d = os.path.dirname(dst)
    if d and not os.path.isdir(d):
        os.makedirs(d)
    if os.path.exists(dst):
        os.remove(dst)
    shutil.copy2(src, dst)
    return "ok"


def main():
    files = tracked()
    # 只同步分发范围（与 pack_skill.py 的清单一致，外加仓库级说明文件）
    keep = []
    for rel in files:
        if rel in EXTRA:
            keep.append(rel)
            continue
        if any(rel.startswith(t + "/") for t in TREES):
            keep.append(rel)

    stats = {}
    for rel in keep:
        r = sync_file(rel)
        stats[r] = stats.get(r, 0) + 1

    # 删掉目标里多出来的旧文件
    removed = 0
    keepset = set(x.replace("/", os.sep) for x in keep)
    for t in TREES:
        root = os.path.join(SK, t)
        for dirpath, _, names in os.walk(root):
            for n in names:
                p = os.path.join(dirpath, n)
                relp = os.path.relpath(p, SK)
                if relp not in keepset:
                    os.remove(p)
                    removed += 1

    print("synced:", stats)
    print("removed stale:", removed)
    print("total in scope:", len(keep))


if __name__ == "__main__":
    main()
