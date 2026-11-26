# -*- coding: utf-8 -*-
"""探测 F10 下 4 个 POU 的真实格式：ST / LD / CFC，以及声明与实现的开头。

task_scan_f10.py 把它们都判成 POU(?)，说明实现文本里既没有 "NetworkList"
也没有 "IMPLEMENTATION" —— 需要看真实文本才能确定格式与翻译策略。

输出 ipc/f10_probe.log
"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[0])))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
LOG = os.path.join(IPC, u"f10_probe.log")
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


def txt(o, attr):
    try:
        d = getattr(o, attr)
        if d is None:
            return None
        return unicode(getattr(d, u"text", d) or u"")
    except Exception, e:
        return u"<%s: %s>" % (type(e).__name__, e)


try:
    app = projects.primary.active_application
    f10 = None
    for c in kids(app):
        if nm(c).upper().startswith(u"F10"):
            f10 = c
            break
    if f10 is None:
        raise RuntimeError(u"F10 not found")

    for p in kids(f10):
        n = nm(p)
        L(u"################ %s ################" % n)
        L(u"--- dir (前 40) ---")
        L(u"  %s" % [a for a in dir(p) if not a.startswith(u"_")][:40])

        dec = txt(p, u"textual_declaration")
        imp = txt(p, u"textual_implementation")
        L(u"--- declaration (%s chars) ---" % (len(dec) if dec else 0))
        if dec:
            L(dec[:1800])
        L(u"--- implementation (%s chars) ---" % (len(imp) if imp else 0))
        if imp:
            L(imp[:2500])
        L(u"")
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
print(u"done")
