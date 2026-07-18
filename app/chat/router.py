from typing import Annotated

from fastapi import APIRouter, Depends, Header, Path, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.chat.adapters.model_gateway import ModelGatewayChatAdapter
from app.chat.qa_pipeline import QuestionAnsweringPipeline
from app.chat.schemas import (
    ChatExchangeData,
    ChatMessageData,
    ChatQuestionRequest,
    ChatSessionCreate,
    ChatSessionData,
    DeleteChatSessionData,
)
from app.chat.service import ChatService
from app.common.contracts import ApiSuccessResponse
from app.config.database import get_db
from app.model_gateway.gateway import ModelGateway
from app.orchestrator.dependencies import get_model_gateway
from app.reranking.adapters.mock.provider import LexicalRerankerProvider
from app.reranking.service import RerankingService
from app.retrieval.service import HybridRetrievalService
from app.streaming.sse import answer_event_stream
from app.vector_store.adapters.mock.embedding import DeterministicEmbeddingProvider
from app.vector_store.pgvector_store import PgVectorStore

router = APIRouter(tags=["Document Q&A"])


def get_chat_service(
    session: Annotated[Session, Depends(get_db)],
    gateway: Annotated[ModelGateway, Depends(get_model_gateway)],
) -> ChatService:
    retrieval = HybridRetrievalService(
        vector_store=PgVectorStore(session),
        embedding_provider=DeterministicEmbeddingProvider(),
    )
    pipeline = QuestionAnsweringPipeline(
        retrieval=retrieval,
        reranking=RerankingService(LexicalRerankerProvider()),
        model_router=ModelGatewayChatAdapter(gateway),
    )
    return ChatService(session, qa_pipeline=pipeline)


@router.post(
    "/workspaces/{workspaceId}/chat/sessions",
    response_model=ApiSuccessResponse[ChatSessionData],
    status_code=status.HTTP_201_CREATED,
)
def create_chat_session(
    workspace_id: Annotated[str, Path(alias="workspaceId", min_length=1, max_length=40)],
    payload: ChatSessionCreate,
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> ApiSuccessResponse[ChatSessionData]:
    return ApiSuccessResponse(
        data=service.create_session(workspace_id, payload),
        message="Tạo phiên Q&A thành công",
    )


@router.get(
    "/chat/sessions/{sessionId}",
    response_model=ApiSuccessResponse[ChatSessionData],
)
def get_chat_session(
    session_id: Annotated[str, Path(alias="sessionId", min_length=1, max_length=40)],
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> ApiSuccessResponse[ChatSessionData]:
    return ApiSuccessResponse(data=service.get_session(session_id))


@router.get(
    "/chat/sessions/{sessionId}/messages",
    response_model=ApiSuccessResponse[list[ChatMessageData]],
)
def list_chat_messages(
    session_id: Annotated[str, Path(alias="sessionId", min_length=1, max_length=40)],
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> ApiSuccessResponse[list[ChatMessageData]]:
    return ApiSuccessResponse(data=service.list_messages(session_id))


@router.post(
    "/chat/sessions/{sessionId}/messages",
    response_model=ApiSuccessResponse[ChatExchangeData],
    responses={
        200: {
            "description": "JSON exchange or a server-sent event stream",
            "content": {"text/event-stream": {"schema": {"type": "string"}}},
        }
    },
)
def send_chat_message(
    session_id: Annotated[str, Path(alias="sessionId", min_length=1, max_length=40)],
    payload: ChatQuestionRequest,
    service: Annotated[ChatService, Depends(get_chat_service)],
    accept: Annotated[str | None, Header()] = None,
) -> ApiSuccessResponse[ChatExchangeData] | StreamingResponse:
    exchange = service.ask(session_id, payload)
    if payload.stream or (accept and "text/event-stream" in accept.lower()):
        return StreamingResponse(
            answer_event_stream(exchange.answer),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    return ApiSuccessResponse(data=exchange)


@router.delete(
    "/chat/sessions/{sessionId}",
    response_model=ApiSuccessResponse[DeleteChatSessionData],
)
def delete_chat_session(
    session_id: Annotated[str, Path(alias="sessionId", min_length=1, max_length=40)],
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> ApiSuccessResponse[DeleteChatSessionData]:
    return ApiSuccessResponse(data=service.delete_session(session_id))
