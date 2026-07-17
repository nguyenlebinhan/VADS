import logging
from threading import Lock
from typing import BinaryIO, Protocol

import boto3
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.config.settings import Settings
from app.exceptions import StorageUnavailableError

logger = logging.getLogger(__name__)


class ObjectStorage(Protocol):
    bucket_name: str

    def upload(
        self,
        file_object: BinaryIO,
        *,
        object_key: str,
        content_type: str,
        metadata: dict[str, str] | None = None,
    ) -> None: ...

    def delete(self, *, object_key: str) -> None: ...

    def download(self, *, object_key: str) -> bytes: ...

    def health_check(self) -> bool: ...


class S3ObjectStorage:
    """S3 client configured for either AWS S3 or a MinIO endpoint."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.bucket_name = settings.s3_bucket_name
        self._bucket_ready = False
        self._bucket_lock = Lock()
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key.get_secret_value(),
            region_name=settings.s3_region,
            config=Config(
                signature_version="s3v4",
                s3={"addressing_style": ("path" if settings.s3_force_path_style else "virtual")},
            ),
        )

    def _ensure_bucket(self) -> None:
        if self._bucket_ready:
            return
        with self._bucket_lock:
            if self._bucket_ready:
                return
            try:
                self.client.head_bucket(Bucket=self.bucket_name)
            except ClientError as exc:
                error_code = str(exc.response.get("Error", {}).get("Code", ""))
                if error_code not in {"404", "NoSuchBucket", "NotFound"}:
                    logger.exception("Cannot access object-storage bucket")
                    raise StorageUnavailableError() from exc
                try:
                    arguments: dict[str, object] = {"Bucket": self.bucket_name}
                    if (
                        self.settings.s3_endpoint_url is None
                        and self.settings.s3_region != "us-east-1"
                    ):
                        arguments["CreateBucketConfiguration"] = {
                            "LocationConstraint": self.settings.s3_region
                        }
                    self.client.create_bucket(**arguments)
                except (BotoCoreError, ClientError) as create_exc:
                    logger.exception("Cannot create object-storage bucket")
                    raise StorageUnavailableError() from create_exc
            except BotoCoreError as exc:
                logger.exception("Cannot reach object storage")
                raise StorageUnavailableError() from exc
            self._bucket_ready = True

    def upload(
        self,
        file_object: BinaryIO,
        *,
        object_key: str,
        content_type: str,
        metadata: dict[str, str] | None = None,
    ) -> None:
        self._ensure_bucket()
        file_object.seek(0)
        extra_args: dict[str, object] = {"ContentType": content_type}
        if metadata:
            extra_args["Metadata"] = metadata
        try:
            self.client.upload_fileobj(
                file_object,
                self.bucket_name,
                object_key,
                ExtraArgs=extra_args,
            )
        except (BotoCoreError, ClientError, OSError) as exc:
            logger.exception("Object upload failed", extra={"object_key": object_key})
            raise StorageUnavailableError() from exc

    def delete(self, *, object_key: str) -> None:
        self._ensure_bucket()
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=object_key)
        except (BotoCoreError, ClientError) as exc:
            logger.exception("Object deletion failed", extra={"object_key": object_key})
            raise StorageUnavailableError() from exc

    def download(self, *, object_key: str) -> bytes:
        self._ensure_bucket()
        try:
            response = self.client.get_object(Bucket=self.bucket_name, Key=object_key)
            return response["Body"].read()
        except (BotoCoreError, ClientError, OSError) as exc:
            logger.exception("Object download failed", extra={"object_key": object_key})
            raise StorageUnavailableError() from exc

    def health_check(self) -> bool:
        try:
            self._ensure_bucket()
            self.client.head_bucket(Bucket=self.bucket_name)
        except (BotoCoreError, ClientError, StorageUnavailableError):
            return False
        return True
