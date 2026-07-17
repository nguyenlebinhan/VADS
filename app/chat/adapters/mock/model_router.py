from typing import Any


class MockModelRouter:
    """Deterministic test/local generator; never used as an embedding engine."""

    def generate(
        self,
        *,
        model_alias: str,
        prompt: str,
        context: list[dict[str, Any]],
        private: bool,
    ) -> str:
        del model_alias, prompt, private
        if not context:
            return "Không tìm thấy thông tin phù hợp trong các tài liệu đã chọn."
        source = str(context[0]["content"]).strip()
        return f"Theo tài liệu được trích dẫn: {source[:600]}"
