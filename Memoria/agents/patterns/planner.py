from typing import List, Dict, Any, Callable
from ..agents import BaseAgent, AgentResponse
import asyncio

class PlannerAgent(BaseAgent):
    """
    Planner Agent: Decomposes a complex task into sub-tasks and delegates them.
    """
    def __init__(
        self,
        agent_id: str,
        core_memory: Dict[str, Any],
        memory_manager: Any,
        llm_client: Any,
        prompt_builder: Callable[[str, Dict], str],
        worker_agent: BaseAgent = None
    ):
        super().__init__(agent_id, core_memory, memory_manager, llm_client, prompt_builder)
        self.worker = worker_agent # The agent that executes the sub-tasks

    async def step(self, user_input: str) -> AgentResponse:
        context = await self._build_context(user_input)
        
        # 1. Generate Plan
        plan_prompt = f"Goal: {user_input}\nContext: {context}\nCreate a numbered list of steps to achieve this goal."
        plan_text = await self.llm_client.generate(plan_prompt)
        
        # Parse plan (simple split by newline)
        steps = [line.strip() for line in plan_text.split('\n') if line.strip() and line[0].isdigit()]
        
        results = []
        for step_desc in steps:
            # 2. Execute each step using the worker agent
            # We assume the worker agent can handle the step description directly
            if self.worker:
                response = await self.worker.step(step_desc)
                results.append(f"Step '{step_desc}' Result: {response.content}")
            else:
                # If no worker, the planner itself tries to solve it (or just mocks it)
                results.append(f"Step '{step_desc}' Planned (No worker to execute)")

        final_summary = "\n".join(results)
        
        # 3. Summarize final result
        summary_prompt = f"Goal: {user_input}\nExecution Results:\n{final_summary}\nProvide a final answer to the user."
        final_response = await self.llm_client.generate(summary_prompt)
        
        await self._emit('response_generated', {'response': final_response})
        return AgentResponse(content=final_response)
