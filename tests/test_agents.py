import json

import httpx
import pytest

from docagent.agents import ChatModel, LLMAgents, ModelConfig, ModelError, parse_json_object, validate_answer


def test_invalid_model_output_is_not_silently_accepted():
    with pytest.raises(ModelError):
        parse_json_object('[]')
    with pytest.raises(ModelError):
        validate_answer({"answer": "x", "status": "answered", "evidence": [{"id": "invented"}]})
    with pytest.raises(ModelError):
        validate_answer({"answer": "x", "status": "answered", "evidence": [
            {"id": "x", "doc_id": "a", "page": True, "section_id": "s1", "text": "x", "source_type": "text"}]})


async def test_credentials_are_only_in_header_and_errors_are_sanitized():
    secret = "unit-test-secret"
    assert secret not in repr(ModelConfig(api_key=secret))
    async def handler(request):
        assert request.headers["Authorization"] == "Bearer " + secret
        assert secret not in request.content.decode()
        return httpx.Response(401, text="provider echoed " + secret)
    async with ChatModel(ModelConfig(api_key=secret), httpx.MockTransport(handler)) as model:
        with pytest.raises(ModelError) as failure:
            await model.complete([{"role": "user", "content": "Return JSON"}])
        assert secret not in str(failure.value)


async def test_usage_comes_from_actual_response_and_reasoning_not_persisted():
    async def handler(request):
        data = json.loads(request.content)
        assert data["thinking"]["type"] == "disabled"
        return httpx.Response(200, json={"model": "actual-model", "usage": {"prompt_tokens": 7, "completion_tokens": 3},
            "choices": [{"message": {"role": "assistant", "content": '{"answer":"ok"}'}}]})
    async with ChatModel(ModelConfig(api_key="test"), httpx.MockTransport(handler)) as model:
        response = await model.complete([{"role": "user", "content": "JSON"}])
        assert response["content"] == '{"answer":"ok"}'
        assert model.usage == {"requests": 1, "prompt_tokens": 7, "completion_tokens": 3, "api_retries": 0}
        assert model.returned_models == {"actual-model"}


async def test_transient_error_retries_but_auth_failure_does_not():
    calls = 0
    async def handler(request):
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(503)
        return httpx.Response(200, json={"choices": [{"message": {"content": "{}"}}]})
    async with ChatModel(ModelConfig(api_key="test"), httpx.MockTransport(handler)) as model:
        await model.complete([])
        assert calls == 2
        assert model.usage["api_retries"] == 1


async def test_multiple_image_tools_preserve_required_message_order():
    class ImageGateway:
        async def list_tools(self):
            return [{"name": "get_image", "inputSchema": {"type": "object"}}]

        async def call(self, name, arguments):
            return {"evidence": [], "images": [{"data": "aGVsbG8=", "mimeType": "image/png"}]}

    count = 0

    async def handler(request):
        nonlocal count
        count += 1
        if count == 1:
            return httpx.Response(200, json={"choices": [{"message": {"tool_calls": [
                {"id": f"call{i}", "type": "function", "function": {"name": "get_image",
                 "arguments": json.dumps({"doc_id": "demo", "image_id": str(i)})}}
                for i in (1, 2)]}}]})
        sent = json.loads(request.content)["messages"]
        assert [m["role"] for m in sent] == ["system", "user", "assistant", "tool", "tool", "user", "user"]
        return httpx.Response(200, json={"choices": [{"message": {
            "content": '{"answer":"unknown","status":"insufficient","evidence":[]}'}}]})

    async with ChatModel(ModelConfig(api_key="test", vision=True), httpx.MockTransport(handler)) as model:
        result = await LLMAgents(model).actor("Read both images", "demo", ImageGateway(), [])
        assert result["status"] == "insufficient"
        assert count == 2
