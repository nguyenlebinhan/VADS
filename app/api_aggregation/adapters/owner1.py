from sqlalchemy import select
from sqlalchemy.orm import Session

from app.chunking.reader import SqlAlchemyDocumentChunkReader
from app.chunking.repository import ExtractionReadRepository
from app.model.documents import Document
from app.model.repositories.documents import DocumentRepository


class Owner1ReadAdapter:
    """Read-only adapter over Owner 1's public models/repositories."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.documents = DocumentRepository(session)
        self.extraction = ExtractionReadRepository(session)
        self.chunks = SqlAlchemyDocumentChunkReader(session)

    def list_workspace_documents(self, workspace_id: str) -> list[Document]:
        return list(
            self.session.scalars(
                select(Document)
                .where(
                    Document.workspace_id == workspace_id,
                    Document.deleted_at.is_(None),
                )
                .order_by(Document.updated_at.desc())
            )
        )

    def get_document(self, document_id: str) -> Document | None:
        return self.documents.get_active(document_id)
