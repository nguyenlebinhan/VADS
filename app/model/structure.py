from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, ForeignKey, Index, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.model.base import Base, TimestampMixin, prefixed_uuid

if TYPE_CHECKING:
    from app.model.documents import Document


class SectionType(str, Enum):
    DOCUMENT_TITLE = "DOCUMENT_TITLE"
    DOCUMENT_NUMBER = "DOCUMENT_NUMBER"
    ISSUING_AUTHORITY = "ISSUING_AUTHORITY"
    ISSUED_DATE = "ISSUED_DATE"
    LEGAL_BASIS = "LEGAL_BASIS"
    PREAMBLE = "PREAMBLE"
    CHAPTER = "CHAPTER"
    SECTION = "SECTION"
    ARTICLE = "ARTICLE"
    CLAUSE = "CLAUSE"
    POINT = "POINT"
    SUBPOINT = "SUBPOINT"
    APPENDIX = "APPENDIX"
    FORM = "FORM"
    TABLE = "TABLE"
    SIGNATURE = "SIGNATURE"
    RECIPIENT_LIST = "RECIPIENT_LIST"
    PARAGRAPH = "PARAGRAPH"


class DocumentSection(TimestampMixin, Base):
    __tablename__ = "document_sections"
    __table_args__ = (
        Index("ix_document_sections_document_order", "document_id", "order_index"),
        Index("ix_document_sections_parent", "parent_id"),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=prefixed_uuid("section"))
    document_id: Mapped[str] = mapped_column(
        String(40),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parent_id: Mapped[str | None] = mapped_column(
        String(40),
        ForeignKey("document_sections.id", ondelete="CASCADE"),
        nullable=True,
    )
    section_type: Mapped[SectionType] = mapped_column(
        SAEnum(
            SectionType,
            name="section_type",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
        index=True,
    )
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    hierarchy_level: Mapped[int] = mapped_column(Integer, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    page_start: Mapped[int] = mapped_column(Integer, nullable=False)
    page_end: Mapped[int] = mapped_column(Integer, nullable=False)
    start_block_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("page_blocks.id", ondelete="RESTRICT"), nullable=False
    )
    end_block_id: Mapped[str] = mapped_column(
        String(40), ForeignKey("page_blocks.id", ondelete="RESTRICT"), nullable=False
    )
    heading_path: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)

    document: Mapped[Document] = relationship("Document", back_populates="sections")
    parent: Mapped[DocumentSection | None] = relationship(
        "DocumentSection", remote_side="DocumentSection.id", back_populates="children"
    )
    children: Mapped[list[DocumentSection]] = relationship(
        "DocumentSection", back_populates="parent", cascade="all, delete-orphan"
    )
