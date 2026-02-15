from typing import List, Dict, Any, Callable
from ..agents import BaseAgent, AgentResponse

class Tool:
    def __init__(self, name: str, func: Callable, description: str):
        self.name = name
        self.func = func
        self.description = description

    async def execute(self, **kwargs) -> str:
        if asyncio.iscoroutinefunction(self.func):
            return await self.func(**kwargs)
        return self.func(**kwargs)

class ReActAgent(BaseAgent):
    """
    ReAct (Reasoning + Acting) Agent Implementation.
    """
    def __init__(
        self,
        agent_id: str,
        core_memory: Dict[str, Any],
        memory_manager: Any,
        llm_client: Any,
        prompt_builder: Callable[[str, Dict], str],
        tools: List[Tool] = None,
        max_steps: int = 5
    ):
        super().__init__(agent_id, core_memory, memory_manager, llm_client, prompt_builder)
        self.tools = {t.name: t for t in tools} if tools else {}
        self.max_steps = max_steps

    async def step(self, user_input: str) -> AgentResponse:
        """
        Executes the ReAct loop: Thought -> Action -> Observation -> Thought...
        """
        context = await self._build_context(user_input)
        # Initialize conversation history for this step with the user input
        step_history = [f"User: {user_input}"]
        
        for _ in range(self.max_steps):
            # 1. Construct prompt with current history (including previous thoughts/actions)
            # Note: The prompt_builder needs to support appending the step_history
            current_prompt = self.prompt_builder(user_input, {**context, "step_history": "\n".join(step_history), "tools": self._get_tool_descriptions()})
            
            # 2. Generate Thought/Action
            response_text = await self.llm_client.generate(current_prompt)
            step_history.append(f"Assistant: {response_text}")
            
            # 3. Check for Final Answer
            if "Final Answer:" in response_text:
                final_answer = response_text.split("Final Answer:")[-1].strip()
                await self._emit('response_generated', {'response': final_answer})
                return AgentResponse(content=final_answer)
            
            # 4. Parse Action
            action_name, action_args = self._parse_action(response_text)
            
            if action_name and action_name in self.tools:
                # 5. Execute Action
                try:
                    observation = await self.tools[action_name].execute(**action_args)
                    step_history.append(f"Observation: {observation}")
                except Exception as e:
                    step_history.append(f"Observation: Error executing {action_name}: {str(e)}")
            else:
                 # If no valid action found or tool missing, treat as just a thought or ask for clarification
                 if not action_name:
                     # Assume the model is just thinking or chatting without tools
                     pass 
                 else:
                    step_history.append(f"Observation: Tool '{action_name}' not found.")

        # Fallback if max steps reached
        return AgentResponse(content="I could not complete the task within the step limit.")

    def _get_tool_descriptions(self) -> str:
        return "\n".join([f"- {t.name}: {t.description}" for t in self.tools.values()])

    def _parse_action(self, text: str):
        # Simple regex parsing (mock implementation)
        # Expected format: Action: tool_name({"arg": "value"})
        import re
        match = re.search(r"Action:\s*(\w+)\((.*)\)", text)
        if match:
            name = match.group(1)
            args_str = match.group(2)
            try:
                # WARNING: eval is unsafe, use json.loads in production with strict formatting
                # For this snippet, we'll assume a simpler parsing or safe eval
                args = eval(f"dict({args_str})") 
                return name, args
            except:
                return name, {}
        return None, None
