"""Add vector search, chat and meeting API tables.

Revision ID: 20260718_0004
Revises: 20260718_0003
"""

from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

from alembic import op

revision: str = "20260718_0004"
down_revision: str | None = "20260718_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    ]


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "document_embeddings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("chunk_id", sa.String(40), nullable=False),
        sa.Column("document_id", sa.String(40), nullable=False),
        sa.Column("workspace_id", sa.String(40), nullable=False),
        sa.Column("vector", Vector(384), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("normalized_content", sa.Text(), nullable=False),
        sa.Column("language", sa.String(16), nullable=False),
        sa.Column("chapter", sa.String(255), nullable=True),
        sa.Column("article", sa.String(255), nullable=True),
        sa.Column("clause", sa.String(255), nullable=True),
        sa.Column("point", sa.String(255), nullable=True),
        sa.Column("pdf_page_start", sa.Integer(), nullable=False),
        sa.Column("pdf_page_end", sa.Integer(), nullable=False),
        sa.Column("printed_page_start", sa.Integer(), nullable=True),
        sa.Column("printed_page_end", sa.Integer(), nullable=True),
        sa.Column("entity_metadata", sa.JSON(), nullable=False),
        sa.Column("node_type", sa.String(100), nullable=True),
        sa.Column("agency", sa.String(255), nullable=True),
        sa.Column("issued_date", sa.Date(), nullable=True),
        sa.Column("embedding_model", sa.String(100), nullable=False),
        sa.Column("embedding_version", sa.String(50), nullable=False),
        *_timestamps(),
        sa.UniqueConstraint(
            "chunk_id",
            "embedding_model",
            "embedding_version",
            name="uq_embedding_chunk_model_version",
        ),
    )
    op.create_index("ix_document_embeddings_chunk_id", "document_embeddings", ["chunk_id"])
    op.create_index("ix_document_embeddings_document_id", "document_embeddings", ["document_id"])
    op.create_index("ix_document_embeddings_workspace_id", "document_embeddings", ["workspace_id"])
    op.create_index("ix_document_embeddings_language", "document_embeddings", ["language"])
    op.create_index("ix_document_embeddings_node_type", "document_embeddings", ["node_type"])
    op.create_index("ix_document_embeddings_agency", "document_embeddings", ["agency"])
    op.create_index("ix_document_embeddings_issued_date", "document_embeddings", ["issued_date"])
    op.create_index(
        "ix_embeddings_workspace_document",
        "document_embeddings",
        ["workspace_id", "document_id"],
    )
    op.create_index(
        "ix_embeddings_legal_path",
        "document_embeddings",
        ["document_id", "chapter", "article", "clause"],
    )

    op.create_table(
        "document_index_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("document_id", sa.String(40), nullable=False),
        sa.Column("workspace_id", sa.String(40), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("total_chunks", sa.Integer(), nullable=False),
        sa.Column("indexed_chunks", sa.Integer(), nullable=False),
        sa.Column("progress", sa.Float(), nullable=False),
        sa.Column("embedding_models", sa.JSON(), nullable=False),
        sa.Column("error_code", sa.String(100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('QUEUED', 'INDEXING', 'COMPLETED', 'FAILED')",
            name="document_index_status",
        ),
        sa.UniqueConstraint(
            "document_id", "attempt", name="uq_index_job_document_attempt"
        ),
    )
    op.create_index("ix_document_index_jobs_document_id", "document_index_jobs", ["document_id"])
    op.create_index("ix_document_index_jobs_workspace_id", "document_index_jobs", ["workspace_id"])
    op.create_index("ix_document_index_jobs_status", "document_index_jobs", ["status"])

    op.create_table(
        "chat_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("workspace_id", sa.String(40), nullable=False),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("is_private", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'DELETED')", name="chat_session_status"
        ),
    )
    op.create_index("ix_chat_sessions_workspace_id", "chat_sessions", ["workspace_id"])
    op.create_index("ix_chat_sessions_status", "chat_sessions", ["status"])

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "session_id",
            sa.String(36),
            sa.ForeignKey("chat_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(30), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("document_ids", sa.JSON(), nullable=False),
        sa.Column("answer_payload", sa.JSON(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "role IN ('USER', 'ASSISTANT', 'SYSTEM')", name="chat_role"
        ),
    )
    op.create_index("ix_chat_messages_session_id", "chat_messages", ["session_id"])
    op.create_index(
        "ix_chat_messages_session_created",
        "chat_messages",
        ["session_id", "created_at"],
    )

    op.create_table(
        "meeting_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("workspace_id", sa.String(40), nullable=False),
        sa.Column("chat_session_id", sa.String(36), nullable=True),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("document_ids", sa.JSON(), nullable=False),
        sa.Column("transcription_model", sa.String(100), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'PROCESSING_AUDIO', 'COMPLETED', 'FAILED')",
            name="meeting_status",
        ),
    )
    op.create_index("ix_meeting_sessions_workspace_id", "meeting_sessions", ["workspace_id"])
    op.create_index("ix_meeting_sessions_status", "meeting_sessions", ["status"])

    op.create_table(
        "meeting_transcript_segments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "meeting_id",
            sa.String(36),
            sa.ForeignKey("meeting_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("start_ms", sa.Integer(), nullable=False),
        sa.Column("end_ms", sa.Integer(), nullable=False),
        sa.Column("speaker", sa.String(255), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("segment_type", sa.String(30), nullable=False),
        sa.Column("qa_message_id", sa.String(36), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "segment_type IN ('SPEECH', 'QUESTION')",
            name="meeting_segment_type",
        ),
    )
    op.create_index(
        "ix_meeting_transcript_segments_meeting_id",
        "meeting_transcript_segments",
        ["meeting_id"],
    )
    op.create_index(
        "ix_transcript_meeting_start",
        "meeting_transcript_segments",
        ["meeting_id", "start_ms"],
    )


def downgrade() -> None:
    op.drop_table("meeting_transcript_segments")
    op.drop_table("meeting_sessions")
    op.drop_table("chat_messages")
    op.drop_table("chat_sessions")
    op.drop_table("document_index_jobs")
    op.drop_table("document_embeddings")
