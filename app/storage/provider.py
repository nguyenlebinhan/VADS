from typing import BinaryIO, Protocol, runtime_checkable

from app.config.settings import Settings
from app.service.storage import S3ObjectStorage


@runtime_checkable
class StorageProvider(Protocol):
    """Business-facing object-storage boundary."""

    bucket_name: str

    def upload(
        self,
        file_object: BinaryIO,
        *,
        object_key: str,
        content_type: str,
        metadata: dict[str, str] | None = None,
    ) -> None: ...

    def download(self, *, object_key: str) -> bytes: ...

    def delete(self, *, object_key: str) -> None: ...

    def health_check(self) -> bool: ...


class MinioStorageProvider(S3ObjectStorage):
    """MinIO implementation using its S3-compatible API."""

    def __init__(self, settings: Settings) -> None:
        if settings.s3_endpoint_url is None:
            raise ValueError("MinIO requires VADS_S3_ENDPOINT_URL")
        super().__init__(settings)
