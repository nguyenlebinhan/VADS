from io import BytesIO
from typing import BinaryIO

import pytest
from fastapi import FastAPI, UploadFile
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker
from starlette.datastructures import Headers

from app.exceptions import StorageUnavailableError
from app.model.documents import Document
from app.model.processing import ProcessingJob, ProcessingStatus, ProcessingStep
from app.model.schemas.workspaces import WorkspaceCreate
from app.service.documents import DocumentService
from app.service.processing import ProcessingStateService
from app.service.workspaces import WorkspaceService
from app.tests.helpers import minimal_pdf, pdf_with_pages
from app.utils.storage_dependencies import get_object_storage


class TrackingStorage:
    bucket_name = "test-documents"

    def __init__(self, *, fail_upload: bool = False, fail_download: bool = False) -> None:
        self.objects: dict[str, bytes] = {}
        self.fail_upload = fail_upload
        self.fail_download = fail_download
        self.deleted_keys: list[str] = []

    def upload(
        self,
        file_object: BinaryIO,
        *,
        object_key: str,
        content_type: str,
        metadata: dict[str, str] | None = None,
    ) -> None:
        del content_type, metadata
        if self.fail_upload:
            raise StorageUnavailableError()
        file_object.seek(0)
        self.objects[object_key] = file_object.read()

    def download(self, *, object_key: str) -> bytes:
        if self.fail_download:
            raise StorageUnavailableError()
        return self.objects[object_key]

    def delete(self, *, object_key: str) -> None:
        self.deleted_keys.append(object_key)
        self.objects.pop(object_key, None)

    def health_check(self) -> bool:
        return not self.fail_upload


class NoopDispatcher:
    def enqueue_processing(self, job_id: str) -> None:
        del job_id

    def enqueue_purge(self, document_id: str) -> None:
        del document_id


def test_storage_upload_error_does_not_create_document(
    client: TestClient,
    application: FastAPI,
    workspace_id: str,
) -> None:
    failing = TrackingStorage(fail_upload=True)
    original = application.dependency_overrides[get_object_storage]
    application.dependency_overrides[get_object_storage] = lambda: failing
    try:
        response = client.post(
            f"/api/workspaces/{workspace_id}/documents",
            files={"file": ("document.pdf", minimal_pdf(), "application/pdf")},
        )
    finally:
        application.dependency_overrides[get_object_storage] = original

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "OBJECT_STORAGE_UNAVAILABLE"
    with application.state.session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Document)) == 0


def test_database_error_after_storage_upload_deletes_object(
    session_factory: sessionmaker[Session],
    test_settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    storage = TrackingStorage()
    with session_factory() as session:
        workspace = WorkspaceService(session).create(WorkspaceCreate(name="DB failure"))
        service = DocumentService(
            session,
            storage=storage,
            dispatcher=NoopDispatcher(),
            settings=test_settings,
        )
        upload = UploadFile(
            file=BytesIO(minimal_pdf()),
            filename="document.pdf",
            headers=Headers({"content-type": "application/pdf"}),
        )

        def fail_commit() -> None:
            raise RuntimeError("database unavailable")

        monkeypatch.setattr(session, "commit", fail_commit)
        with pytest.raises(RuntimeError, match="database unavailable"):
            service.upload(workspace.id, upload)

    assert storage.objects == {}
    assert len(storage.deleted_keys) == 1
    with session_factory() as verification_session:
        assert verification_session.scalar(select(func.count()).select_from(Document)) == 0


def test_reprocess_creates_a_new_attempt(
    client: TestClient,
    application: FastAPI,
    workspace_id: str,
) -> None:
    upload = client.post(
        f"/api/workspaces/{workspace_id}/documents",
        files={"file": ("document.pdf", minimal_pdf(), "application/pdf")},
    )
    document_id = upload.json()["data"]["documentId"]
    with application.state.session_factory() as session:
        first = session.scalar(
            select(ProcessingJob).where(ProcessingJob.document_id == document_id)
        )
        assert first is not None
        ProcessingStateService(session).transition(
            first.id,
            status=ProcessingStatus.FAILED,
            progress=0,
            current_step=ProcessingStep.VALIDATING_FILE,
            error_code="TEST_FAILURE",
            error_message="Failure used to test reprocessing",
        )

    response = client.post(f"/api/documents/{document_id}/reprocess")

    assert response.status_code == 202
    assert response.json()["data"]["status"] == "UPLOADED"
    with application.state.session_factory() as session:
        jobs = list(
            session.scalars(
                select(ProcessingJob)
                .where(ProcessingJob.document_id == document_id)
                .order_by(ProcessingJob.attempt)
            )
        )
        assert [job.attempt for job in jobs] == [1, 2]


def test_processing_task_marks_job_failed(
    client: TestClient,
    application: FastAPI,
    workspace_id: str,
    test_settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    upload = client.post(
        f"/api/workspaces/{workspace_id}/documents",
        files={
            "file": (
                "document.pdf",
                pdf_with_pages(["A sufficiently long searchable text layer for processing."]),
                "application/pdf",
            )
        },
    )
    document_id = upload.json()["data"]["documentId"]
    with application.state.session_factory() as session:
        job = session.scalar(select(ProcessingJob).where(ProcessingJob.document_id == document_id))
        assert job is not None
        job_id = job.id

    from app.service import processing_tasks

    monkeypatch.setattr(processing_tasks, "SessionLocal", application.state.session_factory)
    monkeypatch.setattr(processing_tasks, "get_settings", lambda: test_settings)
    monkeypatch.setattr(
        processing_tasks,
        "get_object_storage",
        lambda: TrackingStorage(fail_download=True),
    )
    processing_tasks.process_document.run(job_id)

    with application.state.session_factory() as session:
        failed = session.get(ProcessingJob, job_id)
        assert failed is not None
        assert failed.status == ProcessingStatus.FAILED
        assert failed.error_code == "OBJECT_STORAGE_UNAVAILABLE"
        assert failed.error_message
