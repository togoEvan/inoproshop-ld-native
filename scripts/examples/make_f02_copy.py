# -*- coding: utf-8 -*-
"""把 F02_Struct 的 17 个顶层 Struct DUT「原样复制 + 加后缀」，生成可导入的 native。

思路与 make_f01_copy.py 一致，但对象类型是 DUT（TypeGuid 2db5746d）：
  · DUT 与 GVL 高度同构：Object > Interface > TextDocument > TextLines
  · 无 NetVarProperties / AddAttributeSubsequent / ParameterList（GVL 有，DUT 没有）
  · 无 AT 绝对地址问题（DUT 不占内存地址，不需要剥 AT）
  · ⚠ DUT 的类型名写在**声明文本**里（`TYPE Struct_Clock :`），
    MetaObject.Name 和声明首行必须一起改，否则导入后类型名对不上。

只改「类型名 + 成员名」（成员名加后缀避免潜在重名），
类型引用、注释、缩进全部原样保留。

用法：
    python make_f02_copy.py <输出目录> <后缀> <目标文件夹名>
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_gvl

SRC_DIR = u"D:/小艺Work工作空间/20261123160323/inoproshop-ld-native/scripts/ipc/f02"

# 声明行：  缩进 + 标识符 + 冒号 + 其余（DUT 成员行；不动 TYPE/STRUCT/END_* 行）
MEMBER_RE = re.compile(
    u"^(\\s*)([^\\s:;()]+)(\\s*:.*)$", re.UNICODE)

SKIP_RE = re.compile(
    u"^\\s*(TYPE|STRUCT|UNION|END_|VAR_|END_VAR|\\(\\*|$)", re.IGNORECASE)


def is_comment_line(ln):
    s = ln.strip()
    return s.startswith(u"(*") or s.startswith(u"//")


def rename_member(ln, suffix):
    """DUT 成员行加后缀；注释行 / 段标记行原样返回。"""
    if SKIP_RE.match(ln):
        return ln, False
    if is_comment_line(ln):
        return ln, False
    m = MEMBER_RE.match(ln)
    if not m:
        return ln, False
    return u"%s%s%s%s" % (m.group(1), m.group(2), suffix, m.group(3)), True


def process_struct(native_path, suffix, out_dir):
    """读单个 Struct native → 改名 → 写新 native。返回 (新名, 路径, 统计)。"""
    import xml.etree.ElementTree as ET
    t = ET.parse(native_path)
    root = t.getroot()

    # 1) 找 MetaObject，取原名
    mo = None
    for s in root.iter(u"Single"):
        if s.get(u"Name") == u"MetaObject":
            mo = s
            break
    name_el = None
    for c in mo:
        if c.get(u"Name") == u"Name":
            name_el = c
            break
    old_name = (name_el.text or u"").strip()
    new_name = old_name + suffix
    name_el.text = new_name

    # 2) 改声明文本：TYPE 行 + 成员行
    renamed_members = 0
    for tl in root.iter(u"Single"):
        if tl.get(u"Name") != u"Text":
            continue
        txt = tl.text if tl.text is not None else u""
        s = txt.strip()
        # TYPE 行： `TYPE OldName :` / `TYPE OldName:` 
        m = re.match(u"^(TYPE\\s+)(\\S+)(\\s*:.*?)$", s, re.IGNORECASE)
        if m and m.group(2) == old_name:
            tl.text = u"%s%s%s" % (m.group(1), new_name, m.group(3))
            continue
        # 成员行
        new_ln, hit = rename_member(txt, suffix)
        if hit:
            tl.text = new_ln
            renamed_members += 1

    # 3) Path 数组最后补上目标文件夹名（原件 Path 尾是 F02_Struct）
    for arr in root.iter(u"Array"):
        if arr.get(u"Name") == u"Path":
            for child in list(arr):
                if (child.text or u"").strip() == u"F02_Struct":
                    child.text = u"F02_Struct_Verify"
            break

    out = os.path.join(out_dir, u"%s.native" % new_name)
    t.write(out, encoding=u"utf-8", xml_declaration=False)
    with io.open(out, u"r", encoding=u"utf-8") as f:
        _ = f.read()  # 触发异常早暴露
    return new_name, out, renamed_members


def U(s):
    """CPython3 / IronPython2 兼容的 unicode()。"""
    try:
        return unicode(s)  # noqa: F821  (IronPython 2.7)
    except NameError:
        return str(s)


def main():
    out_dir = U(sys.argv[1])
    suffix = U(sys.argv[2])
    folder = U(sys.argv[3])
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    names = sorted(
        f[:-7] for f in os.listdir(SRC_DIR)
        if f.endswith(u".native") and f != u"SF01_Alarm.native"
        and f != u"F02_Struct_backup.native")
    report = []
    for n in names:
        new_name, out, cnt = process_struct(
            os.path.join(SRC_DIR, n + u".native"), suffix, out_dir)
        report.append(u"%s -> %s (%d members renamed)" % (n, new_name, cnt))
    rf = io.open(os.path.join(out_dir, u"_report.txt"), u"w", encoding=u"utf-8")
    rf.write(u"\n".join(report))
    rf.close()
    print(u"\n".join(report))
    print(u"folder = %s, total = %d" % (folder, len(report)))


if __name__ == u"__main__":
    main()
