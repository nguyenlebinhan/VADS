"""Add page extraction, legal structure and document chunks.

Revision ID: 20260717_0002
Revises: 20260717_0001
Create Date: 2026-07-17 11:30:00+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260717_0002"
down_revision: str | None = "20260717_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PROCESSING_STATUSES = (
    "UPLOADED",
    "QUEUED",
    "PROCESSING",
    "COMPLETED",
    "FAILED",
    "CANCELLED",
    "NEEDS_REVIEW",
)
PROCESSING_STEPS = (
    "VALIDATING_FILE",
    "DETECTING_PDF_TYPE",
    "RENDERING_PAGES",
    "OCR_PROCESSING",
    "DETECTING_STRUCTURE",
    "CREATING_CHUNKS",
    "GENERATING_SUMMARY",
    "BUILDING_KNOWLEDGE_GRAPH",
    "INDEXING_VECTOR_DATA",
    "COMPLETED",
)
SECTION_TYPES = (
    "DOCUMENT_TITLE",
    "DOCUMENT_NUMBER",
    "ISSUING_AUTHORITY",
    "ISSUED_DATE",
    "LEGAL_BASIS",
    "PREAMBLE",
    "CHAPTER",
    "SECTION",
    "ARTICLE",
    "CLAUSE",
    "POINT",
    "SUBPOINT",
    "APPENDIX",
    "FORM",
    "TABLE",
    "SIGNATURE",
    "RECIPIENT_LIST",
    "PARAGRAPH",
)


def _enum_check(column: str, values: tuple[str, ...]) -> str:
    quoted = ", ".join(f"'{value}'" for value in values)
    return f"{column} IN ({quoted})"


def upgrade() -> None:
    op.create_table(
        "workspace_members",
        sa.Column("id", sa.String(length=40), nullable=False),
        sa.Column("workspace_id", sa.String(length=40), nullable=False),
        sa.Column("user_id", sa.String(length=40), nullable=False),
        sa.Column(
            "role",
            sa.Enum(
                "OWNER",
                "ADMIN",
                "MEMBER",
                "VIEWER",
                name="workspace_role",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "user_id", name="uq_workspace_member_user"),
    )
    op.create_index("ix_workspace_members_workspace_id", "workspace_members", ["workspace_id"])
    op.create_index("ix_workspace_members_user_id", "workspace_members", ["user_id"])

    with op.batch_alter_table("documents", recreate="always") as batch_op:
        batch_op.drop_constraint("document_processing_status", type_="check")
        batch_op.alter_column(
            "status", existing_type=sa.String(length=10), type_=sa.String(length=20)
        )
        batch_op.add_column(
            sa.Column(
                "document_type",
                sa.String(length=10),
                nullable=True,
            )
        )
        batch_op.create_check_constraint(
            "document_type",
            _enum_check("document_type", ("TEXT_BASED", "SCANNED", "HYBRID", "DOCX")),
        )
        batch_op.create_check_constraint(
            "document_processing_status", _enum_check("status", PROCESSING_STATUSES)
        )
    op.create_index("ix_documents_document_type", "documents", ["document_type"])

    # Batch mode makes the constraint/column migration portable to SQLite test
    # databases while emitting normal ALTER statements on PostgreSQL.
    with op.batch_alter_table("processing_jobs", recreate="always") as batch_op:
        batch_op.drop_constraint("uq_processing_job_document_type", type_="unique")
        batch_op.drop_constraint("processing_step", type_="check")
        batch_op.drop_constraint("processing_status", type_="check")
        batch_op.add_column(sa.Column("attempt", sa.Integer(), server_default="1", nullable=False))
        batch_op.add_column(sa.Column("current_page", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("total_pages", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("message", sa.Text(), nullable=True))
        batch_op.alter_column(
            "status", existing_type=sa.String(length=10), type_=sa.String(length=20)
        )
        batch_op.create_unique_constraint(
            "uq_processing_job_document_type_attempt",
            ["document_id", "job_type", "attempt"],
        )
    op.execute(
        "UPDATE processing_jobs SET current_step = CASE "
        "WHEN current_step = 'WAITING_FOR_PROCESSING' THEN 'VALIDATING_FILE' "
        "WHEN current_step = 'EXTRACTING_TEXT' THEN 'OCR_PROCESSING' "
        "WHEN current_step = 'DETECTING_PAGE_BOUNDARIES' THEN 'RENDERING_PAGES' "
        "ELSE current_step END"
    )
    with op.batch_alter_table("processing_jobs", recreate="always") as batch_op:
        batch_op.create_check_constraint(
            "processing_step", _enum_check("current_step", PROCESSING_STEPS)
        )
        batch_op.create_check_constraint(
            "processing_status", _enum_check("status", PROCESSING_STATUSES)
        )
        batch_op.alter_column("attempt", server_default=None)

    op.create_table(
        "document_pages",
        sa.Column("id", sa.String(length=40), nullable=False),
        sa.Column("document_id", sa.String(length=40), nullable=False),
        sa.Column("page_index", sa.Integer(), nullable=False),
        sa.Column("printed_page_number", sa.Integer(), nullable=True),
        sa.Column("width", sa.Float(), nullable=False),
        sa.Column("height", sa.Float(), nullable=False),
        sa.Column("rotation", sa.Integer(), nullable=False),
        sa.Column("has_text_layer", sa.Boolean(), nullable=False),
        sa.Column("image_only", sa.Boolean(), nullable=False),
        sa.Column("needs_ocr", sa.Boolean(), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=False),
        sa.Column("rendered_object_key", sa.String(length=1024), nullable=True),
        sa.Column("ocr_confidence", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", "page_index", name="uq_document_page_index"),
    )
    op.create_index("ix_document_pages_document_id", "document_pages", ["document_id"])
    op.create_index(
        "ix_document_pages_document_order",
        "document_pages",
        ["document_id", "page_index"],
    )

    op.create_table(
        "page_blocks",
        sa.Column("id", sa.String(length=40), nullable=False),
        sa.Column("document_id", sa.String(length=40), nullable=False),
        sa.Column("page_id", sa.String(length=40), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("block_type", sa.String(length=50), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("normalized_text", sa.Text(), nullable=False),
        sa.Column("bbox", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["page_id"], ["document_pages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("page_id", "order_index", name="uq_page_block_order"),
    )
    op.create_index("ix_page_blocks_document_id", "page_blocks", ["document_id"])
    op.create_index("ix_page_blocks_page_id", "page_blocks", ["page_id"])
    op.create_index(
        "ix_page_blocks_document_page_order",
        "page_blocks",
        ["document_id", "page_id", "order_index"],
    )

    op.create_table(
        "document_sections",
        sa.Column("id", sa.String(length=40), nullable=False),
        sa.Column("document_id", sa.String(length=40), nullable=False),
        sa.Column("parent_id", sa.String(length=40), nullable=True),
        sa.Column(
            "section_type",
            sa.Enum(
                *SECTION_TYPES,
                name="section_type",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("label", sa.String(length=255), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("hierarchy_level", sa.Integer(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("page_start", sa.Integer(), nullable=False),
        sa.Column("page_end", sa.Integer(), nullable=False),
        sa.Column("start_block_id", sa.String(length=40), nullable=False),
        sa.Column("end_block_id", sa.String(length=40), nullable=False),
        sa.Column("heading_path", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["end_block_id"], ["page_blocks.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["parent_id"], ["document_sections.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["start_block_id"], ["page_blocks.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_document_sections_document_id", "document_sections", ["document_id"])
    op.create_index("ix_document_sections_section_type", "document_sections", ["section_type"])
    op.create_index("ix_document_sections_parent", "document_sections", ["parent_id"])
    op.create_index(
        "ix_document_sections_document_order",
        "document_sections",
        ["document_id", "order_index"],
    )

    op.create_table(
        "document_tables",
        sa.Column("id", sa.String(length=40), nullable=False),
        sa.Column("document_id", sa.String(length=40), nullable=False),
        sa.Column("section_id", sa.String(length=40), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("page_start", sa.Integer(), nullable=False),
        sa.Column("page_end", sa.Integer(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("start_block_id", sa.String(length=40), nullable=True),
        sa.Column("end_block_id", sa.String(length=40), nullable=True),
        sa.Column("bounding_boxes", sa.JSON(), nullable=False),
        sa.Column("header_rows", sa.JSON(), nullable=False),
        sa.Column("rows", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["end_block_id"], ["page_blocks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["section_id"], ["document_sections.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["start_block_id"], ["page_blocks.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_document_tables_document_id", "document_tables", ["document_id"])
    op.create_index(
        "ix_document_tables_document_order",
        "document_tables",
        ["document_id", "page_start", "order_index"],
    )

    op.create_table(
        "document_chunks",
        sa.Column("id", sa.String(length=40), nullable=False),
        sa.Column("document_id", sa.String(length=40), nullable=False),
        sa.Column("section_id", sa.String(length=40), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("chunk_type", sa.String(length=50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("normalized_content", sa.Text(), nullable=False),
        sa.Column("chapter", sa.String(length=255), nullable=True),
        sa.Column("section", sa.String(length=255), nullable=True),
        sa.Column("article", sa.String(length=255), nullable=True),
        sa.Column("clause", sa.String(length=255), nullable=True),
        sa.Column("point", sa.String(length=255), nullable=True),
        sa.Column("appendix", sa.String(length=255), nullable=True),
        sa.Column("form_code", sa.String(length=255), nullable=True),
        sa.Column("pdf_page_start", sa.Integer(), nullable=False),
        sa.Column("pdf_page_end", sa.Integer(), nullable=False),
        sa.Column("printed_page_start", sa.Integer(), nullable=True),
        sa.Column("printed_page_end", sa.Integer(), nullable=True),
        sa.Column("start_block_id", sa.String(length=40), nullable=False),
        sa.Column("end_block_id", sa.String(length=40), nullable=False),
        sa.Column("bounding_boxes", sa.JSON(), nullable=False),
        sa.Column("ocr_confidence", sa.Float(), nullable=True),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["end_block_id"], ["page_blocks.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["section_id"], ["document_sections.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["start_block_id"], ["page_blocks.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])
    op.create_index("ix_document_chunks_section", "document_chunks", ["section_id"])
    op.create_index(
        "ix_document_chunks_document_order",
        "document_chunks",
        ["document_id", "order_index"],
    )


def downgrade() -> None:
    op.drop_table("document_chunks")
    op.drop_table("document_tables")
    op.drop_table("document_sections")
    op.drop_table("page_blocks")
    op.drop_table("document_pages")
    with op.batch_alter_table("processing_jobs", recreate="always") as batch_op:
        batch_op.drop_constraint("uq_processing_job_document_type_attempt", type_="unique")
        batch_op.drop_constraint("processing_status", type_="check")
        batch_op.drop_constraint("processing_step", type_="check")
    op.execute(
        "UPDATE processing_jobs SET current_step = CASE "
        "WHEN current_step = 'VALIDATING_FILE' THEN 'WAITING_FOR_PROCESSING' "
        "WHEN current_step = 'OCR_PROCESSING' THEN 'EXTRACTING_TEXT' "
        "WHEN current_step = 'RENDERING_PAGES' THEN 'DETECTING_PAGE_BOUNDARIES' "
        "ELSE current_step END"
    )
    old_statuses = PROCESSING_STATUSES[:-1]
    old_steps = (
        "WAITING_FOR_PROCESSING",
        "EXTRACTING_TEXT",
        "DETECTING_PAGE_BOUNDARIES",
        "DETECTING_STRUCTURE",
        "CREATING_CHUNKS",
        "GENERATING_SUMMARY",
        "BUILDING_KNOWLEDGE_GRAPH",
        "INDEXING_VECTOR_DATA",
        "COMPLETED",
    )
    with op.batch_alter_table("processing_jobs", recreate="always") as batch_op:
        batch_op.create_check_constraint("processing_step", _enum_check("current_step", old_steps))
        batch_op.create_check_constraint("processing_status", _enum_check("status", old_statuses))
        batch_op.drop_column("message")
        batch_op.drop_column("total_pages")
        batch_op.drop_column("current_page")
        batch_op.drop_column("attempt")
        batch_op.alter_column(
            "status", existing_type=sa.String(length=20), type_=sa.String(length=10)
        )
        batch_op.create_unique_constraint(
            "uq_processing_job_document_type", ["document_id", "job_type"]
        )
    op.drop_index("ix_documents_document_type", table_name="documents")
    op.execute("UPDATE documents SET status = 'FAILED' WHERE status = 'NEEDS_REVIEW'")
    with op.batch_alter_table("documents", recreate="always") as batch_op:
        batch_op.drop_constraint("document_processing_status", type_="check")
        batch_op.drop_constraint("document_type", type_="check")
        batch_op.drop_column("document_type")
        batch_op.alter_column(
            "status", existing_type=sa.String(length=20), type_=sa.String(length=10)
        )
        batch_op.create_check_constraint(
            "document_processing_status", _enum_check("status", old_statuses)
        )
    op.drop_table("workspace_members")
