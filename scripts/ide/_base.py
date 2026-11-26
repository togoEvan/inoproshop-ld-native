# -*- coding: utf-8 -*-
# =====================================================================
#  路径自解析（IronPython 2.7，IDE 内运行）
#
#  为什么需要这个文件：
#    IDE 内的脚本跑在 InoProShop 进程里，继承的是「IDE 启动那一刻」的环境变量，
#    跟你在 PowerShell 里临时 set 的 PLC_MCP_BASE 毫无关系。
#    实测：在 IDE 内读 os.environ.get("PLC_MCP_BASE") 永远是 None。
#    所以不能依赖环境变量，必须让脚本自己算出自己在哪。
#
#  解析优先级（高 → 低）：
#    1. 环境变量 PLC_MCP_BASE
#       仅当 IDE 是通过 launch_ide_daemon.py 启动时才有效（子进程继承环境）
#    2. <BASE>/base_path.txt 第一行
#       手工兜底：把工作目录写进这个文件，脚本就认它
#    3. 从本脚本自身路径反推
#       <BASE>/ide/xxx.py          ->  <BASE>
#       <BASE>/ide/tasks/xxx.py    ->  <BASE>（上溯两级）
#       <BASE>/ide/studies/xxx.py  ->  <BASE>（上溯两级）
#       实测 sys.argv[0] 就是脚本绝对路径，这是最可靠的方式
#    4. 最后退回 D:\plc_mcp
#
#  自检：在 IDE 里执行 scripts/ide/tasks/task_check.py，看 ipc/check.log 第一行
#        会打印实际解析到的 BASE 与来源，便于排查部署问题。
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
    """读 <BASE>/base_path.txt 第一行"""
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

    # 1) 从脚本自身路径反推：<BASE>/ide/xxx.py -> <BASE>
    #    最可靠。sys.argv[0] 走 Windows 原生 UTF-16 命令行，中文路径绝对无损；
    #    而环境变量传中文路径经子进程会按 GBK 解码损坏（实测：小艺Work工作空间
    #    变成 灏忚壓Work宸ヤ綔绌洪棿）。daemon 恒从 <BASE>/ide/plc_daemon.py 跑，
    #    所以推导结果总是正确。
    if sd:
        _b = os.path.basename(sd).lower()
        # <BASE>/ide/tasks/xxx.py 或 <BASE>/ide/studies/xxx.py -> 再上溯一级
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

    # 2) 配置文件（先看 <BASE>/base_path.txt，再看 <BASE>/ide/base_path.txt）
    parent = os.path.dirname(sd) if sd else u""
    for cand in (parent, sd):
        v = _read_config(cand)
        if v:
            SOURCE = u"config:%s" % os.path.join(cand, CONFIG_NAME)
            return v

    # 3) 环境变量（仅当路径真实存在才采用；损坏的 GBK 乱码路径 isdir 必为 False）
    #    注意：只有 IDE 由 launch_ide_daemon.py 启动时才传得到，手动开 IDE 取不到。
    env = _clean(os.environ.get("PLC_MCP_BASE") or u"")
    if env and os.path.isdir(env):
        SOURCE = u"env:PLC_MCP_BASE"
        return env

    # 4) 最后兜底
    SOURCE = u"fallback"
    return FALLBACK


def resolve_ipc(base=None):
    """IPC 目录：优先 <BASE>/ipc；仅当它不存在时才退回环境变量 PLC_MCP_IPC。

    不能反过来：IDE 进程会继承「启动它的那个环境」里的 PLC_MCP_IPC。
    实测（2026-11-25）：IDE 从旧工作区启动时带着
    PLC_MCP_IPC=D:\\小艺Work工作空间\\20261123160323\\plc_mcp\\ipc，
    若环境变量优先，守护会把 ready.flag / 心跳写到旧目录，
    新版部署永远等不到就绪信号。
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
