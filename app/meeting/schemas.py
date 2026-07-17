from datetime import datetime

from pydantic import Field, model_validator

from app.common.contracts import APIModel
from app.meeting.models import MeetingStatus, SegmentType


class MeetingSessionCreate(APIModel):
    workspace_id: str
    title: str | None = Field(default=None, max_length=255)
    document_ids: list[str] = Field(default_factory=list, max_length=100)


class MeetingSessionData(APIModel):
    id: str
    workspace_id: str
    chat_session_id: str | None = None
    title: str | None = None
    document_ids: list[str]
    transcription_model: str
    status: MeetingStatus
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class TranscriptSegmentData(APIModel):
    id: str
    start_ms: int = Field(ge=0)
    end_ms: int = Field(ge=0)
    speaker: str | None = None
    text: str
    confidence: float = Field(ge=0, le=1)
    segment_type: SegmentType
    qa_message_id: str | None = None

    @model_validator(mode="after")
    def validate_time_range(self):
        if self.end_ms < self.start_ms:
            raise ValueError("end_ms must be greater than or equal to start_ms")
        return self


class MeetingTranscriptData(APIModel):
    session_id: str
    status: MeetingStatus
    segments: list[TranscriptSegmentData]
