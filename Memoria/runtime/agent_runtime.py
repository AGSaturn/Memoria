# runtime/agent_runtime.py
class AgentRuntime:
    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}
        self._lock = asyncio.Lock()

    async def create_agent(self, agent_id: str, config: dict) -> BaseAgent:
        async with self._lock:
            if agent_id in self._agents:
                return self._agents[agent_id]
            
            # 创建依赖（全部基于 API，无本地模型）
            llm_client = create_llm_client(**config["llm"])
            memory_manager = SQLiteMemoryManager()
            await memory_manager.set_core_memory(agent_id, config["core_memory"])
            
            agent = CompanionAgent(
                agent_id=agent_id,
                core_memory=config["core_memory"],
                memory_manager=memory_manager,
                llm_client=llm_client,
                prompt_builder=...  # 你的 build_prompt 封装
            )
            self._agents[agent_id] = agent
            return agent

    async def remove_agent(self, agent_id: str):
        async with self._lock:
            agent = self._agents.pop(agent_id, None)
            if agent:
                # 清理短期记忆（长期记忆已在 DB 中）
                agent.memory_manager._short_term_cache.pop(agent_id, None)