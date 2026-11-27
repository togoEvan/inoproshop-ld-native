# 语料工具链（把整个工程的 LD 导出、索引、统计成可查的表）

这套工具是「按模板学」的基础设施：**先把真实工程变成可统计的语料，再谈怎么写**。
实现在 `scripts/corpus/`，五个脚本分两类：

| 脚本 | 跑在哪 | 作用 |
|---|---|---|
| `export_all.py` | **IDE 内（IronPython 2.7）** | 递归导出 `active_application` 全部后代，每个对象一个 `.native` |
| `index_native.py` | 主机（Python 3） | 解析每个 `.native` 的元数据 → `index.json`（名称/类型/语言/网络数/框数） |
| `scan_forms.py` | 主机 | BoxType × CallType × 槽数 × InputFlags 统计 |
| `parse_net.py` | 主机 | 按网络拆解、统计形状 → `net_shapes.json` |
| `ld_dump.py` | 主机 | 把单个 POU 的某个网络打成结构树（调试用） |

## 环境变量（全部可覆盖，默认在当前目录的 `ld_study/`）

| 变量 | 默认 | 含义 |
|---|---|---|
| `LD_BASE` | `./ld_study` | 语料根目录 |
| `LD_RAW` | `$LD_BASE/raw` | `.native` 导出目录 |
| `LD_PROJ` | `$LD_BASE/proj/study_lead.project` | 要导出的工程副本 |
| `LD_INDEX` | `$LD_BASE/index.json` | 索引输出 |
| `LD_SHAPES` | `$LD_BASE/net_shapes.json` | 形状统计输出 |
| `LD_EXPORT_LOG` | `$LD_BASE/export_all.log` | 导出日志 |

## 流程

```
# 1) 复制一份工程（绝不导出正在编辑的原件）
cp study.project ld_study/proj/study_lead.project

# 2) 在 IDE 里跑 export_all.py（IronPython）
#    方式 A：IDE 菜单 Tools -> Scripting -> Execute Script File...
#    方式 B：InoProShop.exe --profile=<p> --runscript=<export_all.py>（会显示窗口）
#    方式 C：隐藏桌面实例（推荐，不抢前台），见 references/mcp-bridge.md

# 3) 主机侧索引与统计
python scripts/corpus/index_native.py
python scripts/corpus/scan_forms.py
python scripts/corpus/parse_net.py

# 4) 看某个 POU 的结构
python scripts/corpus/ld_dump.py ld_study/raw/040_A00_上料移栽.native 1 6
```

## 实测产出（InoPack 包装模板）

| 指标 | 值 |
|---|---|
| 导出文件 | **713** 个 / 320.2 MB |
| 导出耗时 | 约 20 分钟（隐藏桌面实例，含 126 秒单次耗时的大 POU） |
| 失败对象 | 5 个，全是**任务调用条目**（`M000_MAIN` 等），报 `file does not exist`，属正常 |
| 去重后对象 | 470（LD 61 / ST 192 / 无实现 217） |
| 小于 200 B 的文件 | 自动删除（空对象导出的空壳） |

## 坑

1. **不要把导出目录放进工程目录**：会被工程扫描/备份逻辑干扰；
2. `export_native` 在隐藏桌面实例上偶发卡死（同一脚本第一次 1 秒、第二次 2 分钟不返回），主机侧要加超时；
3. 文件名里的中文没有问题（UTF-8），但 `ld_dump.py` 走 `sys.argv` 时要确保控制台也是 UTF-8；
4. `id` 去重要按「同一 `MetaObject/Name` 取字节最大的一份」——同一个对象会在多个父级导出里重复出现；
5. IronPython 下写文件必须显式 `close()`，否则句柄滞留 IDE 进程、主机侧读会 `PermissionError`。

---

配套阅读：`references/corpus/inopack-template-survey.md`（普查结论）、`references/corpus/ld-network-shapes.md`（形状表）。
