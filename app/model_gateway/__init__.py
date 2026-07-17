"""Provider-neutral model access and policy-driven routing."""

from app.model_gateway.gateway import (
    CallableModelGateway,
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
    "ModelCapability",
    "ModelGateway",
    "ModelMetadata",
    "ModelRegistry",
    "ModelResponse",
    "ModelRouter",
    "RoutingDecision",
    "RoutingPolicy",
    "RoutingRequest",
    "TaskType",
    "UnavailableModelGateway",
    "build_default_registry",
]
