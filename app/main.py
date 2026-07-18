from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import Settings, get_settings
from app.controller.common import router as common_router
from app.documents.router import router as documents_router
from app.exceptions.handlers import register_exception_handlers
from app.model_gateway.fpt_ai import build_fpt_ai_gateway
from app.orchestrator.router import router as ai_orchestration_router
from app.utils.middleware import RequestContextMiddleware
from app.utils.model_registry import import_models
from app.workspaces.router import router as workspaces_router


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
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )
    application.add_middleware(RequestContextMiddleware)
    register_exception_handlers(application)

    application.include_router(common_router)
    application.include_router(workspaces_router, prefix=app_settings.api_prefix)
    application.include_router(documents_router, prefix=app_settings.api_prefix)
    application.include_router(ai_orchestration_router, prefix=app_settings.api_prefix)
    return application


app = create_app()
