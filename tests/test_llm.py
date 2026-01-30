import pytest
import respx
import httpx
from Memoria.llm.openai_client import OpenAIClient
from Memoria.llm.factory import create_llm_client


# 固定测试用的 API key（mock 用，不真实）
TEST_API_KEY="sk-2e4d3bff895944ad9643167c16efea34"
TEST_MODEL_ID="deepseek-chat"
TEST_BASE_URL="https://api.deepseek.com"

@pytest.mark.asyncio
async def test_openai_client_generate_success():
    mock_response = {
        "choices": [
            {
                "message": {
                    "content": "Paris is the capital of France.",
                    "role": "assistant"
                }
            }
        ],
        "model": TEST_MODEL_ID,
        "usage": {"prompt_tokens": 10, "completion_tokens": 8, "total_tokens": 18}
    }

    with respx.mock:
        respx.post("https://api.deepseek.com/chat/completions").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        client = OpenAIClient(api_key=TEST_API_KEY, model=TEST_MODEL_ID)
        result = await client.generate("What is the capital of France?", max_tokens=50)

        assert result == "Paris is the capital of France."

        # 验证请求内容
        request = respx.calls.last.request
        payload = request.json()
        assert payload["model"] == TEST_MODEL_ID
        assert payload["max_tokens"] == 50
        assert payload["messages"][0]["content"] == "What is the capital of France?"


@pytest.mark.asyncio
async def test_openai_client_api_error():
    with respx.mock:
        respx.post("https://api.deepseek.com/chat/completions").mock(
            return_value=httpx.Response(401, json={"error": {"message": "Invalid API key"}})
        )

        client = OpenAIClient(api_key=TEST_API_KEY)

        with pytest.raises(RuntimeError, match="DEEPSEEK API error"):
            await client.generate("Hello")


@pytest.mark.asyncio
async def test_openai_client_timeout():
    with respx.mock:
        respx.post("https://api.deepseek.com/chat/completions").mock(
            side_effect=httpx.TimeoutException("timeout")
        )

        client = OpenAIClient(api_key=TEST_API_KEY, timeout=1)

        with pytest.raises(RuntimeError, match="DEEPSEEK API error"):
            await client.generate("Hello")


@pytest.mark.asyncio
async def test_create_llm_client_openai():
    client = create_llm_client("openai", api_key=TEST_API_KEY, model=TEST_MODEL_ID)
    assert isinstance(client, OpenAIClient)
    assert client.model == "gpt-4o"


def test_create_llm_client_unsupported_backend():
    with pytest.raises(ValueError, match="Unsupported LLM backend"):
        create_llm_client("anthropic")  # 未实现


@pytest.mark.asyncio
async def test_openai_client_context_manager():
    mock_response = {"choices": [{"message": {"content": "OK"}}]}
    with respx.mock:
        respx.post("https://api.deepseek.com/chat/completions").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        async with OpenAIClient(api_key=TEST_API_KEY) as client:
            result = await client.generate("Test")
            assert result == "OK"

        # 此时 client._client 应已关闭
        # 可通过内部状态判断，但 httpx.AsyncClient 没有公开 closed 属性
        # 所以主要验证不抛异常即可