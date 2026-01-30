# memory/manager.py
from typing import List, Optional, Union
from .policy.base import BasePolicy
from .store.episodic_store import EpisodicStore
from .store.semantic_store import SemanticStore
from .processor.default_processor import DefaultProcessor
from .vector_index import VectorIndex


class MemoryManager:
    """
    记忆管理器：统一协调 episodic（事件记忆）与 semantic（语义记忆）的 CRUD 操作。
    
    职责：
    - 提供面向用户的记忆操作接口（增删改查）
    - 强制执行 agent_id 隔离策略
    - 调用策略模块（Policy）判断是否允许某项操作
    - 协调存储层（Store）与向量索引（VectorIndex）的一致性
    
    设计原则：
    - 高内聚低耦合：依赖注入各子模块
    - 安全优先：所有操作均校验 agent_id 归属
    - 可扩展：支持替换存储后端或嵌入模型
    """

    def __init__(
        self,
        policy: BasePolicy,
        episodic_store: EpisodicStore,
        semantic_store: SemanticStore,
        vector_index: VectorIndex,
        processor: DefaultProcessor,
    ):
        """
        初始化记忆管理器。
        
        参数：
        - policy: 控制记忆行为的策略对象（如是否存储、是否可编辑等）
        - episodic_store: 原始对话事件的持久化存储
        - semantic_store: 语义摘要的持久化存储（含 embedding）
        - vector_index: 向量索引，用于语义检索
        - processor: 负责文本嵌入和摘要生成的处理器
        """
        self.policy = policy
        self.episodic_store = episodic_store
        self.semantic_store = semantic_store
        self.vector_index = vector_index
        self.processor = processor

    async def add_event(self, agent_id: str, event: dict) -> int:
        """
        添加一条原始对话事件到 episodic 记忆。
        
        参数：
        - agent_id: 当前 AI Partner 的唯一标识，用于数据隔离
        - event: 包含 'content' 和 'role' 的字典（如 {'content': '我喜欢猫', 'role': 'user'}）
        
        返回：
        - 成功时返回数据库中的 episodic_id；若被策略过滤则返回 -1
        
        注意：
        - 此方法不触发语义摘要生成（应由 orchestrator 异步处理）
        """
        if not self.policy.should_store_as_episodic(agent_id, event):
            return -1
        episodic_id = await self.episodic_store.insert(agent_id, event["content"], event["role"])
        # TODO: 触发 summarization 逻辑（例如累计 N 条后生成 semantic 记忆）
        return episodic_id

    async def list_recent_memories(self, agent_id: str, limit: int = 10) -> List[dict]:
        """
        获取指定 agent 最近的 episodic 和 semantic 记忆列表（按时间倒序）。
        
        参数：
        - agent_id: Agent 唯一标识
        - limit: 每类记忆最多返回条数
        
        返回：
        - 合并后的记忆列表（未排序，调用方可自行合并排序）
        
        用途：
        - 用于初始化对话上下文或展示记忆历史
        """
        episodic = await self.episodic_store.list_by_agent(agent_id, limit)
        semantic = await self.semantic_store.list_by_agent(agent_id, limit)
        return episodic + semantic

    async def search_memories(self, agent_id: str, query: str) -> List[dict]:
        """
        混合检索：结合关键词匹配（episodic）与语义向量检索（semantic）。
        
        参数：
        - agent_id: Agent 唯一标识
        - query: 用户查询文本
        
        返回：
        - 匹配的记忆项列表（包含 episodic 和 semantic）
        
        实现细节：
        - episodic 使用 SQLite 的 LIKE 进行简单模糊匹配（MVP）
        - semantic 使用 FAISS 向量索引进行近似最近邻搜索
        """
        # 1. 在 episodic 记忆中进行文本模糊匹配
        episodic_hits = await self.episodic_store.search(agent_id, query)
        # 2. 对 query 嵌入，并在 semantic 记忆中进行向量检索
        embedding = await self.processor.embed(query)
        semantic_ids = self.vector_index.search(agent_id, embedding, k=5)
        semantic_hits = await self.semantic_store.get_by_ids(agent_id, semantic_ids)
        return episodic_hits + semantic_hits

    async def get_memory_item(self, agent_id: str, mem_id: int, mem_type: str) -> Optional[dict]:
        """
        根据 ID 和类型获取单条记忆详情。
        
        参数：
        - agent_id: Agent 唯一标识
        - mem_id: 记忆项的数据库主键
        - mem_type: "episodic" 或 "semantic"
        
        返回：
        - 记忆字典（含 id, content/summary, timestamp 等），若不存在或无权限则返回 None
        
        安全性：
        - 存储层自动校验 agent_id，防止跨用户访问
        """
        if mem_type == "episodic":
            return await self.episodic_store.get_by_id(agent_id, mem_id)
        elif mem_type == "semantic":
            return await self.semantic_store.get_by_id(agent_id, mem_id)
        return None

    async def update_memory_content(self, agent_id: str, mem_id: int, new_content: str, mem_type: str) -> bool:
        """
        更新指定记忆的内容（支持用户修正错误记忆）。
        
        参数：
        - agent_id: Agent 唯一标识
        - mem_id: 记忆项 ID
        - new_content: 新内容
        - mem_type: "episodic" 或 "semantic"
        
        返回：
        - 是否更新成功（受策略控制）
        
        特别说明：
        - 若更新 semantic 记忆，会重新计算 embedding 并更新向量索引
        - 策略可通过 allow_user_to_edit_memory 禁止编辑
        """
        if not self.policy.allow_user_to_edit_memory(agent_id, mem_type):
            return False
        if mem_type == "episodic":
            return await self.episodic_store.update_content(agent_id, mem_id, new_content)
        elif mem_type == "semantic":
            embedding = await self.processor.embed(new_content)
            return await self.semantic_store.update_content(agent_id, mem_id, new_content, embedding)
        return False

    async def delete_memory(self, agent_id: str, mem_id: int, mem_type: str) -> bool:
        """
        删除单条记忆，并同步清理向量索引（如适用）。
        
        参数：
        - agent_id: Agent 唯一标识
        - mem_id: 记忆项 ID
        - mem_type: "episodic" 或 "semantic"
        
        返回：
        - 是否删除成功
        
        数据一致性：
        - 删除 semantic 记忆时，会从 FAISS 索引中移除对应向量
        - episodic 记忆虽无向量，但保留统一接口
        """
        if mem_type == "episodic":
            success = await self.episodic_store.delete_by_id(agent_id, mem_id)
            if success:
                self.vector_index.remove(agent_id, "episodic", mem_id)
            return success
        elif mem_type == "semantic":
            success = await self.semantic_store.delete_by_id(agent_id, mem_id)
            if success:
                self.vector_index.remove(agent_id, "semantic", mem_id)
            return success
        return False

    async def delete_memories_before(self, agent_id: str, timestamp: str) -> int:
        """
        批量删除早于指定时间戳的记忆（用于 TTL 自动清理）。
        
        参数：
        - agent_id: Agent 唯一标识
        - timestamp: ISO 8601 格式时间字符串，如 "2026-01-01T00:00:00"
        
        返回：
        - 总共删除的记忆条数
        
        注意：
        - MVP 中不实时清理 FAISS 向量（因 FAISS 不支持高效删除）
        - 生产环境建议定期重建索引或使用支持删除的索引结构
        """
        count1 = await self.episodic_store.delete_before(agent_id, timestamp)
        count2 = await self.semantic_store.delete_before(agent_id, timestamp)
        # Note: FAISS cleanup is deferred or batched (MVP skips real-time sync for range delete)
        return count1 + count2

    async def clear_all_memories(self, agent_id: str) -> int:
        """
        彻底清空某个 agent 的所有记忆（GDPR 合规“被遗忘权”支持）。
        
        参数：
        - agent_id: Agent 唯一标识
        
        返回：
        - 总共删除的记忆条数
        
        安全性：
        - 同时清理数据库和向量索引，确保无残留
        - 适用于用户注销或请求删除数据场景
        """
        count1 = await self.episodic_store.clear(agent_id)
        count2 = await self.semantic_store.clear(agent_id)
        self.vector_index.clear_agent(agent_id)
        return count1 + count2