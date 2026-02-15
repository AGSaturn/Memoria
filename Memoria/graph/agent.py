from typing import TypedDict, Annotated, List, Union
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.runnables import RunnableConfig
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import BaseTool

from ..memory.core_memory import CoreMemory

class AgentState(TypedDict):
    messages: List[BaseMessage]
    core_memory: CoreMemory

def create_memoria_agent(llm, tools: List[BaseTool], core_memory: CoreMemory):
    """
    Creates a LangGraph agent that mimics Letta's architecture.
    """
    
    # 1. Define Nodes
    
    async def chatbot(state: AgentState, config: RunnableConfig):
        """
        The main chatbot node. It constructs the prompt with Core Memory and calls the LLM.
        """
        messages = state["messages"]
        current_core_memory = state["core_memory"]
        
        # Construct System Prompt dynamically from Core Memory
        system_prompt = (
            "You are Memoria, an AI partner with long-term memory.\n"
            "You have access to a Core Memory which defines who you are and who you are talking to.\n"
            "You can edit this memory using the provided tools (core_memory_append, core_memory_replace).\n"
            "You also have access to Archival Memory to search for past events.\n\n"
            f"{current_core_memory.to_prompt_string()}\n\n"
            "Always check your memory before answering if you are unsure.\n"
            "If you learn something new and important about the user or yourself, update your Core Memory immediately."
        )
        
        # Prepend System Message
        # We need to be careful not to duplicate system messages if they are already in history
        # For simplicity, we just filter out old system messages and prepend the new one
        filtered_messages = [m for m in messages if not isinstance(m, SystemMessage)]
        prompt_messages = [SystemMessage(content=system_prompt)] + filtered_messages
        
        # Bind tools
        llm_with_tools = llm.bind_tools(tools)
        
        response = await llm_with_tools.ainvoke(prompt_messages, config)
        return {"messages": [response]}

    # ToolNode automatically handles tool execution
    tool_node = ToolNode(tools)

    # 2. Build Graph
    graph_builder = StateGraph(AgentState)
    
    graph_builder.add_node("chatbot", chatbot)
    graph_builder.add_node("tools", tool_node)
    
    graph_builder.set_entry_point("chatbot")
    
    # 3. Define Edges
    graph_builder.add_conditional_edges(
        "chatbot",
        tools_condition,
    )
    graph_builder.add_edge("tools", "chatbot")
    
    return graph_builder.compile()
