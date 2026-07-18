class ModelGatewayError(RuntimeError):
    """Base error raised by a model adapter."""


class ModelUnavailableError(ModelGatewayError):
    def __init__(self, model_alias: str, message: str | None = None) -> None:
        self.model_alias = model_alias
        super().__init__(message or f"Model {model_alias!r} is unavailable")


class ModelRateLimitError(ModelUnavailableError):
    """Provider rejected the request because its shared quota is exhausted."""

    def __init__(
        self,
        model_alias: str,
        message: str | None = None,
        *,
        retry_after_seconds: int | None = None,
    ) -> None:
        self.retry_after_seconds = retry_after_seconds
        super().__init__(model_alias, message or "Model provider rate limit exceeded")


class StructuredOutputError(ModelGatewayError):
    def __init__(self, model_alias: str, detail: str, raw_output: object = None) -> None:
        self.model_alias = model_alias
        self.detail = detail
        self.raw_output = raw_output
        super().__init__(f"Invalid structured output from {model_alias!r}: {detail}")


class ModelRoutingError(ModelGatewayError):
    pass
