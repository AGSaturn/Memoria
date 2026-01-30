# memory/policy/default_policy.py
from .base import BasePolicy


class DefaultPolicy(BasePolicy):
    def should_store_as_episodic(self, agent_id: str, event: dict) -> bool:
        content = event["content"].strip()
        if len(content) < 5:
            return False
        if content.lower() in {"嗯", "哦", "好的", "hello"}:
            return False
        return True

    def should_summarize_to_semantic(self, agent_id: str, episodic_count: int) -> bool:
        return episodic_count % 10 == 0

    def get_episodic_ttl_days(self, agent_id: str) -> int:
        return 7

    def allow_user_to_edit_memory(self, agent_id: str, mem_type: str) -> bool:
        return True  # 可配置为 False