from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.common.contracts import BoundingBox
from app.extraction.ocr import MockOcrProvider
from app.extraction.schemas import OcrBlock, OcrPageResult
from app.model.documents import Document
from app.model.processing import ProcessingJob, ProcessingStatus, ProcessingStep
from app.processing.pipeline import DocumentProcessingPipeline
from app.service.processing import ProcessingStateService
from app.tests.helpers import pdf_with_pages


def test_pipeline_persists_ocr_bbox_pages_and_chunks(
    client: TestClient,
    application: FastAPI,
    workspace_id: str,
) -> None:
    upload = client.post(
        f"/api/workspaces/{workspace_id}/documents",
        files={"file": ("scan.pdf", pdf_with_pages([None]), "application/pdf")},
    )
    assert upload.status_code == 201
    document_id = upload.json()["data"]["documentId"]
    ocr = MockOcrProvider(
        {
            0: OcrPageResult(
                page_index=0,
                text="Điều 1. Phạm vi điều chỉnh",
                average_confidence=0.98,
                blocks=[
                    OcrBlock(
                        text="Điều 1. Phạm vi điều chỉnh",
                        confidence=0.98,
                        bbox=BoundingBox(x1=110, y1=202, x2=810, y2=245),
                        order_index=0,
                    )
                ],
            )
        }
    )

    with application.state.session_factory() as session:
        job = session.scalar(select(ProcessingJob).where(ProcessingJob.document_id == document_id))
        assert job is not None
        ProcessingStateService(session).transition(
            job.id,
            status=ProcessingStatus.QUEUED,
            progress=0,
            current_step=ProcessingStep.VALIDATING_FILE,
        )
        DocumentProcessingPipeline(
            session,
            storage=application.state.fake_storage,
            ocr_provider=ocr,
            settings=application.state.settings,
        ).run(job.id)

    status = client.get(f"/api/documents/{document_id}/status").json()["data"]
    assert status["status"] == "COMPLETED"
    assert status["progress"] == 100
    page = client.get(f"/api/documents/{document_id}/pages/0").json()["data"]
    assert page["blocks"][0]["bbox"] == {"x1": 110, "y1": 202, "x2": 810, "y2": 245}
    assert page["blocks"][0]["confidence"] == 0.98
    pages = client.get(f"/api/documents/{document_id}/pages").json()["data"]
    assert pages[0]["pageIndex"] == 0
    sections = client.get(f"/api/documents/{document_id}/sections").json()["data"]
    assert sections["items"][0]["sectionType"] == "ARTICLE"
    chunks = client.get(f"/api/documents/{document_id}/chunks").json()["data"]["items"]
    assert chunks[0]["article"] == "Điều 1"
    assert chunks[0]["startBlockId"] == page["blocks"][0]["id"]
    chunk = client.get(f"/api/documents/{document_id}/chunks/{chunks[0]['id']}").json()["data"]
    assert chunk["id"] == chunks[0]["id"]

    with application.state.session_factory() as session:
        document = session.get(Document, document_id)
        assert document is not None
        assert document.document_type.value == "SCANNED"
