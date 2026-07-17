from __future__ import annotations

from enum import Enum
from uuid import uuid4

from sqlalchemy import JSON, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.model.base import Base, TimestampMixin


class MeetingStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PROCESSING_AUDIO = "PROCESSING_AUDIO"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class SegmentType(str, Enum):
    SPEECH = "SPEECH"
    QUESTION = "QUESTION"


class MeetingSession(TimestampMixin, Base):
    __tablename__ = "meeting_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    workspace_id: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    chat_session_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    document_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    transcription_model: Mapped[str] = mapped_column(
        String(100), nullable=False, default="whisper-large-v3-turbo"
    )
    status: Mapped[MeetingStatus] = mapped_column(
        SAEnum(
            MeetingStatus,
            name="meeting_status",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
        default=MeetingStatus.ACTIVE,
        index=True,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    segments: Mapped[list[TranscriptSegment]] = relationship(
        "TranscriptSegment",
        back_populates="meeting",
        cascade="all, delete-orphan",
        order_by="TranscriptSegment.start_ms",
    )


class TranscriptSegment(TimestampMixin, Base):
    __tablename__ = "meeting_transcript_segments"
    __table_args__ = (Index("ix_transcript_meeting_start", "meeting_id", "start_ms"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    meeting_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("meeting_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    start_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    end_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    speaker: Mapped[str | None] = mapped_column(String(255), nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    segment_type: Mapped[SegmentType] = mapped_column(
        SAEnum(
            SegmentType,
            name="meeting_segment_type",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
        default=SegmentType.SPEECH,
    )
    qa_message_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    meeting: Mapped[MeetingSession] = relationship("MeetingSession", back_populates="segments")
