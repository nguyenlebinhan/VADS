from app.meeting.transcriber import TranscribedSegment


class MockMeetingTranscriber:
    """Treat UTF-8 test payload as a deterministic transcript."""

    def transcribe(
        self,
        audio: bytes,
        *,
        primary_model: str,
        fallback_model: str,
        low_cost_model: str,
    ) -> list[TranscribedSegment]:
        del primary_model, fallback_model, low_cost_model
        text = audio.decode("utf-8", errors="ignore").strip() or "Không có nội dung nhận dạng."
        return [
            TranscribedSegment(
                start_ms=0,
                end_ms=max(1000, len(text) * 70),
                speaker=None,
                text=text,
                confidence=0.92,
                segment_type="QUESTION" if "?" in text else None,
            )
        ]

    def health_check(self) -> bool:
        return True
