# -*- coding: utf-8 -*-
"""F08 轴组用法探测：工程里轴组是怎么被 POU 引用的 + 对照实验。

三个目的：
  1) 找 FB_AxisGroup（depth=3）的声明与实现，看轴组在 ST 里用什么类型
  2) 找工程里所有引用 AxesGroup_A1 / AxesGroup_C1 的 POU，抄它的写法
  3) 对照实验：把原件 AxesGroup_A1 不改任何字段、只改名导入到 Verify 文件夹，
     看 AxisGuid 是否同样被清空 —— 证明「清空是 IDE 必然行为，与复制脚本无关」

输出 ipc/f08_usage.log
"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
LOG = os.path.join(IPC, u"f08_usage.log")
_lf = io.open(LOG, "w", encoding="utf-8")


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


def kids(o):
    try:
        return list(o.get_children())
    except Exception:
        return []


def nm(o):
    try:
        return unicode(o.get_name())
    except Exception:
        return u"?"


def walk_all(o, depth=0, acc=None):
    if acc is None:
        acc = []
    acc.append((o, depth))
    for c in kids(o):
        walk_all(c, depth + 1, acc)
    return acc


def text_of(o, attr):
    try:
        d = getattr(o, attr)
        if d is None:
            return None
        return unicode(getattr(d, u"text", d) or u"")
    except Exception:
        return None


try:
    app = projects.primary.active_application
    allobj = walk_all(app)

    # 1) FB_AxisGroup
    L(u"=== FB_AxisGroup 声明 ===")
    for o, d in allobj:
        n = nm(o)
        if n in (u"FB_AxisGroup", u"FB_AxisGroup_F04V"):
            L(u"--- %s (depth=%d) ---" % (n, d))
            dec = text_of(o, u"textual_declaration")
            if dec:
                L(u"[DECLARATION]")
                L(dec)
            imp = text_of(o, u"textual_implementation")
            if imp:
                L(u"[IMPLEMENTATION 前 1500 字]")
                L(imp[:1500])
            L(u"")

    # 2) 搜索所有 POU 里出现 AxesGroup 字样的地方
    L(u"=== 引用 AxesGroup 的 POU（声明或实现里出现 AxesGroup 字样）===")
    hits = 0
    for o, d in allobj:
        dec = text_of(o, u"textual_declaration")
        imp = text_of(o, u"textual_implementation")
        for label, txt in ((u"decl", dec), (u"impl", imp)):
            if not txt:
                continue
            if u"AxesGroup" in txt or u"AXES_GROUP" in txt.upper():
                hits += 1
                L(u"--- %s [%s] ---" % (nm(o), label))
                # 只打含关键字的行
                for ln in txt.split(u"\n"):
                    if u"AxesGroup" in ln or u"AXES_GROUP" in ln.upper():
                        L(u"    %s" % ln.strip())
                L(u"")
                break
    L(u"命中 POU 数 = %d" % hits)
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
print(u"done")
