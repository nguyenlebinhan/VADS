from __future__ import annotations

from enum import Enum

from pydantic import Field, model_validator

from app.common.contracts import APIModel


class ModelCapability(str, Enum):
    TEXT_GENERATION = "TEXT_GENERATION"
    STRUCTURED_OUTPUT = "STRUCTURED_OUTPUT"
    LONG_CONTEXT = "LONG_CONTEXT"
    VISION = "VISION"
    REASONING = "REASONING"
    PRIVATE_DEPLOYMENT = "PRIVATE_DEPLOYMENT"


class CostClass(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class TaskType(str, Enum):
    DOCUMENT_ANALYSIS = "DOCUMENT_ANALYSIS"
    DOCUMENT_SUMMARY = "DOCUMENT_SUMMARY"
    CROSS_DOCUMENT_ANALYSIS = "CROSS_DOCUMENT_ANALYSIS"
    ORCHESTRATOR_REASONING = "ORCHESTRATOR_REASONING"
    ENTITY_RELATION_EXTRACTION = "ENTITY_RELATION_EXTRACTION"
    ENTITY_NORMALIZATION = "ENTITY_NORMALIZATION"
    COMPLEX_RELATION_VERIFICATION = "COMPLEX_RELATION_VERIFICATION"
    RED_FLAG_DETECTION = "RED_FLAG_DETECTION"
    RED_FLAG_VERIFICATION = "RED_FLAG_VERIFICATION"
    CRITICAL_QUESTION_GENERATION = "CRITICAL_QUESTION_GENERATION"
    CRITICAL_QUESTION_VERIFICATION = "CRITICAL_QUESTION_VERIFICATION"
    PAGE_CLASSIFICATION = "PAGE_CLASSIFICATION"
    DIFFICULT_PAGE_ANALYSIS = "DIFFICULT_PAGE_ANALYSIS"
    LAYOUT_TABLE_ANALYSIS = "LAYOUT_TABLE_ANALYSIS"
    OCR_IMAGE_REVIEW = "OCR_IMAGE_REVIEW"
    METADATA_NORMALIZATION = "METADATA_NORMALIZATION"
    JSON_SCHEMA_REPAIR = "JSON_SCHEMA_REPAIR"
    PRIVATE_REASONING = "PRIVATE_REASONING"


class ModelMetadata(APIModel):
    alias: str
    capabilities: set[ModelCapability]
    supports_vision: bool = False
    supports_private_deployment: bool = False
    cost_class: CostClass
    enabled: bool = True
    fallback_models: list[str] = Field(default_factory=list)
    provider: str | None = None

    @model_validator(mode="after")
    def capabilities_match_flags(self) -> ModelMetadata:
        if self.supports_vision and ModelCapability.VISION not in self.capabilities:
            self.capabilities.add(ModelCapability.VISION)
        if self.supports_private_deployment:
            self.capabilities.add(ModelCapability.PRIVATE_DEPLOYMENT)
        return self


class RoutingPolicy(APIModel):
    task_type: TaskType
    preferred_models: list[str]
    private_preferred_models: list[str] = Field(default_factory=list)
    required_capabilities: set[ModelCapability] = Field(default_factory=set)
    reason: str
    timeout_seconds: int = Field(default=90, ge=1, le=900)
    max_retries: int = Field(default=2, ge=0, le=2)


class RoutingRequest(APIModel):
    task_type: TaskType
    require_private: bool = False
    require_vision: bool = False
    excluded_models: set[str] = Field(default_factory=set)


class RoutingDecision(APIModel):
    task_type: TaskType
    primary_model: str
    fallback_model: str | None = None
    reason_for_selection: str
    timeout_seconds: int
    max_retries: int
