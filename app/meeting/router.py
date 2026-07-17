from typing import Annotated

from fastapi import APIRouter, Depends, File, Path, UploadFile, status
from sqlalchemy.orm import Session

from app.chat.adapters.mock.model_router import MockModelRouter
from app.chat.qa_pipeline import QuestionAnsweringPipeline
from app.chat.service import ChatService
from app.common.contracts import ApiSuccessResponse
from app.config.database import get_db
from app.meeting.adapters.mock.transcriber import MockMeetingTranscriber
from app.meeting.schemas import MeetingSessionCreate, MeetingSessionData, MeetingTranscriptData
from app.meeting.service import MeetingService
from app.reranking.adapters.mock.provider import LexicalRerankerProvider
from app.reranking.service import RerankingService
from app.retrieval.service import HybridRetrievalService
from app.vector_store.adapters.mock.embedding import DeterministicEmbeddingProvider
from app.vector_store.pgvector_store import PgVectorStore

router = APIRouter(tags=["Meeting Audio"])


def get_meeting_service(session: Annotated[Session, Depends(get_db)]) -> MeetingService:
    qa_pipeline = QuestionAnsweringPipeline(
        retrieval=HybridRetrievalService(
            vector_store=PgVectorStore(session),
            embedding_provider=DeterministicEmbeddingProvider(),
        ),
        reranking=RerankingService(LexicalRerankerProvider()),
        model_router=MockModelRouter(),
    )
    return MeetingService(
        session,
        transcriber=MockMeetingTranscriber(),
        chat_service=ChatService(session, qa_pipeline=qa_pipeline),
    )


@router.post(
    "/meeting-sessions",
    response_model=ApiSuccessResponse[MeetingSessionData],
    status_code=status.HTTP_201_CREATED,
)
def create_meeting_session(
    payload: MeetingSessionCreate,
    service: Annotated[MeetingService, Depends(get_meeting_service)],
) -> ApiSuccessResponse[MeetingSessionData]:
    return ApiSuccessResponse(data=service.create(payload))


@router.post(
    "/meeting-sessions/{sessionId}/audio",
    response_model=ApiSuccessResponse[MeetingTranscriptData],
)
async def upload_meeting_audio(
    session_id: Annotated[str, Path(alias="sessionId", min_length=1, max_length=40)],
    audio: Annotated[UploadFile, File(description="Meeting audio")],
    service: Annotated[MeetingService, Depends(get_meeting_service)],
) -> ApiSuccessResponse[MeetingTranscriptData]:
    content = await audio.read()
    return ApiSuccessResponse(
        data=service.process_audio(
            session_id,
            content=content,
            content_type=(audio.content_type or "application/octet-stream").lower(),
        )
    )


@router.get(
    "/meeting-sessions/{sessionId}/transcript",
    response_model=ApiSuccessResponse[MeetingTranscriptData],
)
def get_meeting_transcript(
    session_id: Annotated[str, Path(alias="sessionId", min_length=1, max_length=40)],
    service: Annotated[MeetingService, Depends(get_meeting_service)],
) -> ApiSuccessResponse[MeetingTranscriptData]:
    return ApiSuccessResponse(data=service.transcript(session_id))
