from abc import ABC, abstractmethod

class BasePolicy(ABC):
    @abstractmethod
    def should_store_as_episodic(self, agent_id: str, event: dict) -> bool:
        pass

    @abstractmethod
    def should_summarize_to_semantic(self, agent_id: str, episodic_count: int) -> bool:
        pass
