# -*- coding: utf-8 -*-
# @ipy2
"""核对 F01_Variable_GVLVerify 下 8 个副本 GVL 是否保留了 AT 地址，
并与 F01_Variable 原件做地址重叠统计。

输出 ipc/at_check.log
"""
import io
import os
import re
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
_lf = io.open(os.path.join(IPC, u"at_check.log"), "w", encoding="utf-8")

AT_RE = re.compile(u"AT\s*%(M[BDWX]?)(\d+)", re.IGNORECASE)
NAMES = [u"HMI_Alarm", u"HMI_Persistent", u"HMI_UnPersistent", u"PLC_Auto",
         u"PLC_Common", u"PLC_Constant", u"PLC_IO", u"PLC_MES"]


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


def find_child(parent, name):
    for o in parent.get_children():
        if unicode(o.get_name()) == name:
            return o
    return None


def collect(gvl):
    txt = unicode(gvl.textual_declaration.text)
    out = []
    for ln in txt.split(u"\n"):
        m = AT_RE.search(ln)
        if not m:
            continue
        nm = ln.strip().split()[0]
        out.append((nm, m.group(0).replace(u" ", u"").upper(), m.group(1).upper(), int(m.group(2))))
    return out, txt


try:
    proj = projects.primary
    app = proj.active_application
    fold = find_child(app, u"F01_Variable_GVLVerify")
    L(u"folder: %s" % (unicode(fold.get_name()) if fold else u"MISSING"))

    orig_addr = {}   # (kind, num) -> (gvl, var)
    orig_folder = find_child(app, u"F01_Variable")
    L(u"=== 原件 F01_Variable ===")
    for o in orig_folder.get_children():
        recs, txt = collect(o)
        L(u"  %-18s AT=%2d  lines=%d" % (unicode(o.get_name()), len(recs), len(txt.split(u"\n"))))
        for nm, a, kind, num in recs:
            orig_addr.setdefault((kind, num), []).append((unicode(o.get_name()), nm))

    L(u"")
    L(u"=== 副本 F01_Variable_GVLVerify ===")
    copy_addr = {}
    for o in fold.get_children():
        nm_o = unicode(o.get_name())
        if not nm_o.endswith(u"_GVLVerify"):
            L(u"  %-24s (skip, 非副本)" % nm_o)
            continue
        recs, txt = collect(o)
        L(u"  %-24s AT=%2d  lines=%d" % (nm_o, len(recs), len(txt.split(u"\n"))))
        for nm, a, kind, num in recs:
            copy_addr.setdefault((kind, num), []).append((nm_o, nm))

    L(u"")
    L(u"=== 地址重叠 ===")
    both = sorted(set(orig_addr) & set(copy_addr))
    L(u"原件地址数=%d  副本地址数=%d  重叠=%d"
      % (len(orig_addr), len(copy_addr), len(both)))
    for k in both:
        L(u"  %%%s%d  原件=%s  副本=%s"
          % (k[0], k[1], orig_addr[k], copy_addr[k]))
    L(u"=== done ===")
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))
finally:
    _lf.close()
