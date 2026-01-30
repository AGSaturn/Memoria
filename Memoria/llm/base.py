# llm/base.py
from abc import ABC, abstractmethod

class LLMClient(ABC):
    """
    统一 LLM 接口，屏蔽底层模型差异。
    所有实现必须是线程安全且支持异步调用。
    """
    @abstractmethod
    async def generate(self, prompt: str, max_tokens: int = 512) -> str:
        """
        向 LLM 发送提示并返回生成文本。
        
        Args:
            prompt: 输入提示（纯文本）
            max_tokens: 最大生成 token 数
            
        Returns:
            生成的文本（不含 prompt）
            
        Raises:
            LLMError: 网络错误、超时、模型拒绝等
        """
        pass