# 预编译错误对照表

## 消息分类 GUID（铁律：验收看预编译）

| 分类 | GUID | 说明 |
|------|------|------|
| 预编译 | `217bc73e-759b-4a3c-bfa1-991c938a6541` | **真正的错误来源，验收标准** |
| 编译 | `97f48d64-a2a3-4856-b640-75c046e37ea9` | build()/rebuild() 只填这个，**永远 0 错误**，不能当验收 |
| 脚本消息 | `194b48a9-ab51-43ae-b9a9-51d3edaaddf3` | |
| 导出/导入 | `2af7707f-6167-4a76-a40e-430967be0f18` | |
| 库管理器 | `56a60174-4139-411b-86c7-df0da1cfc088` | |

## 错误 → 根因 → 修复

### 1. `不允许对类型 'SINT' 进行 'NOT' 操作`

- **根因**：值输入引脚（IN 槽）从触点模板克隆，残留 `IsContact=True` 和/或内部 `Flags=1`（NOT 标志），IDE 对 INT 常量做触点取反逻辑
- **修复**：IN 槽位节点 `IsContact=False` + Operand 内部 `Flags/Flags=0`、`Fixed=False`
- **特征**：每个 MOVE 框恰好 1 个错误；与触点写法、EN 槽内容、BoxType/CallType/IsBoxType 全无关（4 个受控实验证明）

### 2. AND 框报"需要至少 2 操作数"

- **根因**：AND 框 InputItems 里只放了 1 个触点
- **修复**：AND 框至少 2 个触点；单条件时补一个 TRUE 触点

### 3. IDE 红框（画面红框+红波浪线）

- **根因 A**：功能框 InputItems 槽位数 != InputParam 参数数（如 6 触点塞进 [EN, IN] 2 槽）
- **根因 B**：IN 引脚 `Type=BOOL`（应为 INT）或 `Boolean=True`
- **修复**：槽位数严格对齐；常量引脚 `Type=INT` + `Boolean=False`

### 4. `已标识项中有一项的格式无效`

- **根因**：MOVE 框挂错位置（NETITEM.OutputItems 或 NETITEM.RValue）
- **修复**：MOVE 框直接挂 `Network/NetworkItems`

### 5. 预编译分类读出来是 0 但其实有错（假象）

- **根因**：`system.clear_messages()` 清空后，预编译由 IDE 后台**异步**填充，立即读会漏
- **修复**：执行「检查程序」命令（`system.commands` 里 name=="检查程序"，tokens=project/buildactiveapp，索引约 91）后 `process_messageloop()` + 短等待再读；或直接读当前消息（不 clear）

## 编译分类的可忽略警告

- `[Warning] 未加载库(CmpLog)...` —— 库未加载警告，与逻辑无关，可忽略
