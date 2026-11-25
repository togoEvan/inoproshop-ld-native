# -*- coding: utf-8 -*-
"""扫描整个 Application 里所有 AT 绝对地址（含 POU/GVL），算已用区间和空闲区间。

输出 ipc/at_scan.log
"""
import io
import os
import re
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[0])))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
_lf = io.open(os.path.join(IPC, u"at_scan.log"), "w", encoding="utf-8")

AT_RE = re.compile(u"AT\s*%(M[BDWX]?)(\d+)", re.IGNORECASE)
SIZES = {u"BOOL": 1, u"BYTE": 1, u"SINT": 1, u"USINT": 1,
         u"WORD": 2, u"INT": 2, u"UINT": 2,
         u"DWORD": 4, u"DINT": 4, u"UDINT": 4, u"REAL": 4,
         u"LWORD": 8, u"LINT": 8, u"ULINT": 8, u"LREAL": 8}


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


def walk(obj, depth, acc, skip_names=()):
    for o in obj.get_children():
        nm = unicode(o.get_name())
        if nm in skip_names:
            L(u"%s- skip %s" % (u"  " * depth, nm))
            continue
        try:
            txt = unicode(o.textual_declaration.text)
        except Exception:
            txt = None
        if txt:
            for ln in txt.split(u"\n"):
                m = AT_RE.search(ln)
                if m:
                    acc.append((nm, ln.strip()))
        walk(o, depth + 1, acc)


try:
    app = projects.primary.active_application
    acc = []
    walk(app, 0, acc, skip_names=(u"F01_Variable_GVLVerify",))
    L(u"=== 除副本文件夹外的全部 AT 声明 : %d 条 ===" % len(acc))
    spans = []
    for nm, ln in acc:
        m = AT_RE.search(ln)
        kind, num = m.group(1).upper(), int(m.group(2))
        rest = ln[m.end():]
        tm = re.search(u":\s*([A-Za-z_][A-Za-z0-9_]*)", rest)
        tn = tm.group(1).upper() if tm else u"?"
        size = SIZES.get(tn)
        if size is None:
            size = 1
            arr = re.search(u"ARRAY\s*\[\s*(-?\d+)\s*\.\.\s*(-?\d+)\s*\]\s*OF\s+([A-Za-z_][A-Za-z0-9_]*)", rest, re.I)
            if arr:
                n = int(arr.group(2)) - int(arr.group(1)) + 1
                size = n * SIZES.get(arr.group(3).upper(), 1)
        spans.append((kind, num, num + size - 1, nm, tn, ln.strip()[:70]))
    spans.sort()
    # 合并
    merged = []
    for s in spans:
        if merged and s[0] == merged[-1][0] and s[1] <= merged[-1][2] + 1:
            merged[-1] = (s[0], merged[-1][1], max(merged[-1][2], s[2]))
        else:
            merged.append((s[0], s[1], s[2]))
    L(u"=== 合并后已用区间 (%d) ===" % len(merged))
    for k, a, b in merged:
        L(u"  %%%s%d ~ %%%s%d" % (k, a, k, b))
    L(u"=== 空闲（在最后一个已用区间之后从末尾+1 起）===")
    if merged:
        last = merged[-1]
        L(u"  可用起点: %%%s%d" % (last[0], last[2] + 1))
    L(u"=== done ===")
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))
finally:
    _lf.close()
