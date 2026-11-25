# -*- coding: utf-8 -*-
"""把 F01_Variable 的 8 个 GVL「原样复制 + 变量名加后缀」，生成可导入的 native。

设计要点
--------
1. **变量名加后缀**：只改「声明行的标识符」，注释、类型、初值、段标记全部原样。
2. **剥掉 AT 绝对地址**：副本若沿用 `AT %MB146680`，会与原件争用同一物理地址，
   编译必然报地址冲突。副本不需要绑定物理地址，所以把 `AT %MBxxxx` 去掉，
   由 IDE 自行分配（实测 IDE 会给 RETAIN 段自动分配地址）。
3. **块注释状态机**：`(* ... *)` 可能跨行，注释里的「0-心跳」这类文本不能被当声明改。
4. 每个 GVL 输出**单独一个 native**（一个 entry），导入时逐个进目标文件夹，
   避免整包替换文件夹带来的同名覆盖弹框。

用法：
    python make_f01_copy.py <输出目录> <后缀> <目标文件夹名>
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_gvl

SRC_JSON = u"D:/plc_study/f01_lines.json"
PATH_APP = [u"Device", u"PLC 逻辑", u"Application"]

# 声明行：  缩进 + 标识符 + 可选 AT 地址 + 冒号 + 其余
DECL_RE = re.compile(
    u"^(\\s*)([^\\s:()]+)(\\s+AT\\s*%\\S+)?(\\s*:.*)$", re.UNICODE)

SEC_START = re.compile(u"^\\s*VAR_GLOBAL", re.IGNORECASE)
SEC_END = re.compile(u"^\\s*END_VAR", re.IGNORECASE)


def strip_at(line):
    """去掉行内的 ` AT %MBxxxx` 片段（只动声明里的地址，不动注释）。"""
    # 只在第一个 ':' 之前处理
    ci = line.find(u":")
    if ci < 0:
        return line
    head, tail = line[:ci], line[ci:]
    head = re.sub(u"\\s+AT\\s*%\\S+", u"", head, flags=re.IGNORECASE)
    return head + tail


AT_PART_RE = re.compile(u"AT\\s*%(M[BDWX]?)(\\d+)", re.IGNORECASE)


def shift_at(at_part, offset):
    """把 `AT %MB131076` 里的数字整体加 offset，返回新的 AT 片段。

    offset 可以是 int（所有内存区同一个偏移），也可以是
    {u"MB": 400000, u"MW": 4000} 这样的按区偏移字典。
    """
    m = AT_PART_RE.search(at_part)
    if not m:
        return at_part
    kind = m.group(1).upper()
    if isinstance(offset, dict):
        off = offset.get(u"M" + kind, offset.get(kind, 0))
    else:
        off = offset
    new = int(m.group(2)) + off
    return at_part[:m.start()] + u"AT %%%s%d" % (m.group(1), new) + at_part[m.end():]


def rename_lines(lines, suffix, keep_at=False, at_offset=0):
    """返回 (新行列表, 改名列表, 未识别声明列表)。

    keep_at=True 时保留原始 `AT %MBxxxx` 绝对地址（用于验证地址冲突行为）；
    at_offset 非 0 时把地址整体平移（保留 AT 但避开与原件冲突）。
    """
    out = []
    renamed = []
    unknown = []
    in_block = False
    in_sec = False
    for raw in lines:
        if raw is None:
            out.append(None)
            continue
        s = raw
        stripped = s.strip()

        # ---- 块注释状态推进（先算本行结束后的状态） ----
        if in_block:
            if u"*)" in stripped:
                in_block = False
            out.append(s)
            continue
        if stripped.startswith(u"(*") and u"*)" not in stripped:
            in_block = True
            out.append(s)
            continue
        if stripped.startswith(u"(*"):
            out.append(s)
            continue

        if SEC_START.match(s):
            in_sec = True
            out.append(s)
            continue
        if SEC_END.match(s):
            in_sec = False
            out.append(s)
            continue

        if not in_sec:
            out.append(s)
            continue
        if not stripped or stripped.startswith(u"//"):
            out.append(s)
            continue

        m = DECL_RE.match(s)
        if not m:
            unknown.append(s)
            out.append(s)
            continue
        indent, name, at_part, rest = m.group(1), m.group(2), m.group(3) or u"", m.group(4)
        if keep_at:
            ap = shift_at(at_part, at_offset) if at_part else u""
            new_line = indent + name + suffix + ap + rest
        else:
            new_line = indent + name + suffix + rest          # at_part 被丢弃
        if at_part:
            renamed.append((name, name + suffix, at_part.strip()))
        else:
            renamed.append((name, name + suffix, u""))
        out.append(new_line)
    return out, renamed, unknown


def main():
    outdir = sys.argv[1] if len(sys.argv) > 1 else u"."
    suffix = sys.argv[2] if len(sys.argv) > 2 else u"_GVLVerify"
    folder_name = sys.argv[3] if len(sys.argv) > 3 else u"F01_Variable_GVLVerify"
    # 目标文件夹在工程里已存在，必须用它的真实 guid 当父容器
    folder_guid = (sys.argv[4] if len(sys.argv) > 4
                   else u"442efa6b-6fb0-4577-84fe-9d175d3385fc")
    # 第 5 参数：keep 表示保留 AT 地址（验证地址冲突），drop 表示剥掉（默认）
    keep_at = (len(sys.argv) > 5 and sys.argv[5].lower() == u"keep")
    # 第 6 参数：AT 地址平移量。支持 "368924"（所有区同偏移）
    # 或 "MB=368924,MW=4000"（按区偏移；0 = 原样保留，会与原件冲突）
    at_offset = 0
    if len(sys.argv) > 6:
        spec = sys.argv[6]
        if u"=" in spec:
            at_offset = {}
            for part in spec.split(u","):
                k, v = part.split(u"=")
                at_offset[k.strip().upper()] = int(v)
        else:
            at_offset = int(spec)

    import json
    data = json.loads(io.open(SRC_JSON, "r", encoding="utf-8").read())
    total_renamed = 0
    total_at = 0
    report = []
    for gvl_name in sorted(data.keys()):
        lines = data[gvl_name]
        new_lines, renamed, unknown = rename_lines(
            lines, suffix, keep_at=keep_at, at_offset=at_offset)
        total_renamed += len(renamed)
        total_at += sum(1 for r in renamed if r[2])
        report.append((gvl_name, len(lines), len(renamed),
                       sum(1 for r in renamed if r[2]), len(unknown)))
        if unknown:
            print(u"!! %s 未识别声明 %d 行:" % (gvl_name, len(unknown)))
            for u in unknown[:5]:
                print(u"     %r" % u)

        sv = make_gvl.new_guid()
        make_gvl.reset_ids(1000)
        entry = make_gvl.gvl_entry(
            name=gvl_name + suffix,
            lines=new_lines,
            guid=make_gvl.new_guid(),
            parent_container_guid=folder_guid,
            path_parts=PATH_APP + [folder_name],
            sv_root_guid=sv,
            is_root=False)
        dst = os.path.join(outdir, u"%s%s.native" % (gvl_name, suffix))
        make_gvl.build_export([entry], dst, sv)
        print(u"%-18s %4d 行  改名 %3d (含 AT %2d)  -> %s"
              % (gvl_name, len(lines), len(renamed),
                 sum(1 for r in renamed if r[2]), os.path.basename(dst)))

    print(u"-" * 70)
    print(u"合计改名 %d 个变量，其中剥掉 AT 地址 %d 个" % (total_renamed, total_at))
    print(u"folder_guid = %s" % folder_guid)


if __name__ == "__main__":
    main()
