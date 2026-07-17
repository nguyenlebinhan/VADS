import json
from collections.abc import Iterator

from app.chat.schemas import AnswerSchema


def _event(name: str, payload: dict) -> str:
    return f"event: {name}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def answer_event_stream(answer: AnswerSchema) -> Iterator[str]:
    yield _event(
        "metadata",
        {
            "answerStatus": answer.answer_status.value,
            "confidence": answer.confidence,
            "warnings": answer.warnings,
        },
    )
    words = answer.answer.split()
    for index in range(0, len(words), 8):
        yield _event("token", {"text": " ".join(words[index : index + 8]) + " "})
    for citation in answer.citations:
        yield _event("citation", citation.model_dump(by_alias=True))
    yield _event("done", answer.model_dump(by_alias=True, mode="json"))
