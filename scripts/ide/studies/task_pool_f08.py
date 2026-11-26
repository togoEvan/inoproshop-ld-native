# -*- coding: utf-8 -*-
# @ipy2
"""探测 SoftMotion General Axis Pool：能否新建虚拟轴、轴对象长什么样。

背景（2026-11-26 实测）：
  复制 AxesGroup 后 IDE 把 AxisGuid 全部清空为 00000000，
  编译报 2 条「X轴轴映射为空」。
  推测根因：SoftMotion 的物理轴（ServoXX/AxisXX）不能同时属于两个轴组，
  IDE 导入时主动断开映射。

出路：在 SoftMotion General Axis Pool 里建独立虚拟轴，让副本组映射到虚拟轴。

本脚本只探测，不创建。

输出 ipc/f08_pool.log
"""
import io
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))
import _base

BASE = _base.resolve_base()
IPC = _base.ensure_ipc(BASE)
LOG = os.path.join(IPC, u"f08_pool.log")
_lf = io.open(LOG, "w", encoding="utf-8")


def L(m):
    _lf.write(u"%s\n" % unicode(m))
    _lf.flush()


def kids(o):
    try:
        return list(o.get_children())
    except Exception:
        return []


def nm(o):
    try:
        return unicode(o.get_name())
    except Exception:
        return u"?"


def gd(o):
    try:
        return unicode(o.guid)
    except Exception:
        return u"?"


def pub(o):
    return [a for a in dir(o) if not a.startswith(u"_")]


try:
    proj = projects.primary
    L(u"proj 方法: %s" % pub(proj))
    L(u"")
    L(u"projects 模块: %s" % [a for a in dir(projects) if not a.startswith(u"_")])
    L(u"")

    # 找 Device 与 Axis Pool
    dev = None
    for o in kids(proj):
        if nm(o) == u"Device":
            dev = o
            break
    L(u"Device = %s" % (nm(dev) if dev is not None else u"None"))
    if dev is not None:
        L(u"Device 方法: %s" % pub(dev))
        for c in kids(dev):
            L(u"  child: %s (guid=%s)  methods=%s" % (nm(c), gd(c), pub(c)[:20]))

    pool = None
    for c in kids(dev):
        if u"Axis Pool" in nm(c):
            pool = c
            break
    L(u"")
    L(u"Axis Pool = %s" % (nm(pool) if pool is not None else u"None"))
    if pool is not None:
        L(u"pool guid = %s" % gd(pool))
        L(u"pool 方法 = %s" % pub(pool))
        L(u"pool 子对象 = %s" % [nm(k) for k in kids(pool)])
        L(u"pool.is_device = %s" % u"?")
        L(u"pool.is_folder = %s" % u"?")
except Exception, e:
    L(u"FATAL %s\n%s" % (e, traceback.format_exc()))

L(u"=== done ===")
_lf.close()
print(u"done")
