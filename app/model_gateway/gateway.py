from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping
from typing import Any, TypeVar

from pydantic import BaseModel, Field, ValidationError

from app.common.contracts import APIModel
from app.model_gateway.errors import ModelUnavailableError, StructuredOutputError

StructuredT = TypeVar("StructuredT", bound=BaseModel)


class ModelResponse(APIModel):
    model_alias: str
    content: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    provider_request_id: str | None = None
    raw_metadata: dict[str, Any] = Field(default_factory=dict)


class StructuredOutputValidator:
    """Strictly parses JSON and validates it against a Pydantic schema."""

    _fenced_json = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL | re.I)

    def validate(
        self,
        raw_output: str | bytes | Mapping[str, Any] | BaseModel,
        output_schema: type[StructuredT],
        *,
        model_alias: str,
    ) -> StructuredT:
        try:
            if isinstance(raw_output, output_schema):
                return raw_output
            if isinstance(raw_output, BaseModel):
                return output_schema.model_validate(raw_output.model_dump())
            if isinstance(raw_output, Mapping):
                return output_schema.model_validate(dict(raw_output))
            if isinstance(raw_output, bytes):
                raw_output = raw_output.decode("utf-8")
            text = raw_output.strip()
            fenced = self._fenced_json.match(text)
            if fenced:
                text = fenced.group(1)
            payload = json.loads(text)
            return output_schema.model_validate(payload)
        except (UnicodeDecodeError, json.JSONDecodeError, ValidationError, TypeError) as exc:
            raise StructuredOutputError(model_alias, str(exc), raw_output) from exc


class ModelGateway(ABC):
    """Provider-neutral synchronous gateway used by the orchestration engine."""

    def __init__(self, validator: StructuredOutputValidator | None = None) -> None:
        self.validator = validator or StructuredOutputValidator()

    @abstractmethod
    def generate_text(
        self,
        *,
        model_alias: str,
        prompt: str,
        timeout_seconds: int = 90,
        metadata: Mapping[str, Any] | None = None,
    ) -> ModelResponse:
        raise NotImplementedError

    def generate_structured(
        self,
        *,
        model_alias: str,
        prompt: str,
        output_schema: type[StructuredT],
        timeout_seconds: int = 90,
        metadata: Mapping[str, Any] | None = None,
    ) -> StructuredT:
        response = self.generate_text(
            model_alias=model_alias,
            prompt=prompt,
            timeout_seconds=timeout_seconds,
            metadata=metadata,
        )
        return self.validator.validate(
            response.content,
            output_schema,
            model_alias=model_alias,
        )

    @abstractmethod
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
        raise NotImplementedError

    @abstractmethod
    def health_check(self, model_alias: str) -> bool:
        raise NotImplementedError


GatewayHandler = Callable[[str, str, dict[str, Any]], object]


class CallableModelGateway(ModelGateway):
    """Adapter useful for provider SDK bindings and deterministic tests."""

    def __init__(
        self,
        handler: GatewayHandler,
        *,
        health_handler: Callable[[str], bool] | None = None,
    ) -> None:
        super().__init__()
        self.handler = handler
        self.health_handler = health_handler or (lambda alias: True)

    def generate_text(
        self,
        *,
        model_alias: str,
        prompt: str,
        timeout_seconds: int = 90,
        metadata: Mapping[str, Any] | None = None,
    ) -> ModelResponse:
        raw = self.handler(
            "generate_text",
            model_alias,
            {
                "prompt": prompt,
                "timeout_seconds": timeout_seconds,
                "metadata": dict(metadata or {}),
            },
        )
        if isinstance(raw, ModelResponse):
            return raw
        if isinstance(raw, BaseModel):
            content = raw.model_dump_json(by_alias=True)
        elif isinstance(raw, Mapping):
            content = json.dumps(dict(raw), ensure_ascii=False)
        else:
            content = str(raw)
        return ModelResponse(modelAlias=model_alias, content=content)

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
        raw = self.handler(
            "analyze_image",
            model_alias,
            {
                "prompt": prompt,
                "image": image,
                "mime_type": mime_type,
                "timeout_seconds": timeout_seconds,
                "metadata": dict(metadata or {}),
            },
        )
        if isinstance(raw, ModelResponse):
            return raw
        return ModelResponse(modelAlias=model_alias, content=str(raw))

    def health_check(self, model_alias: str) -> bool:
        return self.health_handler(model_alias)


class UnavailableModelGateway(ModelGateway):
    """Safe default until deployment injects a concrete provider adapter."""

    def generate_text(
        self,
        *,
        model_alias: str,
        prompt: str,
        timeout_seconds: int = 90,
        metadata: Mapping[str, Any] | None = None,
    ) -> ModelResponse:
        del prompt, timeout_seconds, metadata
        raise ModelUnavailableError(
            model_alias,
            "No model provider adapter has been configured for this deployment",
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
        del prompt, image, mime_type, timeout_seconds, metadata
        raise ModelUnavailableError(model_alias)

    def health_check(self, model_alias: str) -> bool:
        del model_alias
        return False
