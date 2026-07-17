from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import Field, model_validator

from app.citations.schemas import CitationDraft, CitationView
from app.common.contracts import APIModel


class NodeType(str, Enum):
    LEGAL_DOCUMENT = "LEGAL_DOCUMENT"
    LEGAL_PROVISION = "LEGAL_PROVISION"
    AGENCY = "AGENCY"
    PERSON = "PERSON"
    ROLE = "ROLE"
    TASK = "TASK"
    RESPONSIBILITY = "RESPONSIBILITY"
    AUTHORITY = "AUTHORITY"
    PROCEDURE = "PROCEDURE"
    DOSSIER = "DOSSIER"
    FORM = "FORM"
    DEADLINE = "DEADLINE"
    FUNDING_SOURCE = "FUNDING_SOURCE"
    BUDGET = "BUDGET"
    OUTPUT = "OUTPUT"
    REPORT = "REPORT"
    LEGAL_REFERENCE = "LEGAL_REFERENCE"
    EFFECTIVE_DATE = "EFFECTIVE_DATE"


class EdgeType(str, Enum):
    CONTAINS = "CONTAINS"
    APPLIES_TO = "APPLIES_TO"
    ASSIGNS_RESPONSIBILITY = "ASSIGNS_RESPONSIBILITY"
    GRANTS_AUTHORITY = "GRANTS_AUTHORITY"
    LEADS = "LEADS"
    COORDINATES_WITH = "COORDINATES_WITH"
    REQUIRES = "REQUIRES"
    SUBMITS = "SUBMITS"
    APPROVES = "APPROVES"
    REPORTS_TO = "REPORTS_TO"
    HAS_DEADLINE = "HAS_DEADLINE"
    HAS_FUNDING_SOURCE = "HAS_FUNDING_SOURCE"
    HAS_BUDGET = "HAS_BUDGET"
    PRODUCES = "PRODUCES"
    USES_FORM = "USES_FORM"
    REFERENCES = "REFERENCES"
    REPEALS = "REPEALS"
    REPLACES = "REPLACES"
    TAKES_EFFECT_ON = "TAKES_EFFECT_ON"


class GraphImportance(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class VerificationStatus(str, Enum):
    NOT_REQUIRED = "NOT_REQUIRED"
    VERIFIED = "VERIFIED"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class GraphVersionStatus(str, Enum):
    COMPLETED = "COMPLETED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    SUPERSEDED = "SUPERSEDED"


class KnowledgeNodeDraft(APIModel):
    node_id: str = Field(min_length=1, max_length=255)
    type: NodeType
    name: str = Field(min_length=1)
    canonical_name: str | None = None
    normalized_key: str | None = None
    properties: dict[str, Any] = Field(default_factory=dict)
    importance: GraphImportance = GraphImportance.MEDIUM
    confidence: float = Field(ge=0, le=1)
    citations: list[CitationDraft] = Field(default_factory=list)


class KnowledgeEdgeDraft(APIModel):
    edge_id: str = Field(min_length=1, max_length=255)
    source_node_id: str = Field(min_length=1)
    target_node_id: str = Field(min_length=1)
    type: EdgeType
    properties: dict[str, Any] = Field(default_factory=dict)
    importance: GraphImportance = GraphImportance.MEDIUM
    confidence: float = Field(ge=0, le=1)
    citations: list[CitationDraft] = Field(default_factory=list)
    verification_status: VerificationStatus = VerificationStatus.NOT_REQUIRED


class GraphExtractionOutput(APIModel):
    nodes: list[KnowledgeNodeDraft] = Field(default_factory=list)
    edges: list[KnowledgeEdgeDraft] = Field(default_factory=list)

    @model_validator(mode="after")
    def identifiers_are_unique(self) -> GraphExtractionOutput:
        node_ids = [node.node_id for node in self.nodes]
        edge_ids = [edge.edge_id for edge in self.edges]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("nodeId values must be unique")
        if len(edge_ids) != len(set(edge_ids)):
            raise ValueError("edgeId values must be unique")
        return self


class RelationVerification(APIModel):
    edge_id: str
    verified: bool
    evidence_sufficient: bool
    reason: str


class RelationVerificationOutput(APIModel):
    verifications: list[RelationVerification] = Field(default_factory=list)


class GraphValidationIssue(APIModel):
    code: str
    element_type: str
    element_id: str
    message: str


class KnowledgeNodeView(APIModel):
    id: str
    type: NodeType
    name: str
    canonical_name: str
    normalized_key: str
    properties: dict[str, Any]
    importance: GraphImportance
    confidence: float
    citations: list[CitationView] = Field(default_factory=list)


class KnowledgeEdgeView(APIModel):
    id: str
    source_node_id: str
    target_node_id: str
    type: EdgeType
    properties: dict[str, Any]
    importance: GraphImportance
    confidence: float
    verification_status: VerificationStatus
    citations: list[CitationView] = Field(default_factory=list)


class KnowledgeGraphView(APIModel):
    version_id: str
    document_id: str
    workflow_id: str
    version: int
    status: GraphVersionStatus
    is_current: bool
    created_at: datetime
    nodes: list[KnowledgeNodeView] = Field(default_factory=list)
    edges: list[KnowledgeEdgeView] = Field(default_factory=list)


class KnowledgeGraphGenerationResult(APIModel):
    workflow_id: str
    graph: KnowledgeGraphView | None = None
