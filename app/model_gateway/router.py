from __future__ import annotations

from collections.abc import Callable, Iterable

from app.model_gateway.errors import ModelRoutingError
from app.model_gateway.registry import ModelRegistry
from app.model_gateway.schemas import (
    ModelCapability,
    ModelMetadata,
    RoutingDecision,
    RoutingRequest,
)


class ModelRouter:
    """Selects from registry policy without embedding aliases in routing code."""

    def __init__(
        self,
        registry: ModelRegistry,
        availability_check: Callable[[str], bool] | None = None,
    ) -> None:
        self.registry = registry
        self.availability_check = availability_check

    def route(self, request: RoutingRequest) -> RoutingDecision:
        policy = self.registry.get_policy(request.task_type)
        preferred = (
            policy.private_preferred_models if request.require_private else policy.preferred_models
        )
        primary = self._first_eligible(preferred, request, policy.required_capabilities)
        if primary is None:
            raise ModelRoutingError(
                f"No eligible model for task {request.task_type.value} "
                f"(private={request.require_private}, vision={request.require_vision})"
            )

        fallback = self._first_eligible(
            primary.fallback_models,
            request,
            policy.required_capabilities,
            extra_excluded={primary.alias},
        )
        return RoutingDecision(
            taskType=request.task_type,
            primaryModel=primary.alias,
            fallbackModel=fallback.alias if fallback else None,
            reasonForSelection=policy.reason,
            timeoutSeconds=policy.timeout_seconds,
            maxRetries=policy.max_retries,
        )

    def _first_eligible(
        self,
        aliases: Iterable[str],
        request: RoutingRequest,
        required_capabilities: set[ModelCapability],
        *,
        extra_excluded: set[str] | None = None,
    ) -> ModelMetadata | None:
        excluded = request.excluded_models | (extra_excluded or set())
        for alias in aliases:
            if alias in excluded:
                continue
            model = self.registry.get_model(alias)
            if not model.enabled:
                continue
            if request.require_private and not model.supports_private_deployment:
                continue
            if request.require_vision and not model.supports_vision:
                continue
            if not required_capabilities.issubset(model.capabilities):
                continue
            if self.availability_check is not None and not self.availability_check(alias):
                continue
            return model
        return None
