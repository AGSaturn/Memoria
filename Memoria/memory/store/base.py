from abc import ABC, abstractmethod
from typing import List, Optional

class BaseEpisodicStore(ABC):
    @abstractmethod
    async def insert(self, agent_id: str, content: str, role: str) -> int:
        pass

    @abstractmethod
    async def get_by_id(self, agent_id: str, mem_id: int) -> dict | None:
        pass
    
    @abstractmethod
    async def list_by_agent(self, agent_id: str, limit: int = 10) -> List[dict]:
        pass
