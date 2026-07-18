import json
from io import BytesIO

from docx import Document as WordDocument
from fastapi.testclient import TestClient


def _docx(text: str) -> bytes:
    document = WordDocument()
    for line in text.splitlines():
        document.add_paragraph(line)
    output = BytesIO()
    document.save(output)
    return output.getvalue()


def _upload(
    client: TestClient,
    *,
    workspace_id: str,
    year: int,
    text: str,
) -> dict:
    metadata = {
        "workspaceId": workspace_id,
        "familyKey": "quy-dinh-tham-dinh-ngan-sach",
        "title": "Quy định thẩm định ngân sách",
        "documentNumber": f"01/{year}/QD-UBND",
        "documentType": "QUYET_DINH",
        "issuingAgency": "UBND tỉnh",
        "issuedDate": f"{year}-01-10",
        "effectiveDate": f"{year}-02-01",
        "domain": "Quản lý đầu tư",
        "applicableSubjects": ["Dự án sử dụng ngân sách tỉnh"],
    }
    response = client.post(
        "/api/documents",
        files={
            "file": (
                f"quy-dinh-{year}.docx",
                _docx(text),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ),
            "metadata": (None, json.dumps(metadata, ensure_ascii=False), "application/json"),
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


def test_two_versions_diff_project_impact_and_agent_audit(
    client: TestClient,
    workspace_id: str,
) -> None:
    project_response = client.post(
        "/api/projects",
        json={
            "workspaceId": workspace_id,
            "projectCode": "project-001",
            "name": "Đề án phát triển du lịch cộng đồng",
            "status": "CHO_THAM_DINH",
            "domain": "Quản lý đầu tư",
            "locations": ["Mường Nhé"],
            "leadDepartment": "Phòng Kế hoạch",
            "coordinatingDepartments": ["Phòng Tài chính"],
            "legalBases": [],
            "activities": ["Chuẩn bị hồ sơ thẩm định"],
            "budgetSources": ["Ngân sách tỉnh"],
            "timeline": {"stage": "APPRAISAL"},
            "sections": [{"title": "Mục 4.2 - Quy trình thẩm định"}],
        },
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["data"]["id"]

    old = _upload(
        client,
        workspace_id=workspace_id,
        year=2024,
        text="""Điều 10. Quy định phê duyệt
Khoản 2. Hạn mức và thẩm quyền
Ngưỡng phê duyệt: 500 triệu đồng.
Thời hạn báo cáo: 30 ngày.
Đơn vị phê duyệt: UBND tỉnh.""",
    )
    new = _upload(
        client,
        workspace_id=workspace_id,
        year=2026,
        text="""Điều 12. Quy định phê duyệt
Khoản 3. Hạn mức và thẩm quyền
Ngưỡng phê duyệt: 800 triệu đồng.
Thời hạn báo cáo: 30 ngày.
Đơn vị phê duyệt: Sở Tài chính.""",
    )

    assert old["versionNumber"] == 1
    assert new["versionNumber"] == 2
    assert old["familyId"] == new["familyId"]

    analyze_response = client.post(
        f"/api/documents/{new['documentId']}/analyze",
        json={"force": False},
    )
    assert analyze_response.status_code == 200, analyze_response.text
    analysis = analyze_response.json()["data"]
    changes = {item["factKey"]: item for item in analysis["changes"]}

    assert changes["approval_threshold"]["changeType"] == "VALUE_CHANGED"
    assert changes["approval_threshold"]["oldValue"] == "500 triệu đồng"
    assert changes["approval_threshold"]["newValue"] == "800 triệu đồng"
    assert changes["approval_threshold"]["effectiveYear"] == 2026
    assert changes["approval_threshold"]["oldLocation"] == "Khoản 2, Điều 10"
    assert changes["approval_threshold"]["newLocation"] == "Khoản 3, Điều 12"
    assert len(changes["approval_threshold"]["evidence"]) == 2
    assert changes["reporting_deadline"]["changeType"] == "UNCHANGED"
    assert changes["reporting_deadline"]["status"] == "KEEP_CURRENT_VALUE"
    assert changes["approving_authority"]["changeType"] == "RESPONSIBILITY_CHANGED"

    assert analysis["run"]["status"] == "COMPLETED"
    assert len(analysis["run"]["tasks"]) == 8
    assert analysis["run"]["verification"]["rejectedClaims"] == 0
    assert len(analysis["impacts"]) == 1
    impact = analysis["impacts"][0]
    assert impact["projectId"] == project_id
    assert impact["impactLevel"] == "HIGH"
    assert impact["confidence"] == 0.9
    assert {item["department"] for item in impact["departments"]} == {
        "Phòng Kế hoạch",
        "Phòng Tài chính",
    }
    assert {item["action"] for item in impact["recommendedActions"]} >= {
        "Rà soát lại hồ sơ trình duyệt.",
        "Kiểm tra ngưỡng ngân sách mới.",
    }
    assert {item["sourceType"] for item in impact["evidence"]} == {
        "REGULATION",
        "PROJECT",
    }

    timeline_response = client.get(f"/api/documents/{new['documentId']}/timeline")
    assert timeline_response.status_code == 200
    timeline = timeline_response.json()["data"]
    assert [item["effectiveDate"][:4] for item in timeline] == ["2024", "2026"]
    assert timeline[0]["values"]["approval_threshold"] == "500 triệu đồng"
    assert timeline[1]["values"]["approval_threshold"] == "800 triệu đồng"

    run_id = analysis["run"]["id"]
    run_response = client.get(f"/api/agent-runs/{run_id}")
    assert run_response.status_code == 200
    assert run_response.json()["data"]["status"] == "COMPLETED"

    idempotent_response = client.post(f"/api/documents/{new['documentId']}/analyze")
    assert idempotent_response.json()["data"]["run"]["id"] == run_id

    department_response = client.get(
        "/api/impacts",
        params={"department": "Phòng Tài chính"},
    )
    assert department_response.status_code == 200
    assert department_response.json()["data"][0]["id"] == impact["id"]

    review_response = client.patch(
        f"/api/impacts/{impact['id']}/review",
        json={
            "status": "ACCEPTED",
            "reviewedBy": "legal-expert-001",
            "note": "Đã kiểm tra bằng chứng.",
        },
    )
    assert review_response.status_code == 200
    assert review_response.json()["data"]["reviewStatus"] == "ACCEPTED"

    retry_response = client.post(f"/api/agent-runs/{run_id}/retry")
    assert retry_response.status_code == 200, retry_response.text
    retried_run = retry_response.json()["data"]["run"]
    assert retried_run["attempt"] == 2
    assert retried_run["id"] != run_id
    assert len(retried_run["tasks"]) == 8

    history_response = client.get("/api/impacts", params={"projectId": project_id})
    assert history_response.status_code == 200
    assert len(history_response.json()["data"]) == 2


def test_first_version_does_not_invent_changes(
    client: TestClient,
    workspace_id: str,
) -> None:
    document = _upload(
        client,
        workspace_id=workspace_id,
        year=2026,
        text="""Điều 1. Quy định báo cáo
Thời hạn báo cáo: 30 ngày.""",
    )

    response = client.post(f"/api/documents/{document['documentId']}/analyze")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["changes"] == []
    assert data["impacts"] == []
    assert data["run"]["status"] == "NEEDS_HUMAN_REVIEW"
    assert "Không xác định được phiên bản trước" in data["run"]["verification"]["issues"][0]
