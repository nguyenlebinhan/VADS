from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.knowledge_graph.models import GraphVersion, KnowledgeEdge, KnowledgeNode
from app.knowledge_graph.schemas import (
    GraphVersionStatus,
    KnowledgeEdgeDraft,
    KnowledgeNodeDraft,
)


class KnowledgeGraphRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def next_version(self, document_id: str) -> int:
        statement = select(func.max(GraphVersion.version)).where(
            GraphVersion.document_id == document_id
        )
        return int(self.session.scalar(statement) or 0) + 1

    def create_version(
        self,
        *,
        document_id: str,
        workflow_id: str,
        status: GraphVersionStatus,
        model_pipeline: list[str],
        validation_issues: list[dict[str, Any]],
    ) -> GraphVersion:
        for previous in self.list_versions(document_id):
            if previous.is_current:
                previous.is_current = False
                if previous.status == GraphVersionStatus.COMPLETED.value:
                    previous.status = GraphVersionStatus.SUPERSEDED.value
        version = GraphVersion(
            document_id=document_id,
            workflow_id=workflow_id,
            version=self.next_version(document_id),
            status=status.value,
            is_current=True,
            model_pipeline=model_pipeline,
            validation_issues=validation_issues,
        )
        self.session.add(version)
        self.session.flush()
        return version

    def add_node(
        self,
        version: GraphVersion,
        draft: KnowledgeNodeDraft,
    ) -> KnowledgeNode:
        node = KnowledgeNode(
            graph_version_id=version.id,
            document_id=version.document_id,
            source_key=draft.node_id,
            node_type=draft.type.value,
            name=draft.name,
            canonical_name=draft.canonical_name or draft.name,
            normalized_key=draft.normalized_key or draft.name.casefold(),
            properties=draft.properties,
            importance=draft.importance.value,
            confidence=draft.confidence,
        )
        self.session.add(node)
        self.session.flush()
        return node

    def add_edge(
        self,
        version: GraphVersion,
        draft: KnowledgeEdgeDraft,
        *,
        source_node_id: str,
        target_node_id: str,
    ) -> KnowledgeEdge:
        edge = KnowledgeEdge(
            graph_version_id=version.id,
            document_id=version.document_id,
            source_key=draft.edge_id,
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            edge_type=draft.type.value,
            properties=draft.properties,
            importance=draft.importance.value,
            confidence=draft.confidence,
            verification_status=draft.verification_status.value,
        )
        self.session.add(edge)
        self.session.flush()
        return edge

    def get_version(self, version_id: str) -> GraphVersion | None:
        return self.session.get(GraphVersion, version_id)

    def get_latest(self, document_id: str) -> GraphVersion | None:
        statement = (
            select(GraphVersion)
            .where(GraphVersion.document_id == document_id, GraphVersion.is_current.is_(True))
            .order_by(GraphVersion.version.desc())
        )
        return self.session.scalar(statement)

    def list_versions(self, document_id: str) -> list[GraphVersion]:
        statement = (
            select(GraphVersion)
            .where(GraphVersion.document_id == document_id)
            .order_by(GraphVersion.version.desc())
        )
        return list(self.session.scalars(statement))

    def list_nodes(self, version_id: str) -> list[KnowledgeNode]:
        statement = (
            select(KnowledgeNode)
            .where(KnowledgeNode.graph_version_id == version_id)
            .order_by(KnowledgeNode.node_type, KnowledgeNode.canonical_name)
        )
        return list(self.session.scalars(statement))

    def list_edges(self, version_id: str) -> list[KnowledgeEdge]:
        statement = (
            select(KnowledgeEdge)
            .where(KnowledgeEdge.graph_version_id == version_id)
            .order_by(KnowledgeEdge.edge_type, KnowledgeEdge.id)
        )
        return list(self.session.scalars(statement))
