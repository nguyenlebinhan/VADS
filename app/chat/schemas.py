from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import Field

from app.chat.models import ChatRole, ChatSessionStatus
from app.common.contracts import APIModel


class AnswerStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    NOT_FOUND = "NOT_FOUND"
    CONFLICTING = "CONFLICTING"
    LOW_CONFIDENCE_SOURCE = "LOW_CONFIDENCE_SOURCE"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"


class AnswerCitation(APIModel):
    document_id: str
    chunk_id: str
    pdf_page_index: int
    printed_page_number: int | None = None
    article: str | None = None
    clause: str | None = None
    point: str | None = None
    quote: str
    bounding_boxes: list[dict[str, Any]] = Field(default_factory=list)


class SourceConflict(APIModel):
    topic: str
    values: list[str]
    chunk_ids: list[str]
    description: str


class AnswerSchema(APIModel):
    answer: str
    answer_status: AnswerStatus
    confidence: float = Field(ge=0, le=1)
    citations: list[AnswerCitation] = Field(default_factory=list)
    conflicts: list[SourceConflict] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ChatSessionCreate(APIModel):
    title: str | None = Field(default=None, max_length=255)
    is_private: bool = False


class ChatSessionData(APIModel):
    id: str
    workspace_id: str
    title: str | None = None
    is_private: bool
    status: ChatSessionStatus
    created_at: datetime
    updated_at: datetime


class ChatQuestionRequest(APIModel):
    question: str = Field(min_length=1, max_length=8000)
    document_ids: list[str] = Field(default_factory=list, max_length=100)
    stream: bool = False


class ChatMessageData(APIModel):
    id: str
    session_id: str
    role: ChatRole
    content: str
    document_ids: list[str]
    answer: AnswerSchema | None = None
    created_at: datetime


class ChatExchangeData(APIModel):
    user_message: ChatMessageData
    assistant_message: ChatMessageData
    answer: AnswerSchema


class DeleteChatSessionData(APIModel):
    session_id: str
    status: str = "DELETED"
