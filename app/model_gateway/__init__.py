"""Provider-neutral model access and policy-driven routing."""

from app.model_gateway.fpt_ai import (
    DEFAULT_FPT_MODEL_MAP,
    FptAiGatewayConfig,
    FptAiModelGateway,
    build_fpt_ai_gateway,
)
from app.model_gateway.gateway import (
    CallableModelGateway,
    MetadataModelGateway,
    ModelGateway,
    ModelResponse,
    UnavailableModelGateway,
)
from app.model_gateway.registry import ModelRegistry, build_default_registry
from app.model_gateway.router import ModelRouter
from app.model_gateway.schemas import (
    CostClass,
    ModelCapability,
    ModelMetadata,
    RoutingDecision,
    RoutingPolicy,
    RoutingRequest,
    TaskType,
)

__all__ = [
    "CallableModelGateway",
    "CostClass",
    "DEFAULT_FPT_MODEL_MAP",
    "FptAiGatewayConfig",
    "FptAiModelGateway",
    "ModelCapability",
    "ModelGateway",
    "MetadataModelGateway",
    "ModelMetadata",
    "ModelRegistry",
    "ModelResponse",
    "ModelRouter",
    "RoutingDecision",
    "RoutingPolicy",
    "RoutingRequest",
    "TaskType",
    "UnavailableModelGateway",
    "build_fpt_ai_gateway",
    "build_default_registry",
]
