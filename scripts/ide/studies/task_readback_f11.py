import io, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base
BASE=_base.resolve_base(); IPC=_base.ensure_ipc(BASE)
_lf=io.open(os.path.join(IPC,"readback_f11.log"),"w",encoding="utf-8")
def L(m):
    _lf.write(u"%s\n"%unicode(m)); _lf.flush()
app=projects.primary.active_application
for o in app.get_children():
    if unicode(o.get_name())==u"prg_F11VerifyUse":
        L(u"decl: %r"%unicode(o.textual_declaration.text))
        L(u"impl: %r"%unicode(o.textual_implementation.text))
_lf.close()
print("done")
