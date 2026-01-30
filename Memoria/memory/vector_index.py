# memory/vector_index.py
import faiss
import numpy as np
from typing import List, Tuple


class VectorIndex:
    """
    基于 FAISS 的向量索引封装，用于支持语义记忆（semantic memory）的高效检索。
    
    核心功能：
    - 存储和检索 embedding 向量
    - 支持多 agent 隔离（通过 key 命名空间）
    - 提供逻辑删除与批量清理接口
    
    重要限制（MVP 阶段）：
    - 使用 faiss.IndexFlatIP（精确内积搜索），不支持高效删除
    - 删除操作仅为“逻辑删除”（从映射表移除，但 FAISS 索引中仍保留向量）
    - 适用于低频更新、中小规模数据（单机部署场景）
    
    安全设计：
    - 所有向量通过 "{agent_id}:{type}:{id}" 键进行命名空间隔离
    - 检索时严格过滤 agent_id，防止跨用户信息泄露
    """

    def __init__(self, dim: int = 768):
        """
        初始化向量索引。
        
        参数：
        - dim: embedding 向量维度（默认 768，适配 DeepSeek / OpenAI text-embedding 等模型）
        
        内部结构：
        - self.index: FAISS 的 IndexIDMap2，支持通过外部 ID 查询
        - self.id_to_key: FAISS 内部 ID → 用户可读键（如 "user123:semantic:456"）
        - self.key_to_id: 反向映射，用于快速定位 FAISS ID
        """
        self.dim = dim
        self.index = faiss.IndexIDMap2(faiss.IndexFlatIP(dim))
        self.id_to_key = {}  # faiss_id (int) -> key (str)
        self.key_to_id = {}  # key (str) -> faiss_id (int)

    def _make_key(self, agent_id: str, mem_type: str, mem_id: int) -> str:
        """
        构造唯一键，用于标识一个向量所属的上下文。
        
        格式："{agent_id}:{mem_type}:{mem_id}"
        示例："partner_001:semantic:42"
        
        作用：
        - 实现多用户/多 agent 数据隔离
        - 支持按类型（episodic/semantic）区分（当前仅 semantic 有向量）
        """
        return f"{agent_id}:{mem_type}:{mem_id}"

    def _parse_key(self, key: str) -> Tuple[str, str, int]:
        """
        解析键字符串，还原为 (agent_id, mem_type, mem_id)。
        
        假设输入格式合法（由 _make_key 生成）。
        """
        parts = key.split(":")
        return parts[0], parts[1], int(parts[2])

    def add(self, agent_id: str, mem_type: str, mem_id: int, embedding: np.ndarray):
        """
        添加一个新向量到索引中。
        
        参数：
        - agent_id: Agent 唯一标识
        - mem_type: 记忆类型（通常为 "semantic"）
        - mem_id: 数据库中的主键 ID
        - embedding: 归一化前的原始 embedding 向量（numpy array, shape=[dim]）
        
        行为：
        - 若该 key 已存在，先逻辑删除旧项（避免重复）
        - 自动分配新的 FAISS 内部 ID（连续递增）
        - 对 embedding 进行 L2 归一化（因使用 IndexFlatIP，等价于余弦相似度）
        """
        key = self._make_key(agent_id, mem_type, mem_id)
        # 避免重复插入：先移除旧记录（逻辑删除）
        if key in self.key_to_id:
            self.remove_by_key(key)

        faiss_id = len(self.id_to_key)  # 使用当前映射长度作为新 ID
        self.id_to_key[faiss_id] = key
        self.key_to_id[key] = faiss_id

        # FAISS 要求输入为二维数组 (1, dim)
        emb_2d = embedding.reshape(1, -1)
        faiss.normalize_L2(emb_2d)  # 就地归一化
        self.index.add_with_ids(emb_2d, np.array([faiss_id]))

    def search(self, agent_id: str, query_emb: np.ndarray, k: int = 5) -> List[int]:
        """
        在指定 agent 的语义记忆中执行向量相似性搜索。
        
        参数：
        - agent_id: 目标 Agent ID
        - query_emb: 查询向量（未归一化）
        - k: 最多返回 k 个匹配的 mem_id
        
        返回：
        - 匹配的 semantic memory 的数据库 ID 列表（按相似度降序）
        
        实现细节：
        - 先对查询向量 L2 归一化
        - 检索时 over-fetch（取 k*3）以补偿跨 agent 的噪声结果
        - 仅返回属于当前 agent 且类型为 "semantic" 的结果
        """
        # 归一化查询向量
        query_2d = query_emb.reshape(1, -1)
        faiss.normalize_L2(query_2d)

        # 执行搜索（返回距离 D 和 ID I）
        D, I = self.index.search(query_2d, k * 3)  # over-fetch to filter by agent

        results = []
        for idx in I[0]:
            if idx == -1:
                continue  # FAISS 用 -1 表示无效 ID
            key = self.id_to_key.get(idx)
            if not key:
                continue  # 已被逻辑删除
            aid, mtype, mid = self._parse_key(key)
            # 严格过滤：仅当前 agent 的 semantic 记忆
            if aid == agent_id and mtype == "semantic":
                results.append(mid)
                if len(results) >= k:
                    break
        return results

    def remove(self, agent_id: str, mem_type: str, mem_id: int):
        """
        从索引中移除指定记忆的向量（逻辑删除）。
        
        参数：
        - agent_id, mem_type, mem_id: 三元组唯一标识一条记忆
        
        注意：
        - 实际 FAISS 索引未释放内存（IndexFlat 不支持物理删除）
        - 仅从映射表中移除，后续搜索将忽略该向量
        """
        key = self._make_key(agent_id, mem_type, mem_id)
        self.remove_by_key(key)

    def remove_by_key(self, key: str):
        """
        根据完整 key 执行逻辑删除。
        
        行为：
        - 从 key_to_id 和 id_to_key 中移除对应条目
        - FAISS 索引中的向量仍然存在，但不再被引用
        
        限制说明：
        - MVP 阶段接受索引“膨胀”问题（因单机、低频场景可接受）
        - 未来可考虑定期重建索引，或改用 HNSW/PQ 等支持删除的结构
        """
        if key in self.key_to_id:
            faiss_id = self.key_to_id[key]
            del self.key_to_id[key]
            del self.id_to_key[faiss_id]
            # FAISS doesn't support true deletion; mark as removed via reconstruction or use HNSW later
            # For MVP, accept that index grows — acceptable under single-user / low-volume

    def clear_agent(self, agent_id: str):
        """
        清空某个 agent 的所有向量（GDPR 合规支持）。
        
        参数：
        - agent_id: Agent 唯一标识
        
        实现：
        - 遍历所有 key，找出以 "{agent_id}:" 开头的项
        - 逐个调用 remove_by_key 进行逻辑删除
        
        用途：
        - 配合 MemoryManager.clear_all_memories() 使用
        - 确保用户数据彻底清除（至少在应用层）
        """
        keys_to_remove = [k for k in self.key_to_id if k.startswith(agent_id + ":")]
        for k in keys_to_remove:
            self.remove_by_key(k)