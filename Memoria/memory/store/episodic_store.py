# memory/store/episodic_store.py
import aiosqlite
from .base import BaseEpisodicStore


class EpisodicStore(BaseEpisodicStore):
    """
    原始事件记忆（Episodic Memory）的 SQLite 异步存储实现。
    
    职责：
    - 持久化用户与 AI 的原始对话片段（经策略过滤后）
    - 提供基于 agent_id 隔离的 CRUD 操作
    - 保证所有数据库操作均包含 agent_id 条件，防止跨用户数据泄露
    
    特点：
    - 使用 aiosqlite 支持异步 I/O，避免阻塞 FastAPI 事件循环
    - 每次操作独立连接（适合轻量级单机部署）
    - 所有 SQL 查询使用参数化语句，防止注入攻击
    """

    def __init__(self, db_path: str):
        """
        初始化 EpisodicStore。
        
        参数：
        - db_path: SQLite 数据库文件路径（如 "./data/memory.db"）
        """
        self.db_path = db_path

    async def _get_conn(self):
        """
        获取一个新的异步数据库连接。
        
        返回：
        - aiosqlite.Connection 实例
        
        说明：
        - 每次调用新建连接，适用于低并发场景（MVP）
        - 生产环境高并发时可考虑连接池（如 aiosqlite + contextvars 或使用 asyncpg 替代）
        """
        return await aiosqlite.connect(self.db_path)

    async def insert(self, agent_id: str, content: str, role: str) -> int:
        """
        插入一条新的 episodic 记忆。
        
        参数：
        - agent_id: 当前 AI Partner 的唯一标识，用于数据隔离
        - content: 对话内容文本
        - role: 发言者角色，必须为 'user' 或 'assistant'
        
        返回：
        - 新插入记录的数据库主键 ID（即 episodic_id）
        
        安全性：
        - 自动绑定 agent_id，确保多用户数据隔离
        """
        async with await self._get_conn() as db:
            cursor = await db.execute(
                "INSERT INTO episodic_memory (agent_id, content, role) VALUES (?, ?, ?)",
                (agent_id, content, role),
            )
            await db.commit()
            return cursor.lastrowid

    async def get_by_id(self, agent_id: str, mem_id: int) -> dict | None:
        """
        根据 ID 获取指定的 episodic 记忆（需验证归属）。
        
        参数：
        - agent_id: Agent 唯一标识
        - mem_id: 记忆项的主键 ID
        
        返回：
        - 包含 id, content, role, timestamp 的字典；若不存在或不属于该 agent，则返回 None
        
        安全机制：
        - WHERE 子句同时校验 id 和 agent_id，防止越权访问
        """
        async with await self._get_conn() as db:
            row = await db.execute_fetchall(
                "SELECT id, content, role, timestamp FROM episodic_memory WHERE id = ? AND agent_id = ?",
                (mem_id, agent_id),
            )
            return dict(zip(["id", "content", "role", "timestamp"], row[0])) if row else None

    async def update_content(self, agent_id: str, mem_id: int, new_content: str) -> bool:
        """
        更新指定 episodic 记忆的内容。
        
        参数：
        - agent_id: Agent 唯一标识
        - mem_id: 记忆项 ID
        - new_content: 新的对话内容
        
        返回：
        - 是否成功更新（若记录不存在或不属于该 agent，则返回 False）
        
        注意：
        - 不允许修改 role 或 timestamp，仅更新 content
        """
        async with await self._get_conn() as db:
            await db.execute(
                "UPDATE episodic_memory SET content = ? WHERE id = ? AND agent_id = ?",
                (new_content, mem_id, agent_id),
            )
            await db.commit()
            return db.total_changes > 0

    async def delete_by_id(self, agent_id: str, mem_id: int) -> bool:
        """
        删除指定的 episodic 记忆。
        
        参数：
        - agent_id: Agent 唯一标识
        - mem_id: 记忆项 ID
        
        返回：
        - 是否成功删除
        
        安全性：
        - 仅当记录存在且属于该 agent 时才执行删除
        """
        async with await self._get_conn() as db:
            await db.execute(
                "DELETE FROM episodic_memory WHERE id = ? AND agent_id = ?", (mem_id, agent_id)
            )
            await db.commit()
            return db.total_changes > 0

    async def list_by_agent_recent(self, agent_id: str, limit: int = 10) -> list[dict]:
        """
        获取某个 agent 最近的 N 条 episodic 记忆（按时间倒序）。
        
        参数：
        - agent_id: Agent 唯一标识
        - limit: 最大返回条数（默认 10）
        
        返回：
        - 记忆列表，每项为字典（含 id, content, role, timestamp）
        
        用途：
        - 构建对话上下文、展示记忆历史等
        """
        async with await self._get_conn() as db:
            rows = await db.execute_fetchall(
                "SELECT id, content, role, timestamp FROM episodic_memory WHERE agent_id = ? ORDER BY timestamp DESC LIMIT ?",
                (agent_id, limit),
            )
            return [dict(zip(["id", "content", "role", "timestamp"], r)) for r in rows]

    async def search_by_agent(self, agent_id: str, query: str) -> list[dict]:
        """
        在当前 agent 的 episodic 记忆中进行关键词模糊搜索。
        
        参数：
        - agent_id: Agent 唯一标识
        - query: 搜索关键词
        
        返回：
        - 匹配的记忆列表（按时间倒序）
        
        实现方式：
        - 使用 SQL 的 LIKE 运算符（%query%）
        - MVP 阶段不支持分词或全文检索（如 FTS5），后续可扩展
        
        注意：
        - 性能随数据量增长而下降，建议配合 TTL 清理机制使用
        """
        async with await self._get_conn() as db:
            rows = await db.execute_fetchall(
                "SELECT id, content, role, timestamp FROM episodic_memory WHERE agent_id = ? AND content LIKE ? ORDER BY timestamp DESC",
                (agent_id, f"%{query}%"),
            )
            return [dict(zip(["id", "content", "role", "timestamp"], r)) for r in rows]

    async def delete_before(self, agent_id: str, timestamp: str) -> int:
        """
        删除早于指定时间戳的所有 episodic 记忆（用于 TTL 自动清理）。
        
        参数：
        - agent_id: Agent 唯一标识
        - timestamp: ISO 8601 格式时间字符串（如 "2026-01-01T00:00:00"）
        
        返回：
        - 成功删除的记录数量
        
        应用场景：
        - 配合策略模块的 get_episodic_ttl_days() 实现自动过期
        """
        async with await self._get_conn() as db:
            cur = await db.execute(
                "DELETE FROM episodic_memory WHERE agent_id = ? AND timestamp < ?", (agent_id, timestamp)
            )
            await db.commit()
            return cur.rowcount

    async def clear(self, agent_id: str) -> int:
        """
        清空某个 agent 的所有 episodic 记忆（GDPR 合规支持）。
        
        参数：
        - agent_id: Agent 唯一标识
        
        返回：
        - 删除的记录总数
        
        用途：
        - 用户请求“删除所有数据”时调用
        - 确保彻底清除，不留残留
        """
        async with await self._get_conn() as db:
            cur = await db.execute("DELETE FROM episodic_memory WHERE agent_id = ?", (agent_id,))
            await db.commit()
            return cur.rowcount