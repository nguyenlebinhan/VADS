from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api_aggregation.models import (
    ChatMessage,
    ChatSession,
    DocumentIndexJob,
    EmbeddingRecord,
    MeetingSession,
    TranscriptSegment,
)
from app.model.base import Base
from app.utils.model_registry import import_models

OWNER3_TABLES = [
    EmbeddingRecord.__table__,
    DocumentIndexJob.__table__,
    ChatSession.__table__,
    ChatMessage.__table__,
    MeetingSession.__table__,
    TranscriptSegment.__table__,
]


@pytest.fixture
def db_session() -> Iterator[Session]:
    import_models()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=OWNER3_TABLES)
    with Session(engine, expire_on_commit=False) as session:
        yield session
    Base.metadata.drop_all(engine, tables=list(reversed(OWNER3_TABLES)))
