# memory/processor/default_processor.py
import numpy as np
import pickle
from openai import AsyncOpenAI


class DefaultProcessor:
    def __init__(self, embed_model: str = "deepseek-embedding", llm_client: AsyncOpenAI = None):
        self.embed_model = embed_model
        self.llm = llm_client

    async def embed(self, text: str) -> np.ndarray:
        # TODO: replace with DeepSeek API call or local ONNX model
        # For MVP, mock or use OpenAI-compatible endpoint
        response = await self.llm.embeddings.create(input=text, model=self.embed_model)
        return np.array(response.data[0].embedding)

    async def summarize(self, texts: List[str]) -> str:
        prompt = "Summarize the following user experiences into one concise fact:\n" + "\n".join(texts)
        response = await self.llm.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()