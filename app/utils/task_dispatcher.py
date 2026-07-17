from functools import lru_cache
from typing import Protocol


class TaskDispatcher(Protocol):
    def enqueue_processing(self, job_id: str) -> None: ...

    def enqueue_purge(self, document_id: str) -> None: ...


class CeleryTaskDispatcher:
    def enqueue_processing(self, job_id: str) -> None:
        from app.service.processing_tasks import process_document

        process_document.apply_async(args=[job_id])

    def enqueue_purge(self, document_id: str) -> None:
        from app.service.processing_tasks import purge_document_objects

        purge_document_objects.apply_async(args=[document_id])


@lru_cache
def get_task_dispatcher() -> TaskDispatcher:
    return CeleryTaskDispatcher()
