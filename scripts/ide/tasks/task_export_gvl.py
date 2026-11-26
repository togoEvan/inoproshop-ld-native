# -*- coding: utf-8 -*-
"""按「文件夹/对象」路径导出单个对象（支持子文件夹），用于观察单对象导出的 SV 结构。

参数 ipc/export_gvl_args.json: {"path": ["F01_Variable_GVLVerify", "GVL_VerifyConst"], "out": "xxx.native"}
"""
import io, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base
BASE = _base.resolve_base(); IPC = _base.ensure_ipc(BASE)
_lf = io.open(os.path.join(IPC, u"export_gvl.log"), "w", encoding="utf-8")
def L(m):
    _lf.write(u"%s\n" % unicode(m)); _lf.flush()

args = json.loads(io.open(os.path.join(IPC, u"export_gvl_args.json"), "r", encoding="utf-8").read())
parts = args.get(u"path")
out = args.get(u"out") or u"single_gvl.native"
outp = os.path.join(IPC, out)
if os.path.exists(outp):
    try: os.remove(outp)
    except Exception: pass

proj = projects.primary
cur = proj.active_application
L(u"start at %s" % cur.get_name())
for nm in parts:
    nxt = None
    for o in cur.get_children():
        if unicode(o.get_name()) == unicode(nm):
            nxt = o; break
    if nxt is None:
        raise RuntimeError(u"%s not found" % nm)
    cur = nxt
    L(u" -> %s" % cur.get_name())

cur.export_native(outp)
L(u"exported -> %s (%d bytes)" % (outp, os.path.getsize(outp)))
_lf.close()
