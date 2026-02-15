import aiosqlite
from typing import List, Optional

class SemanticStore:
    """
    Semantic Memory (Archival Memory) implementation using SQLite.
    Stores facts, summaries, and knowledge passages.
    """
    def __init__(self, db_path: str):
        self.db_path = db_path

    async def _get_conn(self):
        return await aiosqlite.connect(self.db_path)

    async def initialize(self):
        async with await self._get_conn() as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS semantic_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute("CREATE INDEX IF NOT EXISTS idx_semantic_agent ON semantic_memory(agent_id)")
            await db.commit()

    async def insert(self, agent_id: str, content: str, metadata: str = "{}") -> int:
        async with await self._get_conn() as db:
            cursor = await db.execute(
                "INSERT INTO semantic_memory (agent_id, content, metadata) VALUES (?, ?, ?)",
                (agent_id, content, metadata),
            )
            await db.commit()
            return cursor.lastrowid

    async def list_by_agent(self, agent_id: str, limit: int = 10) -> List[dict]:
        async with await self._get_conn() as db:
            rows = await db.execute_fetchall(
                "SELECT id, content, metadata, timestamp FROM semantic_memory WHERE agent_id = ? ORDER BY id DESC LIMIT ?",
                (agent_id, limit),
            )
            return [
                {"id": r[0], "content": r[1], "metadata": r[2], "timestamp": r[3], "type": "semantic"}
                for r in rows
            ]

    async def get_by_ids(self, agent_id: str, ids: List[int]) -> List[dict]:
        if not ids:
            return []
        async with await self._get_conn() as db:
            placeholders = ",".join("?" for _ in ids)
            rows = await db.execute_fetchall(
                f"SELECT id, content, metadata, timestamp FROM semantic_memory WHERE agent_id = ? AND id IN ({placeholders})",
                (agent_id, *ids),
            )
            return [
                {"id": r[0], "content": r[1], "metadata": r[2], "timestamp": r[3], "type": "semantic"}
                for r in rows
            ]

    async def update_content(self, agent_id: str, mem_id: int, new_content: str, embedding: Optional[List[float]] = None) -> bool:
        # Note: Embedding is handled by VectorIndex separately in Manager, but we keep the signature compatible if needed.
        async with await self._get_conn() as db:
            cursor = await db.execute(
                "UPDATE semantic_memory SET content = ? WHERE id = ? AND agent_id = ?",
                (new_content, mem_id, agent_id),
            )
            await db.commit()
            return cursor.rowcount > 0

    async def delete_by_id(self, agent_id: str, mem_id: int) -> bool:
        async with await self._get_conn() as db:
            cursor = await db.execute(
                "DELETE FROM semantic_memory WHERE id = ? AND agent_id = ?",
                (mem_id, agent_id),
            )
            await db.commit()
            return cursor.rowcount > 0

    async def search(self, agent_id: str, query: str, limit: int = 5) -> List[dict]:
        # Simple LIKE search for MVP (VectorIndex handles semantic search)
        async with await self._get_conn() as db:
            pattern = f"%{query}%"
            rows = await db.execute_fetchall(
                "SELECT id, content, metadata, timestamp FROM semantic_memory WHERE agent_id = ? AND content LIKE ? LIMIT ?",
                (agent_id, pattern, limit),
            )
            return [
                {"id": r[0], "content": r[1], "metadata": r[2], "timestamp": r[3], "type": "semantic"}
                for r in rows
            ]
