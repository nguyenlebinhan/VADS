from fastapi.testclient import TestClient


def test_user_context_is_created_once_and_updated(client: TestClient) -> None:
    headers = {"X-User-ID": "user-001"}

    missing = client.get("/api/users/me/context", headers=headers)
    assert missing.status_code == 404

    created = client.put(
        "/api/users/me/context",
        headers=headers,
        json={
            "position": "Trưởng phòng Hành chính",
            "department": "Văn phòng UBND huyện",
            "organization": "UBND huyện",
            "province": "Điện Biên",
            "district": "Mường Nhé",
            "responsibilities": [
                "tổng hợp báo cáo",
                "chuẩn bị nội dung họp",
                "tổng hợp báo cáo",
            ],
            "assignedProjects": ["project-001", "project-014"],
        },
    )
    assert created.status_code == 200
    created_data = created.json()["data"]
    assert created_data["userId"] == "user-001"
    assert created_data["responsibilities"] == [
        "tổng hợp báo cáo",
        "chuẩn bị nội dung họp",
    ]

    updated = client.put(
        "/api/users/me/context",
        headers=headers,
        json={
            "position": "Chánh Văn phòng",
            "department": "Văn phòng UBND huyện",
            "organization": "UBND huyện",
            "province": "Điện Biên",
            "district": "Mường Nhé",
            "responsibilities": ["theo dõi kế hoạch"],
            "assignedProjects": ["project-001"],
            "notes": "Hồ sơ onboarding đã xác nhận",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["id"] == created_data["id"]
    assert updated.json()["data"]["position"] == "Chánh Văn phòng"

    fetched = client.get("/api/users/me/context", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["data"] == updated.json()["data"]


def test_user_context_requires_authenticated_subject_header(client: TestClient) -> None:
    response = client.get("/api/users/me/context")

    assert response.status_code == 422
