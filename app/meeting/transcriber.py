from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class TranscribedSegment:
    start_ms: int
    end_ms: int
    speaker: str | None
    text: str
    confidence: float
    segment_type: str | None = None


class MeetingTranscriber(Protocol):
    def transcribe(
        self,
        audio: bytes,
        *,
        primary_model: str,
        fallback_model: str,
        low_cost_model: str,
    ) -> list[TranscribedSegment]: ...

    def health_check(self) -> bool: ...


PRIMARY_TRANSCRIPTION_MODEL = "whisper-large-v3-turbo"
FALLBACK_TRANSCRIPTION_MODEL = "FPT.AI-whisper-large-v3-turbo"
LOW_COST_TRANSCRIPTION_MODEL = "FPT.AI-whisper-medium"
