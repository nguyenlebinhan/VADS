from fastapi import APIRouter

from app.api_aggregation import models as owner3_models
from app.api_aggregation.endpoints import router as aggregation_router
from app.chat.router import router as chat_router
from app.meeting.router import router as meeting_router
from app.retrieval.router import router as retrieval_router
from app.vector_store.router import router as vector_store_router

api_router = APIRouter()
api_router.include_router(vector_store_router)
api_router.include_router(retrieval_router)
api_router.include_router(chat_router)
api_router.include_router(meeting_router)
api_router.include_router(aggregation_router)


def install_owner3_routes(application, *, prefix: str = "/api") -> None:
    """Explicit integration hook; avoids modifying Owner 1's app/main.py."""

    # Importing the registry before application startup makes every Owner 3
    # mapping visible to SQLAlchemy/Alembic without editing Owner 1 modules.
    _ = owner3_models
    application.include_router(api_router, prefix=prefix)
