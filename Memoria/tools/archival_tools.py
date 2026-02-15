from langchain_core.tools import tool
from typing import List

def create_archival_tools(memory_manager, agent_id: str):
    
    @tool
    async def archival_memory_insert(content: str):
        """
        Save a piece of information to archival memory.
        Use this to store important facts, events, or knowledge that should be remembered long-term.
        Args:
            content: The content to store.
        """
        await memory_manager.add_semantic_memory(agent_id, content)
        return "Successfully saved to archival memory."

    @tool
    async def archival_memory_search(query: str, limit: int = 5):
        """
        Search archival memory for information.
        Use this to retrieve past conversations, facts, or knowledge relevant to the current context.
        Args:
            query: The search query string.
            limit: The maximum number of results to return.
        """
        # search_memories performs hybrid search (episodic + semantic)
        # If we only want semantic/archival, we might need a specific method, 
        # but usually getting everything is better for context.
        # Let's use search_memories for now.
        results = await memory_manager.search_memories(agent_id, query)
        
        if not results:
            return "No results found in archival memory."

        formatted_results = []
        for r in results[:limit]:
            # Try to format based on type if available
            rtype = r.get("type", "unknown")
            content = r.get("content", "")
            timestamp = r.get("timestamp", "")
            formatted_results.append(f"[{rtype} | {timestamp}] {content}")
            
        return "Archival Memory Search Results:\n" + "\n".join(formatted_results)

    return [archival_memory_insert, archival_memory_search]
