def import_models() -> None:
    """Import every mapped class before Alembic or metadata operations."""

    from app.api_aggregation import models as api_aggregation_models  # noqa: F401
    from app.citations import models as citation_models  # noqa: F401
    from app.knowledge_graph import models as knowledge_graph_models  # noqa: F401
    from app.model import chunking as chunking_models  # noqa: F401
    from app.model import documents as documents_models  # noqa: F401
    from app.model import extraction as extraction_models  # noqa: F401
    from app.model import processing as processing_models  # noqa: F401
    from app.model import security as security_models  # noqa: F401
    from app.model import storage as storage_models  # noqa: F401
    from app.model import structure as structure_models  # noqa: F401
    from app.model import tenancy as tenancy_models  # noqa: F401
    from app.model import users as users_models  # noqa: F401
    from app.model import workspaces as workspaces_models  # noqa: F401
    from app.model_audit import models as model_audit_models  # noqa: F401
    from app.orchestrator import models as orchestrator_models  # noqa: F401
    from app.red_flags import models as red_flag_models  # noqa: F401
    from app.regulatory_change import models as regulatory_change_models  # noqa: F401
    from app.summaries import models as summary_models  # noqa: F401
    from app.user_context import models as user_context_models  # noqa: F401
