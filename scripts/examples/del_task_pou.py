# -*- coding: utf-8 -*-
"""从 TaskConfig native 里删掉指定任务下的指定 POU 块。

背景（2026-11-26 实测）：
  ScriptPouObjectList.remove("名字") 打印成功但实际摘不掉（同铁律 25）。
  唯一可靠做法：导出 TaskConfig native -> 删 POU 块 -> 同名覆盖导入。

注意：不能用跨行正则 .*?</Single> —— 会连相邻的 </Single> 一起吃，
  导致 XML 标签失配（实测报「开始标记 List 与结束标记 Single 不匹配」）。
  必须按「行」删除：从 <Single Type="{f194d1ef...}"> 起，到下一个 </Single> 止。

用法：
  python del_task_pou.py <taskcfg.native> <任务名> <POU名> [输出路径]
"""
import io
import re
import sys

POU_ENTRY_TYPE = u"{f194d1ef-7376-42ce-a729-4a5485a97a46}"


def _u(x):
    try:
        return unicode(x)  # noqa: F821  (IronPython 2.7)
    except NameError:
        return x


def find_task_block(s, task_name):
    """返回该任务 Single 块的 (start, end) 字符区间。"""
    key = u'>%s</Single>' % task_name
    i = s.find(key)
    if i < 0:
        raise RuntimeError(u"task %s not found" % task_name)
    start = s.rfind(u"<Single Type=", 0, i)
    if start < 0:
        raise RuntimeError(u"task block start not found for %s" % task_name)

    depth = 0
    pos = start
    tag_re = re.compile(r"<(/?)(Single|List|Array|Dictionary|Null)\b")
    while True:
        m = tag_re.search(s, pos)
        if m is None:
            raise RuntimeError(u"unbalanced tags for %s" % task_name)
        is_close = (m.group(1) == u"/")
        if not is_close:
            gt = s.find(u">", m.end())
            if gt < 0:
                raise RuntimeError(u"malformed tag")
            selfclose = s[gt - 1] == u"/"
            if not selfclose:
                depth += 1
        else:
            depth -= 1
        if depth == 0 and is_close:
            end = s.find(u">", m.end()) + 1
            return start, end
        pos = m.end()


def remove_pou_from_task(s, task_name, pou_name):
    a, b = find_task_block(s, task_name)
    block = s[a:b]

    pl_i = block.find(u'Name="PouList"')
    if pl_i < 0:
        raise RuntimeError(u"PouList not found in task %s" % task_name)
    pl_end = block.find(u"</List>", pl_i)
    pl_seg = block[pl_i:pl_end]

    lines = pl_seg.split(u"\n")
    out = []
    i = 0
    removed = False
    marker = u'<Single Type="%s"' % POU_ENTRY_TYPE
    name_marker = u">%s</Single>" % pou_name
    while i < len(lines):
        ln = lines[i]
        if (not removed and marker in ln
                and i + 1 < len(lines) and name_marker in lines[i + 1]):
            # 从 <Single Type=...> 行起，一直跳到「单独一行 </Single>」为止（含）
            j = i
            while j < len(lines):
                if lines[j].strip() == u"</Single>":
                    break
                j += 1
            i = j + 1
            removed = True
            continue
        out.append(ln)
        i += 1

    if not removed:
        return s, False

    new_pl = u"\n".join(out)
    new_block = block[:pl_i] + new_pl + block[pl_end:]
    return s[:a] + new_block + s[b:], True


def main():
    src = sys.argv[1]
    task = _u(sys.argv[2])
    pou = _u(sys.argv[3])
    dst = sys.argv[4] if len(sys.argv) > 4 else src.replace(u".native", u"_fixed.native")

    s = io.open(src, u"r", encoding=u"utf-8").read()
    s2, ok = remove_pou_from_task(s, task, pou)
    if not ok:
        print(u"NOT FOUND: %s in %s" % (pou, task))
        return 2
    io.open(dst, u"w", encoding=u"utf-8").write(s2)
    print(u"removed %s from %s -> %s" % (pou, task, dst))
    return 0


if __name__ == u"__main__":
    sys.exit(main())
