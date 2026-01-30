当然可以。以下是为 `EpisodicStore` 类编写的 **正式接口文档（API Specification）**，采用标准技术文档格式，适用于内部开发、测试或集成参考。

---

# 📄 EpisodicStore 接口文档  
**模块路径**：`memory.store.episodic_store.EpisodicStore`  
**描述**：异步 SQLite 存储实现，用于持久化和管理原始对话事件记忆（Episodic Memory），支持多用户隔离与 GDPR 合规操作。

---

## 1. 初始化

### `__init__(db_path: str)`

初始化存储实例。

| 参数 | 类型 | 说明 |
|------|------|------|
| `db_path` | `str` | SQLite 数据库文件路径（如 `"./data/memory.db"`） |

> 💡 要求：数据库需已存在并包含 `episodic_memory` 表（参见 `init_db.sql`）。

---

## 2. 核心方法

### `insert(agent_id: str, content: str, role: str) -> int`

插入一条新的原始对话事件。

| 参数 | 类型 | 说明 |
|------|------|------|
| `agent_id` | `str` | AI Partner 唯一标识（用于数据隔离） |
| `content` | `str` | 对话文本内容 |
| `role` | `str` | 发言者角色，必须为 `"user"` 或 `"assistant"` |

| 返回值 | 类型 | 说明 |
|--------|------|------|
| `episodic_id` | `int` | 新记录的数据库主键 ID；若失败抛出异常 |

> ✅ 安全：自动绑定 `agent_id`，防止跨用户写入。

---

### `get_by_id(agent_id: str, mem_id: int) -> dict | None`

根据 ID 获取指定记忆项（需验证归属）。

| 参数 | 类型 | 说明 |
|------|------|------|
| `agent_id` | `str` | Agent 唯一标识 |
| `mem_id` | `int` | 记忆项主键 ID |

| 返回值 | 类型 | 说明 |
|--------|------|------|
| `memory` | `dict` or `None` | 成功时返回字典：`{"id": int, "content": str, "role": str, "timestamp": str}`；否则返回 `None` |

> 🔒 安全：仅当记录存在且 `agent_id` 匹配时才返回数据。

---

### `update_content(agent_id: str, mem_id: int, new_content: str) -> bool`

更新指定记忆的内容。

| 参数 | 类型 | 说明 |
|------|------|------|
| `agent_id` | `str` | Agent 唯一标识 |
| `mem_id` | `int` | 记忆项 ID |
| `new_content` | `str` | 新的对话内容 |

| 返回值 | 类型 | 说明 |
|--------|------|------|
| `success` | `bool` | `True` 表示成功更新；`False` 表示记录不存在或无权限 |

> ⚠️ 限制：仅更新 `content` 字段，不修改 `role` 或 `timestamp`。

---

### `delete_by_id(agent_id: str, mem_id: int) -> bool`

删除单条记忆。

| 参数 | 类型 | 说明 |
|------|------|------|
| `agent_id` | `str` | Agent 唯一标识 |
| `mem_id` | `int` | 记忆项 ID |

| 返回值 | 类型 | 说明 |
|--------|------|------|
| `success` | `bool` | `True` 表示删除成功；否则为 `False` |

---

### `list_by_agent_recent(agent_id: str, limit: int = 10) -> list[dict]`

获取某 agent 最近的 N 条记忆（按时间倒序）。

| 参数 | 类型 | 说明 |
|------|------|------|
| `agent_id` | `str` | Agent 唯一标识 |
| `limit` | `int` | 最大返回条数（默认 10） |

| 返回值 | 类型 | 说明 |
|--------|------|------|
| `memories` | `list[dict]` | 每项格式同 `get_by_id` 返回值，按 `timestamp DESC` 排序 |

> 📌 用途：构建对话上下文、前端展示历史等。

---

### `search_by_agent(agent_id: str, query: str) -> list[dict]`

在当前 agent 的记忆中进行关键词模糊搜索。

| 参数 | 类型 | 说明 |
|------|------|------|
| `agent_id` | `str` | Agent 唯一标识 |
| `query` | `str` | 搜索关键词（不区分大小写由 SQLite 配置决定） |

| 返回值 | 类型 | 说明 |
|--------|------|------|
| `memories` | `list[dict]` | 匹配的记忆列表，按时间倒序排列 |

> 🔍 实现：使用 SQL `LIKE '%query%'`，MVP 阶段不支持全文检索（FTS5）。

---

### `delete_before(agent_id: str, timestamp: str) -> int`

批量删除早于指定时间的记忆（TTL 清理）。

| 参数 | 类型 | 说明 |
|------|------|------|
| `agent_id` | `str` | Agent 唯一标识 |
| `timestamp` | `str` | ISO 8601 时间字符串（如 `"2026-01-01T00:00:00"`） |

| 返回值 | 类型 | 说明 |
|--------|------|------|
| `count` | `int` | 成功删除的记录数量 |

> 🗑️ 应用：配合策略模块的 TTL 策略自动清理过期记忆。

---

### `clear(agent_id: str) -> int`

彻底清空某 agent 的所有 episodic 记忆（GDPR 合规）。

| 参数 | 类型 | 说明 |
|------|------|------|
| `agent_id` | `str` | Agent 唯一标识 |

| 返回值 | 类型 | 说明 |
|--------|------|------|
| `count` | `int` | 删除的总记录数 |

> 🛡️ 合规：用于响应用户“删除所有数据”请求，确保无残留。

---

## 3. 安全与隔离保障

- 所有方法强制校验 `agent_id`，SQL 查询均包含 `WHERE agent_id = ?`
- 无任何方法可访问其他 agent 的数据
- 不记录原始对话到系统日志（日志脱敏由上层负责）

---

## 4. 性能与限制（MVP）

| 项目 | 说明 |
|------|------|
| 并发模型 | 每次操作新建连接（适合 ≤50 QPS） |
| 搜索性能 | `LIKE` 查询在 >10k 条记录时可能变慢 |
| 扩展建议 | 高并发场景可引入连接池；大数据量可启用 FTS5 全文索引 |

---

## 5. 依赖表结构（SQLite）

```sql
CREATE TABLE episodic_memory (
    id INTEGER PRIMARY KEY,
    agent_id TEXT NOT NULL,
    content TEXT NOT NULL,
    role TEXT CHECK(role IN ('user', 'assistant')),
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_epi_agent ON episodic_memory(agent_id);
```

---

> ✅ 本接口遵循 **高内聚、低耦合、安全隔离、GDPR 友好** 的设计原则，适用于你的 AI Partner 框架中的记忆子系统。

如需生成 OpenAPI/Swagger 文档或 FastAPI 路由绑定示例，也可继续提出。