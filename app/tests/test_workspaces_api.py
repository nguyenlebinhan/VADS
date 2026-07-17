from uuid import UUID

from fastapi.testclient import TestClient


def test_create_workspace_returns_camel_case_contract(client: TestClient) -> None:
    response = client.post(
        "/api/workspaces",
        json={
            "name": "  Phân tích dự thảo kế hoạch phát triển du lịch  ",
            "description": " Workspace phục vụ phiên họp thẩm định ",
        },
        headers={"X-Request-ID": "test-request-id"},
    )

    assert response.status_code == 201
    assert response.headers["X-Request-ID"] == "test-request-id"
    envelope = response.json()
    assert envelope["success"] is True
    assert envelope["timestamp"].endswith("Z")
    body = envelope["data"]
    UUID(body["id"])
    assert body["name"] == "Phân tích dự thảo kế hoạch phát triển du lịch"
    assert body["description"] == "Workspace phục vụ phiên họp thẩm định"
    assert body["status"] == "ACTIVE"
    assert "createdAt" in body
    assert "created_at" not in body


def test_workspace_validation_uses_consistent_error_envelope(client: TestClient) -> None:
    response = client.post("/api/workspaces", json={"name": "   "})

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "REQUEST_VALIDATION_ERROR"
    assert error["details"][0]
    assert isinstance(error["details"], list)


def test_cors_preflight_is_enabled(client: TestClient) -> None:
    response = client.options(
        "/api/workspaces",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
