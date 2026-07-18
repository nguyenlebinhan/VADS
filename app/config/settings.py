from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven application settings.

    Environment variables use the ``VADS_`` prefix. Lists such as
    ``VADS_CORS_ORIGINS`` are encoded as JSON arrays.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="VADS_",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    app_name: str
    environment: Literal["local", "test", "staging", "production"]
    debug: bool
    api_prefix: str

    database_url: str
    database_async_url: str | None = None
    database_echo: bool

    # Local defaults keep the existing development setup bootable. Staging and
    # production refuse to start until both independent secrets are replaced.
    jwt_secret_key: SecretStr = SecretStr(
        "local-only-jwt-secret-change-before-deployment-32-bytes"
    )
    jwt_algorithm: Literal["HS256"] = "HS256"
    jwt_issuer: str = "vads-api"
    jwt_audience: str = "vads-client"
    jwt_key_id: str = "vads-hs256-v1"
    access_token_ttl_minutes: int = Field(default=10, ge=1, le=30)
    refresh_token_ttl_days: int = Field(default=30, ge=1, le=90)
    refresh_token_pepper: SecretStr = SecretStr(
        "local-only-refresh-pepper-change-before-deployment-32-bytes"
    )
    login_max_failed_attempts: int = Field(default=5, ge=3, le=20)
    login_lock_minutes: int = Field(default=15, ge=1, le=1440)
    user_document_upload_enabled: bool = False
    legacy_api_enabled: bool = False

    redis_url: str
    celery_broker_url: str
    celery_result_backend: str
    celery_task_always_eager: bool
    document_processing_queue: str

    storage_provider: Literal["MINIO", "S3"]
    s3_endpoint_url: str | None
    s3_access_key: str
    s3_secret_key: SecretStr
    s3_bucket_name: str
    s3_region: str
    s3_force_path_style: bool

    max_upload_size_mb: int = Field(
        default=50,
        ge=1,
        le=1024,
        validation_alias=AliasChoices("MAX_UPLOAD_SIZE_MB", "VADS_MAX_UPLOAD_SIZE_MB"),
    )
    upload_spool_memory_mb: int = Field(ge=1, le=128)
    delete_object_on_soft_delete: bool

    pdf_text_min_characters: int = Field(default=20, ge=1, le=10_000)
    pdf_text_page_ratio: float = Field(default=0.8, ge=0, le=1)
    pdf_image_page_ratio: float = Field(default=0.8, ge=0, le=1)
    render_dpi: int = Field(default=150, ge=72, le=600)
    ocr_provider: Literal["MOCK", "PADDLEOCR"] = "MOCK"
    ocr_review_confidence_threshold: float = Field(default=0.7, ge=0, le=1)

    chunk_min_tokens: int = Field(default=300, ge=50, le=2_000)
    chunk_max_tokens: int = Field(default=800, ge=100, le=4_000)
    chunk_overlap_tokens: int = Field(default=75, ge=0, le=500)

    fpt_ai_enabled: bool = False
    fpt_ai_api_key: SecretStr | None = None
    fpt_ai_base_url: str = "https://mkp-api.fptcloud.com"
    fpt_ai_chat_completions_path: str = "/v1/chat/completions"
    fpt_ai_models_path: str = "/v1/models"
    fpt_ai_model_map: dict[str, str] = Field(default_factory=dict)
    fpt_ai_max_tokens: int = Field(default=4096, ge=1, le=131_072)
    fpt_ai_temperature: float = Field(default=0, ge=0, le=2)
    fpt_ai_allow_private_data: bool = False

    cors_origins: list[str]

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_postgresql_driver(cls, value: object) -> object:
        """Make Railway's standard DATABASE_URL use the installed psycopg driver."""

        if isinstance(value, str):
            for prefix in ("postgres://", "postgresql://"):
                if value.startswith(prefix):
                    return value.replace(prefix, "postgresql+psycopg://", 1)
        return value

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def upload_spool_memory_bytes(self) -> int:
        return self.upload_spool_memory_mb * 1024 * 1024

    @property
    def resolved_async_database_url(self) -> str:
        if self.database_async_url:
            return self.database_async_url
        if self.database_url.startswith("postgresql+psycopg://"):
            return self.database_url.replace(
                "postgresql+psycopg://", "postgresql+asyncpg://", 1
            )
        if self.database_url.startswith("sqlite+aiosqlite://"):
            return self.database_url
        if self.database_url.startswith("sqlite://"):
            return self.database_url.replace("sqlite://", "sqlite+aiosqlite://", 1)
        raise ValueError("VADS_DATABASE_ASYNC_URL must use an async SQLAlchemy driver")

    @model_validator(mode="after")
    def reject_local_security_secrets_in_deployed_environments(self) -> "Settings":
        if self.environment in {"staging", "production"}:
            weak_values = {
                "local-only-jwt-secret-change-before-deployment-32-bytes",
                "local-only-refresh-pepper-change-before-deployment-32-bytes",
            }
            configured = {
                self.jwt_secret_key.get_secret_value(),
                self.refresh_token_pepper.get_secret_value(),
            }
            if configured & weak_values or any(
                marker in value.casefold()
                for value in configured
                for marker in ("replace-with", "change-me", "changeme")
            ):
                raise ValueError("JWT and refresh-token secrets must be replaced before deployment")
            if any(len(value.encode("utf-8")) < 32 for value in configured):
                raise ValueError("Security secrets must contain at least 32 bytes")
            if self.legacy_api_enabled:
                raise ValueError("Legacy API cannot be enabled in staging or production")
            if self.debug:
                raise ValueError("Debug mode cannot be enabled in staging or production")
            if "*" in self.cors_origins:
                raise ValueError("Wildcard CORS is forbidden in staging or production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
