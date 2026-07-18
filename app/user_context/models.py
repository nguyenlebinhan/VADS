from sqlalchemy import JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.model.base import Base, TimestampMixin, prefixed_uuid


class UserContextProfile(TimestampMixin, Base):
    __tablename__ = "user_context_profiles"
    __table_args__ = (UniqueConstraint("user_id", name="uq_user_context_profiles_user_id"),)

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=prefixed_uuid("ucp"))
    # OIDC subject; intentionally not tied to the legacy local-password user table.
    user_id: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    position: Mapped[str] = mapped_column(String(255), nullable=False)
    department: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    organization: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    province: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    district: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    responsibilities: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    assigned_projects: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
