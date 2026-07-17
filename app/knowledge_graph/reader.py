from __future__ import annotations

from typing import Protocol

from sqlalchemy.orm import Session

from app.citations.reader import CitationReader, SqlAlchemyCitationReader
from app.citations.schemas import CitationOwnerType
from app.knowledge_graph.models import GraphVersion
from app.knowledge_graph.repository import KnowledgeGraphRepository
from app.knowledge_graph.schemas import (
    KnowledgeEdgeView,
    KnowledgeGraphView,
    KnowledgeNodeView,
)


class KnowledgeGraphReader(Protocol):
    def get_graph(self, document_id: str) -> KnowledgeGraphView | None: ...

    def get_version(self, version_id: str) -> KnowledgeGraphView | None: ...


class SqlAlchemyKnowledgeGraphReader:
    def __init__(self, session: Session, citation_reader: CitationReader | None = None) -> None:
        self.repository = KnowledgeGraphRepository(session)
        self.citation_reader = citation_reader or SqlAlchemyCitationReader(session)

    def get_graph(self, document_id: str) -> KnowledgeGraphView | None:
        version = self.repository.get_latest(document_id)
        return self._view(version) if version else None

    def get_version(self, version_id: str) -> KnowledgeGraphView | None:
        version = self.repository.get_version(version_id)
        return self._view(version) if version else None

    def _view(self, version: GraphVersion) -> KnowledgeGraphView:
        nodes = [
            KnowledgeNodeView(
                id=node.id,
                type=node.node_type,
                name=node.name,
                canonicalName=node.canonical_name,
                normalizedKey=node.normalized_key,
                properties=node.properties,
                importance=node.importance,
                confidence=node.confidence,
                citations=self.citation_reader.list_for_owner(
                    CitationOwnerType.KNOWLEDGE_NODE,
                    node.id,
                ),
            )
            for node in self.repository.list_nodes(version.id)
        ]
        edges = [
            KnowledgeEdgeView(
                id=edge.id,
                sourceNodeId=edge.source_node_id,
                targetNodeId=edge.target_node_id,
                type=edge.edge_type,
                properties=edge.properties,
                importance=edge.importance,
                confidence=edge.confidence,
                verificationStatus=edge.verification_status,
                citations=self.citation_reader.list_for_owner(
                    CitationOwnerType.KNOWLEDGE_EDGE,
                    edge.id,
                ),
            )
            for edge in self.repository.list_edges(version.id)
        ]
        return KnowledgeGraphView(
            versionId=version.id,
            documentId=version.document_id,
            workflowId=version.workflow_id,
            version=version.version,
            status=version.status,
            isCurrent=version.is_current,
            createdAt=version.created_at,
            nodes=nodes,
            edges=edges,
        )
