# llm/factory.py
from typing import Literal
from .openai_client import OpenAIClient
from .ollama_client import OllamaClient
#目前只支持openai，未来会进行拓展
def create_llm_client(
    backend: Literal["openai"],
    **kwargs
) -> LLMClient:
    if backend == "openai":
        return OpenAIClient(**kwargs)
    else:
        raise ValueError(f"Unsupported LLM backend: {backend}")