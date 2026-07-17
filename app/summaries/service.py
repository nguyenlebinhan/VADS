from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.citations.repository import CitationRepository
from app.citations.schemas import CitationOwnerType
from app.citations.validator import CitationValidator
from app.documents.interfaces import DocumentChunkContract, DocumentChunkReader
from app.model_gateway.gateway import ModelGateway
from app.model_gateway.schemas import TaskType
from app.orchestrator.executor import WorkflowExecutor
from app.orchestrator.planner import ExecutionPlanner
from app.orchestrator.schemas import ExecutionStep, StepStatus
from app.summaries.prompts import SUMMARY_CATEGORIES_VI, SUMMARY_PROMPT_VERSION
from app.summaries.reader import SqlAlchemySummaryReader
from app.summaries.repository import SummaryRepository
from app.summaries.schemas import (
    DocumentSummaryOutput,
    RejectedSummaryItem,
    SummaryGenerationResult,
    SummaryItemDraft,
    SummaryItemRepairOutput,
    SummaryStatus,
)


class SummaryService:
    def __init__(
        self,
        session: Session,
        *,
        gateway: ModelGateway,
        planner: ExecutionPlanner,
        chunk_reader: DocumentChunkReader,
        citation_validator: CitationValidator,
    ) -> None:
        self.session = session
        self.gateway = gateway
        self.planner = planner
        self.chunk_reader = chunk_reader
        self.citation_validator = citation_validator
        self.repository = SummaryRepository(session)
        self.citation_repository = CitationRepository(session)

    def generate(
        self,
        document_id: str,
        *,
        private: bool = False,
        prompt_version: str = SUMMARY_PROMPT_VERSION,
    ) -> SummaryGenerationResult:
        chunks = self.chunk_reader.list_chunks(document_id)
        plan = self.planner.summary_plan(document_id, private=private)
        prompt = self._summary_prompt(document_id, chunks, prompt_version)

        def handler(
            step: ExecutionStep,
            model_alias: str,
            dependencies: dict[str, Any],
        ) -> DocumentSummaryOutput:
            del dependencies
            output = self.gateway.generate_structured(
                model_alias=model_alias,
                prompt=prompt,
                output_schema=DocumentSummaryOutput,
                timeout_seconds=step.timeout_seconds,
                metadata={"workflowId": plan.workflow_id, "stepId": step.step_id},
            )
            return self._validate_and_repair(
                output,
                document_id=document_id,
                chunks=chunks,
                model_alias=model_alias,
                timeout_seconds=step.timeout_seconds,
                workflow_id=plan.workflow_id,
            )

        result = WorkflowExecutor(self.session).execute(
            plan,
            {TaskType.DOCUMENT_SUMMARY: handler},
        )
        step_result = result.steps[0]
        if step_result.status != StepStatus.COMPLETED or step_result.output is None:
            return SummaryGenerationResult(workflowId=plan.workflow_id, summary=None)

        output = DocumentSummaryOutput.model_validate(step_result.output)
        status = SummaryStatus.NEEDS_REVIEW if output.rejected_items else SummaryStatus.COMPLETED
        summary = self.repository.create_version(
            document_id=document_id,
            workflow_id=plan.workflow_id,
            model_name=step_result.executor,
            prompt_version=prompt_version,
            status=status,
            rejected_item_count=len(output.rejected_items),
        )
        for order_index, draft in enumerate(output.items):
            item = self.repository.add_item(summary.id, draft, order_index=order_index)
            for citation in draft.citations:
                validated = self.citation_validator.validate_or_raise(
                    citation,
                    expected_document_id=document_id,
                )
                self.citation_repository.add_validated(
                    validated,
                    owner_type=CitationOwnerType.SUMMARY_ITEM,
                    owner_id=item.id,
                )
        self.session.commit()
        view = SqlAlchemySummaryReader(self.session).get_summary(summary.id)
        return SummaryGenerationResult(workflowId=plan.workflow_id, summary=view)

    def _validate_and_repair(
        self,
        output: DocumentSummaryOutput,
        *,
        document_id: str,
        chunks: list[DocumentChunkContract],
        model_alias: str,
        timeout_seconds: int,
        workflow_id: str,
    ) -> DocumentSummaryOutput:
        accepted: list[SummaryItemDraft] = []
        rejected = list(output.rejected_items)
        for item in output.items:
            error = self._item_citation_error(item, document_id)
            if error is None:
                accepted.append(item)
                continue
            repaired: SummaryItemDraft | None = None
            last_error = error
            for repair_attempt in range(1, 3):
                repair_prompt = self._repair_prompt(
                    item,
                    last_error,
                    chunks,
                    document_id=document_id,
                )
                try:
                    repair = self.gateway.generate_structured(
                        model_alias=model_alias,
                        prompt=repair_prompt,
                        output_schema=SummaryItemRepairOutput,
                        timeout_seconds=timeout_seconds,
                        metadata={
                            "workflowId": workflow_id,
                            "operation": "citation-repair",
                            "repairAttempt": repair_attempt,
                        },
                    )
                except Exception as exc:  # provider-specific error; quarantine this item
                    last_error = f"CITATION_REPAIR_FAILED: {type(exc).__name__}: {exc}"
                    continue
                last_error = self._item_citation_error(repair.item, document_id)
                if last_error is None:
                    repaired = repair.item
                    break
            if repaired is not None:
                accepted.append(repaired)
            else:
                rejected.append(RejectedSummaryItem(title=item.title, reason=last_error))
        return DocumentSummaryOutput(items=accepted, rejectedItems=rejected)

    def _item_citation_error(self, item: SummaryItemDraft, document_id: str) -> str | None:
        if item.system_metadata:
            return None
        if not item.citations:
            return "SUMMARY_ITEM_REQUIRES_CITATION"
        results = self.citation_validator.validate_all(
            item.citations,
            expected_document_id=document_id,
        )
        issues = [issue for result in results for issue in result.issues]
        if not issues:
            return None
        return "; ".join(f"{issue.code}: {issue.message}" for issue in issues)

    @staticmethod
    def _summary_prompt(
        document_id: str,
        chunks: list[DocumentChunkContract],
        prompt_version: str,
    ) -> str:
        payload = [
            {
                "chunkId": chunk.id,
                "documentId": chunk.document_id,
                "content": chunk.content,
                "article": chunk.article,
                "clause": chunk.clause,
                "point": chunk.point,
                "pdfPageStart": chunk.pdf_page_start,
                "pdfPageEnd": chunk.pdf_page_end,
                "boundingBoxes": chunk.bounding_boxes,
                "sourceConfidence": chunk.ocr_confidence,
            }
            for chunk in chunks
        ]
        schema = DocumentSummaryOutput.model_json_schema(by_alias=True)
        return (
            f"Prompt version: {prompt_version}\n"
            "Bạn là mô hình tóm tắt văn bản pháp lý. Chỉ dùng bằng chứng trong chunks. "
            "Không suy diễn. Mỗi item phải có ít nhất một citation hợp lệ; ngoại lệ duy nhất "
            "là metadata hệ thống và phải đặt systemMetadata=true. Quote phải được sao chép "
            "từ đúng chunk, page/bbox và Điều/Khoản/Điểm phải khớp metadata.\n"
            f"Các nhóm cần xem xét:\n{SUMMARY_CATEGORIES_VI}\n"
            f"documentId={document_id}\n"
            f"JSON schema={json.dumps(schema, ensure_ascii=False)}\n"
            f"chunks={json.dumps(payload, ensure_ascii=False)}"
        )

    @staticmethod
    def _repair_prompt(
        item: SummaryItemDraft,
        error: str,
        chunks: list[DocumentChunkContract],
        *,
        document_id: str,
    ) -> str:
        source = [
            {
                "chunkId": chunk.id,
                "content": chunk.content,
                "article": chunk.article,
                "clause": chunk.clause,
                "point": chunk.point,
                "pageStart": chunk.pdf_page_start,
                "pageEnd": chunk.pdf_page_end,
                "boundingBoxes": chunk.bounding_boxes,
            }
            for chunk in chunks
        ]
        return (
            "Chỉ sửa item tóm tắt bị lỗi citation dưới đây. Không sửa hoặc tạo item khác. "
            "Quote phải xuất hiện trong đúng chunk của document. Trả JSON theo "
            "SummaryItemRepairOutput.\n"
            f"documentId={document_id}\nerror={error}\n"
            f"item={item.model_dump_json(by_alias=True)}\n"
            f"chunks={json.dumps(source, ensure_ascii=False)}"
        )
