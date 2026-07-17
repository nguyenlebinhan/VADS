from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.model.documents import Document
from app.model.processing import ProcessingJob, ProcessingStatus, ProcessingStep
from app.service.processing import ProcessingStateService
from app.tests.helpers import minimal_docx, minimal_pdf

PDF_MIME = "application/pdf"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def upload_pdf(client: TestClient, workspace_id: str, *, filename: str = "du-thao.pdf"):
    return client.post(
        f"/api/workspaces/{workspace_id}/documents",
        files={"file": (filename, minimal_pdf(), PDF_MIME)},
        data={"displayName": "Dự thảo kế hoạch"},
    )


def test_upload_get_and_poll_pdf(
    client: TestClient,
    application: FastAPI,
    workspace_id: str,
) -> None:
    response = upload_pdf(client, workspace_id)

    assert response.status_code == 201
    upload_body = response.json()["data"]
    document_id = upload_body["documentId"]
    assert upload_body == {
        "documentId": document_id,
        "workspaceId": workspace_id,
        "status": "UPLOADED",
        "progress": 0,
        "currentStep": "VALIDATING_FILE",
    }
    assert len(application.state.fake_storage.objects) == 1
    assert len(application.state.fake_dispatcher.processing_job_ids) == 1

    metadata_response = client.get(f"/api/documents/{document_id}")
    assert metadata_response.status_code == 200
    metadata = metadata_response.json()["data"]
    assert metadata["documentId"] == document_id
    assert metadata["displayName"] == "Dự thảo kế hoạch"
    assert metadata["originalFilename"] == "du-thao.pdf"
    assert metadata["mimeType"] == PDF_MIME
    assert metadata["fileExtension"] == ".pdf"
    assert metadata["fileSize"] == len(minimal_pdf())
    assert len(metadata["checksum"]) == 64

    status_response = client.get(f"/api/documents/{document_id}/status")
    assert status_response.status_code == 200
    status_body = status_response.json()["data"]
    assert status_body["status"] == "UPLOADED"
    assert status_body["progress"] == 0
    assert status_body["message"] == "Tài liệu đang chờ xử lý"
    assert "updatedAt" in status_body


def test_status_polling_reflects_worker_progress(
    client: TestClient,
    application: FastAPI,
    workspace_id: str,
) -> None:
    document_id = upload_pdf(client, workspace_id).json()["data"]["documentId"]
    with application.state.session_factory() as session:
        job = session.scalar(select(ProcessingJob).where(ProcessingJob.document_id == document_id))
        assert job is not None
        state_service = ProcessingStateService(session)
        state_service.transition(
            job.id,
            status=ProcessingStatus.QUEUED,
            progress=0,
            current_step=ProcessingStep.VALIDATING_FILE,
        )
        state_service.transition(
            job.id,
            status=ProcessingStatus.PROCESSING,
            progress=65,
            current_step=ProcessingStep.DETECTING_STRUCTURE,
        )

    response = client.get(f"/api/documents/{document_id}/status")
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["status"] == "PROCESSING"
    assert body["progress"] == 65
    assert body["currentStep"] == "DETECTING_STRUCTURE"
    assert body["message"] == "Đang nhận diện cấu trúc pháp lý"
    assert "startedAt" in body


def test_docx_upload_is_validated_by_zip_structure(
    client: TestClient,
    workspace_id: str,
) -> None:
    response = client.post(
        f"/api/workspaces/{workspace_id}/documents",
        files={"file": ("van-ban.docx", minimal_docx(), DOCX_MIME)},
    )

    assert response.status_code == 201
    document_id = response.json()["data"]["documentId"]
    document = client.get(f"/api/documents/{document_id}").json()["data"]
    assert document["mimeType"] == DOCX_MIME
    assert document["displayName"] == "van-ban"


def test_duplicate_checksum_is_rejected(
    client: TestClient,
    workspace_id: str,
) -> None:
    first = upload_pdf(client, workspace_id)
    second = upload_pdf(client, workspace_id, filename="renamed.pdf")

    assert first.status_code == 201
    assert second.status_code == 409
    error = second.json()["error"]
    assert error["code"] == "DUPLICATE_DOCUMENT"
    assert error["details"]["existingDocumentId"] == first.json()["data"]["documentId"]


def test_same_checksum_is_allowed_in_another_workspace(client: TestClient) -> None:
    workspace_one = client.post("/api/workspaces", json={"name": "WS one"}).json()["data"]["id"]
    workspace_two = client.post("/api/workspaces", json={"name": "WS two"}).json()["data"]["id"]

    assert upload_pdf(client, workspace_one).status_code == 201
    assert upload_pdf(client, workspace_two).status_code == 201


def test_mime_extension_and_magic_bytes_must_agree(
    client: TestClient,
    workspace_id: str,
) -> None:
    mime_mismatch = client.post(
        f"/api/workspaces/{workspace_id}/documents",
        files={"file": ("fake.pdf", minimal_pdf(), DOCX_MIME)},
    )
    bad_magic = client.post(
        f"/api/workspaces/{workspace_id}/documents",
        files={"file": ("fake.pdf", b"this is not a pdf", PDF_MIME)},
    )
    fake_docx = client.post(
        f"/api/workspaces/{workspace_id}/documents",
        files={"file": ("fake.docx", b"PK\x03\x04not-a-real-zip", DOCX_MIME)},
    )

    assert mime_mismatch.status_code == 415
    assert mime_mismatch.json()["error"]["code"] == "MIME_TYPE_MISMATCH"
    assert bad_magic.status_code == 415
    assert bad_magic.json()["error"]["code"] == "INVALID_FILE_SIGNATURE"
    assert fake_docx.status_code == 415
    assert fake_docx.json()["error"]["code"] == "INVALID_FILE_SIGNATURE"


def test_unsupported_file_type_is_rejected(
    client: TestClient,
    workspace_id: str,
) -> None:
    response = client.post(
        f"/api/workspaces/{workspace_id}/documents",
        files={"file": ("notes.txt", b"plain text", "text/plain")},
    )

    assert response.status_code == 415
    assert response.json()["error"]["code"] == "UNSUPPORTED_FILE_EXTENSION"


def test_empty_oversized_and_dangerous_files_are_rejected(
    client: TestClient,
    workspace_id: str,
) -> None:
    empty = client.post(
        f"/api/workspaces/{workspace_id}/documents",
        files={"file": ("empty.pdf", b"", PDF_MIME)},
    )
    oversized = client.post(
        f"/api/workspaces/{workspace_id}/documents",
        files={"file": ("large.pdf", b"%PDF-" + b"a" * (1024 * 1024), PDF_MIME)},
    )
    dangerous = client.post(
        f"/api/workspaces/{workspace_id}/documents",
        files={"file": ("payload.exe.pdf", minimal_pdf(), PDF_MIME)},
    )

    assert empty.status_code == 422
    assert empty.json()["error"]["code"] == "EMPTY_FILE"
    assert oversized.status_code == 413
    assert oversized.json()["error"]["code"] == "FILE_TOO_LARGE"
    assert dangerous.status_code == 422
    assert dangerous.json()["error"]["code"] == "UNSAFE_FILENAME"


def test_delete_is_soft_and_schedules_policy_driven_purge(
    client: TestClient,
    application: FastAPI,
    workspace_id: str,
) -> None:
    document_id = upload_pdf(client, workspace_id).json()["data"]["documentId"]

    response = client.delete(f"/api/documents/{document_id}")

    assert response.status_code == 200
    assert response.json()["data"] == {"documentId": document_id, "status": "DELETED"}
    assert client.get(f"/api/documents/{document_id}").status_code == 404
    assert application.state.fake_dispatcher.purge_document_ids == [document_id]
    # Physical deletion belongs to the asynchronous purge task.
    assert len(application.state.fake_storage.objects) == 1

    with application.state.session_factory() as session:
        document = session.get(Document, document_id)
        assert document is not None
        assert document.deleted_at is not None
        assert document.status == ProcessingStatus.CANCELLED


def test_soft_deleted_checksum_can_be_uploaded_again(
    client: TestClient,
    workspace_id: str,
) -> None:
    first = upload_pdf(client, workspace_id)
    client.delete(f"/api/documents/{first.json()['data']['documentId']}")

    second = upload_pdf(client, workspace_id)
    assert second.status_code == 201
    assert second.json()["data"]["documentId"] != first.json()["data"]["documentId"]


def test_missing_workspace_and_document_return_404(client: TestClient) -> None:
    missing_upload = client.post(
        "/api/workspaces/ws-missing/documents",
        files={"file": ("document.pdf", minimal_pdf(), PDF_MIME)},
    )
    missing_document = client.get("/api/documents/doc-missing")

    assert missing_upload.status_code == 404
    assert missing_upload.json()["error"]["code"] == "WORKSPACE_NOT_FOUND"
    assert missing_document.status_code == 404
    assert missing_document.json()["error"]["code"] == "DOCUMENT_NOT_FOUND"
