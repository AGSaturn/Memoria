from typing import Dict, Optional
from pydantic import BaseModel, Field

class CoreMemory(BaseModel):
    """
    Core Memory block similar to Letta's concept.
    It holds the 'persona' (who I am) and 'human' (who I am talking to).
    These blocks are injected into the system prompt and can be edited by the agent.
    """
    persona: str = Field(default="", description="Description of the agent's persona.")
    human: str = Field(default="", description="Description of the human user.")

    def update_block(self, block_name: str, value: str):
        if block_name == "persona":
            self.persona = value
        elif block_name == "human":
            self.human = value
        else:
            raise ValueError(f"Unknown block name: {block_name}")

    def append_to_block(self, block_name: str, value: str):
        if block_name == "persona":
            self.persona += "\n" + value
        elif block_name == "human":
            self.human += "\n" + value
        else:
            raise ValueError(f"Unknown block name: {block_name}")

    def to_prompt_string(self) -> str:
        return (
            f"=== Core Memory (You can edit this) ===\n"
            f"[Persona]\n{self.persona}\n\n"
            f"[Human]\n{self.human}\n"
            f"======================================="
        )
