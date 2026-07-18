# VADS / Regulatory Change Intelligence — Full API Catalog

Base URL: `http://localhost:8000`

Interactive specification:

- Swagger UI: `GET /api/docs`
- ReDoc: `GET /api/redoc`
- OpenAPI JSON: `GET /api/openapi.json`

Normal JSON responses use the shared envelope:

```json
{
  "success": true,
  "data": {},
  "message": "Operation completed successfully",
  "timestamp": "2026-07-18T00:00:00Z"
}
```

## Health and workspace

| Method | Path | Purpose |
|---|---|---|
| GET | `/health/live` | API liveness |
| POST | `/api/workspaces` | Create workspace |
| GET | `/api/workspaces/{workspaceId}/dashboard` | Aggregated workspace dashboard |

## Core document ingestion and processing

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/workspaces/{workspaceId}/documents` | Original PDF/DOCX upload flow |
| GET | `/api/documents/{documentId}` | Document and processing metadata |
| DELETE | `/api/documents/{documentId}` | Soft-delete document |
| GET | `/api/documents/{documentId}/status` | Processing progress |
| GET | `/api/documents/{documentId}/pages` | Extracted pages |
| GET | `/api/documents/{documentId}/pages/{pageIndex}` | Page, blocks and OCR data |
| GET | `/api/documents/{documentId}/sections` | Original structured section tree |
| GET | `/api/documents/{documentId}/chunks` | Paginated chunks |
| GET | `/api/documents/{documentId}/chunks/{chunkId}` | Chunk detail |
| POST | `/api/documents/{documentId}/reprocess` | Retry document processing |
| GET | `/api/documents/{documentId}/viewer-data` | Frontend viewer aggregation |

## Regulatory document intelligence

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/documents` | Upload file with regulatory metadata and create immutable version |
| GET | `/api/documents` | List regulatory documents; filter by `workspaceId` |
| GET | `/api/documents/{documentId}/regulatory-profile` | Extracted regulatory metadata |
| GET | `/api/documents/{documentId}/summary` | Evidence-backed summary/current values |
| GET | `/api/documents/{documentId}/structured-sections` | Chapter/article/clause hierarchy |
| GET | `/api/documents/{documentId}/versions` | All versions in the family |
| GET | `/api/documents/{documentId}/timeline` | Values through time |
| GET | `/api/documents/{documentId}/changes` | Typed semantic changes |
| GET | `/api/documents/{documentId}/legal-relations` | Extracted legal citations and verification state |
| POST | `/api/documents/{documentId}/analyze` | Run version diff, impact mapping and verification |
| GET | `/api/documents/{documentId}/analysis-overview` | Frontend analysis aggregation |

`POST /api/documents` uses `multipart/form-data`:

```text
file: PDF or DOCX
metadata: JSON string
```

Example metadata:

```json
{
  "workspaceId": "workspace-id",
  "familyKey": "quy-dinh-tham-dinh-ngan-sach",
  "title": "Quy định thẩm định ngân sách",
  "documentNumber": "01/2026/QD-UBND",
  "documentType": "QUYET_DINH",
  "issuingAgency": "UBND tỉnh",
  "issuedDate": "2026-01-10",
  "effectiveDate": "2026-02-01",
  "domain": "Quản lý đầu tư",
  "applicableSubjects": ["Dự án sử dụng ngân sách tỉnh"]
}
```

## Project and impact intelligence

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/projects` | Create project knowledge record |
| GET | `/api/projects` | List projects; filter by `workspaceId` |
| GET | `/api/projects/{projectId}` | Project detail |
| GET | `/api/projects/{projectId}/impacts` | Project impact history |
| GET | `/api/impacts` | All detected impacts |
| GET | `/api/impacts/{impactId}` | Impact, actions and two-sided evidence |
| PATCH | `/api/impacts/{impactId}/review` | Accept/reject/request human review |
| GET | `/api/departments/{departmentName}/impacts` | Department-specific impacts/actions |

Impact review body:

```json
{
  "status": "ACCEPTED",
  "reviewedBy": "legal-expert-001",
  "note": "Đã kiểm tra bằng chứng"
}
```

## Persistent agent execution

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/agent-runs/{runId}` | Run, eight tasks, outputs and verification |
| POST | `/api/agent-runs/{runId}/retry` | Create a new audited attempt |
| GET | `/api/workflows/{workflowId}` | Existing AI orchestration workflow |

## User context onboarding

These endpoints require `X-User-ID`, populated by the authentication gateway in the MVP.

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/users/me/context` | Read persistent role/department/project context |
| PUT | `/api/users/me/context` | Create or update onboarding context |

```json
{
  "position": "Trưởng phòng Hành chính",
  "department": "Văn phòng UBND huyện",
  "organization": "UBND huyện",
  "province": "Điện Biên",
  "district": "Mường Nhé",
  "responsibilities": ["tổng hợp báo cáo", "chuẩn bị nội dung họp"],
  "assignedProjects": ["project-001", "project-014"]
}
```

## AI summary, knowledge graph and risk analysis

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/documents/{documentId}/analysis` | Existing full AI analysis workflow |
| POST | `/api/documents/{documentId}/summaries/generate` | Generate cited summary |
| GET | `/api/documents/{documentId}/summaries` | Summary history |
| GET | `/api/summaries/{summaryId}` | Summary detail |
| POST | `/api/documents/{documentId}/knowledge-graph/generate` | Generate graph |
| GET | `/api/documents/{documentId}/knowledge-graph` | Current graph |
| GET | `/api/documents/{documentId}/red-flags` | Verified red flags |
| POST | `/api/documents/{documentId}/critical-questions/generate` | Generate critical questions |
| GET | `/api/documents/{documentId}/critical-questions` | Critical questions |

The implementation uses snake-case path parameter names internally for these older routes, but the
actual URL accepts the same document ID value shown above.

## Index and hybrid retrieval

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/documents/{documentId}/index` | Build embedding index |
| GET | `/api/documents/{documentId}/index/status` | Index progress |
| POST | `/api/documents/{documentId}/index/rebuild` | Rebuild index |
| POST | `/api/retrieval/search` | Hybrid semantic/keyword search with metadata filters |

## Chat Q&A

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/workspaces/{workspaceId}/chat/sessions` | Create session |
| GET | `/api/chat/sessions/{sessionId}` | Session detail |
| DELETE | `/api/chat/sessions/{sessionId}` | Delete session |
| GET | `/api/chat/sessions/{sessionId}/messages` | Message history |
| POST | `/api/chat/sessions/{sessionId}/messages` | Evidence-backed Q&A |
| POST | `/api/chat/sessions/{sessionId}/messages/stream` | Server-sent event response |

## Meeting audio

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/meeting-sessions` | Create meeting session |
| POST | `/api/meeting-sessions/{sessionId}/audio` | Upload audio |
| GET | `/api/meeting-sessions/{sessionId}/transcript` | Structured transcript |

The running OpenAPI document is the source of truth and currently exposes **60 operations**.
