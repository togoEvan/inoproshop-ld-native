# -*- coding: utf-8 -*-
# @ipy2
# =====================================================================
#  路径自解析（IronPython 2.7，IDE 内运行）
#
#  IDE 内读不到 shell 的环境变量（继承的是 IDE 启动时的环境），必须自己算。
#  解析优先级：
#    1. 从本脚本路径反推（最可靠：argv[0] 走 UTF-16 命令行，中文无损）
#       ide/xxx.py -> <BASE>；ide/{tasks,studies}/xxx.py -> 上溯两级
#    2. <BASE>/base_path.txt 第一行（手工兜底）
#    3. 环境变量 PLC_MCP_BASE（仅 launch_ide_daemon.py 启动时有效）
#    4. 兜底 D:\plc_mcp
#
#  自检：IDE 里执行 ide/tasks/task_check.py，看 ipc/check.log 第一行的 BASE/SOURCE。
# =====================================================================
import os
import sys

FALLBACK = r"D:\plc_mcp"
CONFIG_NAME = "base_path.txt"

# 解析结果的来源标记，写进日志方便排错
SOURCE = u"?"


def _clean(p):
    """去掉首尾空白与包裹引号，统一正斜杠为反斜杠"""
    if not p:
        return u""
    p = p.strip()
    if len(p) >= 2 and p[0] == p[-1] and p[0] in (u'"', u"'"):
        p = p[1:-1]
    return p.replace(u"/", u"\\").rstrip(u"\\")


def _script_dir():
    """本脚本所在目录（<BASE>/ide）"""
    try:
        return os.path.dirname(os.path.abspath(sys.argv[0]))
    except Exception:
        return u""


def _read_config(base_dir):
    """读 base_path.txt 第一行（跳过 # 注释行）"""
    if not base_dir:
        return u""
    cfg = os.path.join(base_dir, CONFIG_NAME)
    if not os.path.isfile(cfg):
        return u""
    try:
        import io
        f = io.open(cfg, "r", encoding="utf-8")
        try:
            for line in f:
                line = _clean(line)
                if line and not line.startswith(u"#"):
                    return line
        finally:
            f.close()
    except Exception:
        pass
    return u""


def resolve_base():
    """返回工作根目录（含 ipc/ 与 ide/），并设置模块级 SOURCE"""
    global SOURCE

    sd = _script_dir()

    # 1) 路径反推（环境变量经子进程会按 GBK 解码损坏，argv[0] 不会）
    if sd:
        _b = os.path.basename(sd).lower()
        if _b in (u"tasks", u"studies"):
            _par = os.path.dirname(sd)
            if os.path.basename(_par).lower() == u"ide":
                SOURCE = u"derive:%s" % sd
                return os.path.dirname(_par)
        if _b == u"ide":
            SOURCE = u"derive:%s" % sd
            return os.path.dirname(sd)
        SOURCE = u"derive-fallback:%s" % sd
        return sd

    # 2) 配置文件 base_path.txt
    parent = os.path.dirname(sd) if sd else u""
    for cand in (parent, sd):
        v = _read_config(cand)
        if v:
            SOURCE = u"config:%s" % os.path.join(cand, CONFIG_NAME)
            return v

    # 3) 环境变量（仅当路径真实存在才采用，防 GBK 乱码路径）
    env = _clean(os.environ.get("PLC_MCP_BASE") or u"")
    if env and os.path.isdir(env):
        SOURCE = u"env:PLC_MCP_BASE"
        return env

    # 4) 兜底
    SOURCE = u"fallback"
    return FALLBACK


def resolve_ipc(base=None):
    """IPC 目录：优先 <BASE>/ipc（存在即用）；否则退环境变量 PLC_MCP_IPC。

    必须目录优先：IDE 进程继承启动时的 PLC_MCP_IPC（可能是旧工作区），
    环境变量优先会把 ready.flag/心跳写去旧目录。
    """
    if base is None:
        base = resolve_base()
    d = os.path.join(base, "ipc")
    if os.path.isdir(d):
        return d
    env = _clean(os.environ.get("PLC_MCP_IPC") or u"")
    if env:
        return env
    return d


def ensure_ipc(base=None):
    """确保 ipc 目录存在，返回其路径"""
    d = resolve_ipc(base)
    try:
        if not os.path.isdir(d):
            os.makedirs(d)
    except Exception:
        pass
    return d
