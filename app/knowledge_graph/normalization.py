from __future__ import annotations

import re
import unicodedata
from collections import defaultdict

from app.citations.schemas import CitationDraft
from app.knowledge_graph.schemas import (
    GraphExtractionOutput,
    GraphImportance,
    KnowledgeEdgeDraft,
    KnowledgeNodeDraft,
)

_IMPORTANCE_RANK = {
    GraphImportance.LOW: 0,
    GraphImportance.MEDIUM: 1,
    GraphImportance.HIGH: 2,
    GraphImportance.CRITICAL: 3,
}


class NodeNormalizer:
    _parenthetical_acronym = re.compile(r"\s*\([A-ZĐ]{2,12}\)\s*$", re.UNICODE)

    def normalize_name(self, value: str) -> tuple[str, str]:
        canonical = " ".join(unicodedata.normalize("NFKC", value).split()).strip(" ,.;")
        canonical = self._parenthetical_acronym.sub("", canonical).strip()
        decomposed = unicodedata.normalize("NFD", canonical.casefold())
        ascii_like = "".join(char for char in decomposed if unicodedata.category(char) != "Mn")
        ascii_like = ascii_like.replace("đ", "d")
        normalized = re.sub(r"[^a-z0-9]+", " ", ascii_like).strip()
        return canonical, normalized

    def normalize_node(self, node: KnowledgeNodeDraft) -> KnowledgeNodeDraft:
        canonical, normalized = self.normalize_name(node.canonical_name or node.name)
        return node.model_copy(
            update={
                "canonical_name": canonical,
                "normalized_key": f"{node.type.value}:{normalized}",
            }
        )

    def normalize(self, graph: GraphExtractionOutput) -> GraphExtractionOutput:
        return GraphExtractionOutput(
            nodes=[self.normalize_node(node) for node in graph.nodes],
            edges=graph.edges,
        )


def _citation_key(citation: CitationDraft) -> tuple[str, str, str, int]:
    return citation.document_id, citation.chunk_id, citation.quote, citation.page


def _merge_citations(*groups: list[CitationDraft]) -> list[CitationDraft]:
    merged: dict[tuple[str, str, str, int], CitationDraft] = {}
    for citation in (citation for group in groups for citation in group):
        key = _citation_key(citation)
        current = merged.get(key)
        if current is None or citation.source_confidence > current.source_confidence:
            merged[key] = citation
    return list(merged.values())


class GraphDeduplicator:
    """Rule-based exact canonical deduplication after model normalization."""

    def deduplicate(self, graph: GraphExtractionOutput) -> GraphExtractionOutput:
        by_key: dict[str, KnowledgeNodeDraft] = {}
        id_mapping: dict[str, str] = {}
        for node in graph.nodes:
            key = node.normalized_key or f"{node.type.value}:{node.name.casefold()}"
            existing = by_key.get(key)
            if existing is None:
                by_key[key] = node
                id_mapping[node.node_id] = node.node_id
                continue
            id_mapping[node.node_id] = existing.node_id
            merged = existing.model_copy(
                update={
                    "properties": {**node.properties, **existing.properties},
                    "confidence": max(existing.confidence, node.confidence),
                    "importance": max(
                        (existing.importance, node.importance),
                        key=_IMPORTANCE_RANK.__getitem__,
                    ),
                    "citations": _merge_citations(existing.citations, node.citations),
                }
            )
            by_key[key] = merged

        edge_groups: dict[tuple[str, str, str], list[KnowledgeEdgeDraft]] = defaultdict(list)
        for edge in graph.edges:
            source = id_mapping.get(edge.source_node_id, edge.source_node_id)
            target = id_mapping.get(edge.target_node_id, edge.target_node_id)
            remapped = edge.model_copy(update={"source_node_id": source, "target_node_id": target})
            edge_groups[(source, target, edge.type.value)].append(remapped)

        edges: list[KnowledgeEdgeDraft] = []
        for duplicates in edge_groups.values():
            first = duplicates[0]
            if len(duplicates) == 1:
                edges.append(first)
                continue
            properties: dict[str, object] = {}
            for duplicate in duplicates:
                properties.update(duplicate.properties)
            edges.append(
                first.model_copy(
                    update={
                        "properties": properties,
                        "confidence": max(edge.confidence for edge in duplicates),
                        "importance": max(
                            (edge.importance for edge in duplicates),
                            key=_IMPORTANCE_RANK.__getitem__,
                        ),
                        "citations": _merge_citations(*(edge.citations for edge in duplicates)),
                    }
                )
            )
        return GraphExtractionOutput(nodes=list(by_key.values()), edges=edges)
