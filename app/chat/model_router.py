from typing import Any, Protocol


class ModelRouter(Protocol):
    """Structural integration contract for Owner 2's future ModelRouter."""

    def generate(
        self,
        *,
        model_alias: str,
        prompt: str,
        context: list[dict[str, Any]],
        private: bool,
    ) -> str: ...
