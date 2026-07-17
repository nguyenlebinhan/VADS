def import_models() -> None:
    """Import every mapped class before Alembic or metadata operations."""

    from app.model import chunking as chunking_models  # noqa: F401
    from app.model import documents as documents_models  # noqa: F401
    from app.model import extraction as extraction_models  # noqa: F401
    from app.model import processing as processing_models  # noqa: F401
    from app.model import storage as storage_models  # noqa: F401
    from app.model import structure as structure_models  # noqa: F401
    from app.model import users as users_models  # noqa: F401
    from app.model import workspaces as workspaces_models  # noqa: F401
