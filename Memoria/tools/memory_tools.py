from typing import List, Optional
from langchain_core.tools import tool
from .core_memory import CoreMemory
# Assuming we can reuse the existing MemoryManager logic or interface
# For this rewrite, we will mock/wrap the existing managers to be tool-compatible

class MemoryTools:
    def __init__(self, core_memory: CoreMemory):
        self.core_memory = core_memory

    @property
    def tools(self) -> List[any]:
        return [
            self.core_memory_append,
            self.core_memory_replace,
        ]

    @tool
    def core_memory_append(self, name: str, content: str) -> str:
        """
        Append content to a specific core memory block.
        Args:
            name: The name of the block to update (either 'persona' or 'human').
            content: The content to append to the block.
        """
        # Note: 'self' here is tricky with @tool decorator if not bound properly.
        # We will handle binding in the graph construction or use a closure.
        # For simplicity in this structure, we might need to define these differently.
        pass

# Redefine to handle stateful tools correctly
def create_memory_tools(core_memory: CoreMemory):
    
    @tool
    def core_memory_append(name: str, content: str):
        """
        Append content to a specific core memory block.
        Use this to add new details you learn about yourself (persona) or the user (human).
        Args:
            name: The name of the block to update (either 'persona' or 'human').
            content: The content to append to the block.
        """
        try:
            core_memory.append_to_block(name, content)
            return f"Successfully appended to {name}."
        except ValueError as e:
            return f"Error: {str(e)}"

    @tool
    def core_memory_replace(name: str, content: str):
        """
        Replace the content of a specific core memory block.
        Use this when you need to rewrite a section entirely (e.g. correcting a name).
        Args:
            name: The name of the block to update (either 'persona' or 'human').
            content: The new content for the block.
        """
        try:
            core_memory.update_block(name, content)
            return f"Successfully replaced {name}."
        except ValueError as e:
            return f"Error: {str(e)}"

    return [core_memory_append, core_memory_replace]
