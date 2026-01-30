# tests/test_openai_client.py
import os
from unittest.mock import patch
import pytest
import respx
from httpx import Response

from llm.openai_client import OpenAIClient


@pytest.mark.asyncio
async def test_complete_success():
    """测试正常调用 OpenAI API 并返回结果"""
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
        client = OpenAIClient()

    mock_response = {
        "choices": [
            {
                "message": {
                    "content": "  Hello from OpenAI!  "
                }
            }
        ]
    }

    with respx.mock:
        route = respx.post("https://api.openai.com/v1/chat/completions")
        route.return_value = Response(200, json=mock_response)

        result = await client.complete("Hello", max_tokens=100)

        # 验证返回内容被 .strip()
        assert result == "Hello from OpenAI!"

        # 验证请求参数
        assert route.called
        request = route.calls[0].request
        payload = request.json()
        assert payload["model"] == "gpt-4-turbo"
        assert payload["messages"] == [{"role": "user", "content": "Hello"}]
        assert payload["max_tokens"] == 100
        assert payload["temperature"] == 0.7
        assert payload["stream"] is False

        # 验证 headers
        assert request.headers["authorization"] == "Bearer test-key"


@pytest.mark.asyncio
async def test_complete_http_error():
    """测试 HTTP 错误（如 500）被正确包装为 RuntimeError"""
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
        client = OpenAIClient()

    with respx.mock:
        respx.post("https://api.openai.com/v1/chat/completions").return_value = Response(
            500, text="Internal Server Error"
        )

        with pytest.raises(RuntimeError, match="OpenAI API error"):
            await client.complete("test")


@pytest.mark.asyncio
async def test_complete_network_timeout():
    """测试超时等网络异常被包装为 RuntimeError"""
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
        client = OpenAIClient(timeout=1)

    with respx.mock:
        respx.post("https://api.openai.com/v1/chat/completions").mock(
            side_effect=TimeoutError("timeout")
        )

        with pytest.raises(RuntimeError, match="OpenAI API error"):
            await client.complete("test")


@pytest.mark.asyncio
async def test_missing_api_key():
    """测试未提供 API key 时抛出 ValueError"""
    with patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
        with pytest.raises(ValueError, match="OpenAI API key is required"):
            OpenAIClient(api_key=None)


@pytest.mark.asyncio
async def test_base_url_stripped():
    """测试 base_url 的尾部空格和斜杠被正确清理"""
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
        client = OpenAIClient(base_url="https://api.openai.com/v1/  ")

    assert client.base_url == "https://api.openai.com/v1"

    with respx.mock:
        route = respx.post("https://api.openai.com/v1/chat/completions")
        route.return_value = Response(200, json={"choices": [{"message": {"content": "ok"}}]})

        await client.complete("test")
        assert route.called


@pytest.mark.asyncio
async def test_async_context_manager():
    """测试 async with 能正确关闭 httpx 客户端"""
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
        async with OpenAIClient() as client:
            assert not client._client.is_closed
        # 退出后应已关闭
        assert client._client.is_closed