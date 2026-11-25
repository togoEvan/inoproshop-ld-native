# -*- coding: utf-8 -*-
"""静态检查：POU 网络里引用的符号，是否都在声明区定义过。

这是「编译器没报错 / 消息窗口读不到，但 POU 打开就是红的」这类问题的
唯一可靠排查手段——不依赖 IDE 消息，直接比对 native 里的操作数和声明。
"""
import io
import os
import re
import sys
import xml.etree.ElementTree as ET

G_BOX = u"{acfc6f68-8e3a-4af5-bf81-3dd512095a46}"
G_CONTACT = u"{9de7f100-1b87-424c-a62e-45b0cfc85ed2}"
G_OPERAND = u"{c9b2f165-48a2-4a45-8326-3952d8a3d708}"


def child(e, name):
    for c in e:
        if (c.get("Name") or "") == name:
            return c
    return None


def decl_lines(root):
    """取 Interface 下的声明区 TextLines（必须锚定 Interface，见铁律 12）。"""
    iface = None
    for el in root.iter():
        if (el.get("Name") or "") == "Interface":
            iface = el
            break
    if iface is None:
        return []
    for el in iface.iter():
        if el.tag == "Array" and (el.get("Name") or "") == "TextLines":
            out = []
            for item in el:
                for g in item:
                    if (g.get("Name") or "") == "Text":
                        out.append(g.text or u"")
            return out
    return []


def declared_names(lines):
    """从声明区文本里抽取变量名（粗粒度：行首 identifier 后跟冒号）。"""
    names = set()
    for ln in lines:
        s = ln.strip()
        if not s or s.startswith(u"//") or s.startswith(u"(*") or s.startswith(u"*"):
            continue
        if s.startswith(u"{") or s.endswith(u")") and s.startswith(u"(*"):
            continue
        # 去掉行尾注释
        s = re.sub(r"//.*$", u"", s).strip()
        s = re.sub(r"\(\*.*?\*\)", u"", s).strip()
        if not s:
            continue
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:", s)
        if m:
            names.add(m.group(1))
            # ARRAY 的 [..] 里可能有变量，不处理
    return names


def operands(root):
    """收集所有 Operand 节点的操作数文本 + 所在 POU 层级。"""
    res = []
    for el in root.iter():
        t = el.get("Type") or ""
        if t not in (G_CONTACT, G_OPERAND):
            continue
        for g in el:
            if (g.get("Name") or "") == "Operand" and g.tag == "Single":
                v = (g.text or u"").strip()
                if v:
                    res.append(v)
    return res


def base_ident(expr):
    """取表达式的最左基础标识符：a.b[0].c -> a"""
    m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)", expr.strip())
    return m.group(1) if m else None


# 不算「未定义符号」的字面量前缀 / 关键字
LITERAL_PREFIX = (u"T#", u"TIME#", u"LT#", u"D#", u"DATE#", u"TOD#",
                  u"DT#", u"16#", u"2#", u"8#", u"BOOL#", u"INT#",
                  u"REAL#", u"LREAL#", u"WORD#", u"DWORD#", u"STRING#")
KEYWORDS = set([u"TRUE", u"FALSE", u"NULL", u"ADR", u"NOT", u"AND", u"OR",
                u"XOR", u"MOD", u"ABS", u"UINT_TO_DWORD", u"TO_DWORD",
                u"TO_REAL", u"SIZEOF"])


def is_literal(expr):
    s = expr.strip()
    if not s:
        return True
    for p in LITERAL_PREFIX:
        if s.upper().startswith(p):
            return True
    # 纯数字 / 负数 / 小数
    if re.match(r"^-?\d+(\.\d+)?$", s):
        return True
    # 带引号的字符串
    if s.startswith(u"'") or s.startswith(u'"'):
        return True
    return False


def check(path, globs=None):
    globs = globs or set()
    root = ET.parse(path).getroot()
    lines = decl_lines(root)
    decl = declared_names(lines)
    # 声明首行给出 POU 名
    pou_name = u""
    for ln in lines:
        s = ln.strip()
        m = re.match(r"^(PROGRAM|FUNCTION_BLOCK|FUNCTION|INTERFACE)\s+([A-Za-z_][A-Za-z0-9_]*)", s)
        if m:
            pou_name = m.group(2)
            break

    ops = operands(root)
    unknown = []
    for v in ops:
        if is_literal(v):
            continue
        b = base_ident(v)
        if b is None:
            continue
        if b in decl:
            continue
        if b in KEYWORDS or b in globs:
            continue
        if b.isdigit():
            continue
        unknown.append(v)

    print(u"=" * 60)
    print(u"FILE : %s" % os.path.basename(path))
    print(u"POU  : %s" % (pou_name or u"(未识别)"))
    print(u"声明变量 %d 个: %s" % (len(decl), u", ".join(sorted(decl))))
    print(u"操作数 %d 处，去重 %d 个" % (len(ops), len(set(ops))))
    if unknown:
        print(u"!! 未在声明区出现的操作数 %d 处：" % len(unknown))
        for v in sorted(set(unknown)):
            print(u"     %s" % v)
    else:
        print(u"OK  所有操作数都能在声明区找到")
    return len(unknown)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    # 全局符号白名单，两级合并：
    #   ① 内置默认（工程级全局对象，不属于任何 POU 的声明区）——实测漏配会造成误报
    #   ② 环境变量 PLC_GLOBAL_SYMBOLS="Master,IO.xEmergencyStop" 追加
    # ⚠ 内置默认的来历：prg_AxisCallTest 的 AXIS_REF_SM3[REF] 引脚直接写轴名
    #   `Master`（轴是全局设备对象），check_symbols 曾把它误报成「未定义符号」。
    DEFAULT_GLOBALS = set([
        u"Master",   # 全局虚轴名（InoProShop 轴配置里定义的轴对象）
    ])
    globals_raw = os.environ.get("PLC_GLOBAL_SYMBOLS", "")
    globs = set(x.strip() for x in globals_raw.split(",") if x.strip())
    globs |= DEFAULT_GLOBALS
    print(u"全局符号白名单（内置 %d + 环境变量 %d）: %s"
          % (len(DEFAULT_GLOBALS), len(globs - DEFAULT_GLOBALS),
             u", ".join(sorted(globs))))
    bad = 0
    for p in sys.argv[1:]:
        bad += check(p, globs)
    print(u"")
    print(u"RESULT: %s (未定义符号 %d 处)" % (u"FAIL" if bad else u"PASS", bad))
    sys.exit(1 if bad else 0)


if __name__ == u"__main__":
    main()
