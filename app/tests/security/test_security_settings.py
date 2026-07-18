import pytest
from pydantic import SecretStr, ValidationError

from app.config.settings import Settings


def test_railway_postgres_url_uses_installed_sync_and_async_drivers(
    test_settings: Settings,
) -> None:
    values = test_settings.model_dump()
    values["database_url"] = "postgresql://vads:secret@postgres.railway.internal:5432/vads"

    settings = Settings.model_validate(values)

    assert settings.database_url.startswith("postgresql+psycopg://")
    assert settings.resolved_async_database_url.startswith("postgresql+asyncpg://")


def test_production_rejects_placeholder_secrets_and_legacy_api(
    test_settings: Settings,
) -> None:
    values = test_settings.model_dump()
    values.update(
        {
            "environment": "production",
            "debug": False,
            "legacy_api_enabled": False,
            "jwt_secret_key": SecretStr(
                "replace-with-an-independent-random-secret-at-least-32-bytes"
            ),
            "refresh_token_pepper": SecretStr(
                "a-real-looking-but-independent-refresh-pepper-123456"
            ),
        }
    )
    with pytest.raises(ValidationError):
        Settings.model_validate(values)

    values["jwt_secret_key"] = SecretStr(
        "production-jwt-secret-with-at-least-thirty-two-random-bytes"
    )
    values["legacy_api_enabled"] = True
    with pytest.raises(ValidationError):
        Settings.model_validate(values)
