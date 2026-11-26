# -*- coding: utf-8 -*-
"""探测 create_pou 需要的 PouType 枚举怎么拿。"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
_lf = io.open(os.path.join(IPC, u"poutype_probe.log"), "w", encoding="utf-8")


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


try:
    L(u"create_pou doc: %s" % (getattr(app_create_pou_doc, "x", u"")))
except Exception:
    pass

proj = projects.primary
app = proj.active_application
cp = app.create_pou
L(u"callable %r" % cp)
for a in (u"__doc__", u"__name__", u"Overloads"):
    try:
        L(u"attr %s = %r" % (a, getattr(cp, a)))
    except Exception, e:
        L(u"attr %s ERR %s" % (a, e))
try:
    L(u"signature: %s" % unicode(cp.__doc__))
except Exception:
    pass

# 尝试从已加载的程序集找枚举
for mod in (u"ScriptEngine", u"ScriptIecLanguageObjects"):
    try:
        m = __import__(mod)
        L(u"import %s ok" % mod)
    except Exception, e:
        L(u"import %s ERR %s" % (mod, e))

try:
    import clr
    for asm in (u"3S.CoDeSys.ScriptEngine", u"3S.CoDeSys.Core"):
        try:
            clr.AddReference(asm)
            L(u"AddReference %s ok" % asm)
        except Exception, e:
            L(u"AddReference %s ERR %s" % (asm, e))
    from System import Type
    L(u"loaded")
except Exception, e:
    L(u"clr ERR %s" % e)

# 直接尝试数字枚举值
for v in (1, 2, 3, 4):
    try:
        p = app.create_pou(u"prg_PouTypeProbe%d" % v, v)
        L(u"create_pou(%d) OK -> %r" % (v, unicode(p.get_name())))
        p.remove()
    except Exception, e:
        L(u"create_pou(%d) ERR %s" % (v, e))

L(u"=== done ===")
_lf.close()
