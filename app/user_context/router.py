from typing import Annotated

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.common.contracts import ApiSuccessResponse
from app.config.database import get_db
from app.user_context.schemas import UserContextData, UserContextUpdate
from app.user_context.service import UserContextService

router = APIRouter(prefix="/users/me/context", tags=["User Context"])


def current_user_id(
    user_id: Annotated[
        str,
        Header(
            alias="X-User-ID",
            min_length=1,
            max_length=160,
            description="OIDC subject supplied by the authentication gateway",
        ),
    ],
) -> str:
    return user_id


def get_user_context_service(
    session: Annotated[Session, Depends(get_db)],
) -> UserContextService:
    return UserContextService(session)


@router.get("", response_model=ApiSuccessResponse[UserContextData])
def get_my_context(
    user_id: Annotated[str, Depends(current_user_id)],
    service: Annotated[UserContextService, Depends(get_user_context_service)],
) -> ApiSuccessResponse[UserContextData]:
    return ApiSuccessResponse(data=service.get(user_id))


@router.put("", response_model=ApiSuccessResponse[UserContextData])
def update_my_context(
    payload: UserContextUpdate,
    user_id: Annotated[str, Depends(current_user_id)],
    service: Annotated[UserContextService, Depends(get_user_context_service)],
) -> ApiSuccessResponse[UserContextData]:
    return ApiSuccessResponse(
        data=service.upsert(user_id, payload),
        message="Đã cập nhật hồ sơ ngữ cảnh người dùng",
    )
