# -*- coding: utf-8 -*-
"""导出 F02_Struct：整文件夹 native + 逐个成员 native；展开子文件夹；dump Struct 声明文本。

用法：bridge.py eval_file {"path": ".../task_export_f02.py"}
输出：ipc/F02_Struct_backup.native + ipc/f02/<名字>.native + ipc/f02_decl.txt
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[0])))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
OUTDIR = os.path.join(IPC, u"f02")
if not os.path.isdir(OUTDIR):
    os.makedirs(OUTDIR)
DECL = os.path.join(IPC, u"f02_decl.txt")
_lf = io.open(DECL, "w", encoding="utf-8")


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


proj = projects.primary
app = proj.active_application
target = None
for o in app.get_children():
    if unicode(o.get_name()) == u"F02_Struct":
        target = o
        break
if target is None:
    raise RuntimeError(u"F02_Struct not found")


def kids(o):
    try:
        return list(o.get_children())
    except Exception:
        return []


def export_one(o, tag):
    n = unicode(o.get_name()).replace(u"/", u"_").replace(u"\\", u"_")
    p = os.path.join(OUTDIR, u"%s.native" % n)
    if os.path.exists(p):
        os.remove(p)
    o.export_native(p)
    L(u"[export %s] %s -> %d bytes" % (tag, n, os.path.getsize(p)))


def dump_tree(o, indent):
    for c in kids(o):
        n = unicode(c.get_name())
        try:
            guid = unicode(c.metaobject_stripped.type_guid)
        except Exception:
            try:
                guid = unicode(c.metaobject.type_guid)
            except Exception:
                guid = u"?"
        L(u"%s- %s  [%s]" % (indent, n, guid))
        # 有文本声明就 dump
        try:
            t = c.textual_declaration
            if t:
                L(u"%s    ```" % indent)
                for ln in unicode(t).split(u"\n"):
                    L(u"%s    %s" % (indent, ln.rstrip()))
                L(u"%s    ```" % indent)
        except Exception:
            pass
        dump_tree(c, indent + u"  ")


# 整文件夹导出
OUTF = os.path.join(IPC, u"F02_Struct_backup.native")
if os.path.exists(OUTF):
    os.remove(OUTF)
target.export_native(OUTF)
L(u"[export folder] F02_Struct -> %d bytes" % os.path.getsize(OUTF))

# 逐个成员导出
for c in kids(target):
    export_one(c, u"child")

# 递归树 + 声明
L(u"")
L(u"=== F02_Struct 递归树 + 声明 ===")
dump_tree(target, u"")
L(u"=== done ===")
_lf.close()
print(u"done")
