from datetime import datetime

from pydantic import Field, field_validator

from app.common.contracts import APIModel


class UserContextUpdate(APIModel):
    position: str = Field(min_length=1, max_length=255)
    department: str = Field(min_length=1, max_length=300)
    organization: str = Field(min_length=1, max_length=300)
    province: str = Field(min_length=1, max_length=160)
    district: str | None = Field(default=None, max_length=160)
    responsibilities: list[str] = Field(default_factory=list, max_length=100)
    assigned_projects: list[str] = Field(default_factory=list, max_length=500)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("responsibilities", "assigned_projects")
    @classmethod
    def normalize_unique_values(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values if value.strip()]
        return list(dict.fromkeys(normalized))


class UserContextData(UserContextUpdate):
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime
