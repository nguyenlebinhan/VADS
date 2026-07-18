from fastapi import APIRouter, FastAPI

from app.api.v1.admin_users import router as admin_users_router
from app.api.v1.audit_logs import router as audit_logs_router
from app.api.v1.auth import router as auth_router
from app.api.v1.documents import router as documents_router
from app.api.v1.rag import router as rag_router
from app.api.v1.staff_directory import router as staff_directory_router

SECURE_V1_ROUTERS: tuple[APIRouter, ...] = (
    auth_router,
    admin_users_router,
    staff_directory_router,
    documents_router,
    rag_router,
    audit_logs_router,
)


def install_secure_v1_routes(application: FastAPI, *, prefix: str) -> None:
    for child_router in SECURE_V1_ROUTERS:
        application.include_router(child_router, prefix=f"{prefix}/v1")
