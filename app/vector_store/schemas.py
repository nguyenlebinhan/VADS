from datetime import datetime

from pydantic import Field

from app.common.contracts import APIModel
from app.vector_store.models import IndexStatus


class IndexStatusData(APIModel):
    job_id: str
    document_id: str
    workspace_id: str
    status: IndexStatus
    progress: float = Field(ge=0, le=100)
    total_chunks: int = Field(ge=0)
    indexed_chunks: int = Field(ge=0)
    embedding_models: list[str] = Field(default_factory=list)
    error_code: str | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    updated_at: datetime
