from sqlalchemy import select
from sqlalchemy.orm import Session

from app.chat.schemas import ChatQuestionRequest, ChatSessionCreate
from app.chat.service import ChatService
from app.exceptions import AppError, NotFoundError, UnsupportedMediaTypeError
from app.meeting.models import MeetingSession, MeetingStatus, SegmentType, TranscriptSegment
from app.meeting.schemas import (
    MeetingSessionCreate,
    MeetingSessionData,
    MeetingTranscriptData,
    TranscriptSegmentData,
)
from app.meeting.transcriber import (
    FALLBACK_TRANSCRIPTION_MODEL,
    LOW_COST_TRANSCRIPTION_MODEL,
    PRIMARY_TRANSCRIPTION_MODEL,
    MeetingTranscriber,
)

MAX_AUDIO_SIZE = 50 * 1024 * 1024
ALLOWED_AUDIO_TYPES = {
    "audio/mpeg",
    "audio/mp4",
    "audio/wav",
    "audio/x-wav",
    "audio/webm",
    "audio/ogg",
}


class MeetingService:
    def __init__(
        self,
        session: Session,
        *,
        transcriber: MeetingTranscriber,
        chat_service: ChatService,
    ) -> None:
        self.session = session
        self.transcriber = transcriber
        self.chat_service = chat_service

    def create(self, payload: MeetingSessionCreate) -> MeetingSessionData:
        chat = self.chat_service.create_session(
            payload.workspace_id,
            ChatSessionCreate(title=payload.title or "Meeting Q&A"),
        )
        meeting = MeetingSession(
            workspace_id=payload.workspace_id,
            chat_session_id=chat.id,
            title=payload.title,
            document_ids=payload.document_ids,
            transcription_model=PRIMARY_TRANSCRIPTION_MODEL,
        )
        self.session.add(meeting)
        self.session.commit()
        self.session.refresh(meeting)
        return MeetingSessionData.model_validate(meeting)

    def process_audio(
        self,
        session_id: str,
        *,
        content: bytes,
        content_type: str,
    ) -> MeetingTranscriptData:
        meeting = self._get(session_id)
        if content_type not in ALLOWED_AUDIO_TYPES:
            raise UnsupportedMediaTypeError(
                "UNSUPPORTED_AUDIO_TYPE",
                "Định dạng âm thanh không được hỗ trợ.",
                {"contentType": content_type},
            )
        if not content:
            raise AppError(status_code=422, code="EMPTY_AUDIO", message="Tệp âm thanh rỗng.")
        if len(content) > MAX_AUDIO_SIZE:
            raise AppError(
                status_code=413,
                code="AUDIO_TOO_LARGE",
                message="Tệp âm thanh vượt quá dung lượng cho phép.",
            )
        meeting.status = MeetingStatus.PROCESSING_AUDIO
        self.session.commit()
        try:
            results = self.transcriber.transcribe(
                content,
                primary_model=PRIMARY_TRANSCRIPTION_MODEL,
                fallback_model=FALLBACK_TRANSCRIPTION_MODEL,
                low_cost_model=LOW_COST_TRANSCRIPTION_MODEL,
            )
            for result in results:
                segment_type = self._segment_type(result.text, result.segment_type)
                segment = TranscriptSegment(
                    meeting_id=meeting.id,
                    start_ms=result.start_ms,
                    end_ms=result.end_ms,
                    speaker=result.speaker,
                    text=result.text,
                    confidence=result.confidence,
                    segment_type=segment_type,
                )
                self.session.add(segment)
                self.session.flush()
                if segment_type == SegmentType.QUESTION and meeting.chat_session_id:
                    exchange = self.chat_service.ask(
                        meeting.chat_session_id,
                        ChatQuestionRequest(
                            question=result.text,
                            document_ids=meeting.document_ids,
                        ),
                    )
                    segment.qa_message_id = exchange.assistant_message.id
            meeting.status = MeetingStatus.COMPLETED
            self.session.commit()
            return self.transcript(session_id)
        except Exception as exc:
            self.session.rollback()
            failed = self._get(session_id)
            failed.status = MeetingStatus.FAILED
            failed.error_message = str(exc)[:4000]
            self.session.commit()
            raise

    def transcript(self, session_id: str) -> MeetingTranscriptData:
        meeting = self._get(session_id)
        segments = self.session.scalars(
            select(TranscriptSegment)
            .where(TranscriptSegment.meeting_id == session_id)
            .order_by(TranscriptSegment.start_ms)
        )
        return MeetingTranscriptData(
            session_id=session_id,
            status=meeting.status,
            segments=[TranscriptSegmentData.model_validate(segment) for segment in segments],
        )

    def _get(self, session_id: str) -> MeetingSession:
        meeting = self.session.get(MeetingSession, session_id)
        if meeting is None:
            raise NotFoundError("MEETING_SESSION", session_id)
        return meeting

    @staticmethod
    def _segment_type(text: str, supplied: str | None) -> SegmentType:
        if supplied == SegmentType.QUESTION.value:
            return SegmentType.QUESTION
        lowered = text.casefold().strip()
        question_markers = ("?", "ở điều nào", "bao lâu", "bao nhiêu", "ai chịu trách nhiệm")
        return (
            SegmentType.QUESTION
            if any(marker in lowered for marker in question_markers)
            else SegmentType.SPEECH
        )
