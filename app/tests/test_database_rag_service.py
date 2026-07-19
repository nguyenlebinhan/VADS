from sqlalchemy.orm import Session, sessionmaker

from app.core.permissions import UserRole
from app.model.chunking import DocumentChunk
from app.model.documents import Document, DocumentApprovalStatus, DocumentType
from app.model.extraction import DocumentPage, PageBlock
from app.model.processing import ProcessingStatus
from app.model.tenancy import Commune, Province
from app.model.users import User, UserStatus
from app.model.workspaces import Workspace
from app.schemas.rag import RagQueryRequest
from app.services.database_rag_service import DatabaseRagService


class FakeRagClient:
    def answer_with_context(self, *, question: str, context: str) -> str:
        assert question == "Thoi han nop bao cao la bao lau?"
        assert "document_id=" in context
        assert "30 ngay" in context
        assert "article=Dieu 3" in context
        assert "clause=Mục 1" in context
        assert "clause=Khoản 1" not in context
        return "Thoi han nop bao cao la 30 ngay. [Nguon 1]"


def test_database_rag_reads_persisted_document_chunks(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        province = Province(name="Tinh RAG", code="RAG")
        session.add(province)
        session.flush()
        commune = Commune(
            province_id=province.id,
            name="Xa RAG",
            code="RAG-01",
        )
        session.add(commune)
        session.flush()
        actor = User(
            commune_id=commune.id,
            username="rag.user",
            email="rag.user@example.gov.vn",
            full_name="RAG User",
            role=UserRole.USER,
            password_hash="test-hash",
            is_active=True,
            must_change_password=False,
            status=UserStatus.ACTIVE,
        )
        session.add(actor)
        session.flush()
        workspace = Workspace(name="RAG Workspace", owner_id=actor.id)
        session.add(workspace)
        session.flush()
        document = Document(
            commune_id=commune.id,
            owner_id=actor.id,
            workspace_id=workspace.id,
            uploaded_by=actor.id,
            approval_status=DocumentApprovalStatus.DRAFT,
            display_name="Quy dinh bao cao",
            original_filename="quy-dinh.docx",
            mime_type=(
                "application/vnd.openxmlformats-officedocument."
                "wordprocessingml.document"
            ),
            file_extension=".docx",
            file_size=100,
            checksum="a" * 64,
            status=ProcessingStatus.COMPLETED,
            total_pages=1,
            document_type=DocumentType.DOCX,
            is_deleted=False,
        )
        session.add(document)
        session.flush()
        page = DocumentPage(
            document_id=document.id,
            page_index=0,
            width=0,
            height=0,
            extracted_text="Thoi han nop bao cao la 30 ngay.",
        )
        session.add(page)
        session.flush()
        block = PageBlock(
            document_id=document.id,
            page_id=page.id,
            order_index=0,
            text="Thoi han nop bao cao la 30 ngay.",
            normalized_text="thoi han nop bao cao la 30 ngay.",
        )
        session.add(block)
        session.flush()
        session.add(
            DocumentChunk(
                document_id=document.id,
                order_index=0,
                chunk_type="PARAGRAPH",
                content="Thoi han nop bao cao la 30 ngay ke tu ngay ban hanh.",
                normalized_content="thoi han nop bao cao la 30 ngay ke tu ngay ban hanh.",
                pdf_page_start=0,
                pdf_page_end=0,
                article="Dieu 3",
                clause="Khoản 1",
                start_block_id=block.id,
                end_block_id=block.id,
                token_count=12,
            )
        )
        session.commit()

        result = DatabaseRagService(session, client=FakeRagClient()).answer(
            actor=actor,
            payload=RagQueryRequest(
                question="Thoi han nop bao cao la bao lau?",
                document_ids=[document.id],
            ),
        )

    assert result.retrieval_mode == "database_lexical"
    assert result.answer == "Thoi han nop bao cao la 30 ngay."
    assert result.sources[0].document_id == document.id
    assert result.sources[0].document_title == "Quy dinh bao cao"
    assert result.sources[0].page_number == 1
    assert result.sources[0].article == "Dieu 3"
    assert result.sources[0].clause == "Mục 1"
