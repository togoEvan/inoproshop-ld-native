# -*- coding: utf-8 -*-
"""F08 对照实验：把副本的 AxisGuid 改成空闲轴，验证「清空」是否因为轴被占用。

背景（2026-11-26 实测）：
  副本 AxesGroup_A1_F08V 导入后，IDE 把 AxisGuid 全部清成 00000000，
  编译报 2 条「X轴轴映射为空」。
  假设：SoftMotion 物理轴不能同时属于两个轴组，IDE 导入时主动断开。

实验设计（两个副本，映射到不同的空闲轴）：
  AxesGroup_A1_F08V -> Axis9_擦拭A1侧Z轴  + Axis10_擦拭B1侧无尘布定长步进轴
  AxesGroup_C1_F08V -> Axis11_擦拭B1侧X轴 + Axis12_擦拭B1侧Y轴
  若导入后 AxisGuid 保留 -> 假设成立，轴占用是唯一原因
  若仍被清空       -> 另有原因（可能是轴组 Guid 与轴的绑定表在别处）

空闲轴 guid（从 f08_device.log 抄）：
  Axis9  d497665b-c20e-4be3-83c0-d99066ce823e
  Axis10 4fdf1211-bd00-419e-837b-0629fe2952b5
  Axis11 1b456f45-b535-4188-ab6d-b1b3efc1ce0a
  Axis12 1a3ce2c8-9a76-49ba-93cf-361bc5ff303c
"""
import io
import os
import sys

SRC = u"ipc/f08_out"
OUT = u"ipc/f08_out_alt"

MAP = {
    u"AxesGroup_A1_F08V": [
        (u"2b9e1a51-3d84-41f9-9187-c4b390e44702", u"d497665b-c20e-4be3-83c0-d99066ce823e"),
        (u"39176bc8-8579-4e58-82de-64bf898d66fb", u"4fdf1211-bd00-419e-837b-0629fe2952b5"),
    ],
    u"AxesGroup_C1_F08V": [
        (u"abafabd0-00c4-4e76-8297-ec8962a0b629", u"1b456f45-b535-4188-ab6d-b1b3efc1ce0a"),
        (u"d9285e5b-cb8f-4be6-92e7-2269a8304159", u"1a3ce2c8-9a76-49ba-93cf-361bc5ff303c"),
    ],
}


def main():
    if not os.path.isdir(OUT):
        os.makedirs(OUT)
    for name, pairs in MAP.items():
        src = os.path.join(SRC, name + u".native")
        if not os.path.isfile(src):
            print(u"MISSING %s" % src)
            continue
        s = io.open(src, u"r", encoding=u"utf-8").read()
        n = 0
        for old, new in pairs:
            if old in s:
                s = s.replace(old, new)
                n += 1
        dst = os.path.join(OUT, name + u".native")
        io.open(dst, u"w", encoding=u"utf-8").write(s)
        print(u"%s: replaced %d axis guid(s) -> %s" % (name, n, os.path.basename(dst)))
    return 0


if __name__ == u"__main__":
    sys.exit(main())
