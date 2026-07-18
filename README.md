# VADS Document Pipeline

Thiết kế và implementation Authentication/Authorization đa xã nằm tại
[docs/authentication-authorization.md](docs/authentication-authorization.md). API bảo mật dùng
prefix /api/v1, access JWT 10 phút và opaque refresh rotation. Route legacy không có tenant
scope mặc định bị tắt; chỉ bật cho test/chuyển đổi bằng VADS_LEGACY_API_ENABLED=true.

Backend Python 3.12 cho phần việc **Người 1** của VADS: tiếp nhận PDF/DOCX, lưu MinIO,
xử lý nền qua Celery, trích xuất trang và OCR có chọn lọc, nhận diện cấu trúc pháp lý,
tạo `DocumentChunk` và cung cấp read interface cho các module phía sau.

Frontend Vite nằm trong `frontend/` và dùng API bảo mật `/api/v1` cho đăng nhập, hồ sơ và
danh sách tài liệu. Các màn hình thư viện/sổ tay còn là dữ liệu mẫu cho tới khi backend có
endpoint tenant-scoped tương ứng.

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

YĂªu cáº§u Python `>=3.12,<3.14`. TrĂªn Windows nĂªn táº¡o virtualenv báº±ng Python launcher Ä‘á»ƒ
trĂ¡nh dĂ¹ng nháº§m Python 3.14:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[test]"
```

TrĂªn macOS/Linux:

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[test]"
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

Worker:

```bash
celery -A app.config.celery_app:celery_app worker --loglevel=INFO
celery -A app.config.celery_app:celery_app beat --loglevel=INFO
```

Docker Compose cài PaddlePaddle CPU và PaddleOCR 3.x riêng trong image `worker`; image
`api` và `beat` không mang runtime OCR nặng. `VADS_OCR_PROVIDER=PADDLEOCR` được bật trong
`.env.example`. Lần chạy đầu worker sẽ tải model tiếng Việt PP-OCRv3, sau đó OCR chỉ các
trang scan/image-only. Khi chạy trực tiếp ngoài Docker, cài runtime bằng các lệnh:

```bash
python -m pip install paddlepaddle==3.2.0 \
  --index-url https://www.paddlepaddle.org.cn/packages/stable/cpu/
python -m pip install -e ".[ocr]"
```

Không dùng vision LLM làm OCR engine chính.

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

### FPT AI Inference

AI orchestration và phần sinh câu trả lời Chat dùng chung `FptAiModelGateway`. Cấu hình khóa trong
`.env` cục bộ hoặc secret manager bằng `VADS_FPT_AI_API_KEY`; không ghi khóa thật vào source hay
`.env.example`. Endpoint mặc định là `https://mkp-api.fptcloud.com` và không cần cài OpenAI SDK.

```dotenv
VADS_FPT_AI_ENABLED=true
VADS_FPT_AI_API_KEY=<fpt-ai-marketplace-key>
VADS_FPT_AI_MODEL_MAP={}
```

Chạy health check theo alias:

```bash
python -c "from app.config.settings import Settings; from app.model_gateway.fpt_ai import build_fpt_ai_gateway; print(build_fpt_ai_gateway(Settings()).health_check('GLM-5.2'))"
```

## Kiểm thử toàn bộ API bằng Postman

1. Chạy backend bằng `docker compose up --build`.
2. Import collection [`docs/postman/VADS.postman_collection.json`](docs/postman/VADS.postman_collection.json).
3. Import environment [`docs/postman/VADS.postman_environment.json`](docs/postman/VADS.postman_environment.json) và chọn **VADS Local**.
4. Chạy lần lượt các folder. Ở request upload, chọn một file PDF/DOCX.

Collection tự lưu `workspaceId`, `documentId`, `chunkId`, `workflowId`, `summaryId`,
`chatSessionId` từ response. Có thể import trực tiếp OpenAPI từ
`http://localhost:8000/api/openapi.json`; Swagger UI nằm tại `http://localhost:8000/api/docs`.

## Regulatory Change Intelligence vertical slice

Backend Python/FastAPI hiện hỗ trợ flow đầu tiên: upload nhiều phiên bản của cùng văn bản, parse
cấu trúc pháp lý, phát hiện thay đổi số liệu/thời hạn/trách nhiệm, mapping với đề án, xác định phòng
ban và hành động, verification và audit từng agent task.

Tài liệu kiến trúc, ERD, sequence và API nằm tại
[`docs/regulatory-change-architecture.md`](docs/regulatory-change-architecture.md).

Metadata khi gọi `POST /api/documents` được gửi dưới dạng JSON trong field multipart `metadata`;
file nằm trong field `file`. Chạy demo/test end-to-end:

```bash
pytest app/tests/test_regulatory_change_vertical_slice.py -q
```

Tạo hai file DOCX demo rồi import collection Postman:

```bash
python scripts/generate_regulatory_demo_documents.py
```

- [`Regulatory Change Postman collection`](docs/postman/Regulatory-Change-Vertical-Slice.postman_collection.json)
- [`VADS Local environment`](docs/postman/VADS.postman_environment.json)

Danh mục API bảo mật và 49 operation legacy đã hợp nhất: [`docs/api-catalog.md`](docs/api-catalog.md).

## Upload và RAG từ database

Frontend dùng luồng bảo mật sau:

```text
POST /api/v1/documents
  -> lưu file gốc vào MinIO/S3
  -> lưu metadata và processing job vào database
  -> Celery trích xuất nội dung và ghi document_chunks vào database

POST /api/v1/rag/query
  -> kiểm tra quyền của người dùng trên tài liệu
  -> retrieval từ document_chunks
  -> gửi các chunk phù hợp cho mô hình và trả câu trả lời kèm nguồn
```

Request RAG nhận một hoặc nhiều tài liệu đã xử lý:

```json
{
  "question": "Thời hạn nộp báo cáo là bao lâu?",
  "document_ids": ["document-id"],
  "top_k": 5
}
```

File người dùng tải lên không được lưu trực tiếp dưới dạng BLOB trong database. File gốc nằm ở
object storage; database lưu metadata, trạng thái xử lý, nội dung đã tách và các chunk dùng cho
retrieval. `VADS_USER_DOCUMENT_UPLOAD_ENABLED=true` mở upload cho tài khoản USER.

## DOCX RAG standalone (legacy)

Module `app/docx_rag` ở chế độ legacy chỉ đọc các file `.docx` trong `app/data`, gồm cả paragraph và table.
Frontend không dùng thư mục này làm nguồn dữ liệu người dùng.
Index được cache tại `.cache/docx_rag/index.json`; cache này không chứa API key và đã được
gitignore. Nếu embedding không gọi được, hệ thống tự chuyển sang lexical retrieval. Việc sinh câu
trả lời vẫn cần OpenAI API key.

Thiết lập một trong hai biến môi trường sau (không ghi key thật vào source hoặc `.env.example`):

```powershell
$env:OPENAI_API_KEY="<your-key>"
# hoặc
$env:VADS_OPENAI_API_KEY="<your-key>"
```

Chạy thử bằng terminal:

```bash
python scripts/test_docx_rag.py "Câu hỏi cần hỏi"
python scripts/test_docx_rag.py "Câu hỏi cần hỏi" --lexical-only
```

Model mặc định là `text-embedding-3-small` và `gpt-4.1-mini`. Có thể đổi bằng
`VADS_OPENAI_EMBEDDING_MODEL`, `VADS_OPENAI_CHAT_MODEL`, hoặc đổi endpoint tương thích bằng
`VADS_OPENAI_BASE_URL`.

API FastAPI:

```text
POST /api/docx-rag/query
```

```json
{
  "question": "Thời hạn lưu hồ sơ là bao lâu?",
  "top_k": 5,
  "rebuild_index": false
}
```

Mỗi lần gọi API, backend thực hiện retrieval và sinh câu trả lời ngay, đồng thời tạo một
`query_id` UUID mới. Kể cả khi gửi cùng một câu hỏi nhiều lần, mỗi request vẫn có ID riêng.
Response của POST chỉ trả metadata về sources, không trả mảng `sources`:

```json
{
  "query_id": "b3e26bd0-23ef-4fcb-9cb6-895108f72ea6",
  "answer": "Hồ sơ phải được lưu trong năm năm. [Nguồn 1]",
  "retrieval_mode": "embedding",
  "sources_available": true,
  "source_count": 1,
  "page_note": "page_number is null because DOCX uses a flowing layout and does not store a stable, device-independent page number.",
  "embedding_error": null
}
```

Chỉ lấy sources khi người dùng yêu cầu xem nguồn:

```text
GET /api/docx-rag/queries/{query_id}/sources
```

```json
{
  "query_id": "b3e26bd0-23ef-4fcb-9cb6-895108f72ea6",
  "sources": [
    {
      "file_name": "70_2025_ND-CP_577816.docx",
      "chunk_id": "70_2025_ND-CP_577816.docx:chunk-0003",
      "paragraph_index": 15,
      "table_index": null,
      "paragraph_indices": [15, 16],
      "table_indices": [],
      "article": "Điều 3",
      "clause": "Khoản 2",
      "page_number": null,
      "quote": "Đoạn trích nguyên bản...",
      "score": 0.87
    }
  ],
  "page_note": "page_number is null because DOCX uses a flowing layout and does not store a stable, device-independent page number."
}
```

Endpoint GET chỉ đọc sources đã lưu từ POST, không chạy embedding, retrieval hoặc gọi OpenAI
lại. ID không tồn tại hoặc đã hết hạn trả HTTP 404. Sources được giữ trong bộ nhớ 30 phút theo
mặc định; có thể đổi TTL bằng `VADS_DOCX_RAG_QUERY_TTL_SECONDS`.

Frontend phải lưu `query_id` riêng trên từng assistant message, không dùng một
`currentQueryId` chung cho cả cuộc trò chuyện:

```javascript
const queryResult = await postQuestion(question);

const assistantMessage = {
  content: queryResult.answer,
  queryId: queryResult.query_id,
  sources: null,
};

// Chỉ gọi khi người dùng bấm "Xem nguồn" trên đúng message này.
const sourceResult = await fetch(
  `/api/docx-rag/queries/${assistantMessage.queryId}/sources`,
);
```

Store hiện tại là in-memory nên dữ liệu sources sẽ mất khi backend restart và không được chia sẻ
giữa nhiều worker/process. Production nên thay implementation của `SourceStore` bằng Redis hoặc
database.

`page_number` luôn là `null`: DOCX dùng layout động nên không có số trang cố định độc lập với
font, máy in và trình hiển thị. Response trả thêm `page_note` để giải thích giới hạn này.
