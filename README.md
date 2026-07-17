# VADS Document Pipeline

Backend Python 3.12 cho phần việc **Người 1** của VADS: tiếp nhận PDF/DOCX, lưu MinIO,
xử lý nền qua Celery, trích xuất trang và OCR có chọn lọc, nhận diện cấu trúc pháp lý,
tạo `DocumentChunk` và cung cấp read interface cho các module phía sau.

Repository này không triển khai summary AI, knowledge graph, red flag, embedding,
reranking, chat Q&A hoặc frontend.

## Pipeline

```text
Upload
  -> validate extension / MIME / magic bytes / filename / size / SHA-256
  -> upload original to MinIO
  -> commit Document + DocumentFile + ProcessingJob
  -> Celery worker
       -> classify TEXT_BASED / SCANNED / HYBRID
       -> render pages
       -> extract text layer or OCR only the required pages
       -> persist DocumentPage + PageBlock + DocumentTable
       -> parse legal hierarchy with rules and regex
       -> persist DocumentSection
       -> create and persist DocumentChunk
```

Luồng code tuân thủ `Router -> Service -> Repository -> Database/External service`.
Business service chỉ biết `StorageProvider`; `MinioStorageProvider` là adapter S3 cụ thể.
OCR chỉ đi qua `OcrProvider`. `DifficultPageReviewer` là extension point để orchestration
kiểm tra trang khó, không thay OCR engine chính.

## Chạy bằng Docker Compose

```bash
cp .env.example .env
docker compose up --build
```

Các service:

- API và Alembic: `http://localhost:8000/api/docs`
- PostgreSQL/pgvector: cổng `5432`
- Redis/Celery: cổng `6379`
- MinIO API/console: `9000`/`9001`

`minio-init` tự tạo bucket được cấu hình bởi `VADS_S3_BUCKET_NAME`. Không commit `.env`;
chỉ `.env.example` được quản lý trong Git.

## Chạy trực tiếp

```bash
python -m venv .venv
pip install -e ".[test]"
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

Worker:

```bash
celery -A app.config.celery_app:celery_app worker --loglevel=INFO
celery -A app.config.celery_app:celery_app beat --loglevel=INFO
```

Mặc định local dùng `VADS_OCR_PROVIDER=MOCK`. Để OCR scan thật, cài PaddleOCR runtime và
đặt `VADS_OCR_PROVIDER=PADDLEOCR`. Không dùng vision LLM làm OCR engine chính.

## API

```text
POST   /api/workspaces
POST   /api/workspaces/{workspaceId}/documents
GET    /api/documents/{documentId}
GET    /api/documents/{documentId}/status
GET    /api/documents/{documentId}/pages
GET    /api/documents/{documentId}/pages/{pageIndex}
GET    /api/documents/{documentId}/sections
GET    /api/documents/{documentId}/chunks
GET    /api/documents/{documentId}/chunks/{chunkId}
DELETE /api/documents/{documentId}
POST   /api/documents/{documentId}/reprocess
```

Tạo workspace:

```bash
curl -X POST http://localhost:8000/api/workspaces \
  -H "Content-Type: application/json" \
  -d '{"name":"Phân tích dự thảo","description":"Phiên họp thẩm định"}'
```

Upload:

```bash
curl -X POST http://localhost:8000/api/workspaces/{workspaceId}/documents \
  -F "file=@du-thao.pdf;type=application/pdf" \
  -F "displayName=Dự thảo kế hoạch"
```

Success response:

```json
{
  "success": true,
  "data": {
    "documentId": "c00e62d1-9eed-4b12-98d4-85fc34bccd38",
    "status": "UPLOADED"
  },
  "message": "Operation completed successfully",
  "timestamp": "2026-07-17T10:00:00Z"
}
```

Error response:

```json
{
  "success": false,
  "error": {
    "code": "DOCUMENT_NOT_FOUND",
    "message": "Không tìm thấy tài liệu.",
    "details": {}
  },
  "timestamp": "2026-07-17T10:00:00Z"
}
```

## Interface dùng chung

Import interface, không truy cập trực tiếp bảng chunk/section/page của module tài liệu:

```python
from app.documents.interfaces import DocumentChunkReader
```

Interface cung cấp:

- `list_chunks(document_id)`
- `get_chunk(chunk_id)`
- `search_chunks_by_section(document_id, filters)`
- `get_page_blocks(document_id, page_index)`
- `get_document_structure(document_id)`

## Test và kiểm tra chất lượng

```bash
pytest
ruff check app
ruff format --check app
alembic upgrade head
docker compose config --quiet
```

Test dùng SQLite, object storage giả và dispatcher giả nên không cần PostgreSQL, Redis hay
MinIO. Bộ test bao phủ upload/validation/compensation, PDF classification, OCR+bbox,
structure hierarchy qua nhiều trang, chunk metadata, soft delete, reprocess và job failure.

## AI orchestration (Người 2)

Tầng AI orchestration nhận `DocumentChunk` qua `DocumentChunkReader` và không phụ thuộc upload,
OCR, parser, vector database hay retrieval. Implementation gồm model registry/gateway, DAG có
retry và fallback, summary có citation, knowledge graph, red-flag rule engine, critical questions
và model execution audit.

Tài liệu vận hành, model routing và cách inject provider adapter nằm tại
[`app/orchestrator/README.md`](app/orchestrator/README.md). Có thể chạy trực tiếp các request mẫu
trong [`app/orchestrator/api_examples.http`](app/orchestrator/api_examples.http).

Các API mới:

```text
POST /api/documents/{documentId}/analysis
GET  /api/workflows/{workflowId}
POST /api/documents/{documentId}/summaries/generate
GET  /api/documents/{documentId}/summaries
GET  /api/summaries/{summaryId}
POST /api/documents/{documentId}/knowledge-graph/generate
GET  /api/documents/{documentId}/knowledge-graph
GET  /api/documents/{documentId}/red-flags
POST /api/documents/{documentId}/critical-questions/generate
GET  /api/documents/{documentId}/critical-questions
```
