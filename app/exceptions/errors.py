from typing import Any


class AppError(Exception):
    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        message: str,
        details: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details


class NotFoundError(AppError):
    def __init__(self, resource: str, resource_id: str) -> None:
        names = {
            "WORKSPACE": "workspace",
            "DOCUMENT": "tài liệu",
            "DOCUMENT_PAGE": "trang tài liệu",
            "PROCESSING_JOB": "processing job",
            "CHUNK": "chunk",
        }
        super().__init__(
            status_code=404,
            code=f"{resource.upper()}_NOT_FOUND",
            message=f"Không tìm thấy {names.get(resource.upper(), resource.lower())}.",
            details={"id": resource_id},
        )


class ConflictError(AppError):
    def __init__(self, code: str, message: str, details: Any | None = None) -> None:
        super().__init__(status_code=409, code=code, message=message, details=details)


class UnsupportedMediaTypeError(AppError):
    def __init__(self, code: str, message: str, details: Any | None = None) -> None:
        super().__init__(status_code=415, code=code, message=message, details=details)


class PayloadTooLargeError(AppError):
    def __init__(self, max_size_bytes: int) -> None:
        super().__init__(
            status_code=413,
            code="FILE_TOO_LARGE",
            message="Tệp vượt quá dung lượng tối đa cho phép.",
            details={"maxSizeBytes": max_size_bytes},
        )


class StorageUnavailableError(AppError):
    def __init__(self) -> None:
        super().__init__(
            status_code=503,
            code="OBJECT_STORAGE_UNAVAILABLE",
            message="Kho lưu trữ tệp tạm thời không khả dụng.",
        )


class InvalidStateTransitionError(AppError):
    def __init__(self, current: str, target: str) -> None:
        super().__init__(
            status_code=409,
            code="INVALID_PROCESSING_STATE_TRANSITION",
            message="Không thể chuyển trạng thái xử lý theo yêu cầu.",
            details={"currentStatus": current, "targetStatus": target},
        )
