from collections.abc import Generator
from typing import Any, BinaryIO

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.config.database import get_db
from app.config.settings import Settings, get_settings
from app.main import create_app
from app.model.base import Base
from app.utils.model_registry import import_models
from app.utils.storage_dependencies import get_object_storage
from app.utils.task_dispatcher import get_task_dispatcher


class FakeObjectStorage:
    bucket_name = "test-documents"

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def upload(
        self,
        file_object: BinaryIO,
        *,
        object_key: str,
        content_type: str,
        metadata: dict[str, str] | None = None,
    ) -> None:
        del content_type, metadata
        file_object.seek(0)
        self.objects[object_key] = file_object.read()

    def delete(self, *, object_key: str) -> None:
        self.objects.pop(object_key, None)

    def download(self, *, object_key: str) -> bytes:
        return self.objects[object_key]

    def health_check(self) -> bool:
        return True


class FakeTaskDispatcher:
    def __init__(self) -> None:
        self.processing_job_ids: list[str] = []
        self.purge_document_ids: list[str] = []
        self.analysis_workflow_ids: list[str] = []

    def enqueue_processing(self, job_id: str) -> None:
        self.processing_job_ids.append(job_id)

    def enqueue_purge(self, document_id: str) -> None:
        self.purge_document_ids.append(document_id)

    def enqueue_analysis(self, workflow_id: str) -> None:
        self.analysis_workflow_ids.append(workflow_id)


@pytest.fixture
def test_settings(tmp_path: Any) -> Settings:
    return Settings(
        _env_file=None,
        app_name="VADS Test API",
        environment="test",
        debug=False,
        api_prefix="/api",
        database_url=f"sqlite:///{tmp_path / 'vads-test.db'}",
        database_echo=False,
        redis_url="redis://localhost:6379/0",
        celery_broker_url="memory://",
        celery_result_backend="cache+memory://",
        celery_task_always_eager=True,
        document_processing_queue="test-document-processing",
        storage_provider="MINIO",
        s3_endpoint_url=None,
        s3_access_key="test",
        s3_secret_key="test",
        s3_bucket_name="test-documents",
        s3_region="us-east-1",
        s3_force_path_style=True,
        max_upload_size_mb=1,
        upload_spool_memory_mb=1,
        delete_object_on_soft_delete=True,
        legacy_api_enabled=True,
        cors_origins=["http://localhost:3000"],
    )


@pytest.fixture
def session_factory(test_settings: Settings) -> Generator[sessionmaker[Session], None, None]:
    import_models()
    engine = create_engine(
        test_settings.database_url,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(dbapi_connection: Any, connection_record: Any) -> None:
        del connection_record
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    factory = sessionmaker(
        bind=engine,
        class_=Session,
        autoflush=False,
        expire_on_commit=False,
    )
    yield factory
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def application(
    test_settings: Settings,
    session_factory: sessionmaker[Session],
) -> Generator[FastAPI, None, None]:
    fake_storage = FakeObjectStorage()
    fake_dispatcher = FakeTaskDispatcher()
    app = create_app(test_settings)

    def override_db() -> Generator[Session, None, None]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_object_storage] = lambda: fake_storage
    app.dependency_overrides[get_task_dispatcher] = lambda: fake_dispatcher
    app.state.fake_storage = fake_storage
    app.state.fake_dispatcher = fake_dispatcher
    app.state.session_factory = session_factory
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def client(application: FastAPI) -> Generator[TestClient, None, None]:
    with TestClient(application) as test_client:
        yield test_client


@pytest.fixture
def workspace_id(client: TestClient) -> str:
    response = client.post(
        "/api/workspaces",
        json={
            "name": "Phân tích dự thảo kế hoạch",
            "description": "Workspace kiểm thử",
        },
    )
    assert response.status_code == 201
    return response.json()["data"]["id"]
