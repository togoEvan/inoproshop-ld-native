# -*- coding: utf-8 -*-
"""从模板导出的 native 里提取「action Entry」的原始 XML 块，作为生成器模板。

action Entry 的特征：EntryList 下 IsRoot=False、TypeGuid=8ac092e5（Action）。
它没有 Interface，Object 直接是 Implementation{25e509de} + NetworkList。
"""
import io
import os
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))
SRC = os.path.join(ROOT, "..", "plc_mcp", "ipc", "axis_prg_EM00_ETC_152738.native")
OUT = os.path.join(ROOT, "assets", "natives", "action_entry_template.xml")


def block_end(s, start, open_tag, close_tag):
    """从 start（指向 open_tag 起点）找到配对的 close_tag 之后的位置。

    起始标签本身计入 depth=1；自闭合的 `<X ... />` 不改变深度。
    """
    i = start
    depth = 0
    while i < len(s):
        no = s.find(open_tag, i)
        nc = s.find(close_tag, i)
        if nc < 0:
            return -1
        if 0 <= no < nc:
            # 检查是否自闭合：标签末尾 '/>' 在 '>' 之前
            gt = s.find(u">", no)
            if gt < 0:
                return -1
            if s[gt - 1] == u"/":
                i = gt + 1
                continue
            depth += 1
            i = gt + 1
        else:
            depth -= 1
            i = nc + len(close_tag)
            if depth == 0:
                return i
    return -1


raw = io.open(SRC, "r", encoding="utf-8").read()

key = u'<List2 Name="EntryList">'
p = raw.find(key)
assert p >= 0, "no EntryList"
inner_start = p + len(key)
end = block_end(raw, p, u"<List2", u"</List2>")
assert end > 0
inner = raw[inner_start:end - len(u"</List2>")]

# 逐个切出顶层 Entry（Type={6198ad31}）
G_ENTRY = u'<Single Type="{6198ad31-4b98-445c-927f-3258a0e82fe3}"'
entries = []
i = 0
while True:
    q = inner.find(G_ENTRY, i)
    if q < 0:
        break
    e = block_end(inner, q, u"<Single", u"</Single>")
    assert e > 0
    entries.append(inner[q:e])
    i = e

print(u"entries found: %d" % len(entries))
action = None
for e in entries:
    if u'<Single Name="IsRoot" Type="bool">False</Single>' in e:
        action = e
        break
assert action is not None, "no action entry"

io.open(OUT, "w", encoding="utf-8").write(action)
print(u"wrote %s (%d bytes)" % (OUT, len(action)))
