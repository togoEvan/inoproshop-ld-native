# -*- coding: utf-8 -*-
"""导出 F01_Variable_GVLVerify 的 GVL 变量名 → GVLVerify 变量名映射 + F04 副本将引用的引脚类型。

输出 ipc/f04_gvl_map.json：
  { "<GVLVerify变量名>": "<类型>" , ... }
以及 ipc/f04_gvl_orig2ver.json：原件名 -> GVLVerify 名（供 F04 副本 FB 引脚把
「Gv_xxx」原件引用改写为「Gv_xxx_GVLVerify」）。
"""
import io
import json
import os
import re
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
LOG = os.path.join(IPC, u"f04_gvl_export.log")
_lf = io.open(LOG, "w", encoding="utf-8")


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


def kids(o):
    try:
        return list(o.get_children())
    except Exception:
        return []


try:
    app = projects.primary.active_application
    gdir = None
    for o in app.get_children():
        if unicode(o.get_name()) == u"F01_Variable_GVLVerify":
            gdir = o
            break
    if gdir is None:
        raise RuntimeError(u"F01_Variable_GVLVerify not found")

    # 每个副本 GVL：解析声明文本，提取 变量名 -> 类型
    VAR_RE = re.compile(
        u"^\\s*([A-Za-z_\\u4e00-\\u9fff][A-Za-z0-9_\\u4e00-\\u9fff]*)\\s*:\\s*([^;]+);")
    gvl_map = {}      # 副本变量名 -> 类型
    orig2ver = {}     # 原件变量名 -> 副本变量名
    total = 0
    for g in kids(gdir):
        gn = unicode(g.get_name())
        if not gn.endswith(u"_GVLVerify"):
            continue
        try:
            txt = unicode(g.textual_declaration.text)
        except Exception, e:
            L(u"WARN: %s decl read failed: %s" % (gn, e))
            continue
        cnt = 0
        for ln in txt.split(u"\n"):
            m = VAR_RE.match(ln)
            if not m:
                continue
            vname = m.group(1)
            vtype = m.group(2).strip()
            gvl_map[vname] = vtype
            orig2ver[vname[:-len(u"_GVLVerify")]] = vname
            cnt += 1
        total += cnt
        L(u"%s: %d vars" % (gn, cnt))
    L(u"total vars: %d" % total)

    io.open(os.path.join(IPC, u"f04_gvl_map.json"), u"w", encoding=u"utf-8").write(
        json.dumps(gvl_map, ensure_ascii=False, indent=1))
    io.open(os.path.join(IPC, u"f04_gvl_orig2ver.json"), u"w", encoding=u"utf-8").write(
        json.dumps(orig2ver, ensure_ascii=False, indent=1))

    # 摘录几个 BOOL 变量供 A/B 样本用
    bools = [k for k, v in gvl_map.items() if v.upper() == u"BOOL"][:10]
    L(u"sample BOOL vars: %s" % bools)
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
print(u"done")
