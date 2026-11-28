# -*- coding: utf-8 -*-
# @ipy2
"""任务配置与对象移动（对齐 inoproshop-mcp extended.py 的安全语义）。

支持 6 个操作，全部走「改 → 逐字段读回 → 失败回滚」：
  create_task   建循环任务，读回 name/interval/interval_unit/priority/kind，失败 remove
  set_task      改 interval_unit/interval/priority，失败恢复原值
  task_info     单任务或全部任务的字段 + pous 列表
  move_object   把对象移到另一个父下，拒保护对象/同名冲突，失败移回
  list_tasks    全部任务名
  tree          打印 Application 直接子对象（排错用）

参数文件：<BASE>/ipc/ext_args.json，输出 <BASE>/ipc/ext_result.json 与 ext.log。
RESULT 用 ### RESULT_JSON ### 包裹（与 inoproshop-mcp _text_utils.emit_result 一致）。

为什么不用 dir()：InoProShop 的脚本对象是 .NET 包装类，dir() 只暴露 Python 侧成员，
接口方法（create_task / move / kind_of_task ...）在 dir() 里根本看不见，必须直接访问。
"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
LOG_PATH = os.path.join(IPC, "ext.log")
RES_PATH = os.path.join(IPC, "ext_result.json")
ARGS_PATH = os.path.join(IPC, "ext_args.json")

_lf = io.open(LOG_PATH, "w", encoding="utf-8")


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


def emit(res):
    txt = u"### RESULT_JSON ###\n%s\n### END_RESULT_JSON ###" % unicode(
        json_dumps(res))
    L(txt)
    f = io.open(RES_PATH, "w", encoding="utf-8")
    try:
        f.write(unicode(json_dumps(res)))
    finally:
        f.close()


def json_dumps(o):
    """IronPython 没有 json 模块，手工拼（只支持 dict/list/str/num/bool/None）。"""
    if o is None:
        return u"null"
    if o is True:
        return u"true"
    if o is False:
        return u"false"
    if isinstance(o, (int, long, float)):
        return unicode(o)
    if isinstance(o, dict):
        parts = []
        for k in o:
            parts.append(u"%s:%s" % (json_dumps(unicode(k)), json_dumps(o[k])))
        return u"{" + u",".join(parts) + u"}"
    if isinstance(o, (list, tuple)):
        return u"[" + u",".join([json_dumps(x) for x in o]) + u"]"
    return json_dumps_str(unicode(o))


def json_dumps_str(s):
    out = []
    for ch in s:
        if ch == u'"':
            out.append(u'\\"')
        elif ch == u"\\":
            out.append(u"\\\\")
        elif ch == u"\n":
            out.append(u"\\n")
        elif ch == u"\r":
            out.append(u"\\r")
        elif ch == u"\t":
            out.append(u"\\t")
        else:
            out.append(ch)
    return u'"' + u"".join(out) + u'"'


def load_args():
    f = io.open(ARGS_PATH, "r", encoding="utf-8")
    try:
        txt = f.read()
    finally:
        f.close()
    try:
        import json
        return json.loads(txt)
    except ImportError:
        pass
    # IronPython 2.7 自带 json，正常走不到这里
    raise RuntimeError(u"json 模块不可用")


def find_child(parent, name):
    for c in parent.get_children():
        try:
            if unicode(c.get_name()) == name:
                return c
        except Exception:
            pass
    return None


def find_obj(root, name):
    """广度优先按名字找对象（深度优先也行，工程树不大）。"""
    q = [root]
    seen = 0
    while q:
        cur = q.pop(0)
        seen += 1
        try:
            kids = list(cur.get_children())
        except Exception:
            kids = []
        for k in kids:
            try:
                if unicode(k.get_name()) == name:
                    return k
            except Exception:
                pass
        q.extend(kids)
        if seen > 5000:
            break
    return None


def find_obj2(root, name):
    """广度优先按名字找 (对象, 父)。

    不能用 k is target 比身份：每次 get_children() 返回的 .NET 包装对象都是新实例，
    is 永远为假（实测报「找不到 prg_SeqDemo 的父节点」）。
    """
    q = [(root, None)]
    seen = 0
    while q:
        cur, par = q.pop(0)
        seen += 1
        try:
            kids = list(cur.get_children())
        except Exception:
            kids = []
        for k in kids:
            try:
                if unicode(k.get_name()) == unicode(name):
                    return k, cur
            except Exception:
                pass
        for k in kids:
            q.append((k, cur))
        if seen > 5000:
            break
    return None, None

def child_names(obj):
    out = []
    try:
        for c in obj.get_children():
            out.append(unicode(c.get_name()))
    except Exception:
        pass
    return out


def protected(obj):
    for (attr, label) in ((u"is_application", u"Application"),
                          (u"is_device", u"Device"),
                          (u"is_task_configuration", u"Task Configuration"),
                          (u"is_task", u"Task")):
        try:
            if getattr(obj, attr):
                return label
        except Exception:
            pass
    return None


def kots():
    """用已有任务的 kind_of_task 当枚举值（KindOfTask 类型按名字反射取不到）。"""
    try:
        app = projects.primary.active_application
        tc = find_child(app, u"Task Configuration")
        for t in tc.get_children():
            try:
                return t.kind_of_task
            except Exception:
                pass
    except Exception:
        pass
    return None


def set_field(obj, attr, val, tag):
    setattr(obj, attr, val)
    got = getattr(obj, attr)
    if unicode(got) != unicode(val):
        raise RuntimeError(u"%s 读回不一致：set=%s got=%s" % (tag, unicode(val), unicode(got)))
    return unicode(got)


def op_list_tasks(app, args):
    tc = find_child(app, u"Task Configuration")
    if tc is None:
        raise RuntimeError(u"找不到 Task Configuration")
    out = []
    for t in tc.get_children():
        out.append(unicode(t.get_name()))
    return {u"tasks": out}


def op_task_info(app, args):
    tc = find_child(app, u"Task Configuration")
    name = args.get(u"name")
    targets = []
    if name:
        t = find_child(tc, name)
        if t is None:
            raise RuntimeError(u"任务不存在：%s" % name)
        targets = [t]
    else:
        targets = [t for t in tc.get_children()]
    info = []
    for t in targets:
        d = {}
        d[u"name"] = unicode(t.get_name())
        for a in (u"interval", u"interval_unit", u"priority", u"kind_of_task"):
            try:
                d[a] = unicode(getattr(t, a))
            except Exception, e:
                d[a] = u"ERR " + unicode(e)
        try:
            d[u"pous"] = [unicode(x) for x in t.pous]
        except Exception, e:
            d[u"pous"] = u"ERR " + unicode(e)
        info.append(d)
    return {u"tasks": info}


def op_create_task(app, args):
    tc = find_child(app, u"Task Configuration")
    if tc is None:
        raise RuntimeError(u"找不到 Task Configuration")
    name = args.get(u"name")
    if not name:
        raise RuntimeError(u"create_task 需要 name")
    if find_child(tc, name) is not None:
        raise RuntimeError(u"同名任务已存在：%s" % name)
    t = tc.create_task(unicode(name))
    try:
        got = unicode(t.get_name())
        if got != unicode(name):
            raise RuntimeError(u"任务名读回不一致：%s != %s" % (got, name))
        k = args.get(u"kind_of_task")
        if k:
            kv = kots()
            if kv is None:
                raise RuntimeError(u"取不到 KindOfTask 枚举值，无法设置 kind_of_task")
            t.kind_of_task = kv
            if u"Cyclic" not in unicode(t.kind_of_task):
                raise RuntimeError(u"kind_of_task 读回不是 Cyclic：%s" % unicode(t.kind_of_task))
        for a in (u"interval_unit", u"interval", u"priority"):
            if args.get(a) is not None:
                set_field(t, a, args.get(a), a)
        if find_child(tc, unicode(name)) is None:
            raise RuntimeError(u"任务建好但不在 Task Configuration 子节点里")
        return {u"name": unicode(name), u"task": task_dict(t)}
    except BaseException, e:
        try:
            t.remove()
        except Exception:
            pass
        raise RuntimeError(u"create_task 失败已回滚：%s" % unicode(e))


def task_dict(t):
    d = {}
    for a in (u"interval", u"interval_unit", u"priority", u"kind_of_task"):
        try:
            d[a] = unicode(getattr(t, a))
        except Exception:
            d[a] = u"?"
    return d


def op_set_task(app, args):
    tc = find_child(app, u"Task Configuration")
    name = args.get(u"name")
    t = find_child(tc, name) if tc is not None else None
    if t is None:
        raise RuntimeError(u"任务不存在：%s" % name)
    before = {}
    for a in (u"interval_unit", u"interval", u"priority"):
        try:
            before[a] = unicode(getattr(t, a))
        except Exception:
            before[a] = None
    changed = {}
    try:
        for a in (u"interval_unit", u"interval", u"priority"):
            if args.get(a) is not None:
                changed[a] = set_field(t, a, args.get(a), a)
        return {u"name": unicode(name), u"before": before, u"after": task_dict(t)}
    except BaseException, e:
        for a in before:
            if before[a] is not None:
                try:
                    setattr(t, a, before[a])
                except Exception:
                    pass
        raise RuntimeError(u"set_task 失败已回滚：%s" % unicode(e))


def op_move_object(app, args):
    name = args.get(u"name")
    target_name = args.get(u"parent")
    if not name:
        raise RuntimeError(u"move_object 需要 name")
    obj, old = find_obj2(app, unicode(name))
    if obj is None:
        raise RuntimeError(u"对象不存在：%s" % name)
    why = protected(obj)
    if why:
        raise RuntimeError(u"拒绝移动受保护对象（%s）：%s" % (why, name))
    if old is None:
        raise RuntimeError(u"找不到 %s 的父节点" % name)
    if target_name:
        tgt = find_obj(app, unicode(target_name))
        if tgt is None:
            raise RuntimeError(u"目标父不存在：%s" % parent_name_safe(target_name))
    else:
        tgt = app
    if old is tgt:
        return {u"name": unicode(name), u"moved": False, u"note": u"已经在该父下"}
    if unicode(name) in child_names(tgt):
        raise RuntimeError(u"目标父下已有同名对象：%s" % name)
    old_names = child_names(old)
    try:
        obj.move(tgt, -1)
        system.process_messageloop()
        if unicode(name) not in child_names(tgt):
            raise RuntimeError(u"移动后目标父里没有该对象")
        if unicode(name) in child_names(old):
            raise RuntimeError(u"移动后旧父里仍有该对象")
        return {u"name": unicode(name), u"moved": True,
                u"from": unicode(old.get_name()), u"to": unicode(tgt.get_name())}
    except BaseException, e:
        try:
            obj.move(old, -1)
            system.process_messageloop()
            L(u"[rollback] 移回 %s，旧父含该对象=%r" % (
                unicode(old.get_name()), unicode(name) in old_names))
        except Exception, e2:
            L(u"[rollback][FAIL] %s" % unicode(e2))
        raise RuntimeError(u"move_object 失败已回滚：%s" % unicode(e))


def parent_name_safe(x):
    return unicode(x)


def op_remove_task(app, args):
    tc = find_child(app, u"Task Configuration")
    name = args.get(u"name")
    if not name:
        raise RuntimeError(u"remove_task 需要 name")
    if unicode(name) in (u"MainTask", u"ETHERCAT"):
        raise RuntimeError(u"拒绝删除系统任务：%s" % name)
    t = find_child(tc, unicode(name))
    if t is None:
        raise RuntimeError(u"任务不存在：%s" % name)
    t.remove()
    system.process_messageloop()
    if find_child(tc, unicode(name)) is not None:
        raise RuntimeError(u"remove 后任务仍在：%s" % name)
    return {u"name": unicode(name), u"removed": True}

OPS = {
    u"list_tasks": op_list_tasks,
    u"task_info": op_task_info,
    u"create_task": op_create_task,
    u"set_task": op_set_task,
    u"move_object": op_move_object,
    u"remove_task": op_remove_task,
}


args = None
try:
    args = load_args()
    op = unicode(args.get(u"op") or u"")
    L(u"BASE = %s (source: %s)" % (BASE, _base.SOURCE))
    L(u"OP = %s ARGS = %s" % (op, unicode(args)))
    if op == u"tree":
        app = projects.primary.active_application
        emit({u"ok": True, u"op": op, u"children": child_names(app)})
    else:
        if op not in OPS:
            raise RuntimeError(u"未知 op：%s" % op)
        app = projects.primary.active_application
        if app is None:
            raise RuntimeError(u"没有活动 Application")
        res = OPS[op](app, args)
        if args.get(u"save"):
            projects.primary.save()
            res[u"saved"] = True
        emit({u"ok": True, u"op": op, u"data": res})
except BaseException, e:
    L(u"[FATAL] %s" % unicode(e))
    L(traceback.format_exc())
    try:
        emit({u"ok": False, u"op": unicode(args.get(u"op")) if args else u"?",
              u"error": unicode(e), u"trace": traceback.format_exc()})
    except Exception:
        pass
finally:
    try:
        _lf.close()
    except Exception:
        pass
