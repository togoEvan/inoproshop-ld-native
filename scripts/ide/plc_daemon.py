# -*- coding: utf-8 -*-
# @ipy2
# =====================================================================
#  InoProShop 常驻守护（IronPython 2.7）
#  在 IDE 内启动后，后台线程轮询 cmd.json，执行后写 result.json。
#  只在启动时需要一次「执行脚本文件」对话框，之后完全静默。
# =====================================================================
import io
import os
import re
import sys
import time
import traceback

# 路径自解析：IDE 内读不到 shell 设的环境变量，必须从 sys.argv[0] 反推。
# 详见同目录 _base.py 顶部说明。
sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[0])))
import _base

BASE = _base.resolve_base()
CMD_DIR = _base.ensure_ipc(BASE)
CMD_FILE = os.path.join(CMD_DIR, "cmd.json")
CMD_RUNNING = os.path.join(CMD_DIR, "running.json")
RES_FILE = os.path.join(CMD_DIR, "result.json")
STOP_FILE = os.path.join(CMD_DIR, "stop.flag")
READY_FILE = os.path.join(CMD_DIR, "ready.flag")
LOG_FILE = os.path.join(CMD_DIR, "daemon.log")
# 取消代数（单调递增）。bridge.cancel() 每次 +1；本守护在每条命令执行前后
# 比对代数，变了就标记 cancelled 并尽快收尾。
# ⚠ 与 stop.flag 的区别：stop.flag 让守护**退出**，cancel.gen 只取消**当前命令**。
CANCEL_GEN_FILE = os.path.join(CMD_DIR, "cancel.gen")

if not os.path.isdir(CMD_DIR):
    try:
        os.makedirs(CMD_DIR)
    except Exception:
        pass

# 单实例保护：用「心跳」判定，而不是 PID。
# 注意：IronPython 脚本跑在 IDE 进程内，GetCurrentProcess().Id 永远等于 IDE 的 PID，
#       用 PID 判活会永远认为"已有实例"，导致守护永远起不来。改用心跳时间戳。
PID_FILE = os.path.join(CMD_DIR, "daemon.pid")
_inst_lock = os.path.join(CMD_DIR, "instance.lock")
HEARTBEAT = os.path.join(CMD_DIR, "heartbeat")
HEARTBEAT_FRESH = 8.0   # 秒；心跳在此时间内视为存活


def _acquire_instance():
    try:
        import System
        me = System.Diagnostics.Process.GetCurrentProcess().Id
    except Exception:
        me = os.getpid()
    # 心跳新鲜 => 已有实例存活
    if os.path.exists(HEARTBEAT):
        try:
            age = time.time() - os.path.getmtime(HEARTBEAT)
            if age < HEARTBEAT_FRESH:
                return False, u"heartbeat age=%.1fs" % age
        except Exception:
            pass
    try:
        f = io.open(_inst_lock, "w")
        f.write(unicode(me))
        f.close()
        f2 = io.open(PID_FILE, "w")
        f2.write(unicode(me))
        f2.close()
        # 立即写一次心跳，占位
        hb = io.open(HEARTBEAT, "w")
        hb.write(unicode(time.time()))
        hb.close()
    except Exception:
        pass
    return True, me


_ok, _who = _acquire_instance()
if not _ok:
    # 已有守护在运行，本次静默退出
    try:
        _lf = io.open(os.path.join(CMD_DIR, "daemon_boot.log"), "a", encoding="utf-8")
        _lf.write(u"[%s] skip: another daemon alive (%s)\n" % (time.strftime("%H:%M:%S"), _who))
        _lf.close()
    except Exception:
        pass
    raise SystemExit

def _open_log():
    """打开日志文件。daemon.log 被上一个实例的句柄锁住时（IDE 进程未释放），
    退化为带时间戳的日志名，绝不让「打不开日志」把整个守护进程搞死。
    """
    for name in ("daemon.log",
                 "daemon_%s.log" % time.strftime("%Y%m%d_%H%M%S")):
        p = os.path.join(CMD_DIR, name)
        try:
            return io.open(p, "a", encoding="utf-8"), p
        except Exception:
            continue
    return None, None


_logf, _logpath = _open_log()


def _boot(msg):
    try:
        bf = io.open(os.path.join(CMD_DIR, "daemon_boot.log"), "a", encoding="utf-8")
        bf.write(u"[%s] %s\n" % (time.strftime("%H:%M:%S"), unicode(msg)))
        bf.close()
    except Exception:
        pass


if _logf is None:
    _boot(u"WARN: 无法打开任何日志文件（目录权限或句柄占用）")
else:
    _boot(u"log file = %s" % _logpath)


_boot(u"script start, pid-file acquired")
_boot(u"BASE = %s (source: %s)" % (BASE, _base.SOURCE))



def log(msg):
    if _logf is None:
        return
    try:
        _logf.write(u"[%s] %s\n" % (time.strftime("%H:%M:%S"), unicode(msg)))
        _logf.flush()
    except Exception:
        pass


def load_json(path):
    import json
    f = io.open(path, "r", encoding="utf-8")
    try:
        return json.load(f)
    finally:
        f.close()


def dump_json(path, obj):
    import json
    tmp = path + ".tmp"
    f = io.open(tmp, "w", encoding="utf-8")
    try:
        f.write(unicode(json.dumps(obj, ensure_ascii=False, indent=1)))
    finally:
        f.close()
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass
    os.rename(tmp, path)


log(u"==== daemon loading ====")

# ---------------------------------------------------------------------
# 动作实现（与 plc_action.py 一致）
# ---------------------------------------------------------------------
def walk(obj, out, limit=20000):
    if len(out) >= limit:
        return
    out.append(obj)
    try:
        kids = obj.get_children()
    except Exception:
        return
    if not kids:
        return
    for k in kids:
        walk(k, out, limit)


def obj_path(o):
    parts = []
    cur = o
    for _ in range(20):
        if cur is None:
            break
        try:
            parts.append(cur.get_name())
        except Exception:
            break
        try:
            cur = cur.parent
        except Exception:
            break
    parts.reverse()
    return u".".join(parts)


def get_proj():
    p = projects.primary
    if p is not None:
        return p
    allp = list(projects.all)
    return allp[0] if allp else None


def find_named(root, name):
    """按名字查找对象（深度优先）。"""
    objs = []
    walk(root, objs)
    for o in objs:
        try:
            if o.get_name() == name:
                return o
        except Exception:
            continue
    return None


def find_app(proj):
    return proj.active_application


def find_device(proj):
    objs = []
    walk(proj, objs)
    for o in objs:
        try:
            if o.is_folder:
                continue
        except Exception:
            pass
        try:
            tname = repr(o.type)
        except Exception:
            continue
        if u"Device" in tname:
            return o
    return None


def collect_messages(limit=100):
    out = []
    try:
        msgs = list(system.get_messages())
    except Exception, e:
        return [{u"severity": u"error", u"text": u"get_messages err: %s" % e}]
    for m in msgs[:limit]:
        d = {}
        for attr in ("severity", "text", "message", "position", "object"):
            try:
                v = getattr(m, attr)
            except Exception:
                continue
            if v is None:
                continue
            if attr == "object":
                try:
                    v = obj_path(v)
                except Exception:
                    v = repr(v)
            d[unicode(attr)] = unicode(v)
        if not d:
            d = {u"text": unicode(repr(m))}
        out.append(d)
    return out


def count_sev(msgs, want):
    n = 0
    for m in msgs:
        if want in (m.get(u"severity") or u"").lower():
            n += 1
    return n


def _resolve_pou(proj, spec):
    objs = []
    walk(proj, objs)
    spec = unicode(spec or u"")
    for o in objs:
        try:
            if o.is_folder:
                continue
        except Exception:
            pass
        try:
            nm = o.get_name()
        except Exception:
            continue
        if nm == spec or obj_path(o) == spec or obj_path(o).endswith(u"." + spec):
            try:
                if o.has_textual_implementation:
                    return o, None
            except Exception:
                pass
    return None, u"POU not found: %s" % spec


# ---------------- actions ----------------
def a_status(proj, cmd):
    app = find_app(proj)
    dev = find_device(proj)
    r = {
        u"project": proj.path,
        u"application": app.get_name() if app is not None else None,
        u"device": obj_path(dev) if dev is not None else None,
    }
    if app is not None:
        # ⚠ 在线接口必须在 IDE 主线程调用。handle_on_main() 正常情况下
        #   会派发到主线程，但 execute_on_primary_thread 失败时会 fallback
        #   inline（在后台线程执行），此时 create_online_application()
        #   抛 SystemError("堆栈为空。")。
        #   在线状态只是 status 的附加信息，绝不能因此让整个 status 失败
        #   —— 离线开发时（没连设备）本来也拿不到。
        try:
            oa = online.create_online_application(app)
            try:
                r[u"logged_in"] = bool(oa.is_logged_in())
                r[u"application_state"] = unicode(oa.application_state())
                try:
                    r[u"operation_state"] = unicode(oa.operation_state())
                except Exception:
                    pass
            finally:
                try:
                    oa.dispose()
                except Exception:
                    pass
        except BaseException, e:
            # SystemError 不继承 Exception，必须兜 BaseException
            r[u"online_error"] = u"%s: %s" % (type(e).__name__, e)
    try:
        r[u"gateways"] = [unicode(g.name) for g in online.gateways]
    except Exception:
        pass
    return r


def a_list_pous(proj, cmd):
    objs = []
    walk(proj, objs)
    out = []
    for o in objs:
        try:
            if o.is_folder or not o.has_textual_implementation:
                continue
        except Exception:
            continue
        out.append({u"name": o.get_name(), u"path": obj_path(o)})
    return {u"count": len(out), u"pous": out}


def a_get_pou(proj, cmd):
    o, err = _resolve_pou(proj, cmd.get("pou"))
    if err:
        return {u"error": err}
    return {u"name": o.get_name(), u"path": obj_path(o),
            u"code": o.textual_implementation.text}


def a_set_pou(proj, cmd):
    o, err = _resolve_pou(proj, cmd.get("pou"))
    if err:
        return {u"error": err}
    code = cmd.get("code")
    if code is None:
        return {u"error": u"missing code"}
    doc = o.textual_implementation
    old_len = doc.length
    doc.replace(unicode(code))
    saved = False
    if cmd.get("save", True):
        proj.save()
        saved = True
    return {u"name": o.get_name(), u"path": obj_path(o),
            u"old_length": old_len, u"new_length": len(code), u"saved": saved}


def a_get_decl(proj, cmd):
    """读取 POU 的声明部分（VAR ... END_VAR）"""
    o, err = _resolve_pou(proj, cmd.get("pou"))
    if err:
        return {u"error": err}
    d = o.textual_declaration
    return {u"name": o.get_name(), u"path": obj_path(o), u"decl": d.text}


def a_set_decl(proj, cmd):
    """写入 POU 的声明部分"""
    o, err = _resolve_pou(proj, cmd.get("pou"))
    if err:
        return {u"error": err}
    decl = cmd.get("decl")
    if decl is None:
        return {u"error": u"missing decl"}
    d = o.textual_declaration
    old_len = d.length
    d.replace(unicode(decl))
    saved = False
    if cmd.get("save", True):
        proj.save()
        saved = True
    return {u"name": o.get_name(), u"path": obj_path(o),
            u"old_length": old_len, u"new_length": len(decl), u"saved": saved}


def a_build(proj, cmd):
    app = find_app(proj)
    if app is None:
        return {u"error": u"no active application"}
    try:
        system.clear_messages(None)
    except Exception:
        pass
    t0 = time.time()
    app.build()
    dt = time.time() - t0
    msgs = collect_messages()
    return {u"ok": count_sev(msgs, u"error") == 0, u"seconds": round(dt, 2),
            u"errors": count_sev(msgs, u"error"),
            u"warnings": count_sev(msgs, u"warning"),
            u"messages": msgs}


def a_login(proj, cmd):
    app = find_app(proj)
    if app is None:
        return {u"error": u"no active application"}
    mode = unicode(cmd.get("mode") or u"full")

    if cmd.get("build", True):
        try:
            system.clear_messages(None)
        except Exception:
            pass
        app.build()
        msgs = collect_messages()
        if count_sev(msgs, u"error") > 0:
            return {u"error": u"build failed", u"errors": count_sev(msgs, u"error"),
                    u"messages": msgs}

    dev = find_device(proj)
    if dev is None:
        return {u"error": u"no device object found"}
    od = online.create_online_device(dev)
    try:
        if not od.connected:
            od.connect()
    finally:
        try:
            od.dispose()
        except Exception:
            pass

    oa = online.create_online_application(app)
    try:
        opt = OnlineChangeOption.Try if mode == u"online_change" else OnlineChangeOption.Never
        t0 = time.time()
        oa.login(opt, False)
        dt = time.time() - t0
        r = {u"ok": True, u"mode": mode, u"seconds": round(dt, 2),
             u"logged_in": bool(oa.is_logged_in()),
             u"application_state": unicode(oa.application_state())}
        if cmd.get("start", True):
            oa.start()
            r[u"started"] = True
            r[u"application_state"] = unicode(oa.application_state())
        return r
    finally:
        try:
            oa.dispose()
        except Exception:
            pass


def a_logout(proj, cmd):
    app = find_app(proj)
    if app is None:
        return {u"error": u"no active application"}
    oa = online.create_online_application(app)
    try:
        oa.logout()
    finally:
        try:
            oa.dispose()
        except Exception:
            pass
    return {u"ok": True}


def a_start(proj, cmd):
    app = find_app(proj)
    oa = online.create_online_application(app)
    try:
        oa.start()
        return {u"ok": True, u"application_state": unicode(oa.application_state())}
    finally:
        try:
            oa.dispose()
        except Exception:
            pass


def a_stop(proj, cmd):
    app = find_app(proj)
    oa = online.create_online_application(app)
    try:
        oa.stop()
        return {u"ok": True, u"application_state": unicode(oa.application_state())}
    finally:
        try:
            oa.dispose()
        except Exception:
            pass


def a_read_value(proj, cmd):
    exprs = cmd.get("exprs") or []
    if isinstance(exprs, basestring):
        exprs = [exprs]
    app = find_app(proj)
    oa = online.create_online_application(app)
    out = {}
    try:
        for e in exprs:
            try:
                out[unicode(e)] = unicode(oa.read_value(unicode(e)))
            except Exception, ex:
                out[unicode(e)] = u"<err %s>" % ex
    finally:
        try:
            oa.dispose()
        except Exception:
            pass
    return {u"values": out}


def a_write_value(proj, cmd):
    vals = cmd.get("values") or {}
    app = find_app(proj)
    oa = online.create_online_application(app)
    done = {}
    try:
        for k, v in vals.items():
            try:
                oa.set_prepared_value(unicode(k), unicode(v))
                done[unicode(k)] = u"prepared"
            except Exception, ex:
                done[unicode(k)] = u"<err %s>" % ex
        oa.write_prepared_values()
        done[u"__written"] = True
    except Exception, ex:
        done[u"__write_error"] = unicode(ex)
    finally:
        try:
            oa.dispose()
        except Exception:
            pass
    return {u"result": done}



def a_import_native(proj, cmd):
    """静默导入 native 文件（绝不弹交互对话框）。

    原理：InoProShop 的 import_native(path) 只有一个路径参数时，遇到同名对象
    会弹出「是否替换」的模态对话框，必须人工点击。而 INativeImportHandler
    是 .NET 接口，IronPython 沙箱里无法实现（metaclass conflict / RuntimeType
    无公共构造函数），所以改用「先改名旧对象 -> 再导入 -> 删旧对象」的方式，
    让导入时不存在同名冲突，从而完全不弹窗。

    cmd:
      path      : native 文件路径（必填）
      parent    : 目标父对象名，默认 prg_EM01_Logic
      keep_old  : True 则保留改名后的旧对象（默认 False，删除）
    """
    path = cmd.get(u"path")
    if not path:
        return {u"ok": False, u"error": u"missing path"}
    if not os.path.exists(path):
        return {u"ok": False, u"error": u"file not found: %s" % path}

    parent_name = unicode(cmd.get(u"parent") or u"prg_EM01_Logic")
    keep_old = bool(cmd.get(u"keep_old"))

    parent = find_named(proj, parent_name)
    if parent is None:
        return {u"ok": False, u"error": u"parent not found: %s" % parent_name}

    # 从 native 文件里读出即将导入的对象名（MetaObject/Name）
    src_name = None
    try:
        head = io.open(path, u"r", encoding=u"utf-8", errors=u"replace").read(4000)
        m = re.search(u'<Single Name="Name" Type="string">([^<]+)</Single>', head)
        if m:
            src_name = m.group(1).strip()
    except Exception:
        src_name = None
    if not src_name:
        return {u"ok": False, u"error": u"cannot determine object name from native file"}

    before = [k.get_name() for k in parent.get_children()]

    # 1) 若存在同名对象，先改名让位
    old_obj = None
    # 注意：IDE 名称校验不允许双下划线（__），必须用单下划线
    tmp_name = u"%s_old_%s" % (src_name, time.strftime(u"%H%M%S"))
    existing = find_named(proj, src_name)
    if existing is not None:
        try:
            existing.rename(tmp_name)
            old_obj = existing
        except Exception, e:
            return {u"ok": False, u"error": u"rename existing failed: %s" % e,
                    u"hint": u"若改名失败请手动处理同名对象"}

    # 2) 导入（此时无同名冲突，不会弹窗）
    t0 = time.time()
    try:
        res = parent.import_native(unicode(path))
    except Exception, e:
        # 回滚改名
        if old_obj is not None:
            try:
                old_obj.rename(src_name)
            except Exception:
                pass
        return {u"ok": False, u"error": u"import_native failed: %s" % e,
                u"traceback": traceback.format_exc()}
    dt = time.time() - t0

    # 3) 校验新对象确实生成
    new_obj = find_named(proj, src_name)
    if new_obj is None:
        if old_obj is not None:
            try:
                old_obj.rename(src_name)
            except Exception:
                pass
        return {u"ok": False, u"error": u"import reported %r but object missing; rolled back" % (res,)}

    # 4) 删除改名后的旧对象
    removed = False
    if old_obj is not None and not keep_old:
        try:
            old_obj.remove()
            removed = True
        except Exception, e:
            return {u"ok": True, u"warning": u"old object not removed: %s" % e,
                    u"old_name": tmp_name}

    after = [k.get_name() for k in parent.get_children()]
    return {u"ok": True, u"import_result": unicode(res), u"object": src_name,
            u"seconds": round(dt, 2), u"replaced": old_obj is not None,
            u"old_removed": removed, u"old_name": (tmp_name if keep_old and old_obj is not None else None),
            u"children_before": before, u"children_after": after}


ACTIONS = {
    u"ping": None,  # 特殊处理：存活探测
    u"eval_file": None,  # 特殊处理：热执行脚本
    u"status": a_status, u"list_pous": a_list_pous,
    u"get_pou": a_get_pou, u"set_pou": a_set_pou,
    u"get_decl": a_get_decl, u"set_decl": a_set_decl,
    u"build": a_build, u"login": a_login, u"logout": a_logout,
    u"start": a_start, u"stop": a_stop,
    u"read_value": a_read_value, u"write_value": a_write_value,
    u"import_native": a_import_native,
    u"open_project": None,  # 特殊处理：主线程打开工程
}


def a_open_project(path):
    """在主线程上打开工程"""
    p = projects.open(unicode(path))
    if p is None:
        return {u"ok": False, u"error": u"projects.open returned None"}
    return {u"ok": True, u"path": p.path, u"application": p.active_application.get_name() if p.active_application is not None else None}


def a_eval_file(cmd):
    """热执行脚本文件。exec 必须放在不含嵌套函数的顶层函数里，
    否则 IronPython 会报 unqualified exec 编译错误。"""
    path = cmd.get("path")
    if not path:
        return {u"ok": False, u"error": u"missing path"}
    try:
        src = io.open(path, "r", encoding="utf-8").read()
    except Exception, e:
        return {u"ok": False, u"error": u"read err: %s" % e}
    g = {u"projects": projects, u"online": online, u"system": system,
         u"__name__": u"__eval__"}
    exec(compile(src, path, "exec"), g)
    return {u"ok": True, u"done": True}


def handle(cmd):
    action = unicode(cmd.get("action") or u"")

    # 特殊：热执行任意 IronPython 脚本文件（调试用，不重启 IDE）
    if action == u"eval_file":
        return a_eval_file(cmd)

    # 特殊：存活探测（不需要工程）
    if action == u"ping":
        return {u"ok": True, u"pong": True, u"time": time.strftime("%H:%M:%S")}

    # 特殊：打开工程（无需已有工程）
    if action == u"open_project":
        path = cmd.get("path")
        if not path:
            return {u"ok": False, u"error": u"missing path"}
        res_holder = {}
        def _work():
            try:
                res_holder[u"res"] = a_open_project(path)
            except Exception, e:
                res_holder[u"res"] = {u"ok": False, u"error": unicode(e), u"traceback": traceback.format_exc()}
        try:
            system.execute_on_primary_thread(_work, False)
        except Exception, e:
            return {u"ok": False, u"error": u"execute_on_primary_thread failed: %s" % e}
        t0 = time.time()
        while u"res" not in res_holder:
            if time.time() - t0 > 180:
                return {u"ok": False, u"error": u"open_project timeout"}
            time.sleep(0.1)
        return res_holder[u"res"]

    fn = ACTIONS.get(action)
    if fn is None:
        return {u"ok": False, u"error": u"unknown action: %s" % action}
    proj = get_proj()
    if proj is None:
        return {u"ok": False, u"error": u"no project open"}
    try:
        data = fn(proj, cmd)
        if not isinstance(data, dict):
            data = {u"result": data}
        data.setdefault(u"ok", u"error" not in data)
        return data
    except Exception, e:
        return {u"ok": False, u"error": unicode(e), u"traceback": traceback.format_exc()}


def handle_on_main(cmd, timeout=180):
    """把动作派发到 IDE 主线程执行（online 接口必须在主线程）"""
    box = {u"done": False, u"res": None}

    def work():
        try:
            box[u"res"] = handle(cmd)
        except Exception, e:
            box[u"res"] = {u"ok": False, u"error": unicode(e),
                           u"traceback": traceback.format_exc()}
        finally:
            box[u"done"] = True

    try:
        system.execute_on_primary_thread(work, False)
    except Exception, e:
        log(u"execute_on_primary_thread err: %s -> fallback inline" % e)
        return handle(cmd)

    t0 = time.time()
    while not box[u"done"]:
        if time.time() - t0 > timeout:
            return {u"ok": False, u"error": u"timeout waiting for main thread"}
        time.sleep(0.05)
    return box[u"res"]



# ---------------------------------------------------------------------
# 心跳线程（独立于轮询线程）
# ---------------------------------------------------------------------
# ⚠ 为什么必须独立成线程（2026-11-26 新增，配合 bridge 的心跳看门狗）：
#   旧实现把 _beat() 写在轮询循环里，于是心跳的含义变成「轮询循环没被卡住」。
#   但 app.build() 在主线程上跑 10~40s 是常态，这段时间轮询线程阻塞在
#   handle_on_main() 里，心跳就停了。bridge 一旦启用「心跳停摆即判定守护已死」
#   的看门狗，就会把「正常编译中」误判成「守护崩了」，把正在跑的编译丢掉。
#   所以心跳必须由独立线程发，语义明确为「守护进程活着」。
def _beat():
    try:
        hb = io.open(HEARTBEAT, "w")
        hb.write(unicode(time.time()))
        hb.close()
    except Exception:
        pass


_BEAT_INTERVAL = 0.5   # 秒。必须显著小于 bridge.HEARTBEAT_STALE(8s)
_beat_stop = [False]


def heartbeat_loop():
    """独立心跳线程：只要本线程活着，就说明守护进程（含 Python 运行时）活着。
    命令执行卡住不会影响它 —— 这正是「守护活着但命令慢」与「守护已死」
    两种状态得以区分的原因。"""
    while not _beat_stop[0]:
        _beat()
        try:
            time.sleep(_BEAT_INTERVAL)
        except Exception:
            pass


def read_cancel_gen():
    """读当前取消代数；文件不存在或读不出都当 0。"""
    try:
        if not os.path.exists(CANCEL_GEN_FILE):
            return 0
        f = io.open(CANCEL_GEN_FILE, "r")
        try:
            return int((f.read() or u"0").strip() or u"0")
        finally:
            f.close()
    except Exception:
        return 0


def loop():
    log(u"loop thread started")
    _beat()
    try:
        f = io.open(READY_FILE, "w")
        f.write(u"ready")
        f.close()
    except Exception:
        pass
    # 注意：不用 mtime+size 签名判重，改用「领取-改名」机制（见循环内注释）
    while True:
        try:
            if os.path.exists(STOP_FILE):
                log(u"stop flag detected, exiting loop")
                try:
                    os.remove(STOP_FILE)
                except Exception:
                    pass
                break
            if os.path.exists(CMD_FILE):
                # ═══ 领取-改名（学自 inoproshop-mcp 的 Watcher）═══
                # 先原子改名为 running.json 再执行，保证同一命令绝不执行两遍：
                # 旧机制靠 mtime+size 签名判重，签名比较失败或执行抛异常时
                # 都可能把同一命令再执行一次。改名后即使本循环崩溃，
                # 文件也不再叫 cmd.json，不会被再次领取。
                taken = False
                try:
                    os.rename(CMD_FILE, CMD_RUNNING)
                    taken = True
                except Exception, e:
                    log(u"claim cmd err: %s" % e)
                if taken:
                    time.sleep(0.05)
                    try:
                        cmd = load_json(CMD_RUNNING)
                    except Exception, e:
                        log(u"read cmd err: %s" % e)
                        cmd = None
                    if cmd:
                        # ── run_id 对账：原样回带，bridge 才能确认「这是我这轮的结果」
                        _run_id = cmd.get(u"run_id")
                        # ── 取消基线：命令发出时的代数
                        try:
                            _gen_at_send = int(cmd.get(u"cancel_gen_at_send") or 0)
                        except Exception:
                            _gen_at_send = 0
                        log(u"CMD: %s (run_id=%s gen=%s)"
                            % (cmd.get("action"), _run_id, _gen_at_send))

                        # 领取后、执行前先看一眼：命令排队期间就被取消了？
                        if read_cancel_gen() > _gen_at_send:
                            res = {u"ok": False, u"cancelled": True,
                                   u"error": u"cancelled before execution"}
                            log(u"CMD cancelled before execution")
                        else:
                            try:
                                res = handle_on_main(cmd)
                            except Exception, e:
                                res = {u"ok": False, u"error": unicode(e),
                                       u"traceback": traceback.format_exc()}
                            except BaseException, e:
                                # ⚠ 关键：IronPython 里 SystemExit / KeyboardInterrupt
                                #   不继承 Exception。被 eval_file 执行的脚本若
                                #   raise SystemExit（例如再注入一次 daemon 时
                                #   _acquire_instance() 判定「已有实例存活」），
                                #   会穿透 except Exception 一路抛出，把本守护
                                #   的轮询线程直接干掉 —— 实测 2026-11-25：
                                #   注入后心跳 0.7s 内停摆、bridge 全部超时。
                                #   所以命令执行层必须兜到 BaseException。
                                res = {u"ok": False,
                                       u"error": u"%s: %s" % (type(e).__name__, e),
                                       u"traceback": traceback.format_exc()}
                                log(u"CMD raised %s: %s" % (type(e).__name__, e))

                        # ── 结果如实回带 run_id + 取消状态
                        if not isinstance(res, dict):
                            res = {u"result": res}
                        if _run_id is not None:
                            res[u"run_id"] = _run_id
                        # 执行期间被取消（长任务如 app.build 跑完才发现）
                        if read_cancel_gen() > _gen_at_send:
                            res[u"cancelled"] = True
                            log(u"CMD cancelled during execution")
                        res.setdefault(u"cancelled", False)

                        try:
                            dump_json(RES_FILE, res)
                            log(u"RESULT written ok=%s cancelled=%s"
                                % (res.get(u"ok"), res.get(u"cancelled")))
                        except Exception, e:
                            log(u"write result err: %s" % e)
                        try:
                            os.remove(CMD_RUNNING)
                        except Exception:
                            pass
        except Exception, e:
            log(u"loop err: %s" % e)
        except BaseException, e:
            # 轮询线程绝不能死：任何 BaseException 都吞掉继续跑
            log(u"loop BaseException %s: %s" % (type(e).__name__, e))
        try:
            system.delay(150)
        except Exception:
            time.sleep(0.15)
    log(u"loop thread finished")
    _beat_stop[0] = True
    for _p in (_inst_lock, HEARTBEAT, READY_FILE):
        try:
            os.remove(_p)
        except Exception:
            pass


import System
import System.Threading

_boot(u"creating threads")
_th = System.Threading.Thread(System.Threading.ThreadStart(loop))
_th.IsBackground = False
_th.Name = u"PLC_MCP_Daemon"
_th.Start()

_boot(u"creating heartbeat thread")
_thb = System.Threading.Thread(System.Threading.ThreadStart(heartbeat_loop))
_thb.IsBackground = True      # 主循环结束就让它跟着走，不阻止进程退出
_thb.Name = u"PLC_MCP_Heartbeat"
_thb.Start()

_boot(u"threads started")
log(u"threads started, script returning")
