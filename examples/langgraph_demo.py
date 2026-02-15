import asyncio
import os
import logging
from typing import List

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from Memoria.memory.core_memory import CoreMemory
from Memoria.tools.memory_tools import create_memory_tools
from Memoria.tools.archival_tools import create_archival_tools
from Memoria.graph.agent import create_memoria_agent
from Memoria.memory.factory import MemoryFactory

# Configure logging to suppress noisy output if needed
logging.basicConfig(level=logging.INFO)

async def main():
    # 1. Setup
    print("Initializing Memoria Agent (LangGraph + Real DB version)...")
    
    # Check for API Key
    if "OPENAI_API_KEY" not in os.environ:
        print("Please set OPENAI_API_KEY environment variable.")
        return

    agent_id = "agent_001"
    
    # Initialize Core Memory
    core_memory = CoreMemory(
        persona="I am Memoria, a helpful AI assistant built with LangGraph. I remember everything you tell me.",
        human="The user is a developer exploring AI frameworks."
    )
    
    # Initialize Real Memory Manager
    # This will create 'memoria.db' in the current directory
    print("Connecting to Memory Database (memoria.db)...")
    # We pass the OpenAI client implicitly via LangChain or direct instantiation if needed.
    # For DefaultProcessor, we might need to pass an async client if we want embeddings.
    from openai import AsyncOpenAI
    openai_client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])
    
    memory_manager = MemoryFactory.create_manager(db_path="memoria.db", openai_client=openai_client)
    
    # Initialize Semantic Store (create tables)
    # Accessing internal stores directly for initialization is a bit hacky but works for demo
    await memory_manager.semantic_store.initialize()
    # EpisodicStore creates tables on insert if using default implementation, 
    # but let's check if we need explicit init. 
    # BaseEpisodicStore usually doesn't enforce init, but let's assume it's fine.
    
    # Create Tools
    mem_tools = create_memory_tools(core_memory)
    arch_tools = create_archival_tools(memory_manager, agent_id)
    all_tools = mem_tools + arch_tools
    
    # Initialize LLM
    llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
    
    # Create Agent Graph
    agent_executor = create_memoria_agent(llm, all_tools, core_memory)
    
    # 2. Run Interaction Loop
    print("\n=== Starting Conversation ===")
    print(f"Current Persona: {core_memory.persona}")
    print(f"Current Human: {core_memory.human}\n")
    print("Type 'exit' to quit.")
    
    messages = []
    
    while True:
        try:
            user_input = input("User: ")
        except EOFError:
            break
            
        if user_input.lower() in ["exit", "quit"]:
            break
            
        # Add user message to local history
        messages.append(HumanMessage(content=user_input))
        
        # Also store raw event to episodic memory (asynchronously)
        # In a real app, this might happen inside the graph or via a callback
        await memory_manager.add_event(agent_id, {"content": user_input, "role": "user"})
        
        # Invoke the graph
        initial_state = {"messages": messages, "core_memory": core_memory}
        config = {"configurable": {"thread_id": "1"}}
        
        print("Agent thinking...")
        async for event in agent_executor.astream(initial_state, config):
            for key, value in event.items():
                if key == "chatbot":
                    last_msg = value["messages"][-1]
                    print(f"Agent: {last_msg.content}")
                    messages.append(last_msg)
                    
                    # Store agent response to episodic memory
                    await memory_manager.add_event(agent_id, {"content": last_msg.content, "role": "assistant"})
                    
                elif key == "tools":
                    # Tool output is handled by LangGraph, but we can print status
                    pass
        
        # Print updated Core Memory if changed
        # (In a real CLI, we might only show diffs)
        # print(f"\n[Debug] Current Human Block: {core_memory.human}\n")

if __name__ == "__main__":
    asyncio.run(main())
