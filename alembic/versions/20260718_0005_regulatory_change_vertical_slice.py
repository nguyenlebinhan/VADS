"""Add regulatory change intelligence vertical slice.

Revision ID: 20260718_0005
Revises: 20260718_0004
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260718_0005"
down_revision: str | None = "20260718_0004"
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
    op.create_table(
        "user_context_profiles",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column("user_id", sa.String(160), nullable=False),
        sa.Column("position", sa.String(255), nullable=False),
        sa.Column("department", sa.String(300), nullable=False),
        sa.Column("organization", sa.String(300), nullable=False),
        sa.Column("province", sa.String(160), nullable=False),
        sa.Column("district", sa.String(160), nullable=True),
        sa.Column("responsibilities", sa.JSON(), nullable=False),
        sa.Column("assigned_projects", sa.JSON(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        *_timestamps(),
        sa.UniqueConstraint("user_id", name="uq_user_context_profiles_user_id"),
    )
    for column in ("user_id", "department", "organization", "province", "district"):
        op.create_index(
            f"ix_user_context_profiles_{column}", "user_context_profiles", [column]
        )

    op.create_table(
        "regulatory_document_families",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.String(40),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("family_key", sa.String(255), nullable=False),
        sa.Column("canonical_title", sa.String(500), nullable=False),
        sa.Column("document_type", sa.String(80), nullable=False),
        *_timestamps(),
        sa.UniqueConstraint(
            "workspace_id", "family_key", name="uq_reg_family_workspace_key"
        ),
    )
    op.create_index(
        "ix_regulatory_document_families_workspace_id",
        "regulatory_document_families",
        ["workspace_id"],
    )
    op.create_index(
        "ix_regulatory_document_families_document_type",
        "regulatory_document_families",
        ["document_type"],
    )

    op.create_table(
        "regulatory_document_versions",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column(
            "family_id",
            sa.String(40),
            sa.ForeignKey("regulatory_document_families.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "document_id",
            sa.String(40),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("document_number", sa.String(160), nullable=False),
        sa.Column("legal_document_type", sa.String(80), nullable=False),
        sa.Column("issuing_agency", sa.String(300), nullable=False),
        sa.Column("issued_date", sa.Date(), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("domain", sa.String(160), nullable=False),
        sa.Column("applicable_subjects", sa.JSON(), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("executive_summary", sa.Text(), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('PARSED', 'ANALYZED', 'NEEDS_HUMAN_REVIEW')",
            name="regulatory_document_status",
        ),
        sa.UniqueConstraint("family_id", "version_number", name="uq_reg_family_version"),
        sa.UniqueConstraint("document_id", name="uq_reg_version_document"),
    )
    for column in (
        "family_id",
        "document_id",
        "document_number",
        "legal_document_type",
        "issuing_agency",
        "issued_date",
        "effective_date",
        "domain",
        "status",
    ):
        op.create_index(
            f"ix_regulatory_document_versions_{column}",
            "regulatory_document_versions",
            [column],
        )

    op.create_table(
        "regulatory_sections",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column(
            "document_version_id",
            sa.String(40),
            sa.ForeignKey("regulatory_document_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("section_type", sa.String(40), nullable=False),
        sa.Column("label", sa.String(255), nullable=True),
        sa.Column("title", sa.String(500), nullable=True),
        sa.Column("legal_location", sa.String(500), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("normalized_content", sa.Text(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("page_start", sa.Integer(), nullable=True),
        sa.Column("page_end", sa.Integer(), nullable=True),
        *_timestamps(),
        sa.UniqueConstraint(
            "document_version_id", "order_index", name="uq_reg_section_order"
        ),
    )
    op.create_index(
        "ix_regulatory_sections_document_version_id",
        "regulatory_sections",
        ["document_version_id"],
    )
    op.create_index(
        "ix_regulatory_sections_section_type",
        "regulatory_sections",
        ["section_type"],
    )

    op.create_table(
        "regulatory_changes",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column(
            "old_version_id",
            sa.String(40),
            sa.ForeignKey("regulatory_document_versions.id"),
            nullable=False,
        ),
        sa.Column(
            "new_version_id",
            sa.String(40),
            sa.ForeignKey("regulatory_document_versions.id"),
            nullable=False,
        ),
        sa.Column("change_type", sa.String(60), nullable=False),
        sa.Column("status", sa.String(60), nullable=True),
        sa.Column("fact_key", sa.String(120), nullable=False),
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column("effective_year", sa.Integer(), nullable=True),
        sa.Column("old_location", sa.String(500), nullable=True),
        sa.Column("new_location", sa.String(500), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "change_type IN ('ADDED','REMOVED','MODIFIED','UNCHANGED','MOVED',"
            "'RENUMBERED','CLARIFIED','VALUE_CHANGED','DEADLINE_CHANGED',"
            "'RESPONSIBILITY_CHANGED','SCOPE_CHANGED','PROCEDURE_CHANGED',"
            "'LEGAL_BASIS_CHANGED')",
            name="regulatory_change_type",
        ),
        sa.UniqueConstraint(
            "new_version_id", "fact_key", name="uq_reg_change_version_fact"
        ),
    )
    op.create_index(
        "ix_regulatory_changes_old_version_id", "regulatory_changes", ["old_version_id"]
    )
    op.create_index(
        "ix_regulatory_changes_new_version_id", "regulatory_changes", ["new_version_id"]
    )
    op.create_index(
        "ix_regulatory_changes_change_type", "regulatory_changes", ["change_type"]
    )

    op.create_table(
        "regulatory_projects",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.String(40),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("project_code", sa.String(100), nullable=False),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("status", sa.String(60), nullable=False),
        sa.Column("domain", sa.String(160), nullable=False),
        sa.Column("locations", sa.JSON(), nullable=False),
        sa.Column("lead_department", sa.String(300), nullable=False),
        sa.Column("coordinating_departments", sa.JSON(), nullable=False),
        sa.Column("legal_bases", sa.JSON(), nullable=False),
        sa.Column("activities", sa.JSON(), nullable=False),
        sa.Column("budget_sources", sa.JSON(), nullable=False),
        sa.Column("timeline", sa.JSON(), nullable=False),
        sa.Column("sections", sa.JSON(), nullable=False),
        *_timestamps(),
        sa.UniqueConstraint(
            "workspace_id", "project_code", name="uq_reg_project_workspace_code"
        ),
    )
    for column in ("workspace_id", "status", "domain", "lead_department"):
        op.create_index(
            f"ix_regulatory_projects_{column}", "regulatory_projects", [column]
        )

    op.create_table(
        "regulatory_agent_runs",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column(
            "document_version_id",
            sa.String(40),
            sa.ForeignKey("regulatory_document_versions.id"),
            nullable=False,
        ),
        sa.Column("idempotency_key", sa.String(255), nullable=False, unique=True),
        sa.Column("status", sa.String(60), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('PENDING','RUNNING','COMPLETED','FAILED','NEEDS_RETRY',"
            "'NEEDS_HUMAN_REVIEW')",
            name="regulatory_agent_run_status",
        ),
    )
    op.create_index(
        "ix_regulatory_agent_runs_document_version_id",
        "regulatory_agent_runs",
        ["document_version_id"],
    )
    op.create_index(
        "ix_regulatory_agent_runs_status", "regulatory_agent_runs", ["status"]
    )

    op.create_table(
        "regulatory_agent_tasks",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column(
            "agent_run_id",
            sa.String(40),
            sa.ForeignKey("regulatory_agent_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("agent_name", sa.String(100), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(60), nullable=False),
        sa.Column("input_references", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('PENDING','RUNNING','COMPLETED','FAILED','NEEDS_RETRY',"
            "'NEEDS_HUMAN_REVIEW')",
            name="regulatory_agent_task_status",
        ),
        sa.UniqueConstraint("agent_run_id", "sequence_number", name="uq_reg_task_sequence"),
    )
    op.create_index(
        "ix_regulatory_agent_tasks_agent_run_id",
        "regulatory_agent_tasks",
        ["agent_run_id"],
    )

    op.create_table(
        "regulatory_agent_outputs",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column(
            "agent_task_id",
            sa.String(40),
            sa.ForeignKey("regulatory_agent_tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("agent_name", sa.String(100), nullable=False),
        sa.Column("result", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        *_timestamps(),
    )
    op.create_index(
        "ix_regulatory_agent_outputs_agent_task_id",
        "regulatory_agent_outputs",
        ["agent_task_id"],
    )

    op.create_table(
        "regulatory_impacts",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column(
            "document_version_id",
            sa.String(40),
            sa.ForeignKey("regulatory_document_versions.id"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            sa.String(40),
            sa.ForeignKey("regulatory_projects.id"),
            nullable=False,
        ),
        sa.Column(
            "agent_run_id",
            sa.String(40),
            sa.ForeignKey("regulatory_agent_runs.id"),
            nullable=False,
        ),
        sa.Column("impact_level", sa.String(30), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("affected_areas", sa.JSON(), nullable=False),
        sa.Column("departments", sa.JSON(), nullable=False),
        sa.Column("recommended_actions", sa.JSON(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("review_status", sa.String(60), nullable=False),
        sa.Column("reviewed_by", sa.String(160), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "impact_level IN ('NONE','LOW','MEDIUM','HIGH','CRITICAL')",
            name="regulatory_impact_level",
        ),
        sa.UniqueConstraint(
            "document_version_id",
            "project_id",
            "agent_run_id",
            name="uq_reg_impact_version_project_run",
        ),
    )
    for column in ("document_version_id", "project_id", "agent_run_id", "impact_level"):
        op.create_index(
            f"ix_regulatory_impacts_{column}", "regulatory_impacts", [column]
        )

    op.create_table(
        "regulatory_verification_results",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column(
            "agent_run_id",
            sa.String(40),
            sa.ForeignKey("regulatory_agent_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(60), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("issues", sa.JSON(), nullable=False),
        sa.Column("checked_claims", sa.Integer(), nullable=False),
        sa.Column("rejected_claims", sa.Integer(), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('PENDING','RUNNING','COMPLETED','FAILED','NEEDS_RETRY',"
            "'NEEDS_HUMAN_REVIEW')",
            name="regulatory_verification_status",
        ),
    )
    op.create_index(
        "ix_regulatory_verification_results_agent_run_id",
        "regulatory_verification_results",
        ["agent_run_id"],
    )


def downgrade() -> None:
    op.drop_table("regulatory_verification_results")
    op.drop_table("regulatory_impacts")
    op.drop_table("regulatory_agent_outputs")
    op.drop_table("regulatory_agent_tasks")
    op.drop_table("regulatory_agent_runs")
    op.drop_table("regulatory_projects")
    op.drop_table("regulatory_changes")
    op.drop_table("regulatory_sections")
    op.drop_table("regulatory_document_versions")
    op.drop_table("regulatory_document_families")
    op.drop_table("user_context_profiles")
