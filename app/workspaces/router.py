from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.common.contracts import ApiSuccessResponse
from app.config.database import get_db
from app.model.schemas.workspaces import WorkspaceCreate, WorkspaceResponse
from app.service.workspaces import WorkspaceService

router = APIRouter(prefix="/workspaces", tags=["Workspaces"])


def get_workspace_service(session: Annotated[Session, Depends(get_db)]) -> WorkspaceService:
    return WorkspaceService(session)


@router.post(
    "",
    response_model=ApiSuccessResponse[WorkspaceResponse],
    status_code=status.HTTP_201_CREATED,
)
def create_workspace(
    payload: WorkspaceCreate,
    service: Annotated[WorkspaceService, Depends(get_workspace_service)],
) -> ApiSuccessResponse[WorkspaceResponse]:
    workspace = service.create(payload)
    return ApiSuccessResponse(
        data=WorkspaceResponse.model_validate(workspace),
        message="Tạo workspace thành công",
    )
