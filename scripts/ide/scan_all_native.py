# -*- coding: utf-8 -*-
"""批量导出工程里所有可导出的 POU（含 FB/PRG/Function），用于结构学习。

与 export_live.py 的区别：本脚本不依赖 ipc/export_targets.txt，
而是自己遍历 active_application 的**全部后代对象**，凡是能
export_native 的都导出，文件名带序号+对象名，避免重名覆盖。

输出：<IPC>/scan_<序号>_<名字>.native
日志：<IPC>/scan_all.log
"""
import io
import os
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[0])))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
_lf = io.open(os.path.join(IPC, "scan_all.log"), "w", encoding="utf-8")


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


def walk(obj, depth=0, out=None):
    """递归收集所有对象（不进入 folder 的深层也可，但先都收）"""
    if out is None:
        out = []
    try:
        children = list(obj.get_children())
    except Exception:
        return out
    for c in children:
        try:
            name = unicode(c.get_name())
        except Exception:
            continue
        out.append((depth, name, c))
        walk(c, depth + 1, out)
    return out


try:
    proj = projects.primary
    app = proj.active_application
    L(u"app = %s" % unicode(app.get_name()))

    objs = walk(app)
    L(u"total objects = %d" % len(objs))

    n_ok = 0
    n_fail = 0
    idx = 0
    for depth, name, o in objs:
        idx += 1
        safe = u"".join(ch if (ch.isalnum() or ch in u"_-") else u"_" for ch in name)
        outp = os.path.join(IPC, u"scan_%03d_%s.native" % (idx, safe))
        try:
            o.export_native(outp)
            sz = os.path.getsize(outp)
            if sz < 200:
                # 空壳（folder 等），删掉免得干扰
                os.remove(outp)
                L(u"SKIP %s (empty %d bytes)" % (name, sz))
            else:
                n_ok += 1
                L(u"OK   [%03d] %s%s -> %s (%d bytes)"
                  % (idx, u"  " * depth, name, os.path.basename(outp), sz))
        except Exception, e:
            n_fail += 1
            L(u"FAIL [%03d] %s : %s" % (idx, name, e))

    L(u"")
    L(u"导出成功 %d 个，失败 %d 个" % (n_ok, n_fail))
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))
finally:
    _lf.close()
