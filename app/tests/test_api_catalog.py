from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_openapi_exposes_complete_product_api(application: FastAPI) -> None:
    paths = application.openapi()["paths"]

    expected_operations = {
        ("/health/live", "get"),
        ("/api/workspaces", "post"),
        ("/api/workspaces/{workspaceId}/documents", "post"),
        ("/api/documents/{documentId}/index", "post"),
        ("/api/retrieval/search", "post"),
        ("/api/workspaces/{workspaceId}/chat/sessions", "post"),
        ("/api/chat/sessions/{sessionId}/messages", "post"),
        ("/api/chat/sessions/{sessionId}/messages/stream", "post"),
        ("/api/meeting-sessions", "post"),
        ("/api/meeting-sessions/{sessionId}/audio", "post"),
        ("/api/workspaces/{workspaceId}/dashboard", "get"),
        ("/api/documents/{documentId}/viewer-data", "get"),
        ("/api/documents/{documentId}/analysis-overview", "get"),
        ("/api/documents/{document_id}/analysis", "post"),
        ("/api/documents", "post"),
        ("/api/documents", "get"),
        ("/api/documents/{documentId}/versions", "get"),
        ("/api/documents/{documentId}/timeline", "get"),
        ("/api/documents/{documentId}/changes", "get"),
        ("/api/documents/{documentId}/analyze", "post"),
        ("/api/projects", "post"),
        ("/api/projects/{projectId}/impacts", "get"),
        ("/api/impacts/{impactId}/review", "patch"),
        ("/api/agent-runs/{runId}", "get"),
        ("/api/agent-runs/{runId}/retry", "post"),
        ("/api/users/me/context", "get"),
        ("/api/users/me/context", "put"),
    }

    for path, method in expected_operations:
        assert path in paths
        assert method in paths[path]


def test_product_routes_use_unique_operation_ids(application: FastAPI) -> None:
    operation_ids = [
        operation["operationId"]
        for path in application.openapi()["paths"].values()
        for method, operation in path.items()
        if method in {"get", "post", "put", "patch", "delete"}
    ]

    assert len(operation_ids) == len(set(operation_ids))


def test_required_regulatory_change_api_is_complete(application: FastAPI) -> None:
    paths = application.openapi()["paths"]
    required = {
        ("post", "/api/documents"),
        ("get", "/api/documents"),
        ("get", "/api/documents/{documentId}"),
        ("get", "/api/documents/{documentId}/summary"),
        ("get", "/api/documents/{documentId}/versions"),
        ("get", "/api/documents/{documentId}/timeline"),
        ("get", "/api/documents/{documentId}/changes"),
        ("get", "/api/documents/{documentId}/legal-relations"),
        ("post", "/api/documents/{documentId}/analyze"),
        ("post", "/api/projects"),
        ("get", "/api/projects"),
        ("get", "/api/projects/{projectId}"),
        ("get", "/api/projects/{projectId}/impacts"),
        ("get", "/api/impacts"),
        ("get", "/api/impacts/{impactId}"),
        ("patch", "/api/impacts/{impactId}/review"),
        ("get", "/api/departments/{departmentId}/impacts"),
        ("get", "/api/users/me/context"),
        ("put", "/api/users/me/context"),
        ("get", "/api/agent-runs/{runId}"),
        ("post", "/api/agent-runs/{runId}/retry"),
    }

    missing = {(method, path) for method, path in required if method not in paths.get(path, {})}
    assert missing == set()


def test_product_session_and_dashboard_routes_are_callable(
    client: TestClient,
    workspace_id: str,
) -> None:
    chat_response = client.post(
        f"/api/workspaces/{workspace_id}/chat/sessions",
        json={"title": "Postman Q&A", "isPrivate": False},
    )
    meeting_response = client.post(
        "/api/meeting-sessions",
        json={
            "workspaceId": workspace_id,
            "title": "Postman meeting",
            "documentIds": [],
        },
    )
    dashboard_response = client.get(f"/api/workspaces/{workspace_id}/dashboard")

    assert chat_response.status_code == 201
    assert chat_response.json()["data"]["workspaceId"] == workspace_id
    assert meeting_response.status_code == 201
    assert meeting_response.json()["data"]["workspaceId"] == workspace_id
    assert dashboard_response.status_code == 200
    assert dashboard_response.json()["data"]["workspaceId"] == workspace_id
