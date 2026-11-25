# -*- coding: utf-8 -*-
"""反射查找 PouType 枚举类型，拿到枚举值后 create_pou。"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[0])))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
_lf = io.open(os.path.join(IPC, u"poutype_probe3.log"), "w", encoding="utf-8")


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


proj = projects.primary
app = proj.active_application

try:
    import System
    asms = System.AppDomain.CurrentDomain.GetAssemblies()
    L(u"assemblies: %d" % asms.Length)
    found = None
    for a in asms:
        try:
            for t in a.GetTypes():
                if unicode(t.Name) == u"PouType":
                    found = t
                    L(u"FOUND %s in %s" % (unicode(t.FullName), unicode(a.GetName().Name)))
                    for n in System.Enum.GetNames(t):
                        L(u"   %s = %s" % (n, System.Enum.Parse(t, n)))
        except Exception, e:
            pass
    if found is None:
        L(u"PouType not found by reflection")
except Exception, e:
    L(u"reflect ERR %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
