from __future__ import annotations

import base64
import json
from collections.abc import Callable, Mapping
from contextlib import AbstractContextManager
from dataclasses import dataclass
from http.client import HTTPResponse
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from pydantic import SecretStr

from app.config.settings import Settings
from app.model_gateway.errors import ModelUnavailableError
from app.model_gateway.gateway import ModelGateway, ModelResponse, UnavailableModelGateway

# This FPT account exposes VADS aliases directly. Deployments with different
# catalog IDs can override individual aliases through VADS_FPT_AI_MODEL_MAP.
DEFAULT_FPT_MODEL_MAP = {"Gemma-3-27B": "gemma-3-27b-it"}

UrlOpen = Callable[..., AbstractContextManager[HTTPResponse]]


@dataclass(frozen=True, slots=True)
class FptAiGatewayConfig:
    api_key: SecretStr
    base_url: str = "https://mkp-api.fptcloud.com"
    chat_completions_path: str = "/v1/chat/completions"
    models_path: str = "/v1/models"
    model_map: Mapping[str, str] | None = None
    max_tokens: int = 4096
    temperature: float = 0
    allow_private_data: bool = False

    def __post_init__(self) -> None:
        parsed = urlparse(self.base_url)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("FPT AI base URL must be an absolute HTTPS URL")
        for path in (self.chat_completions_path, self.models_path):
            if not path.startswith("/"):
                raise ValueError("FPT AI API paths must start with '/'")


class FptAiModelGateway(ModelGateway):
    """FPT AI Marketplace adapter using its OpenAI-compatible HTTP protocol.

    This adapter does not import or call the OpenAI SDK/service. Internal VADS
    aliases remain provider-neutral and are resolved at the adapter boundary.
    """

    def __init__(
        self,
        config: FptAiGatewayConfig,
        *,
        transport: UrlOpen = urlopen,
    ) -> None:
        super().__init__()
        self.config = config
        self.transport = transport
        self.model_map = {**DEFAULT_FPT_MODEL_MAP, **dict(config.model_map or {})}

    def generate_text(
        self,
        *,
        model_alias: str,
        prompt: str,
        timeout_seconds: int = 90,
        metadata: Mapping[str, Any] | None = None,
    ) -> ModelResponse:
        provider_model = self._resolve_model(
            model_alias,
            private_request=bool(metadata and metadata.get("private")),
        )
        payload = {
            "model": provider_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "stream": False,
        }
        return self._completion(
            model_alias=model_alias,
            provider_model=provider_model,
            payload=payload,
            timeout_seconds=timeout_seconds,
        )

    def analyze_image(
        self,
        *,
        model_alias: str,
        prompt: str,
        image: bytes,
        mime_type: str,
        timeout_seconds: int = 90,
        metadata: Mapping[str, Any] | None = None,
    ) -> ModelResponse:
        if not mime_type.startswith("image/"):
            raise ValueError("mime_type must be an image media type")
        provider_model = self._resolve_model(
            model_alias,
            private_request=bool(metadata and metadata.get("private")),
        )
        encoded = base64.b64encode(image).decode("ascii")
        payload = {
            "model": provider_model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime_type};base64,{encoded}"},
                        },
                    ],
                }
            ],
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "stream": False,
        }
        return self._completion(
            model_alias=model_alias,
            provider_model=provider_model,
            payload=payload,
            timeout_seconds=timeout_seconds,
        )

    def health_check(self, model_alias: str) -> bool:
        try:
            provider_model = self._resolve_model(model_alias)
            payload = self._request_json(
                "GET",
                self.config.models_path,
                timeout_seconds=10,
            )
            models = payload.get("data")
            if not isinstance(models, list):
                return True
            available = {
                item.get("id") for item in models if isinstance(item, dict) and item.get("id")
            }
            return not available or provider_model in available
        except (ModelUnavailableError, ValueError):
            return False

    def _completion(
        self,
        *,
        model_alias: str,
        provider_model: str,
        payload: dict[str, Any],
        timeout_seconds: int,
    ) -> ModelResponse:
        response = self._request_json(
            "POST",
            self.config.chat_completions_path,
            payload=payload,
            timeout_seconds=timeout_seconds,
            model_alias=model_alias,
        )
        try:
            choice = response["choices"][0]
            content = choice["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ModelUnavailableError(
                model_alias,
                "FPT AI returned an invalid chat completion response",
            ) from exc
        if not isinstance(content, str) or not content.strip():
            raise ModelUnavailableError(model_alias, "FPT AI returned an empty response")
        usage = response.get("usage") if isinstance(response.get("usage"), dict) else {}
        return ModelResponse(
            modelAlias=model_alias,
            content=content,
            promptTokens=usage.get("prompt_tokens"),
            completionTokens=usage.get("completion_tokens"),
            providerRequestId=response.get("id"),
            rawMetadata={
                "provider": "FPT_AI",
                "providerModel": provider_model,
                "finishReason": choice.get("finish_reason"),
            },
        )

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        timeout_seconds: int,
        model_alias: str = "FPT_AI",
    ) -> dict[str, Any]:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload else None
        request = Request(
            self._url(path),
            data=body,
            method=method,
            headers={
                "Authorization": f"Bearer {self.config.api_key.get_secret_value()}",
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "VADS/0.1 FPT-AI-Gateway",
            },
        )
        try:
            with self.transport(request, timeout=timeout_seconds) as response:
                raw = response.read()
        except HTTPError as exc:
            detail = self._safe_http_error(exc)
            raise ModelUnavailableError(
                model_alias,
                f"FPT AI request failed with HTTP {exc.code}: {detail}",
            ) from exc
        except (URLError, TimeoutError) as exc:
            raise ModelUnavailableError(model_alias, "FPT AI endpoint is unavailable") from exc
        try:
            decoded = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ModelUnavailableError(model_alias, "FPT AI returned invalid JSON") from exc
        if not isinstance(decoded, dict):
            raise ModelUnavailableError(model_alias, "FPT AI returned an invalid payload")
        return decoded

    def _resolve_model(self, model_alias: str, *, private_request: bool = False) -> str:
        if private_request and not self.config.allow_private_data:
            raise ModelUnavailableError(
                model_alias,
                "Private processing is disabled for the public FPT AI endpoint",
            )
        return self.model_map.get(model_alias, model_alias)

    def _url(self, path: str) -> str:
        return urljoin(f"{self.config.base_url.rstrip('/')}/", path.lstrip("/"))

    @staticmethod
    def _safe_http_error(error: HTTPError) -> str:
        if error.code in {401, 403}:
            return "authentication was rejected"
        if error.code == 429:
            return "rate limit or account quota exceeded"
        return "provider rejected the request"


def build_fpt_ai_gateway(settings: Settings) -> ModelGateway:
    if not settings.fpt_ai_enabled or settings.fpt_ai_api_key is None:
        return UnavailableModelGateway()
    return FptAiModelGateway(
        FptAiGatewayConfig(
            api_key=settings.fpt_ai_api_key,
            base_url=settings.fpt_ai_base_url,
            chat_completions_path=settings.fpt_ai_chat_completions_path,
            models_path=settings.fpt_ai_models_path,
            model_map=settings.fpt_ai_model_map,
            max_tokens=settings.fpt_ai_max_tokens,
            temperature=settings.fpt_ai_temperature,
            allow_private_data=settings.fpt_ai_allow_private_data,
        )
    )
