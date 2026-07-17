"""Add AI orchestration, summaries, graph, red flags and audit tables.

Revision ID: 20260718_0003
Revises: 20260717_0002
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260718_0003"
down_revision: str | None = "20260717_0002"
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
        "ai_workflows",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column(
            "document_id",
            sa.String(40),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("intent", sa.String(80), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("private_processing", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("plan", sa.JSON(), nullable=False),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
    )
    op.create_index("ix_ai_workflows_document_id", "ai_workflows", ["document_id"])
    op.create_index("ix_ai_workflows_intent", "ai_workflows", ["intent"])
    op.create_index("ix_ai_workflows_status", "ai_workflows", ["status"])

    op.create_table(
        "ai_workflow_steps",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column(
            "workflow_id",
            sa.String(40),
            sa.ForeignKey("ai_workflows.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("step_id", sa.String(100), nullable=False),
        sa.Column("task_type", sa.String(80), nullable=False),
        sa.Column("executor", sa.String(100), nullable=False),
        sa.Column("reason_for_selection", sa.Text(), nullable=False),
        sa.Column("depends_on", sa.JSON(), nullable=False),
        sa.Column("can_run_in_parallel", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False),
        sa.Column("max_retries", sa.Integer(), nullable=False),
        sa.Column("fallback_model", sa.String(100), nullable=True),
        sa.Column("expected_output_schema", sa.String(255), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("output", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
    )
    op.create_index("ix_ai_workflow_steps_workflow_id", "ai_workflow_steps", ["workflow_id"])
    op.create_index("ix_ai_workflow_steps_status", "ai_workflow_steps", ["status"])
    op.create_index(
        "uq_ai_workflow_steps_workflow_key",
        "ai_workflow_steps",
        ["workflow_id", "step_id"],
        unique=True,
    )

    op.create_table(
        "model_executions",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column(
            "workflow_id",
            sa.String(40),
            sa.ForeignKey("ai_workflows.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "workflow_step_id",
            sa.String(40),
            sa.ForeignKey("ai_workflow_steps.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("model_alias", sa.String(100), nullable=False),
        sa.Column("task_type", sa.String(80), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("is_fallback", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("request_metadata", sa.JSON(), nullable=False),
        sa.Column("response_metadata", sa.JSON(), nullable=False),
        sa.Column("output_snapshot", sa.JSON(), nullable=True),
        sa.Column("error_type", sa.String(255), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_model_executions_workflow_id", "model_executions", ["workflow_id"])
    op.create_index(
        "ix_model_executions_workflow_step_id", "model_executions", ["workflow_step_id"]
    )
    op.create_index("ix_model_executions_model_alias", "model_executions", ["model_alias"])
    op.create_index(
        "ix_model_executions_workflow_step",
        "model_executions",
        ["workflow_id", "workflow_step_id"],
    )

    op.create_table(
        "document_summaries",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column(
            "document_id",
            sa.String(40),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "workflow_id",
            sa.String(40),
            sa.ForeignKey("ai_workflows.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("model_name", sa.String(100), nullable=False),
        sa.Column("prompt_version", sa.String(100), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("rejected_item_count", sa.Integer(), nullable=False, server_default="0"),
        *_timestamps(),
        sa.UniqueConstraint("document_id", "version", name="uq_document_summary_version"),
    )
    op.create_index("ix_document_summaries_document_id", "document_summaries", ["document_id"])
    op.create_index("ix_document_summaries_workflow_id", "document_summaries", ["workflow_id"])
    op.create_index("ix_document_summaries_status", "document_summaries", ["status"])
    op.create_index(
        "ix_document_summaries_current", "document_summaries", ["document_id", "is_current"]
    )

    op.create_table(
        "summary_items",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column(
            "summary_id",
            sa.String(40),
            sa.ForeignKey("document_summaries.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("category", sa.String(60), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("importance", sa.String(20), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("system_metadata", sa.Boolean(), nullable=False, server_default=sa.false()),
        *_timestamps(),
    )
    op.create_index("ix_summary_items_summary_id", "summary_items", ["summary_id"])
    op.create_index("ix_summary_items_category", "summary_items", ["category"])
    op.create_index(
        "ix_summary_items_summary_order", "summary_items", ["summary_id", "order_index"]
    )

    op.create_table(
        "citations",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column("owner_type", sa.String(40), nullable=False),
        sa.Column("owner_id", sa.String(40), nullable=False),
        sa.Column(
            "document_id",
            sa.String(40),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "chunk_id",
            sa.String(40),
            sa.ForeignKey("document_chunks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("quote", sa.Text(), nullable=False),
        sa.Column("normalized_quote", sa.Text(), nullable=False),
        sa.Column("page", sa.Integer(), nullable=False),
        sa.Column("bounding_box", sa.JSON(), nullable=True),
        sa.Column("article", sa.String(255), nullable=True),
        sa.Column("clause", sa.String(255), nullable=True),
        sa.Column("point", sa.String(255), nullable=True),
        sa.Column("source_confidence", sa.Float(), nullable=False),
        *_timestamps(),
    )
    op.create_index("ix_citations_document_id", "citations", ["document_id"])
    op.create_index("ix_citations_chunk_id", "citations", ["chunk_id"])
    op.create_index("ix_citations_owner", "citations", ["owner_type", "owner_id"])
    op.create_index("ix_citations_document_chunk", "citations", ["document_id", "chunk_id"])

    op.create_table(
        "graph_versions",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column(
            "document_id",
            sa.String(40),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "workflow_id",
            sa.String(40),
            sa.ForeignKey("ai_workflows.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("model_pipeline", sa.JSON(), nullable=False),
        sa.Column("validation_issues", sa.JSON(), nullable=False),
        *_timestamps(),
        sa.UniqueConstraint("document_id", "version", name="uq_graph_version_document_version"),
    )
    op.create_index("ix_graph_versions_document_id", "graph_versions", ["document_id"])
    op.create_index("ix_graph_versions_workflow_id", "graph_versions", ["workflow_id"])
    op.create_index("ix_graph_versions_status", "graph_versions", ["status"])
    op.create_index("ix_graph_versions_current", "graph_versions", ["document_id", "is_current"])

    op.create_table(
        "knowledge_nodes",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column(
            "graph_version_id",
            sa.String(40),
            sa.ForeignKey("graph_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "document_id",
            sa.String(40),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_key", sa.String(255), nullable=False),
        sa.Column("node_type", sa.String(60), nullable=False),
        sa.Column("name", sa.String(1000), nullable=False),
        sa.Column("canonical_name", sa.String(1000), nullable=False),
        sa.Column("normalized_key", sa.String(1000), nullable=False),
        sa.Column("properties", sa.JSON(), nullable=False),
        sa.Column("importance", sa.String(20), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        *_timestamps(),
    )
    op.create_index("ix_knowledge_nodes_graph_version_id", "knowledge_nodes", ["graph_version_id"])
    op.create_index("ix_knowledge_nodes_document_id", "knowledge_nodes", ["document_id"])
    op.create_index(
        "ix_knowledge_nodes_version_type", "knowledge_nodes", ["graph_version_id", "node_type"]
    )
    op.create_index(
        "ix_knowledge_nodes_normalized",
        "knowledge_nodes",
        ["graph_version_id", "normalized_key"],
    )

    op.create_table(
        "knowledge_edges",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column(
            "graph_version_id",
            sa.String(40),
            sa.ForeignKey("graph_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "document_id",
            sa.String(40),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_key", sa.String(255), nullable=False),
        sa.Column(
            "source_node_id",
            sa.String(40),
            sa.ForeignKey("knowledge_nodes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "target_node_id",
            sa.String(40),
            sa.ForeignKey("knowledge_nodes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("edge_type", sa.String(60), nullable=False),
        sa.Column("properties", sa.JSON(), nullable=False),
        sa.Column("importance", sa.String(20), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("verification_status", sa.String(30), nullable=False),
        *_timestamps(),
    )
    op.create_index("ix_knowledge_edges_graph_version_id", "knowledge_edges", ["graph_version_id"])
    op.create_index("ix_knowledge_edges_document_id", "knowledge_edges", ["document_id"])
    op.create_index("ix_knowledge_edges_source_node_id", "knowledge_edges", ["source_node_id"])
    op.create_index("ix_knowledge_edges_target_node_id", "knowledge_edges", ["target_node_id"])
    op.create_index(
        "ix_knowledge_edges_version_type", "knowledge_edges", ["graph_version_id", "edge_type"]
    )
    op.create_index(
        "ix_knowledge_edges_source_target",
        "knowledge_edges",
        ["source_node_id", "target_node_id"],
    )

    op.create_table(
        "red_flags",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column(
            "document_id",
            sa.String(40),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "graph_version_id",
            sa.String(40),
            sa.ForeignKey("graph_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "workflow_id",
            sa.String(40),
            sa.ForeignKey("ai_workflows.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("issue_type", sa.String(80), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("related_edge_ids", sa.JSON(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("verification_model", sa.String(100), nullable=True),
        sa.Column("verification_reason", sa.Text(), nullable=True),
        *_timestamps(),
    )
    op.create_index("ix_red_flags_document_id", "red_flags", ["document_id"])
    op.create_index("ix_red_flags_graph_version_id", "red_flags", ["graph_version_id"])
    op.create_index("ix_red_flags_workflow_id", "red_flags", ["workflow_id"])
    op.create_index("ix_red_flags_issue_type", "red_flags", ["issue_type"])
    op.create_index("ix_red_flags_severity", "red_flags", ["severity"])
    op.create_index("ix_red_flags_status", "red_flags", ["status"])
    op.create_index("ix_red_flags_document_severity", "red_flags", ["document_id", "severity"])
    op.create_index("ix_red_flags_document_status", "red_flags", ["document_id", "status"])

    op.create_table(
        "red_flag_nodes",
        sa.Column(
            "red_flag_id",
            sa.String(40),
            sa.ForeignKey("red_flags.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "node_id",
            sa.String(40),
            sa.ForeignKey("knowledge_nodes.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )

    op.create_table(
        "critical_questions",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column(
            "document_id",
            sa.String(40),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "workflow_id",
            sa.String(40),
            sa.ForeignKey("ai_workflows.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "red_flag_id",
            sa.String(40),
            sa.ForeignKey("red_flags.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("issue_type", sa.String(80), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("related_subject", sa.String(1000), nullable=False),
        sa.Column("source_location", sa.String(1000), nullable=False),
        sa.Column("risk_if_unresolved", sa.Text(), nullable=False),
        sa.Column("verification_status", sa.String(30), nullable=False),
        sa.Column("verification_model", sa.String(100), nullable=True),
        *_timestamps(),
    )
    op.create_index("ix_critical_questions_document_id", "critical_questions", ["document_id"])
    op.create_index("ix_critical_questions_workflow_id", "critical_questions", ["workflow_id"])
    op.create_index("ix_critical_questions_red_flag_id", "critical_questions", ["red_flag_id"])
    op.create_index(
        "ix_critical_questions_document_created",
        "critical_questions",
        ["document_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_table("critical_questions")
    op.drop_table("red_flag_nodes")
    op.drop_table("red_flags")
    op.drop_table("knowledge_edges")
    op.drop_table("knowledge_nodes")
    op.drop_table("graph_versions")
    op.drop_table("citations")
    op.drop_table("summary_items")
    op.drop_table("document_summaries")
    op.drop_table("model_executions")
    op.drop_table("ai_workflow_steps")
    op.drop_table("ai_workflows")
