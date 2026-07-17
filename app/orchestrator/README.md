# VADS AI Orchestration

Module Người 2 chỉ đọc dữ liệu nguồn qua `DocumentChunkReader`. Nó không upload file, chạy OCR,
parse PDF, tạo embedding, retrieval/reranking hay cung cấp chat/frontend.

## Luồng xử lý

```text
ExecutionPlanner + ModelRegistry
  -> persisted ai_workflows / ai_workflow_steps
  -> WorkflowExecutor (DAG; parallel theo dependency)
       -> tối đa 2 retry trên primary
       -> tối đa 1 lần gọi fallback
       -> validate structured JSON bằng Pydantic
       -> model_executions cho từng attempt
  -> citation validation bằng code
  -> persist artifact đã qua publication gate
```

Workflow phân tích đầy đủ dùng nhiều executor:

```text
DeepSeek summary ------------------------------+
DeepSeek entity/relation extraction            |  (hai step đầu có thể song song)
  -> gpt-oss-20b normalization                  |
  -> rule-based deduplication                   |
  -> GLM-5.2 complex relation verification     |
  -> code red-flag rules                        |
  -> GLM-5.2 HIGH/CRITICAL verification         |
  -> DeepSeek critical-question generation     |
  -> GLM-5.2 complex-question verification ----+
```

Khi `privateProcessing=true`, policy chọn model hỗ trợ private deployment, ưu tiên
`gpt-oss-120b` cho reasoning. Tên model và fallback chain chỉ nằm trong `ModelRegistry`; router
không chứa alias hard-code.

## Model provider adapter

`app.main` dùng `UnavailableModelGateway` an toàn khi deployment chưa cấu hình provider. Adapter
thực tế phải implement bốn method của `ModelGateway`: `generate_text`, `generate_structured`,
`analyze_image`, `health_check`. Có thể gắn adapter vào app lúc bootstrap:

```python
from app.main import create_app
from app.model_gateway import CallableModelGateway


def provider(operation: str, model_alias: str, payload: dict):
    # Gọi SDK/provider nội bộ ở đây và trả text, dict hoặc Pydantic model.
    ...


app = create_app()
app.state.model_gateway = CallableModelGateway(provider)
```

Không log prompt/raw document vào audit. Audit chỉ lưu task metadata, output snapshot có cấu trúc,
latency, attempt, fallback và lỗi provider.

## Citation publication gate

`CitationValidator` kiểm tra bằng code:

- document tồn tại và đúng document đang xử lý;
- chunk tồn tại và thuộc document;
- quote nằm trong `content`/`normalizedContent` sau Unicode + whitespace normalization;
- Điều, Khoản, Điểm khớp metadata chunk;
- page thuộc page range;
- bbox nằm trong source anchor của đúng page;
- `sourceConfidence` thuộc `[0, 1]`.

Summary item lỗi citation chỉ được sửa đúng item đó, tối đa hai lần. Nếu vẫn lỗi, item không được
ghi vào `summary_items` và summary version mang trạng thái `NEEDS_REVIEW`. HIGH/CRITICAL red flag
thiếu citation hợp lệ bị `SUPPRESSED`, nên reader mặc định không phát hành nó.

## Reader contracts cho Người 3

```python
from app.citations import CitationReader
from app.knowledge_graph import KnowledgeGraphReader
from app.red_flags import RedFlagReader
from app.summaries import SummaryReader
```

Các SQLAlchemy adapter tương ứng là `SqlAlchemyCitationReader`,
`SqlAlchemyKnowledgeGraphReader`, `SqlAlchemyRedFlagReader` và `SqlAlchemySummaryReader`.

## Execution plan mẫu

```json
{
  "workflowId": "73556a5e-3ec8-4d48-9721-32ddd83c9195",
  "intent": "DOCUMENT_SUMMARY",
  "documentId": "document-id",
  "privateProcessing": false,
  "steps": [
    {
      "stepId": "generate-summary",
      "taskType": "DOCUMENT_SUMMARY",
      "executor": "DeepSeek-V4-Flash",
      "reasonForSelection": "Tác vụ tóm tắt có cấu trúc cho một tài liệu",
      "dependsOn": [],
      "canRunInParallel": true,
      "timeoutSeconds": 90,
      "maxRetries": 2,
      "fallbackModel": "GLM-5.1",
      "expectedOutputSchema": "DocumentSummaryOutput"
    }
  ]
}
```

## Kiểm tra

```bash
pytest app/tests/test_ai_orchestration.py
pytest
ruff check app
ruff format --check app
alembic upgrade head
```

Migration của module là `20260718_0003_ai_orchestration.py`; không sửa migration của pipeline tài
liệu. Bộ test module bao phủ đủ 21 case routing/private/retry/fallback/schema/citation/versioning/
graph/rules/questions/audit.
