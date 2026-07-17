from datetime import datetime

from pydantic import Field, model_validator

from app.model.processing import ProcessingStatus, ProcessingStep
from app.model.schemas.base import APIModel


class ProcessingStatusResponse(APIModel):
    document_id: str
    status: ProcessingStatus
    progress: int = Field(ge=0, le=100)
    current_step: ProcessingStep
    current_page: int | None = Field(default=None, ge=0)
    total_pages: int | None = Field(default=None, ge=0)
    message: str
    started_at: datetime | None = None
    updated_at: datetime
    completed_at: datetime | None = None
    error_code: str | None = None
    error_message: str | None = None


class ProcessingUpdate(APIModel):
    status: ProcessingStatus
    progress: int = Field(ge=0, le=100)
    current_step: ProcessingStep
    current_page: int | None = Field(default=None, ge=0)
    total_pages: int | None = Field(default=None, ge=0)
    message: str | None = Field(default=None, max_length=4000)
    error_code: str | None = Field(default=None, max_length=100)
    error_message: str | None = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def validate_terminal_state(self) -> "ProcessingUpdate":
        if self.status == ProcessingStatus.COMPLETED:
            if self.progress != 100 or self.current_step != ProcessingStep.COMPLETED:
                raise ValueError("COMPLETED requires progress=100 and step=COMPLETED")
        if self.status == ProcessingStatus.FAILED and not self.error_message:
            raise ValueError("FAILED requires error_message")
        return self
