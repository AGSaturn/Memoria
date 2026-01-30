# prompt/builder.py

from typing import List, Union, Dict, Any, Optional
from jinja2 import Template, Environment, StrictUndefined
from .templates import DEFAULT_ROLEPLAY_TEMPLATE
from memory.models import Message  # 假设 Message 在 memory/models.py 中定义

def build_prompt(
    core: Dict[str, Any],
    long_mem: List[str],
    short_hist: List[Message],
    user_input: str,
    template: Union[str, Template] = DEFAULT_ROLEPLAY_TEMPLATE
) -> str:
    """
    构建 LLM 提示词（Prompt），支持自定义 Jinja2 模板。
    
    Args:
        core: 核心记忆字典，如 {"name": "Sarah", "personality": "温柔"}
        long_mem: 长期记忆摘要列表，如 ["上周去了图书馆", "喜欢喝美式咖啡"]
        short_hist: 短期对话历史（Message 对象列表）
        user_input: 当前用户输入
        template: Jinja2 模板字符串或 Template 对象
    
    Returns:
        渲染后的完整 prompt 字符串
    
    Raises:
        jinja2.UndefinedError: 模板中使用了未提供的变量
    """
    # 确保模板是 Template 对象
    if isinstance(template, str):
        # 使用 StrictUndefined：如果模板用了未传入的变量，立即报错（避免静默失败）
        env = Environment(undefined=StrictUndefined)
        tmpl = env.from_string(template)
    else:
        tmpl = template

    # 准备上下文数据
    context = {
        "core": core,
        "long_mem": long_mem,
        "short_hist": short_hist,
        "user_input": user_input
    }

    # 渲染模板
    return tmpl.render(context).strip()