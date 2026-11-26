# -*- coding: utf-8 -*-
"""验证 GVL 变量是否真的成为「全局变量」：用多种只读 API 探测符号是否存在。

全部 try/except，任何一种 API 不可用都不会中断；不写工程、不 sleep。
输出 ipc/gvl_symbol_check.log
"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
LOG = os.path.join(IPC, u"gvl_symbol_check.log")
_lf = io.open(LOG, "w", encoding="utf-8")

TARGET = u"Gv_xEnable"
GVL = u"GVL_VerifyTest"


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


proj = projects.primary
app = proj.active_application

# 1) GVL 对象文本是否完整读回
try:
    gvl = None
    for o in app.get_children():
        if unicode(o.get_name()) == u"F99_GVLVerify":
            for k in o.get_children():
                if unicode(k.get_name()) == GVL:
                    gvl = k
    L(u"gvl found: %s" % (gvl is not None))
    if gvl is not None:
        txt = None
        for attr in (u"textual_declaration", u"textual_implementation"):
            pass
        try:
            d = gvl.textual_declaration
            L(u"textual_declaration type = %r" % unicode(type(d)))
            try:
                txt = d.text
            except Exception:
                txt = None
        except Exception, e:
            L(u"textual_declaration err: %s" % e)
        if txt:
            L(u"decl len=%d  contains %s: %s" % (len(txt), TARGET, TARGET in txt))
            L(u"--- decl head ---")
            for ln in txt.splitlines()[:6]:
                L(u"  | %s" % ln)
except Exception, e:
    L(u"[1] err %s\n%s" % (e, traceback.format_exc()))

# 2) 尝试各类符号表 API
for expr in (u"proj.get_symbols()", u"app.get_symbols()",
             u"app.get_symbol_configuration()"):
    try:
        res = eval(expr)
        L(u"%s -> %r" % (expr, res))
    except Exception, e:
        L(u"%s -> ERR %s" % (expr, e))

# 3) 变量级访问：GVL 对象的 Object.Interface 里是否有变量枚举 API
try:
    names = [n for n in dir(gvl) if not n.startswith(u"_")]
    L(u"gvl dir: %s" % u", ".join(sorted(names)))
except Exception, e:
    L(u"dir err %s" % e)

# 4) 用 system 的符号服务（若有）
try:
    L(u"system has get_symbols: %s" % hasattr(system, u"get_symbols"))
except Exception, e:
    L(u"system probe err %s" % e)

L(u"=== done ===")
_lf.close()
