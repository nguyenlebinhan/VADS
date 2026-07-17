from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.model.base import Base, TimestampMixin, prefixed_uuid


class GraphVersion(TimestampMixin, Base):
    __tablename__ = "graph_versions"
    __table_args__ = (
        UniqueConstraint("document_id", "version", name="uq_graph_version_document_version"),
        Index("ix_graph_versions_current", "document_id", "is_current"),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=prefixed_uuid("graph"))
    document_id: Mapped[str] = mapped_column(
        String(40),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workflow_id: Mapped[str] = mapped_column(
        String(40),
        ForeignKey("ai_workflows.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    model_pipeline: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    validation_issues: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )


class KnowledgeNode(TimestampMixin, Base):
    __tablename__ = "knowledge_nodes"
    __table_args__ = (
        Index("ix_knowledge_nodes_version_type", "graph_version_id", "node_type"),
        Index("ix_knowledge_nodes_normalized", "graph_version_id", "normalized_key"),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=prefixed_uuid("knode"))
    graph_version_id: Mapped[str] = mapped_column(
        String(40),
        ForeignKey("graph_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[str] = mapped_column(
        String(40),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_key: Mapped[str] = mapped_column(String(255), nullable=False)
    node_type: Mapped[str] = mapped_column(String(60), nullable=False)
    name: Mapped[str] = mapped_column(String(1000), nullable=False)
    canonical_name: Mapped[str] = mapped_column(String(1000), nullable=False)
    normalized_key: Mapped[str] = mapped_column(String(1000), nullable=False)
    properties: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    importance: Mapped[str] = mapped_column(String(20), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)


class KnowledgeEdge(TimestampMixin, Base):
    __tablename__ = "knowledge_edges"
    __table_args__ = (
        Index("ix_knowledge_edges_version_type", "graph_version_id", "edge_type"),
        Index("ix_knowledge_edges_source_target", "source_node_id", "target_node_id"),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=prefixed_uuid("kedge"))
    graph_version_id: Mapped[str] = mapped_column(
        String(40),
        ForeignKey("graph_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[str] = mapped_column(
        String(40),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_key: Mapped[str] = mapped_column(String(255), nullable=False)
    source_node_id: Mapped[str] = mapped_column(
        String(40),
        ForeignKey("knowledge_nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_node_id: Mapped[str] = mapped_column(
        String(40),
        ForeignKey("knowledge_nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    edge_type: Mapped[str] = mapped_column(String(60), nullable=False)
    properties: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    importance: Mapped[str] = mapped_column(String(20), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    verification_status: Mapped[str] = mapped_column(String(30), nullable=False)
