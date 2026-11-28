# @py3
# -*- coding: utf-8 -*-
"""把一个多网络的 native 拆成「一个网络一个文件」，供克隆 / 比对 / 建模板库。

用法：
    python split_networks.py <源 native> <输出目录> [网络序号 ...]
例：
    python split_networks.py ../assets/natives/prg_Stn3LoadSeq.native out/net 1 2 8
不给序号时导出全部网络。

为什么不用字符串切：NetworkList 的 List2 是嵌套的，靠肉眼配对标签深度实测会把每块
截成 140 字符；用 ElementTree 取 NetworkList 的子元素，才真是「一个网络一个节点」。
注意：ET 重新序列化会规范化属性顺序与空元素写法（<X></X> 与 <X/>），克隆回 native
时 IDE 接受，但不要拿输出做字节级比对。
"""
import io, os, sys
import xml.etree.ElementTree as ET


def find_network_list(root):
    for e in root.iter("List2"):
        if e.get("Name") == "NetworkList":
            return e
    raise RuntimeError("no List2 Name=NetworkList in this native")


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    src, out_dir = argv[1], argv[2]
    want = [int(x) for x in argv[3:]] if len(argv) > 3 else None
    root = ET.parse(src).getroot()
    nets = list(find_network_list(root))
    print("networks = %d" % len(nets))
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    n = 0
    for i, el in enumerate(nets, 1):
        if want and i not in want:
            continue
        txt = ET.tostring(el, encoding="unicode")
        p = os.path.join(out_dir, "net%02d.xml" % i)
        f = io.open(p, "w", encoding="utf-8")
        try:
            f.write(txt)
        finally:
            f.close()
        n += 1
        print("%-24s %d chars" % (p, len(txt)))
    print("done, %d files" % n)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))