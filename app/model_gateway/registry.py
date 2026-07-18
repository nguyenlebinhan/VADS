from __future__ import annotations

from collections.abc import Iterable

from app.model_gateway.errors import ModelRoutingError
from app.model_gateway.schemas import (
    CostClass,
    ModelCapability,
    ModelMetadata,
    RoutingPolicy,
    TaskType,
)


class ModelRegistry:
    """Owns model metadata and routing policy; the router contains no model names."""

    def __init__(
        self,
        models: Iterable[ModelMetadata] = (),
        policies: Iterable[RoutingPolicy] = (),
    ) -> None:
        self._models: dict[str, ModelMetadata] = {}
        self._policies: dict[TaskType, RoutingPolicy] = {}
        for model in models:
            self.register_model(model)
        for policy in policies:
            self.register_policy(policy)

    def register_model(self, metadata: ModelMetadata, *, replace: bool = False) -> None:
        if metadata.alias in self._models and not replace:
            raise ValueError(f"Model alias already registered: {metadata.alias}")
        self._models[metadata.alias] = metadata

    def register_policy(self, policy: RoutingPolicy, *, replace: bool = False) -> None:
        if policy.task_type in self._policies and not replace:
            raise ValueError(f"Routing policy already registered: {policy.task_type}")
        unknown = [
            alias
            for alias in policy.preferred_models + policy.private_preferred_models
            if alias not in self._models
        ]
        if unknown:
            raise ValueError(f"Routing policy references unknown models: {unknown}")
        self._policies[policy.task_type] = policy

    def get_model(self, alias: str) -> ModelMetadata:
        try:
            return self._models[alias]
        except KeyError as exc:
            raise ModelRoutingError(f"Unknown model alias: {alias}") from exc

    def get_policy(self, task_type: TaskType) -> RoutingPolicy:
        try:
            return self._policies[task_type]
        except KeyError as exc:
            raise ModelRoutingError(f"No routing policy for task: {task_type.value}") from exc

    def list_models(self, *, enabled_only: bool = False) -> list[ModelMetadata]:
        models = list(self._models.values())
        if enabled_only:
            models = [model for model in models if model.enabled]
        return models

    def set_enabled(self, alias: str, enabled: bool) -> None:
        current = self.get_model(alias)
        self._models[alias] = current.model_copy(update={"enabled": enabled})


def _model(
    alias: str,
    capabilities: set[ModelCapability],
    *,
    cost: CostClass,
    fallbacks: list[str] | None = None,
    vision: bool = False,
    private: bool = False,
) -> ModelMetadata:
    return ModelMetadata(
        alias=alias,
        capabilities=capabilities,
        supportsVision=vision,
        supportsPrivateDeployment=private,
        costClass=cost,
        fallbackModels=fallbacks or [],
    )


def build_default_registry() -> ModelRegistry:
    text = {
        ModelCapability.TEXT_GENERATION,
        ModelCapability.STRUCTURED_OUTPUT,
        ModelCapability.LONG_CONTEXT,
    }
    reasoning = text | {ModelCapability.REASONING}
    vision = text | {ModelCapability.VISION}
    models = [
        _model(
            "GLM-5.2",
            reasoning,
            cost=CostClass.HIGH,
            fallbacks=["gpt-oss-120b", "GLM-5.1", "DeepSeek-V4-Flash"],
        ),
        _model(
            "DeepSeek-V4-Flash",
            text,
            cost=CostClass.MEDIUM,
            fallbacks=["GLM-5.1", "Qwen3.6-27B", "gpt-oss-120b"],
        ),
        _model(
            "gemma-4-26B-A4B-it",
            vision,
            cost=CostClass.MEDIUM,
            fallbacks=["gemma-4-31B-it", "Gemma-3-27B"],
            vision=True,
        ),
        _model(
            "gemma-4-31B-it",
            vision,
            cost=CostClass.HIGH,
            fallbacks=["Gemma-3-27B"],
            vision=True,
        ),
        _model(
            "Qwen2.5-VL-7B-Instruct",
            vision,
            cost=CostClass.LOW,
            fallbacks=["gemma-4-26B-A4B-it"],
            vision=True,
        ),
        _model(
            "gpt-oss-20b",
            text,
            cost=CostClass.LOW,
            fallbacks=["Qwen3.6-27B", "SaoLa3.1-medium", "DeepSeek-V4-Flash"],
            private=True,
        ),
        _model(
            "gpt-oss-120b",
            reasoning,
            cost=CostClass.HIGH,
            fallbacks=["Qwen3.6-27B", "Llama-3.3-70B-Instruct"],
            private=True,
        ),
        _model("GLM-5.1", reasoning, cost=CostClass.HIGH),
        _model("Qwen3.6-27B", text, cost=CostClass.MEDIUM, private=True),
        _model("Llama-3.3-70B-Instruct", text, cost=CostClass.HIGH, private=True),
        _model("SaoLa3.1-medium", text, cost=CostClass.LOW, private=True),
        _model("Gemma-3-27B", vision, cost=CostClass.MEDIUM, vision=True),
    ]

    def policy(
        task: TaskType,
        preferred: list[str],
        reason: str,
        *,
        required: set[ModelCapability] | None = None,
        private_preferred: list[str] | None = None,
        timeout: int = 90,
    ) -> RoutingPolicy:
        return RoutingPolicy(
            taskType=task,
            preferredModels=preferred,
            privatePreferredModels=private_preferred or ["gpt-oss-120b"],
            requiredCapabilities=required or {ModelCapability.STRUCTURED_OUTPUT},
            reason=reason,
            timeoutSeconds=timeout,
            maxRetries=2,
        )

    policies = [
        policy(
            TaskType.DOCUMENT_SUMMARY,
            ["DeepSeek-V4-Flash"],
            "Tác vụ tóm tắt có cấu trúc cho một tài liệu",
        ),
        policy(
            TaskType.CROSS_DOCUMENT_ANALYSIS,
            ["GLM-5.2"],
            "Cần reasoning và đối chiếu nhiều tài liệu",
            required={ModelCapability.REASONING, ModelCapability.LONG_CONTEXT},
        ),
        policy(
            TaskType.ORCHESTRATOR_REASONING,
            ["GLM-5.2"],
            "Lập kế hoạch và hợp nhất kết quả phức tạp",
            required={ModelCapability.REASONING},
        ),
        policy(
            TaskType.ENTITY_RELATION_EXTRACTION,
            ["DeepSeek-V4-Flash"],
            "Trích xuất entity và relation sơ bộ",
        ),
        policy(
            TaskType.ENTITY_NORMALIZATION,
            ["gpt-oss-20b"],
            "Chuẩn hóa type, tên và metadata entity",
            private_preferred=["gpt-oss-20b", "gpt-oss-120b"],
        ),
        policy(
            TaskType.COMPLEX_RELATION_VERIFICATION,
            ["GLM-5.2"],
            "Kiểm chứng relation phức tạp hoặc mâu thuẫn",
            required={ModelCapability.REASONING, ModelCapability.STRUCTURED_OUTPUT},
        ),
        policy(
            TaskType.RED_FLAG_VERIFICATION,
            ["GLM-5.2"],
            "Kiểm chứng cảnh báo HIGH hoặc CRITICAL",
            required={ModelCapability.REASONING, ModelCapability.STRUCTURED_OUTPUT},
        ),
        policy(
            TaskType.CRITICAL_QUESTION_GENERATION,
            ["DeepSeek-V4-Flash"],
            "Sinh câu hỏi phản biện bám theo bằng chứng",
        ),
        policy(
            TaskType.CRITICAL_QUESTION_VERIFICATION,
            ["GLM-5.2"],
            "Kiểm chứng câu hỏi phản biện phức tạp",
            required={ModelCapability.REASONING, ModelCapability.STRUCTURED_OUTPUT},
        ),
        policy(
            TaskType.PAGE_CLASSIFICATION,
            ["Qwen2.5-VL-7B-Instruct"],
            "Phân loại trang bằng vision nhẹ",
            required={ModelCapability.VISION},
            timeout=60,
        ),
        policy(
            TaskType.DIFFICULT_PAGE_ANALYSIS,
            ["gemma-4-26B-A4B-it"],
            "Phân tích trang scan khó",
            required={ModelCapability.VISION},
        ),
        policy(
            TaskType.LAYOUT_TABLE_ANALYSIS,
            ["gemma-4-26B-A4B-it"],
            "Kiểm tra layout và bảng",
            required={ModelCapability.VISION},
        ),
        policy(
            TaskType.OCR_IMAGE_REVIEW,
            ["gemma-4-26B-A4B-it"],
            "Kiểm tra kết quả OCR bằng ảnh",
            required={ModelCapability.VISION},
        ),
        policy(
            TaskType.METADATA_NORMALIZATION,
            ["gpt-oss-20b"],
            "Phân loại và chuẩn hóa metadata",
            private_preferred=["gpt-oss-20b", "gpt-oss-120b"],
        ),
        policy(
            TaskType.JSON_SCHEMA_REPAIR,
            ["gpt-oss-20b"],
            "Sửa output JSON theo schema",
            private_preferred=["gpt-oss-20b", "gpt-oss-120b"],
        ),
        policy(
            TaskType.PRIVATE_REASONING,
            ["gpt-oss-120b"],
            "Reasoning trong private cloud/on-premise",
            private_preferred=["gpt-oss-120b"],
            required={ModelCapability.REASONING, ModelCapability.PRIVATE_DEPLOYMENT},
        ),
    ]
    return ModelRegistry(models, policies)
