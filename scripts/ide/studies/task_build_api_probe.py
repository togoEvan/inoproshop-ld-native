# -*- coding: utf-8 -*-
"""探测 app 的构建类方法（rebuild / clean / generate_code 等），并看它们是否真的重编译。"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
_lf = io.open(os.path.join(IPC, u"build_api_probe.log"), "w", encoding="utf-8")


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


proj = projects.primary
app = proj.active_application
names = [u"build", u"rebuild", u"clean", u"clean_all", u"generate_code",
         u"check_all_pous", u"check", u"generate_code_for_all",
         u"get_build_properties", u"set_build_properties"]
for n in names:
    try:
        v = getattr(app, n)
        L(u"app.%s = %r" % (n, v))
    except Exception, e:
        L(u"app.%s ERR %s" % (n, unicode(e)[:100]))

L(u"--- application object type: %s" % unicode(type(app)))
L(u"=== done ===")
_lf.close()
