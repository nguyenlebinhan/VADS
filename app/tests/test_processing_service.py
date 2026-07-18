import subprocess
import sys

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.exceptions import AppError, InvalidStateTransitionError
from app.model.processing import ProcessingJob, ProcessingStatus, ProcessingStep
from app.service.processing import ProcessingStateService
from app.tests.helpers import minimal_pdf


def test_processing_tasks_bootstrap_all_mapper_relationships() -> None:
    script = (
        "from sqlalchemy.orm import configure_mappers; "
        "from app.service.processing_tasks import redispatch_uploaded_jobs; "
        "configure_mappers(); "
        "assert redispatch_uploaded_jobs.name == "
        "'vads.processing.redispatch_uploaded_jobs'"
    )
    completed = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        check=False,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr


def test_processing_state_machine_rejects_progress_regression(
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
        job = session.scalar(select(ProcessingJob).where(ProcessingJob.document_id == document_id))
        assert job is not None
        service = ProcessingStateService(session)
        service.transition(
            job.id,
            status=ProcessingStatus.QUEUED,
            progress=0,
            current_step=ProcessingStep.VALIDATING_FILE,
        )
        service.transition(
            job.id,
            status=ProcessingStatus.PROCESSING,
            progress=50,
            current_step=ProcessingStep.OCR_PROCESSING,
        )

        with pytest.raises(AppError) as error:
            service.transition(
                job.id,
                status=ProcessingStatus.PROCESSING,
                progress=40,
                current_step=ProcessingStep.RENDERING_PAGES,
            )
        assert error.value.code == "PROCESSING_PROGRESS_REGRESSION"


def test_processing_state_machine_rejects_terminal_transition(
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
        job = session.scalar(select(ProcessingJob).where(ProcessingJob.document_id == document_id))
        assert job is not None
        service = ProcessingStateService(session)
        service.transition(
            job.id,
            status=ProcessingStatus.CANCELLED,
            progress=0,
            current_step=ProcessingStep.VALIDATING_FILE,
        )
        with pytest.raises(InvalidStateTransitionError):
            service.transition(
                job.id,
                status=ProcessingStatus.PROCESSING,
                progress=1,
                current_step=ProcessingStep.OCR_PROCESSING,
            )
