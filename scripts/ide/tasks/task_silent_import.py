# -*- coding: utf-8 -*-
# @ipy2
# 静默导入 native（绝不弹确认框）：改名让位 -> 导入 -> 校验 -> 删旧 -> 保存
# 参数从 ipc/import_args.json 读取: {"path": "...", "parent": "prg_EM01_Logic", "expect": ["kw1","kw2"]}
import io, os, sys, time, traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base
BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
LOG = os.path.join(IPC, "silent_import.log")
ARGS = os.path.join(IPC, "import_args.json")
_lf = io.open(LOG, "w", encoding="utf-8")


def L(m):
    _lf.write(u"[%s] %s\n" % (time.strftime("%H:%M:%S"), unicode(m)))
    _lf.flush()


def find_child(parent, name):
    """只在 parent 的【直接子对象】里按名字找。

    为什么不递归：全局递归会误命中 Task Configuration 里的调用对象
    （见 README 铁律「禁止全局 find_named」）。
    """
    if parent is None:
        return None
    try:
        kids = parent.get_children()
    except Exception:
        return None
    if not kids:
        return None
    for o in kids:
        try:
            if unicode(o.get_name()) == unicode(name):
                return o
        except Exception:
            continue
    return None


def load_args():
    import json
    f = io.open(ARGS, "r", encoding="utf-8")
    try:
        return json.loads(f.read())
    finally:
        f.close()


def obj_name_from_native(path):
    import re
    head = io.open(path, "r", encoding="utf-8", errors="replace").read(4000)
    m = re.search(u'<Single Name="Name" Type="string">([^<]+)</Single>', head)
    return m.group(1).strip() if m else None


def main():
    args = load_args()
    src = args.get(u"path")
    parent_name = args.get(u"parent") or u"prg_EM01_Logic"
    expect = args.get(u"expect") or []
    L(u"=== silent import ===")
    L(u"src = %s" % src)
    if not src or not os.path.exists(src):
        L(u"FATAL: src not found")
        return

    src_name = obj_name_from_native(src)
    L(u"object name in native = %s" % src_name)
    if not src_name:
        L(u"FATAL: cannot read object name")
        return

    proj = projects.primary
    app = proj.active_application

    # 父对象：在 Application 的直接子对象里找（不递归）
    parent = find_child(app, parent_name)
    if parent is None:
        # 兜底：允许 parent_name 就是 Application 自身
        try:
            if unicode(app.get_name()) == unicode(parent_name):
                parent = app
        except Exception:
            pass
    if parent is None:
        L(u"FATAL: parent %s not found under %s" % (parent_name, app.get_name()))
        return
    L(u"parent = %s" % parent.get_name())
    L(u"children before: %s" % u", ".join([k.get_name() for k in parent.get_children()]))

    # 待替换对象：只在 parent 的直接子对象里找，避免误命中 Task Configuration
    old = find_child(parent, src_name)
    tmp = None
    t0 = time.time()
    if old is not None:
        tmp = u"%s_old_tmp" % src_name
        leftover = find_child(parent, tmp)
        if leftover is not None:
            leftover.remove()
            L(u"removed leftover %s" % tmp)
        old.rename(tmp)
        L(u"renamed %s -> %s (让位，避免同名冲突弹框)" % (src_name, tmp))

    # 导入（无同名冲突 => 不弹框）
    r = parent.import_native(src)
    dt = time.time() - t0
    L(u"import_native -> %r  (%.2fs)" % (r, dt))

    newobj = find_child(parent, src_name)
    L(u"new object exists: %s" % (newobj is not None))
    if newobj is None:
        if old is not None:
            try:
                old.rename(src_name)
                L(u"ROLLBACK: renamed back")
            except Exception, e:
                L(u"ROLLBACK FAIL: %s" % e)
        L(u"=== ABORT ===")
        return

    # 校验内容（校验导出使用唯一文件名，避免复用上一次的文件触发"文件已存在"弹框）
    chk = os.path.join(IPC, u"silent_after_%s.native" % time.strftime(u"%H%M%S"))
    if os.path.exists(chk):
        try:
            os.remove(chk)
        except Exception:
            pass
    newobj.export_native(chk)
    s = io.open(chk, "r", encoding="utf-8", errors="replace").read()
    L(u"exported size: %d" % len(s))
    NETTAG = u'Type="{d9a99d73-b633-47db-b876-a752acb25871}"'
    L(u"networks: %d" % s.count(NETTAG))
    for kw in expect:
        L(u"  expect %-24s x%d" % (kw, s.count(kw)))

    # 删旧
    if old is not None:
        old.remove()
        L(u"removed old (%s)" % tmp)

    L(u"children after: %s" % u", ".join([k.get_name() for k in parent.get_children()]))

    proj.save()
    L(u"saved")
    L(u"=== done ===")


try:
    main()
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))
finally:
    _lf.close()
