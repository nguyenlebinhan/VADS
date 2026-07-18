from typing import Any

from app.model_gateway.gateway import ModelGateway


class ModelGatewayChatAdapter:
    """Adapts the shared provider gateway to the Chat module contract."""

    def __init__(self, gateway: ModelGateway) -> None:
        self.gateway = gateway

    def generate(
        self,
        *,
        model_alias: str,
        prompt: str,
        context: list[dict[str, Any]],
        private: bool,
    ) -> str:
        context_text = "\n\n".join(
            f"[Nguồn {index}] {item.get('content', '')}"
            for index, item in enumerate(context, start=1)
        )
        response = self.gateway.generate_text(
            model_alias=model_alias,
            prompt=(
                "Chỉ trả lời dựa trên các nguồn bên dưới. Không tự tạo dữ kiện.\n\n"
                f"Câu hỏi: {prompt}\n\nNguồn:\n{context_text}"
            ),
            metadata={"private": private, "sourceCount": len(context)},
        )
        return response.content
