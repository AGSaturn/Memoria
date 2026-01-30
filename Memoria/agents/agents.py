from abc import ABC, abstractmethod
from typing import Callable, Dict, Any
import asyncio

# 假设的返回类型（可根据实际需要调整）
class AgentResponse:
    def __init__(self, content: str, metadata: Dict[str, Any] = None):
        self.content = content
        self.metadata = metadata or {}

# 假设的依赖组件接口（实际可替换为具体实现）
class MemoryManager:
    pass

class LLMClient:
    async def generate(self, prompt: str) -> str:
        raise NotImplementedError

# 抽象基类 BaseAgent
class BaseAgent(ABC):
    def __init__(
        self,
        agent_id: str,
        core_memory: Dict[str, Any],
        memory_manager: MemoryManager,
        llm_client: LLMClient,
        prompt_builder: Callable[[str, Dict], str]
    ):
        self.agent_id = agent_id
        self.core_memory = core_memory
        self.memory_manager = memory_manager
        self.llm_client = llm_client
        self.prompt_builder = prompt_builder
        self._event_handlers: Dict[str, list] = {}

    async def step(self, user_input: str) -> AgentResponse:
        """
        主交互入口：协调记忆读取、提示构建、LLM 调用和事件触发。
        """
        # 1. 构建完整上下文（可从 memory_manager 获取短期/长期记忆）
        context = await self._build_context(user_input)
        prompt = self.prompt_builder(user_input, context)

        # 2. 调用 LLM
        response_text = await self.llm_client.generate(prompt)

        # 3. 可选：触发事件（如 'response_generated'）
        await self._emit('response_generated', {'response': response_text})

        return AgentResponse(content=response_text)

    async def _build_context(self, user_input: str) -> Dict[str, Any]:
        """
        内部方法：组合 core_memory + 短期/长期记忆（由子类或 memory_manager 实现细节）
        """
        # 示例：仅返回核心记忆（实际应从 memory_manager 获取更多）
        return {
            "core_memory": self.core_memory,
            "user_input": user_input
        }

    def on(self, event: str, callback: Callable) -> None:
        """
        注册事件回调
        """
        if event not in self._event_handlers:
            self._event_handlers[event] = []
        self._event_handlers[event].append(callback)

    def off(self, event: str, callback: Callable = None) -> None:
    """
    取消事件监听
    - 如果 callback 为 None：移除该事件所有监听器
    - 否则：仅移除指定的 callback
    """
    if event not in self._event_handlers:
        return

    if callback is None:
        del self._event_handlers[event]
    else:
        # 注意：必须是同一个函数对象（或可比较的）
        self._event_handlers[event] = [
            cb for cb in self._event_handlers[event] if cb != callback
        ]
        # 如果列表空了，可以清理 key（可选）
        if not self._event_handlers[event]:
            del self._event_handlers[event]

    async def _emit(self, event: str, data: Dict[str, Any]) -> None:
        """
        触发事件（异步执行所有注册的回调）
        """
        if event in self._event_handlers:
            tasks = [cb(data) for cb in self._event_handlers[event] if asyncio.iscoroutinefunction(cb)]
            sync_cbs = [cb(data) for cb in self._event_handlers[event] if not asyncio.iscoroutinefunction(cb)]
            if tasks:
                await asyncio.gather(*tasks)
            # 同步回调直接执行（也可放入线程池）
            for cb in sync_cbs:
                cb(data)

    @abstractmethod
    async def update_memory(self, new_info: Dict[str, Any]) -> None:
        """
        子类必须实现如何更新记忆（例如写入短期/长期记忆）
        """
        pass