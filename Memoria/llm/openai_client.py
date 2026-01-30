# llm/openai_client.py
import os
import httpx
from typing import Optional
from .base import LLMClient

class OpenAIClient(LLMClient):
    def __init__(
        self,
        api_key: str = None,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4-turbo",
        timeout: int = 60
    ):
        self.api_key = api_key 
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self._client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            timeout=httpx.Timeout(timeout, connect=10.0),
            limits=httpx.Limits(max_connections=20)  # 防止连接耗尽
        )

    async def generate(self, prompt: str, max_tokens: int = 512) -> str:
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.7,
            "stream": False
        }
        try:
            response = await self._client.post(
                f"{self.base_url}/chat/completions",
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            raise RuntimeError(f"OpenAI API error: {e}") from e

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._client.aclose()