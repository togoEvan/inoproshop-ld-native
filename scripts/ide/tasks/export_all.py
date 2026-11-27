# -*- coding: utf-8 -*-
# @ipy2
"""在 IDE 里跑：递归导出 active_application 的全部后代为独立 .native（IronPython 2.7）。

用法（隐藏桌面实例或 --runscript 注入）：
    LD_PROJ / LD_RAW / LD_EXPORT_LOG 三个环境变量可覆盖默认路径。
每个对象一个文件 raw/NNN_<safe_name>.native；小于 200 字节的自动删除（空对象导出）。
"""
import io, os, sys, traceback

LD_BASE = os.environ.get('LD_BASE') or r'D:/plc_mcp/ld_study'
PROJ = os.environ.get('LD_PROJ') or os.path.join(LD_BASE, 'proj', 'study_lead.project')
OUT  = os.environ.get('LD_RAW')  or os.path.join(LD_BASE, 'raw')
LOG  = os.environ.get('LD_EXPORT_LOG') or os.path.join(LD_BASE, 'export_all.log')

if not os.path.isdir(OUT):
    os.makedirs(OUT)
lf = io.open(LOG, "w", encoding="utf-8")
def L(m):
    lf.write(u"%s\n" % unicode(m))
    lf.flush()

def walk(obj, depth, out):
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
    import System
    system.prompt_handling = System.Enum.Parse(
        System.Type.GetType("_3S.CoDeSys.ScriptEngine.BasicFunctionality.PromptHandling, ScriptEngine"),
        "LogSimplePrompts")
    system.process_messageloop()
    proj = projects.open(PROJ, u"", True)
    app = proj.active_application
    L(u"opened: %s" % PROJ)
    objs = walk(app, 1, [])
    L(u"objects: %d" % len(objs))
    ok = 0
    fail = 0
    for i, (d, n, o) in enumerate(objs):
        safe = u"".join([c if (c.isalnum() or c in u"-_.") else u"_" for c in n])[:60]
        p = os.path.join(OUT, u"%03d_%s.native" % (i, safe))
        try:
            o.export_native(p)
            if os.path.getsize(p) < 200:
                os.remove(p)
            ok += 1
        except Exception, e:
            fail += 1
            L(u"FAIL %d %s : %s" % (i, n, unicode(e)))
    L(u"DONE ok=%d fail=%d" % (ok, fail))
    proj.close()
except BaseException, e:
    L(u"FATAL " + unicode(e))
    L(unicode(traceback.format_exc()))
finally:
    try:
        lf.close()
    except Exception:
        pass
