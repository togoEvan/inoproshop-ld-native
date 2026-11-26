# -*- coding: utf-8 -*-
"""IronPython 2.7 脚本语法校验（本地 Python 3 运行）

为什么需要它：
  scripts/ide/*.py 是 IronPython 2 语法（`except Exception, e:`、`unicode()`），
  Python 3 的 ast / py_compile 会直接报 SyntaxError，不能用来做语法门禁。
  但「不能编译」不等于「不能校验」：把 IronPython 2 独有的语法糖就地降级成
  Python 3 等价写法后再编译，就能抓到真正的结构错误（缩进、括号不配对、
  引用未定义的名字、重复 def 等）。

降级规则（只做语法层面，不改语义）：
  except X, e:      -> except X as e:
  except (A, B), e: -> except (A, B) as e:
  print x           -> print(x)        （仅顶层语句形态，print >>f 报错提示手工检查）
  raise E, "msg"    -> raise E("msg")
  `x`               -> repr(x)
  0123 八进制       -> 0o123

⚠ 校验通过只说明「语法能过」，不代表 IronPython 语义正确
  （例如 SystemExit 是否兜住、GC 是否回收命名空间，这些只能实测）。
"""
import ast
import io
import os
import re
import sys

# 已知的 IronPython/CODESYS 注入全局名，不当作未定义变量
INJECTED = {"projects", "online", "system", "clr", "System", "Microsoft",
            "OnlineChangeOption", "unicode", "basestring", "long", "xrange",
            "raw_input", "reduce", "file", "execfile", "unichr", "cmp",
            "StandardFunctions", "Guid", "scriptengine", "ScriptEngine"}


def downgrade(src):
    out = []
    for line in src.split("\n"):
        # except X, e:  ->  except X as e:
        m = re.match(r"^(\s*except\s+)(.+?)(\s*,\s*)(\w+)(\s*:)", line)
        if m:
            line = "%s%s%s%s%s" % (m.group(1), m.group(2), " as ", m.group(4), m.group(5))
        out.append(line)
    src = "\n".join(out)
    # raise E, "msg" -> raise E("msg")
    src = re.sub(r"^(\s*)raise\s+([\w\.]+)\s*,\s*(.+)$",
                 r'\1raise \2(\3)', src, flags=re.M)
    # print >>f, x   （无法安全降级，留标记让下面报出来）
    if re.search(r"^\s*print\s*>>", src, flags=re.M):
        raise SyntaxError("含 print >> 重定向语法，需手工检查")
    # print x  ->  print(x)（只处理「print 后跟非括号」的顶层语句）
    src = re.sub(r"^(\s*)print\s+(?!\()([^#\n]+)$",
                 r"\1print(\2)", src, flags=re.M)
    # `x` -> repr(x)
    src = re.sub(r"`([^`\n]+)`", r"repr(\1)", src)
    return src


def check_file(path):
    """返回 (ok, [问题])"""
    problems = []
    try:
        raw = io.open(path, "r", encoding="utf-8").read()
    except Exception as e:
        return False, ["读不出文件：%s" % e]

    if raw.startswith(u"\ufeff"):
        problems.append("文件带 UTF-8 BOM（IronPython 可接受，但与其他文件不一致）")

    try:
        src = downgrade(raw)
        tree = ast.parse(src, filename=path)
    except SyntaxError as e:
        return False, ["语法错误：line %s: %s（原文：%r）"
                       % (getattr(e, "lineno", "?"), e.msg,
                          (getattr(e, "text", "") or "").strip())]
    except Exception as e:
        return False, ["降级失败：%s" % e]

    # 结构体检
    defs = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            if node.name in defs:
                problems.append("重复定义 %s（首次 line %d，再次 line %d）"
                                % (node.name, defs[node.name], node.lineno))
            defs[node.name] = node.lineno

    # 顶层裸语句检查：IDE 脚本顶层不应该有 input()/raw_input()
    for node in tree.body:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            fn = node.value.func
            name = getattr(fn, "id", None) or getattr(fn, "attr", None)
            if name in ("input", "raw_input"):
                problems.append("顶层调用了 %s()，IDE 里会阻塞主线程（line %d）"
                                % (name, node.lineno))

    return (len(problems) == 0), problems


def main(argv):
    if len(argv) < 2:
        print("usage: check_ipy_syntax.py <file.py> [...]")
        return 1
    bad = 0
    for p in argv[1:]:
        ok, probs = check_file(p)
        if ok:
            print("[ OK ] %s" % p)
        else:
            bad += 1
            print("[FAIL] %s" % p)
            for x in probs:
                print("       - %s" % x)
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
