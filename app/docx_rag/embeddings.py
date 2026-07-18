from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.docx_rag.schemas import OpenAIConfigurationError, OpenAIRequestError

DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
DEFAULT_CHAT_MODEL = "gpt-4.1-mini"
DEFAULT_BASE_URL = "https://api.openai.com/v1"
ENV_FILE_PATH = Path(__file__).resolve().parents[2] / ".env"


@lru_cache(maxsize=1)
def _dotenv_values() -> dict[str, str]:
    """Read the repository .env without mutating the process environment."""
    if not ENV_FILE_PATH.exists():
        return {}
    values: dict[str, str] = {}
    for raw_line in ENV_FILE_PATH.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        name, separator, value = line.partition("=")
        if not separator:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        values[name.strip()] = value
    return values


def resolve_config_value(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    dotenv = _dotenv_values()
    for name in names:
        value = dotenv.get(name)
        if value:
            return value
    return None


def resolve_api_key(*, required: bool = True) -> str | None:
    key = resolve_config_value("OPENAI_API_KEY", "VADS_OPENAI_API_KEY")
    if required and not key:
        raise OpenAIConfigurationError(
            "Missing OpenAI API key. Set OPENAI_API_KEY or VADS_OPENAI_API_KEY."
        )
    return key


class OpenAIAPIClient:
    """Small dependency-free OpenAI REST client for this hackathon module."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        embedding_model: str | None = None,
        chat_model: str | None = None,
        timeout_seconds: float = 60.0,
    ) -> None:
        self.api_key = api_key or resolve_api_key(required=True)
        configured_base_url = resolve_config_value("VADS_OPENAI_BASE_URL")
        self.base_url = (base_url or configured_base_url or DEFAULT_BASE_URL).rstrip("/")
        self.embedding_model = (
            embedding_model
            or resolve_config_value("VADS_OPENAI_EMBEDDING_MODEL")
            or DEFAULT_EMBEDDING_MODEL
        )
        configured_chat_model = resolve_config_value("VADS_OPENAI_CHAT_MODEL")
        self.chat_model = chat_model or configured_chat_model or DEFAULT_CHAT_MODEL
        self.timeout_seconds = timeout_seconds

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        request = Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:  # noqa: S310
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            try:
                message = json.loads(detail).get("error", {}).get("message", detail)
            except json.JSONDecodeError:
                message = detail
            raise OpenAIRequestError(f"OpenAI API returned HTTP {error.code}: {message}") from error
        except (URLError, TimeoutError, json.JSONDecodeError) as error:
            raise OpenAIRequestError(f"OpenAI API request failed: {error}") from error

    def embed_texts(self, texts: list[str], *, batch_size: int = 64) -> list[list[float]]:
        embeddings: list[list[float]] = []
        for start in range(0, len(texts), batch_size):
            batch = texts[start : start + batch_size]
            response = self._post(
                "/embeddings",
                {"model": self.embedding_model, "input": batch, "encoding_format": "float"},
            )
            try:
                ordered = sorted(response["data"], key=lambda item: item["index"])
                embeddings.extend(item["embedding"] for item in ordered)
            except (KeyError, TypeError) as error:
                raise OpenAIRequestError("OpenAI embedding response is malformed") from error
        if len(embeddings) != len(texts):
            raise OpenAIRequestError("OpenAI returned an unexpected number of embeddings")
        return embeddings

    def answer_with_context(self, *, question: str, context: str) -> str:
        response = self._post(
            "/chat/completions",
            {
                "model": self.chat_model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Bạn là trợ lý tra cứu văn bản. Chỉ trả lời bằng thông tin "
                            "có trong CONTEXT. Không dùng kiến thức bên ngoài và không "
                            "suy đoán. Nếu context không đủ, hãy nói rõ không tìm thấy "
                            "thông tin trong tài liệu. Mỗi ý phải gắn nguồn dạng "
                            "[Nguồn N] đúng với số nguồn trong context."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"QUESTION:\n{question}\n\nCONTEXT:\n{context}",
                    },
                ],
            },
        )
        try:
            content = response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise OpenAIRequestError("OpenAI chat response is malformed") from error
        if not isinstance(content, str) or not content.strip():
            raise OpenAIRequestError("OpenAI chat response is empty")
        return content.strip()
