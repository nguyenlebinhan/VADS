# VADS / Regulatory Change Intelligence — Consolidated API Catalog

Base URL: `http://localhost:8000`

Interactive specification:

- Swagger UI: `GET /api/docs`
- ReDoc: `GET /api/redoc`
- OpenAPI JSON: `GET /api/openapi.json`

## Secure API (enabled by default)

The frontend uses the tenant-scoped `/api/v1` API. These endpoints return their response models
directly and use bearer access tokens plus rotating refresh tokens.

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/auth/login` | Sign in with username or email |
| POST | `/api/v1/auth/refresh` | Rotate a refresh token and issue a new token pair |
| POST | `/api/v1/auth/logout` | Revoke the current session |
| POST | `/api/v1/auth/logout-all` | Revoke all sessions for the current user |
| POST | `/api/v1/auth/change-password` | Change password and revoke existing sessions |
| GET | `/api/v1/auth/me` | Read the current user profile |
| POST | `/api/v1/admin/users` | Create a commune-scoped user |
| GET | `/api/v1/admin/users` | List visible users |
| GET | `/api/v1/admin/users/{user_id}` | Read a visible user |
| PATCH | `/api/v1/admin/users/{user_id}/lock` | Lock a user |
| PATCH | `/api/v1/admin/users/{user_id}/unlock` | Unlock a user |
| POST | `/api/v1/admin/users/{user_id}/reset-password` | Reset a user's password |
| GET | `/api/v1/staff-directory` | List active staff visible to the caller |
| GET | `/api/v1/documents` | List documents visible to the caller |
| GET | `/api/v1/documents/{document_id}` | Read a visible document |
| DELETE | `/api/v1/documents/{document_id}` | Soft-delete an owned document |
| POST | `/api/v1/documents/{document_id}/restore` | Restore a commune document (admin) |
| GET | `/api/v1/admin/audit-logs` | List commune audit records (admin) |
| GET | `/api/v1/admin/audit-logs/{audit_log_id}` | Read an audit record (admin) |

## Legacy compatibility API (disabled by default)

Set `VADS_LEGACY_API_ENABLED=true` only for tests or migration. Legacy JSON responses use the
shared envelope:

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

## Regulatory document intelligence

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/documents` | Upload file with regulatory metadata and create immutable version |
| GET | `/api/documents` | List regulatory documents; filter by `workspaceId` |
| GET | `/api/documents/{documentId}/regulatory-profile` | Extracted regulatory metadata |
| GET | `/api/documents/{documentId}/summary` | Evidence-backed summary/current values |
| GET | `/api/documents/{documentId}/versions` | All versions in the family |
| GET | `/api/documents/{documentId}/timeline` | Values through time |
| GET | `/api/documents/{documentId}/changes` | Typed semantic changes |
| GET | `/api/documents/{documentId}/legal-relations` | Extracted legal citations and verification state |
| POST | `/api/documents/{documentId}/analyze` | Run version diff, impact mapping and verification |

Structured content uses the canonical `GET /api/documents/{documentId}/sections` endpoint.

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
| GET | `/api/impacts` | Detected impacts; filter by `projectId` and/or `department` |
| GET | `/api/impacts/{impactId}` | Impact, actions and two-sided evidence |
| PATCH | `/api/impacts/{impactId}/review` | Accept/reject/request human review |

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
| POST | `/api/documents/{documentId}/index` | Build embedding index; use `?rebuild=true` to replace it |
| GET | `/api/documents/{documentId}/index/status` | Index progress |
| POST | `/api/retrieval/search` | Hybrid semantic/keyword search with metadata filters |

## Chat Q&A

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/workspaces/{workspaceId}/chat/sessions` | Create session |
| GET | `/api/chat/sessions/{sessionId}` | Session detail |
| DELETE | `/api/chat/sessions/{sessionId}` | Delete session |
| GET | `/api/chat/sessions/{sessionId}/messages` | Message history |
| POST | `/api/chat/sessions/{sessionId}/messages` | Evidence-backed Q&A; set `stream=true` or `Accept: text/event-stream` for SSE |

## Removed overlapping routes

| Removed path | Canonical replacement |
|---|---|
| `/api/workspaces/{workspaceId}/dashboard` | Query the underlying document/project resources |
| `/api/documents/{documentId}/viewer-data` | `/pages`, `/sections`, and `/chunks` |
| `/api/documents/{documentId}/analysis-overview` | Summary, graph, red-flag, and critical-question resources |
| `/api/documents/{documentId}/structured-sections` | `/api/documents/{documentId}/sections` |
| `/api/documents/{documentId}/index/rebuild` | `POST /api/documents/{documentId}/index?rebuild=true` |
| `/api/chat/sessions/{sessionId}/messages/stream` | `POST /api/chat/sessions/{sessionId}/messages` with streaming enabled |
| `/api/projects/{projectId}/impacts` | `GET /api/impacts?projectId=...` |
| `/api/departments/{departmentName}/impacts` | `GET /api/impacts?department=...` |
| `/api/meeting-sessions...` | Removed from the current product API |

With the default configuration, OpenAPI exposes **20 operations**: health plus 19 secure v1
operations. Compatibility mode exposes **68 operations** in total; the consolidated legacy
catalog contributes 49 operations including the shared health endpoint.
