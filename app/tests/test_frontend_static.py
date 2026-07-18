from fastapi.testclient import TestClient

import app.main as main_module
from app.config.settings import Settings


def test_frontend_is_served_without_shadowing_api(
    monkeypatch,
    tmp_path,
    test_settings: Settings,
) -> None:
    (tmp_path / "index.html").write_text(
        "<!doctype html><title>VADS frontend</title>",
        encoding="utf-8",
    )
    monkeypatch.setattr(main_module, "FRONTEND_DIST", tmp_path)

    with TestClient(main_module.create_app(test_settings)) as client:
        root_response = client.get("/")
        health_response = client.get("/health/live")

    assert root_response.status_code == 200
    assert "VADS frontend" in root_response.text
    assert health_response.status_code == 200
    assert health_response.json() == {"status": "ok", "service": "vads-api"}
