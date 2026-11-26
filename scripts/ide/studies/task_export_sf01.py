# -*- coding: utf-8 -*-
"""补导出：SF01_Alarm 子文件夹的 14 个报警结构体 + F02_Struct_Verify 文件夹的 SV GUID。

输出：
  ipc/f02b/<名字>.native     14 个报警结构体
  ipc/f02b_verify_sv.txt     F02_Struct_Verify 的 SV 节点 guid（子文件夹的 parent_container_guid）
  ipc/f02b_folder_native.txt F02_Struct_Verify 导出 native 的路径（供解析其内部 entry 布局）
"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
OUTDIR = os.path.join(IPC, u"f02b")
if not os.path.isdir(OUTDIR):
    os.makedirs(OUTDIR)
SVF = os.path.join(IPC, u"f02b_verify_sv.txt")
LOG = os.path.join(IPC, u"f02b_export.log")
_lf = io.open(LOG, u"w", encoding="utf-8")


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

    # 1) 找 F02_Struct_Verify 与 F02_Struct>SF01_Alarm
    verify_folder = None
    sf01 = None
    for o in app.get_children():
        n = unicode(o.get_name())
        if n == u"F02_Struct_Verify":
            verify_folder = o
        elif n == u"F02_Struct":
            for k in kids(o):
                if unicode(k.get_name()) == u"SF01_Alarm":
                    sf01 = k
    if verify_folder is None:
        raise RuntimeError(u"F02_Struct_Verify not found")
    if sf01 is None:
        raise RuntimeError(u"SF01_Alarm not found")

    # 2) 导出 F02_Struct_Verify 整文件夹（GUID 解析放主机侧——
    #    IDE 内的 ElementTree 是老 xmllib，解析 native 报 illegal character）
    out_native = os.path.join(OUTDIR, u"F02_Struct_Verify_backup.native")
    if os.path.exists(out_native):
        os.remove(out_native)
    verify_folder.export_native(out_native)
    L(u"verify folder exported -> %d bytes" % os.path.getsize(out_native))

    # 3) 逐个导出 SF01_Alarm 的 14 个结构体
    cnt = 0
    for c in kids(sf01):
        n = unicode(c.get_name())
        p = os.path.join(OUTDIR, u"%s.native" % n)
        if os.path.exists(p):
            os.remove(p)
        c.export_native(p)
        L(u"[export] %s -> %d bytes" % (n, os.path.getsize(p)))
        cnt += 1
    L(u"exported %d structs" % cnt)

    # 4) dump 一个结构体的声明文本（供 A/B 样本参考）
    for c in kids(sf01):
        n = unicode(c.get_name())
        if u"Common" in n:
            L(u"--- decl of %s ---" % n)
            try:
                td = c.textual_declaration
                # ScriptTextDocument：用 .text
                txt = None
                try:
                    txt = unicode(td.text)
                except Exception:
                    txt = unicode(td)
                if txt and u"ScriptTextDocument" not in txt:
                    for ln in txt.split(u"\n"):
                        L(u"  %s" % ln.rstrip())
                    break
            except Exception, e:
                L(u"  (read decl failed: %s)" % e)
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
print(u"done")
