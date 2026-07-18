from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.api.v1.router import SECURE_V1_ROUTERS


def test_secure_v1_router_contains_dispatchable_routes() -> None:
    assert SECURE_V1_ROUTERS
    assert all(
        isinstance(route, APIRoute)
        for router in SECURE_V1_ROUTERS
        for route in router.routes
    )


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
        ("/api/documents/{document_id}/analysis", "post"),
        ("/api/documents", "post"),
        ("/api/documents", "get"),
        ("/api/documents/{documentId}/versions", "get"),
        ("/api/documents/{documentId}/timeline", "get"),
        ("/api/documents/{documentId}/changes", "get"),
        ("/api/documents/{documentId}/analyze", "post"),
        ("/api/projects", "post"),
        ("/api/impacts", "get"),
        ("/api/impacts/{impactId}/review", "patch"),
        ("/api/agent-runs/{runId}", "get"),
        ("/api/agent-runs/{runId}/retry", "post"),
        ("/api/users/me/context", "get"),
        ("/api/users/me/context", "put"),
        ("/api/docx-rag/query", "post"),
        ("/api/docx-rag/queries/{query_id}/sources", "get"),
        ("/api/v1/documents", "post"),
        ("/api/v1/documents/{document_id}/reprocess", "post"),
        ("/api/v1/rag/query", "post"),
    }

    for path, method in expected_operations:
        assert path in paths
        assert method in paths[path]

    operation_count = sum(
        method in {"get", "post", "put", "patch", "delete"}
        for operations in paths.values()
        for method in operations
    )
    secure_operation_count = sum(
        method in {"get", "post", "put", "patch", "delete"}
        for path, operations in paths.items()
        if path.startswith("/api/v1/")
        for method in operations
    )

    # Compatibility-mode tests expose the 49 consolidated legacy/health
    # operations, 22 tenant-scoped v1 operations, and 2 DOCX RAG operations.
    assert secure_operation_count == 22
    assert operation_count == 73


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
        ("get", "/api/impacts"),
        ("get", "/api/impacts/{impactId}"),
        ("patch", "/api/impacts/{impactId}/review"),
        ("get", "/api/users/me/context"),
        ("put", "/api/users/me/context"),
        ("get", "/api/agent-runs/{runId}"),
        ("post", "/api/agent-runs/{runId}/retry"),
    }

    missing = {(method, path) for method, path in required if method not in paths.get(path, {})}
    assert missing == set()


def test_meeting_audio_routes_are_not_exposed(application: FastAPI) -> None:
    paths = application.openapi()["paths"]

    assert not any(path.startswith("/api/meeting-sessions") for path in paths)


def test_redundant_alias_routes_are_not_exposed(application: FastAPI) -> None:
    paths = application.openapi()["paths"]
    removed_paths = {
        "/api/workspaces/{workspaceId}/dashboard",
        "/api/documents/{documentId}/viewer-data",
        "/api/documents/{documentId}/analysis-overview",
        "/api/documents/{documentId}/structured-sections",
        "/api/documents/{documentId}/index/rebuild",
        "/api/chat/sessions/{sessionId}/messages/stream",
        "/api/projects/{projectId}/impacts",
        "/api/departments/{departmentId}/impacts",
    }

    assert removed_paths.isdisjoint(paths)


def test_consolidated_routes_expose_filter_and_mode_parameters(application: FastAPI) -> None:
    paths = application.openapi()["paths"]
    index_parameters = {
        parameter["name"]
        for parameter in paths["/api/documents/{documentId}/index"]["post"]["parameters"]
    }
    impact_parameters = {
        parameter["name"] for parameter in paths["/api/impacts"]["get"]["parameters"]
    }

    assert "rebuild" in index_parameters
    assert {"projectId", "department"} <= impact_parameters


def test_product_chat_route_is_callable(
    client: TestClient,
    workspace_id: str,
) -> None:
    chat_response = client.post(
        f"/api/workspaces/{workspace_id}/chat/sessions",
        json={"title": "Postman Q&A", "isPrivate": False},
    )

    assert chat_response.status_code == 201
    assert chat_response.json()["data"]["workspaceId"] == workspace_id
