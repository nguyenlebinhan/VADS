class ModelGatewayError(RuntimeError):
    """Base error raised by a model adapter."""


class ModelUnavailableError(ModelGatewayError):
    def __init__(self, model_alias: str, message: str | None = None) -> None:
        self.model_alias = model_alias
        super().__init__(message or f"Model {model_alias!r} is unavailable")


class StructuredOutputError(ModelGatewayError):
    def __init__(self, model_alias: str, detail: str, raw_output: object = None) -> None:
        self.model_alias = model_alias
        self.detail = detail
        self.raw_output = raw_output
        super().__init__(f"Invalid structured output from {model_alias!r}: {detail}")


class ModelRoutingError(ModelGatewayError):
    pass
