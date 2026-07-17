from typing import Annotated

from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from app.api_aggregation.adapters.mock.owner2 import (
    MockCriticalQuestionReader,
    MockKnowledgeGraphReader,
    MockRedFlagReader,
    MockSummaryReader,
)
from app.api_aggregation.adapters.mock.page_signer import MockPageImageUrlSigner
from app.api_aggregation.schemas import (
    AnalysisOverviewData,
    ViewerData,
    WorkspaceDashboardData,
)
from app.api_aggregation.service import ApiAggregationService
from app.common.contracts import ApiSuccessResponse
from app.config.database import get_db

router = APIRouter(tags=["Frontend Aggregation"])


def get_aggregation_service(
    session: Annotated[Session, Depends(get_db)],
) -> ApiAggregationService:
    return ApiAggregationService(
        session,
        summary_reader=MockSummaryReader(),
        graph_reader=MockKnowledgeGraphReader(),
        red_flag_reader=MockRedFlagReader(),
        critical_question_reader=MockCriticalQuestionReader(),
        page_signer=MockPageImageUrlSigner(),
    )


@router.get(
    "/workspaces/{workspaceId}/dashboard",
    response_model=ApiSuccessResponse[WorkspaceDashboardData],
)
def workspace_dashboard(
    workspace_id: Annotated[str, Path(alias="workspaceId", min_length=1, max_length=40)],
    service: Annotated[ApiAggregationService, Depends(get_aggregation_service)],
) -> ApiSuccessResponse[WorkspaceDashboardData]:
    return ApiSuccessResponse(data=service.dashboard(workspace_id))


@router.get(
    "/documents/{documentId}/viewer-data",
    response_model=ApiSuccessResponse[ViewerData],
)
def document_viewer_data(
    document_id: Annotated[str, Path(alias="documentId", min_length=1, max_length=40)],
    service: Annotated[ApiAggregationService, Depends(get_aggregation_service)],
) -> ApiSuccessResponse[ViewerData]:
    return ApiSuccessResponse(data=service.viewer_data(document_id))


@router.get(
    "/documents/{documentId}/analysis-overview",
    response_model=ApiSuccessResponse[AnalysisOverviewData],
)
def document_analysis_overview(
    document_id: Annotated[str, Path(alias="documentId", min_length=1, max_length=40)],
    service: Annotated[ApiAggregationService, Depends(get_aggregation_service)],
) -> ApiSuccessResponse[AnalysisOverviewData]:
    return ApiSuccessResponse(data=service.analysis_overview(document_id))
