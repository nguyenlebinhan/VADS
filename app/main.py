from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import install_secure_v1_routes
from app.api_aggregation.router import api_router as product_api_router
from app.config.settings import Settings, get_settings
from app.controller.common import router as common_router
from app.documents.router import router as documents_router
from app.docx_rag.router import router as docx_rag_router
from app.exceptions.handlers import register_exception_handlers
from app.model_gateway.fpt_ai import build_fpt_ai_gateway
from app.orchestrator.router import router as ai_orchestration_router
from app.regulatory_change.router import router as regulatory_change_router
from app.user_context.router import router as user_context_router
from app.utils.middleware import RequestContextMiddleware
from app.utils.model_registry import import_models
from app.workspaces.router import router as workspaces_router

FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend-dist"


def create_app(settings: Settings | None = None) -> FastAPI:
    import_models()
    app_settings = settings or get_settings()
    application = FastAPI(
        title=app_settings.app_name,
        version="0.1.0",
        debug=app_settings.debug,
        openapi_url=f"{app_settings.api_prefix}/openapi.json",
        docs_url=f"{app_settings.api_prefix}/docs",
        redoc_url=f"{app_settings.api_prefix}/redoc",
    )
    application.state.settings = app_settings
    application.state.model_gateway = build_fpt_ai_gateway(app_settings)

    application.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-User-ID"],
        expose_headers=["X-Request-ID"],
    )
    application.add_middleware(RequestContextMiddleware)
    register_exception_handlers(application)

    application.include_router(common_router)
    install_secure_v1_routes(application, prefix=app_settings.api_prefix)
    if app_settings.legacy_api_enabled:
        application.include_router(workspaces_router, prefix=app_settings.api_prefix)
        application.include_router(documents_router, prefix=app_settings.api_prefix)
        application.include_router(ai_orchestration_router, prefix=app_settings.api_prefix)
        application.include_router(product_api_router, prefix=app_settings.api_prefix)
        application.include_router(regulatory_change_router, prefix=app_settings.api_prefix)
        application.include_router(user_context_router, prefix=app_settings.api_prefix)
        application.include_router(docx_rag_router, prefix=app_settings.api_prefix)
    if FRONTEND_DIST.is_dir():
        application.mount(
            "/",
            StaticFiles(directory=FRONTEND_DIST, html=True),
            name="frontend",
        )
    return application


app = create_app()
