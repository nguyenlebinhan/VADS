from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Path, Query, UploadFile, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.common.contracts import ApiSuccessResponse
from app.config.database import get_db
from app.documents.router import get_document_service
from app.regulatory_change.schemas import (
    AgentRunData,
    AnalyzeData,
    AnalyzeRequest,
    ChangeData,
    ImpactData,
    ImpactReviewRequest,
    ProjectCreate,
    ProjectData,
    RegulatoryDocumentData,
    RegulatoryUploadData,
    RegulatoryUploadMetadata,
    TimelineEntry,
)
from app.regulatory_change.service import RegulatoryChangeService
from app.service.documents import DocumentService

router = APIRouter(tags=["Regulatory Change Intelligence"])


def get_regulatory_service(
    session: Annotated[Session, Depends(get_db)],
) -> RegulatoryChangeService:
    return RegulatoryChangeService(session)


def parse_upload_metadata(
    metadata: Annotated[str, Form(description="Regulatory metadata as a JSON object")],
) -> RegulatoryUploadMetadata:
    try:
        return RegulatoryUploadMetadata.model_validate_json(metadata)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors(include_url=False)) from exc


@router.post(
    "/documents",
    response_model=ApiSuccessResponse[RegulatoryUploadData],
    status_code=status.HTTP_201_CREATED,
)
def upload_regulatory_document(
    file: Annotated[UploadFile, File(description="PDF or DOCX")],
    metadata: Annotated[RegulatoryUploadMetadata, Depends(parse_upload_metadata)],
    document_service: Annotated[DocumentService, Depends(get_document_service)],
    service: Annotated[RegulatoryChangeService, Depends(get_regulatory_service)],
) -> ApiSuccessResponse[RegulatoryUploadData]:
    return ApiSuccessResponse(
        data=service.upload(file, metadata, document_service),
        message="Tải lên và nhận diện phiên bản tài liệu thành công",
    )


@router.get(
    "/documents",
    response_model=ApiSuccessResponse[list[RegulatoryDocumentData]],
)
def list_regulatory_documents(
    service: Annotated[RegulatoryChangeService, Depends(get_regulatory_service)],
    workspace_id: Annotated[str | None, Query(alias="workspaceId", max_length=40)] = None,
) -> ApiSuccessResponse[list[RegulatoryDocumentData]]:
    return ApiSuccessResponse(data=service.list_documents(workspace_id))


@router.get(
    "/documents/{documentId}/regulatory-profile",
    response_model=ApiSuccessResponse[RegulatoryDocumentData],
)
def get_regulatory_profile(
    document_id: Annotated[str, Path(alias="documentId", min_length=1, max_length=40)],
    service: Annotated[RegulatoryChangeService, Depends(get_regulatory_service)],
) -> ApiSuccessResponse[RegulatoryDocumentData]:
    return ApiSuccessResponse(data=service.profile(document_id))


@router.get("/documents/{documentId}/summary", response_model=ApiSuccessResponse[dict[str, Any]])
def get_regulatory_summary(
    document_id: Annotated[str, Path(alias="documentId", min_length=1, max_length=40)],
    service: Annotated[RegulatoryChangeService, Depends(get_regulatory_service)],
) -> ApiSuccessResponse[dict[str, Any]]:
    return ApiSuccessResponse(data=service.summary(document_id))


@router.get(
    "/documents/{documentId}/versions",
    response_model=ApiSuccessResponse[list[RegulatoryDocumentData]],
)
def get_document_versions(
    document_id: Annotated[str, Path(alias="documentId", min_length=1, max_length=40)],
    service: Annotated[RegulatoryChangeService, Depends(get_regulatory_service)],
) -> ApiSuccessResponse[list[RegulatoryDocumentData]]:
    return ApiSuccessResponse(data=service.versions(document_id))


@router.get(
    "/documents/{documentId}/timeline",
    response_model=ApiSuccessResponse[list[TimelineEntry]],
)
def get_document_timeline(
    document_id: Annotated[str, Path(alias="documentId", min_length=1, max_length=40)],
    service: Annotated[RegulatoryChangeService, Depends(get_regulatory_service)],
) -> ApiSuccessResponse[list[TimelineEntry]]:
    return ApiSuccessResponse(data=service.timeline(document_id))


@router.get(
    "/documents/{documentId}/changes",
    response_model=ApiSuccessResponse[list[ChangeData]],
)
def get_document_changes(
    document_id: Annotated[str, Path(alias="documentId", min_length=1, max_length=40)],
    service: Annotated[RegulatoryChangeService, Depends(get_regulatory_service)],
) -> ApiSuccessResponse[list[ChangeData]]:
    return ApiSuccessResponse(data=service.changes(document_id))


@router.get(
    "/documents/{documentId}/legal-relations",
    response_model=ApiSuccessResponse[list[dict[str, Any]]],
)
def get_legal_relations(
    document_id: Annotated[str, Path(alias="documentId", min_length=1, max_length=40)],
    service: Annotated[RegulatoryChangeService, Depends(get_regulatory_service)],
) -> ApiSuccessResponse[list[dict[str, Any]]]:
    return ApiSuccessResponse(data=service.legal_relations(document_id))


@router.post(
    "/documents/{documentId}/analyze",
    response_model=ApiSuccessResponse[AnalyzeData],
)
def analyze_document_changes(
    document_id: Annotated[str, Path(alias="documentId", min_length=1, max_length=40)],
    service: Annotated[RegulatoryChangeService, Depends(get_regulatory_service)],
    payload: AnalyzeRequest | None = None,
) -> ApiSuccessResponse[AnalyzeData]:
    return ApiSuccessResponse(
        data=service.analyze(document_id, force=payload.force if payload else False),
        message="Hoàn thành phân tích thay đổi và tác động",
    )


@router.post(
    "/projects",
    response_model=ApiSuccessResponse[ProjectData],
    status_code=status.HTTP_201_CREATED,
)
def create_project(
    payload: ProjectCreate,
    service: Annotated[RegulatoryChangeService, Depends(get_regulatory_service)],
) -> ApiSuccessResponse[ProjectData]:
    return ApiSuccessResponse(data=service.create_project(payload))


@router.get("/projects", response_model=ApiSuccessResponse[list[ProjectData]])
def list_projects(
    service: Annotated[RegulatoryChangeService, Depends(get_regulatory_service)],
    workspace_id: Annotated[str | None, Query(alias="workspaceId", max_length=40)] = None,
) -> ApiSuccessResponse[list[ProjectData]]:
    return ApiSuccessResponse(data=service.list_projects(workspace_id))


@router.get("/projects/{projectId}", response_model=ApiSuccessResponse[ProjectData])
def get_project(
    project_id: Annotated[str, Path(alias="projectId", min_length=1, max_length=40)],
    service: Annotated[RegulatoryChangeService, Depends(get_regulatory_service)],
) -> ApiSuccessResponse[ProjectData]:
    return ApiSuccessResponse(data=service.get_project(project_id))


@router.get("/impacts", response_model=ApiSuccessResponse[list[ImpactData]])
def list_impacts(
    service: Annotated[RegulatoryChangeService, Depends(get_regulatory_service)],
    project_id: Annotated[
        str | None,
        Query(alias="projectId", max_length=40),
    ] = None,
    department: Annotated[str | None, Query(max_length=300)] = None,
) -> ApiSuccessResponse[list[ImpactData]]:
    if project_id:
        service.get_project(project_id)
    return ApiSuccessResponse(
        data=service.impacts(project_id=project_id, department=department)
    )


@router.get("/impacts/{impactId}", response_model=ApiSuccessResponse[ImpactData])
def get_impact(
    impact_id: Annotated[str, Path(alias="impactId", min_length=1, max_length=40)],
    service: Annotated[RegulatoryChangeService, Depends(get_regulatory_service)],
) -> ApiSuccessResponse[ImpactData]:
    return ApiSuccessResponse(data=service.impact(impact_id))


@router.patch("/impacts/{impactId}/review", response_model=ApiSuccessResponse[ImpactData])
def review_impact(
    impact_id: Annotated[str, Path(alias="impactId", min_length=1, max_length=40)],
    payload: ImpactReviewRequest,
    service: Annotated[RegulatoryChangeService, Depends(get_regulatory_service)],
) -> ApiSuccessResponse[ImpactData]:
    return ApiSuccessResponse(
        data=service.review_impact(
            impact_id,
            status=payload.status,
            reviewed_by=payload.reviewed_by,
            note=payload.note,
        )
    )


@router.get("/agent-runs/{runId}", response_model=ApiSuccessResponse[AgentRunData])
def get_agent_run(
    run_id: Annotated[str, Path(alias="runId", min_length=1, max_length=40)],
    service: Annotated[RegulatoryChangeService, Depends(get_regulatory_service)],
) -> ApiSuccessResponse[AgentRunData]:
    return ApiSuccessResponse(data=service.run_data(run_id))


@router.post("/agent-runs/{runId}/retry", response_model=ApiSuccessResponse[AnalyzeData])
def retry_agent_run(
    run_id: Annotated[str, Path(alias="runId", min_length=1, max_length=40)],
    service: Annotated[RegulatoryChangeService, Depends(get_regulatory_service)],
) -> ApiSuccessResponse[AnalyzeData]:
    return ApiSuccessResponse(data=service.retry_run(run_id))
