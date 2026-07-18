from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request

import pytest
from pydantic import SecretStr

from app.chat.adapters.model_gateway import ModelGatewayChatAdapter
from app.model_gateway.errors import ModelRateLimitError, ModelUnavailableError
from app.model_gateway.fpt_ai import FptAiGatewayConfig, FptAiModelGateway
from app.model_gateway.gateway import MetadataModelGateway
from app.model_gateway.registry import build_default_registry
from app.model_gateway.router import ModelRouter
from app.model_gateway.schemas import RoutingRequest, TaskType


class FakeResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        del args

    def read(self) -> bytes:
        return json.dumps(self.payload).encode()


class RecordingTransport:
    def __init__(self, responses: list[dict[str, Any]]) -> None:
        self.responses = responses
        self.requests: list[tuple[Request, int]] = []

    def __call__(self, request: Request, *, timeout: int) -> FakeResponse:
        self.requests.append((request, timeout))
        return FakeResponse(self.responses.pop(0))


def gateway(transport: RecordingTransport, **overrides: Any) -> FptAiModelGateway:
    return FptAiModelGateway(
        FptAiGatewayConfig(
            api_key=SecretStr("test-fpt-key"),
            **overrides,
        ),
        transport=transport,
    )


def completion_payload(content: str = "Kết quả") -> dict[str, Any]:
    return {
        "id": "fpt-request-1",
        "choices": [
            {
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 12, "completion_tokens": 4},
    }


def test_fpt_gateway_maps_alias_and_parses_completion() -> None:
    transport = RecordingTransport([completion_payload()])
    adapter = gateway(transport)

    result = adapter.generate_text(
        model_alias="DeepSeek-V4-Flash",
        prompt="Tóm tắt tài liệu",
        timeout_seconds=15,
    )

    request, timeout = transport.requests[0]
    body = json.loads(request.data or b"{}")
    assert request.full_url == "https://mkp-api.fptcloud.com/v1/chat/completions"
    assert request.get_header("Authorization") == "Bearer test-fpt-key"
    assert body["model"] == "DeepSeek-V4-Flash"
    assert body["messages"][0]["content"] == "Tóm tắt tài liệu"
    assert timeout == 15
    assert result.content == "Kết quả"
    assert result.provider_request_id == "fpt-request-1"
    assert result.raw_metadata["provider"] == "FPT_AI"


def test_fpt_gateway_supports_vision_payload() -> None:
    transport = RecordingTransport([completion_payload("Trang hợp lệ")])
    adapter = gateway(transport, model_map={"vision": "fpt/vision-model"})

    result = adapter.analyze_image(
        model_alias="vision",
        prompt="Kiểm tra trang",
        image=b"image-bytes",
        mime_type="image/png",
    )

    body = json.loads(transport.requests[0][0].data or b"{}")
    image_url = body["messages"][0]["content"][1]["image_url"]["url"]
    assert image_url.startswith("data:image/png;base64,")
    assert result.content == "Trang hợp lệ"


def test_fpt_gateway_health_check_uses_model_catalog() -> None:
    transport = RecordingTransport([{"data": [{"id": "GLM-5.2"}, {"id": "DeepSeek-V4-Flash"}]}])

    assert gateway(transport).health_check("GLM-5.2") is True
    assert transport.requests[0][0].get_method() == "GET"


def test_fpt_gateway_rejects_private_processing_by_default() -> None:
    transport = RecordingTransport([completion_payload()])
    adapter = gateway(transport)

    assert adapter.generate_text(model_alias="gpt-oss-120b", prompt="Dữ liệu thường").content

    with pytest.raises(ModelUnavailableError, match="Private processing is disabled"):
        MetadataModelGateway(adapter, {"private": True}).generate_text(
            model_alias="GLM-5.2", prompt="Dữ liệu mật"
        )


def test_private_routing_never_falls_back_to_public_model() -> None:
    decision = ModelRouter(build_default_registry()).route(
        RoutingRequest(taskType=TaskType.DOCUMENT_SUMMARY, requirePrivate=True)
    )

    assert decision.primary_model == "gpt-oss-120b"
    assert decision.fallback_model == "Qwen3.6-27B"


def test_fpt_gateway_redacts_authentication_failure() -> None:
    def reject(request: Request, *, timeout: int) -> FakeResponse:
        del timeout
        raise HTTPError(request.full_url, 401, "bad test-fpt-key", {}, None)

    adapter = FptAiModelGateway(
        FptAiGatewayConfig(api_key=SecretStr("test-fpt-key")),
        transport=reject,
    )

    with pytest.raises(ModelUnavailableError) as error:
        adapter.generate_text(model_alias="GLM-5.2", prompt="test")
    assert "test-fpt-key" not in str(error.value)
    assert "authentication was rejected" in str(error.value)


def test_fpt_gateway_exposes_rate_limit_as_non_retryable_error() -> None:
    def reject(request: Request, *, timeout: int) -> FakeResponse:
        del timeout
        raise HTTPError(request.full_url, 429, "rate limited", {"Retry-After": "30"}, None)

    adapter = FptAiModelGateway(
        FptAiGatewayConfig(api_key=SecretStr("test-fpt-key")),
        transport=reject,
    )

    with pytest.raises(ModelRateLimitError) as error:
        adapter.generate_text(model_alias="GLM-5.2", prompt="test")
    assert error.value.retry_after_seconds == 30


def test_chat_adapter_uses_shared_fpt_gateway() -> None:
    transport = RecordingTransport([completion_payload("Câu trả lời có nguồn")])
    adapter = ModelGatewayChatAdapter(gateway(transport))

    answer = adapter.generate(
        model_alias="DeepSeek-V4-Flash",
        prompt="Thời hạn là bao lâu?",
        context=[{"content": "Thời hạn là 30 ngày."}],
        private=False,
    )

    prompt = json.loads(transport.requests[0][0].data or b"{}")["messages"][0]["content"]
    assert answer == "Câu trả lời có nguồn"
    assert "Thời hạn là 30 ngày." in prompt
