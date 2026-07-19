<div align='center'>

# ⚖️ VADS

### Vietnamese Administrative Document System

**Biến văn bản hành chính thành quyết định có căn cứ, có người chịu trách nhiệm và có thể kiểm chứng.**

*Evidence-first AI for Vietnamese administrative and regulatory documents.*

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688?logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-pgvector-4169E1?logo=postgresql&logoColor=white)
![React](https://img.shields.io/badge/React-TypeScript-61DAFB?logo=react&logoColor=111827)
![Test cases](https://img.shields.io/badge/automated_test_cases-110-7C3AED)
![API operations](https://img.shields.io/badge/API_operations-68-0F766E)

[Mã nguồn tích hợp](https://github.com/nguyenlebinhan/VADS) ·
[Backend](https://github.com/nguyenlebinhan/VADS/tree/SU) ·
[Frontend](https://github.com/nguyenlebinhan/VADS/tree/SU/frontend) ·
[Figma Prototype](https://www.figma.com/design/b7Egr7gD623CWdrn6JdVpK/VADS---Prototype) ·
[API Catalog](https://github.com/nguyenlebinhan/VADS/blob/main/docs/api-catalog.md)

</div>

---

## 📋 Mục Lục

1. [🔍 Tổng Quan Dự Án](#1--tổng-quan-dự-án)
2. [🛠️ Tech Stack](#2-️-tech-stack)
3. [🏗️ Kiến Trúc Hệ Thống](#3-️-kiến-trúc-hệ-thống)
4. [📦 Yêu Cầu Cài Đặt](#4--yêu-cầu-cài-đặt)
5. [🗄️ Cài Đặt Database](#5-️-cài-đặt-database)
6. [🚀 Hướng Dẫn Chạy Dự Án](#6--hướng-dẫn-chạy-dự-án)
7. [📁 Cấu Trúc Thư Mục](#7--cấu-trúc-thư-mục)
8. [🗃️ Database Schema](#8-️-database-schema)
9. [✨ Tính Năng Hệ Thống](#9--tính-năng-hệ-thống)
10. [🔗 URL Routes & APIs](#10--url-routes--apis)
11. [🔐 Xác Thực & Phân Quyền](#11--xác-thực--phân-quyền)
12. [🧠 Quy Trình AI & Phân Tích](#12--quy-trình-ai--phân-tích)
13. [👨‍💼 Admin Panel](#13--admin-panel)
14. [📧 Hệ Thống Xử Lý Tài Liệu](#14--hệ-thống-xử-lý-tài-liệu)
15. [🎨 Giao Diện Frontend](#15--giao-diện-frontend)
16. [⚙️ Cấu Hình Hệ Thống](#16-️-cấu-hình-hệ-thống)
17. [👥 Thành Viên Nhóm](#17--thành-viên-nhóm)

---

## 1. 🔍 Tổng Quan Dự Án

VADS là nền tảng full-stack xử lý tài liệu hành chính tiếng Việt theo hướng **evidence-first**. Hệ thống giúp cán bộ hành chính đối chiếu nhiều phiên bản văn bản pháp lý, xác định điều khoản nào thay đổi, thay đổi đó tác động đến đề án nào, đơn vị nào phải xử lý và căn cứ nằm chính xác ở đâu trong tài liệu gốc.

Dự án tuân theo mô hình **Modular Monolith** — một codebase để phát triển nhanh trong MVP, nhưng ranh giới module và provider đủ rõ để tách worker/service khi tải tăng.

> **VADS trả lời bốn câu hỏi nghiệp vụ:** Văn bản mới thay đổi gì? Tác động đến công việc nào? Ai cần hành động? Bằng chứng nằm ở đâu?

### Vai trò người dùng

| Vai trò | Chức năng |
|---|---|
| 👤 User (Người dùng) | Tải lên tài liệu PDF/DOCX, xem phân tích AI (tóm tắt, knowledge graph, red flags), truy vấn RAG chatbot, xem tác động pháp lý, so sánh phiên bản văn bản |
| 🔑 Admin (Quản trị viên) | Quản lý tài khoản người dùng (tạo/khoá/mở khoá/reset mật khẩu), xem audit log append-only, quản trị tenant (xã/phường), dashboard thống kê hệ thống |

### Những con số có thể kiểm chứng trong repository

| Bằng chứng | Giá trị | Ý nghĩa |
|---|---:|---|
| Agent trong luồng Regulatory Change | **8** | Tách intake, versioning, semantic diff, legal research, graph, impact, advisor và verification |
| Test case tự động trên `main` | **110** | Bao phủ pipeline, AI, security, retrieval, chat và vertical slice |
| API operation khi bật đầy đủ compatibility mode | **68** | Từ ingestion đến impact review, Q&A và quản trị |
| API operation an toàn bật mặc định | **20** | Health check và 19 operation tenant-scoped `/api/v1` |
| Chế độ tài liệu PDF | **3** | `TEXT_BASED`, `SCANNED`, `HYBRID` để chỉ OCR khi cần |
| Thời hạn access token | **10 phút** | Giảm cửa sổ rủi ro; refresh token được rotate theo từng lần dùng |
| Database migration | **6** | 6 file Alembic migration quản lý schema tiến hoá |

---

## 2. 🛠️ Tech Stack

### ☕ Backend

| Công nghệ | Phiên bản | Mục đích |
|---|---|---|
| Python | 3.12+ | Ngôn ngữ lập trình chính |
| FastAPI | 0.115+ | Framework API RESTful async tốc độ cao |
| Pydantic | v2.10+ | Validation dữ liệu, structured output, API contracts |
| SQLAlchemy | 2.0.40+ | ORM — truy cập database theo repository pattern |
| Alembic | 1.14+ | Versioned database migration |
| Celery + Redis | 5.4+ / 7 | Hàng đợi tác vụ nền (OCR, AI pipeline) |
| PyMuPDF | 1.24+ | Trích xuất text layer và render trang PDF |
| python-docx | 1.1+ | Xử lý tài liệu DOCX |
| PaddleOCR | 3.3.0 | OCR tiếng Việt cho tài liệu scan |
| Argon2-cffi | 23.1+ | Hash mật khẩu chuẩn bảo mật (Argon2id) |
| PyJWT | 2.10+ | Tạo và xác minh JWT access/refresh token |
| Boto3 | 1.39+ | Tương tác S3-compatible object storage (MinIO) |
| Uvicorn | 0.30+ | ASGI server chạy FastAPI |

### 🌐 Frontend

| Công nghệ | Phiên bản | Mục đích |
|---|---|---|
| React | 18+ | Thư viện UI xây dựng Single Page Application |
| TypeScript | — | Kiểu tĩnh cho JavaScript, tăng tính an toàn |
| Vite | — | Build tool nhanh, HMR tức thì cho development |
| Tailwind CSS | v4+ | Utility-first CSS framework |
| MUI (Material UI) | — | Component library cho bảng, dialog, form |
| Radix UI | — | Headless component primitives (accessible) |
| Recharts | — | Biểu đồ và chart cho dashboard |
| Inter (Google Fonts) | — | Font chữ chính cho giao diện |

### 🗄️ Database & Storage

| Công nghệ | Chi tiết |
|---|---|
| PostgreSQL 16 + pgvector | Database quan hệ chính, lưu trữ metadata, vector embedding, audit log |
| Redis 7 (Alpine) | Message broker cho Celery, cache, result backend |
| MinIO / S3 | Object storage lưu file PDF/DOCX gốc (binary bất biến) |

### 🔧 Công Cụ Phát Triển

| Công cụ | Mục đích |
|---|---|
| Docker & Docker Compose | Containerization — chạy toàn bộ stack local bằng 1 lệnh |
| Pytest 8.3+ | Framework test tự động cho backend |
| HTTPX | HTTP client async cho integration test |
| Ruff | Linter + formatter Python tốc độ cao |
| Postman | Bộ collection sẵn sàng để test API flow |
| Caddy | Reverse proxy, tự động HTTPS khi deploy production |

---

## 3. 🏗️ Kiến Trúc Hệ Thống

```
┌─────────────────────────────────────────────────────────┐
│                     Client (Browser)                    │
│        React + TypeScript + Tailwind + MUI + Radix      │
└────────────────────────┬────────────────────────────────┘
                         │ REST API / SSE (Server-Sent Events)
┌────────────────────────▼────────────────────────────────┐
│          FastAPI Application (Uvicorn ASGI Server)      │
│                                                         │
│  ┌──────────────┐   ┌───────────────┐   ┌───────────┐   │
│  │   Security   │──▶│  Controllers  │──▶│   Views  │   │
│  │  JWT Verify  │   │  (Routers)    │   │ (Pydantic │   │
│  │  RBAC Check  │   │               │   │  Schemas) │   │
│  │  Tenant Gate │   └───────┬───────┘   └───────────┘   │
│  └──────────────┘           │                           │
│                    ┌────────▼────────┐                  │
│                    │    Services     │                  │
│                    │  (Business +    │                  │
│                    │  Orchestrator)  │                  │
│                    └────────┬────────┘                  │
│                             │                           │
│                    ┌────────▼────────┐                  │
│                    │  Repositories   │                  │
│                    │  (Data Access)  │                  │
│                    └────────┬────────┘                  │
└─────────────────────────────┼───────────────────────────┘
                              │ SQLAlchemy + Boto3
          ┌───────────────────┼───────────────────┐
┌─────────▼──────────┐ ┌─────▼──────────┐ ┌──────▼──────────┐
│     PostgreSQL     │ │     Redis      │ │   MinIO / S3    │
│  (pgvector, 5432)  │ │   (6379)       │ │  (9000 / 9001)  │
│  Relational data   │ │  Celery broker │ │  File storage   │
│  + Vector store    │ │  + result      │ │  (immutable)    │
└────────────────────┘ └────────────────┘ └─────────────────┘
```

### Mô hình MVC được áp dụng

Dự án tuân theo mô hình phân tách rõ ràng:

- **📦 Model** — `app/*/models.py` và `app/*/repository.py`: Định nghĩa ORM entities (SQLAlchemy) và các thao tác CRUD tenant-scoped lên database.
- **🖼️ View** — `app/*/schemas.py` và `frontend/src/`: Pydantic schemas định nghĩa request/response contracts; React components hiển thị dữ liệu.
- **🎮 Controller** — `app/*/router.py` và `app/*/service.py`: FastAPI routers tiếp nhận HTTP request, services điều phối business logic.

### Luồng dữ liệu tài liệu

```
Upload PDF/DOCX
  → validate extension + MIME + magic bytes + filename + size + SHA-256
  → lưu binary bất biến trên MinIO/S3
  → commit Document + DocumentFile + ProcessingJob vào PostgreSQL
  → Celery worker nhận job:
      → phân loại TEXT_BASED / SCANNED / HYBRID
      → trích text layer (PyMuPDF) hoặc OCR (PaddleOCR) đúng trang cần thiết
      → lưu page + block + table + bounding box
      → parse Chương / Điều / Khoản / Điểm (legal hierarchy)
      → tạo chunk kèm legal metadata và source anchor
      → embed chunk vào pgvector index
```

PostgreSQL là nguồn dữ liệu chuẩn; object storage chỉ giữ binary. Vì không có transaction ACID chung giữa hai hệ thống, upload dùng **compensating transaction**: nếu commit database thất bại, object vừa upload được xóa bù.

---

## 4. 📦 Yêu Cầu Cài Đặt

Trước khi chạy dự án, cần cài đặt đầy đủ các công cụ sau:

| Yêu cầu | Phiên bản | Link tải |
|---|---|---|
| 🐳 Docker Desktop / Docker Engine | Có Docker Compose | [Tải về](https://docs.docker.com/get-docker/) |
| 🔧 Git | Bất kỳ | [Tải về](https://git-scm.com/) |
| 🟢 Node.js + npm | 18+ | [Tải về](https://nodejs.org/) (chỉ cần nếu chạy frontend rời) |
| 🔑 FPT AI API Key | — | [FPT AI Marketplace](https://marketplace.fptcloud.com/) (tuỳ chọn, để gọi model thật) |
| 🤖 OpenAI API Key | — | [OpenAI](https://platform.openai.com/) (tuỳ chọn, cho DOCX RAG) |

> 💡 **Lưu ý:** Toàn bộ backend, database, Redis và MinIO đều chạy qua Docker Compose — **không cần cài đặt riêng** Python, PostgreSQL hay Redis trên máy host.

---

## 5. 🗄️ Cài Đặt Database

### Hệ thống tự động hoá hoàn toàn

Không cần tạo database thủ công. Khi chạy `docker compose up`, hệ thống sẽ tự động:

1. **Khởi tạo PostgreSQL container** với image `pgvector/pgvector:pg16`, bật extension `pgvector` cho vector search.
2. **Chạy Alembic migrations** — 6 file migration tự tạo toàn bộ schema:

| Migration | Mục đích |
|---|---|
| `20260717_0001_document_core.py` | Bảng Document, DocumentFile, Workspace cốt lõi |
| `20260717_0002_document_pipeline.py` | Bảng Page, Block, Section, Chunk cho pipeline xử lý |
| `20260718_0003_ai_orchestration.py` | Bảng Workflow, Summary, KnowledgeGraph, RedFlag |
| `20260718_0004_product_api.py` | API tổng hợp, retrieval index, chat session |
| `20260718_0005_regulatory_change_vertical_slice.py` | Bảng Version, Change, Impact, AgentRun, AgentTask |
| `20260718_0006_auth_tenant_security.py` | Bảng User, AuthSession, AuditLog, Commune, Grant |

3. **Khởi tạo MinIO container** và tạo bucket `vads-documents` cho file storage.
4. **Khởi tạo Redis container** làm Celery broker và result backend.

### Thông tin kết nối mặc định

Mặc định trong `.env.example`, thông tin kết nối database là:

```
VADS_DATABASE_URL=postgresql+psycopg://vads:replace-with-a-strong-password@postgres:5432/vads
POSTGRES_DB=vads
POSTGRES_USER=vads
POSTGRES_PASSWORD=replace-with-a-strong-password
```

⚠️ **Trước khi deploy production**, hãy đổi toàn bộ mật khẩu mặc định trong file `.env`. Ứng dụng sẽ **từ chối khởi động** nếu phát hiện secret mặc định ở môi trường staging/production.

---

## 6. 🚀 Hướng Dẫn Chạy Dự Án

### Bước 1 — Clone repository

```bash
git clone https://github.com/nguyenlebinhan/VADS.git
cd VADS
```

### Bước 2 — Tạo file cấu hình môi trường

**Linux / macOS:**
```bash
cp .env.example .env
```

**PowerShell (Windows):**
```powershell
Copy-Item .env.example .env
```

### Bước 3 — Khởi động toàn bộ backend stack

```bash
docker compose up --build
```

Lệnh này sẽ build và khởi động **6 services**:

| Service | Mô tả | Port |
|---|---|---|
| `api` | FastAPI server (chạy Alembic migrate trước, rồi Uvicorn) | `8000` |
| `worker` | Celery worker xử lý OCR, AI pipeline (2 concurrency) | — |
| `beat` | Celery Beat scheduler cho periodic tasks | — |
| `postgres` | PostgreSQL 16 + pgvector | `5432` |
| `redis` | Redis 7 Alpine (message broker) | `6379` |
| `minio` | MinIO S3-compatible object storage | `9000` (API) / `9001` (Console) |

### Bước 4 — Tạo tài khoản demo

```bash
python -m app.seed_demo_accounts
```

| Vai trò | Tài khoản | Mật khẩu |
|---|---|---|
| 🔑 ADMIN | `admin.demo` | `VadsAdmin@2026` |
| 👤 USER | `user.demo` | `VadsUser@2026!` |

> Có thể đổi thông tin đăng nhập qua các biến `VADS_DEMO_ADMIN_*` và `VADS_DEMO_USER_*` trước khi chạy lệnh seed.

### Bước 5 — Chạy Frontend (local development)

```bash
cd frontend
npm ci
npm run dev
```

### 🌐 Truy cập ứng dụng

Mở trình duyệt và truy cập:

| Dịch vụ | URL |
|---|---|
| 🖥️ Frontend (React) | `http://localhost:5173` |
| 📘 Swagger UI (API Docs) | `http://localhost:8000/api/docs` |
| 📗 ReDoc (API Docs) | `http://localhost:8000/api/redoc` |
| 📄 OpenAPI JSON | `http://localhost:8000/api/openapi.json` |
| ❤️ Health Check | `http://localhost:8000/health/live` |
| 📦 MinIO Console | `http://localhost:9001` |

### Bước 6 (Tuỳ chọn) — Chạy demo Regulatory Change

```bash
python scripts/generate_regulatory_demo_documents.py
```

Sau đó import Postman collections:

- [VADS Postman collection](https://github.com/nguyenlebinhan/VADS/blob/main/docs/postman/VADS.postman_collection.json)
- [Regulatory Change collection](https://github.com/nguyenlebinhan/VADS/blob/main/docs/postman/Regulatory-Change-Vertical-Slice.postman_collection.json)
- [VADS Local environment](https://github.com/nguyenlebinhan/VADS/blob/main/docs/postman/VADS.postman_environment.json)

Collection tự lưu các ID quan trọng từ response để có thể chạy tuần tự toàn bộ flow.

---

## 7. 📁 Cấu Trúc Thư Mục

```
VADS/
│
├── app/                               # Toàn bộ source code Python backend
│   ├── api/v1/                        # API bảo mật, tenant-scoped (bật mặc định)
│   │   ├── router.py                  # Đăng ký toàn bộ v1 routes vào FastAPI
│   │   ├── auth.py                    # Login, refresh, logout, change-password, me
│   │   ├── admin_users.py             # CRUD tài khoản (Admin only)
│   │   ├── documents.py               # Upload, list, delete, restore tài liệu
│   │   ├── knowledge_graph.py         # Knowledge graph endpoint
│   │   ├── rag.py                     # RAG query endpoint
│   │   ├── regulatory.py              # Regulatory change analysis endpoints
│   │   ├── audit_logs.py              # Audit log viewer (Admin only)
│   │   └── staff_directory.py         # Danh bạ nhân viên
│   │
│   ├── documents/                     # Logic tải lên và quản lý vòng đời tài liệu
│   │   └── router.py                  # Legacy upload, status, pages, sections, chunks
│   │
│   ├── extraction/                    # Trích xuất nội dung từ PDF/DOCX
│   │                                  # Xử lý text layer (PyMuPDF), OCR (PaddleOCR)
│   │                                  # Lưu bounding box cho từng block/table
│   │
│   ├── structure/                     # Parser cấu trúc pháp lý Chương/Điều/Khoản/Điểm
│   │
│   ├── chunking/                      # Chia nhỏ văn bản thành chunk
│   │                                  # Giữ legal metadata và source anchor
│   │                                  # Min 300 / Max 800 / Overlap 75 tokens
│   │
│   ├── orchestrator/                  # AI orchestrator tổng quát
│   │                                  # Model routing theo tác vụ (ModelRegistry)
│   │                                  # DAG execution, retry, fallback, audit
│   │
│   ├── summaries/                     # Cited, versioned summaries có publication gate
│   │
│   ├── knowledge_graph/               # Entity/relation extraction + citation validation
│   │
│   ├── red_flags/                     # Rule engine + reasoning verification
│   │
│   ├── citations/                     # CitationValidator — kiểm tra trích dẫn AI
│   │                                  # Đối chiếu document, chunk, quote, page, bbox
│   │
│   ├── regulatory_change/            # 8-agent Regulatory Change Intelligence
│   │   ├── intake.py                  # PDF/DOCX text extraction, legal hierarchy
│   │   ├── diff.py                    # Typed semantic diff (VALUE, RESPONSIBILITY, UNCHANGED)
│   │   ├── impact.py                  # Multi-signal project impact scoring
│   │   ├── orchestrator.py            # Persistent 8-agent execution + verification
│   │   ├── agents.py                  # Định nghĩa 8 agent contracts
│   │   ├── models.py                  # SQLAlchemy ORM entities
│   │   ├── repository.py             # Data access layer
│   │   ├── service.py                 # Transactions, DTO mapping, use cases
│   │   ├── schemas.py                 # Pydantic API contracts
│   │   └── router.py                  # FastAPI endpoints
│   │
│   ├── vector_store/                  # pgvector index — embedding store
│   ├── retrieval/                     # Hybrid semantic/keyword search + reranking
│   ├── reranking/                     # Reranker provider abstraction
│   ├── chat/                          # Evidence-backed Q&A + SSE streaming
│   ├── streaming/                     # Server-Sent Events infrastructure
│   │
│   ├── model_gateway/                 # Provider-neutral AI gateway
│   │                                  # FPT AI Marketplace adapter (HTTPS)
│   │                                  # Không phụ thuộc SDK nhà cung cấp
│   ├── model_audit/                   # Audit mọi model execution
│   │
│   ├── users/                         # User entity, Argon2id password hashing
│   ├── policies/                      # RBAC + ABAC resource policies
│   ├── user_context/                  # Onboarding context (chức vụ, phòng ban, dự án)
│   │
│   ├── database/                      # Database engine, session factory
│   ├── config/                        # Pydantic Settings, Celery app config
│   ├── common/                        # Shared utilities
│   ├── exceptions/                    # Exception handlers
│   ├── dependencies/                  # FastAPI dependency injection
│   ├── repositories/                  # Base repository pattern
│   ├── storage/                       # Storage provider abstraction (MinIO/S3)
│   │
│   ├── main.py                        # FastAPI application factory
│   ├── seed_demo_accounts.py          # Script tạo tài khoản demo (idempotent)
│   │
│   └── tests/                         # Toàn bộ automated tests
│       ├── test_ai_orchestration.py           # AI pipeline, DAG, retry/fallback
│       ├── test_documents_api.py              # Document upload, lifecycle
│       ├── test_pipeline_integration.py       # End-to-end pipeline
│       ├── test_pdf_ocr.py                    # PDF classification, OCR
│       ├── test_structure_chunking.py         # Legal parsing, chunking
│       ├── test_fpt_ai_gateway.py             # Model gateway, routing
│       ├── test_regulatory_change_vertical_slice.py  # 8-agent full flow
│       ├── test_secure_regulatory_api.py      # Secure API regulatory endpoints
│       ├── test_failure_and_reprocess.py       # Error recovery, reprocess
│       ├── test_docx_rag.py                   # DOCX RAG pipeline
│       ├── test_api_catalog.py                # API catalog validation
│       ├── test_workspaces_api.py             # Workspace CRUD
│       ├── test_user_context_api.py           # User context onboarding
│       ├── test_database_rag_service.py       # RAG service integration
│       ├── test_processing_service.py         # Processing pipeline
│       ├── test_frontend_static.py            # Frontend static files
│       └── security/                          # Security test suite
│           ├── test_auth_api.py               # Login, refresh, logout, lockout
│           ├── test_authorization_api.py      # Cross-tenant IDOR, permission
│           ├── test_document_policy.py        # Document state policy
│           └── test_security_settings.py      # Security configuration
│
├── frontend/                          # Frontend React / TypeScript
│   └── src/
│       ├── main.tsx                   # React entry point
│       ├── api.ts                     # API client (Axios/Fetch) — gọi backend
│       ├── password.ts                # Password validation utilities
│       ├── app/
│       │   ├── App.tsx                # Root component, routing, auth guard
│       │   ├── AdminPortal.tsx        # Admin dashboard — quản lý user, audit log
│       │   ├── UserPortal.tsx         # User portal — document management, chat
│       │   ├── KnowledgeGraphScreen.tsx  # Visualisation biểu đồ tri thức
│       │   ├── RegulatoryIntelligence.tsx # So sánh phiên bản, tác động
│       │   └── components/            # Shared UI components
│       │       ├── ui/                # Shadcn/Radix primitive components
│       │       └── figma/             # Components từ Figma design system
│       ├── lib/                       # Utility functions
│       └── styles/
│           ├── theme.css              # Design tokens (colors, spacing, radius)
│           ├── globals.css            # Global styles
│           ├── fonts.css              # Font imports (Inter)
│           ├── tailwind.css           # Tailwind directives
│           └── index.css              # Style entry point
│
├── alembic/                           # Versioned database migrations
│   ├── env.py                         # Alembic environment config
│   └── versions/                      # 6 migration files (ordered)
│
├── docs/                              # Tài liệu dự án
│   ├── api-catalog.md                 # Danh mục 68 API operation
│   ├── architecture.md                # Kiến trúc tổng quan
│   ├── authentication-authorization.md # Thiết kế bảo mật chi tiết
│   ├── regulatory-change-architecture.md # Kiến trúc 8-agent
│   ├── requirements-document.md       # Tài liệu yêu cầu
│   ├── deploy-azure-vm.md             # Hướng dẫn deploy Azure VM
│   ├── deploy-railway.md              # Hướng dẫn deploy Railway
│   └── postman/                       # Postman collections & environment
│       ├── VADS.postman_collection.json
│       ├── Regulatory-Change-Vertical-Slice.postman_collection.json
│       └── VADS.postman_environment.json
│
├── scripts/                           # Script tiện ích
│   ├── generate_regulatory_demo_documents.py  # Tạo tài liệu demo
│   └── test_docx_rag.py               # Test DOCX RAG riêng
│
├── docker-compose.yml                 # Cấu hình 6 services cho local
├── docker-compose.azure.yml           # Cấu hình cho Azure VM
├── Dockerfile                         # Multi-stage build cho backend
├── Caddyfile                          # Reverse proxy config
├── railway.json                       # Railway deployment config
├── pyproject.toml                     # Python dependencies & tool config
├── alembic.ini                        # Alembic configuration
├── .env.example                       # Template biến môi trường (92 biến)
└── README.md                          # Tài liệu này
```

---

## 8. 🗃️ Database Schema

### Sơ đồ quan hệ giữa các module chính

```
Commune (1) ────── (N) User ────── (N) AuthSession
                        │                    │
                        │               AuditLog (append-only)
                        │
              Document (1) ────── (1) DocumentFile (MinIO ref)
                   │
                   ├── (N) Page ────── (N) Block (bounding box)
                   ├── (N) Section (Chương/Điều/Khoản)
                   ├── (N) Chunk (vector embedding)
                   │
                   └── (1) RegulatoryDocumentVersion
                              │
                              ├── (N) RegulatoryChange (VALUE, RESPONSIBILITY, UNCHANGED)
                              └── (N) RegulatoryImpact ────── (N) DepartmentAction
                                         │
                              RegulatoryAgentRun (1) ── (8) AgentTask ── (1) AgentOutput
                                                   └── (1) VerificationResult
```

### Chi tiết các nhóm bảng chính

#### 👤 User & Authentication

| Cột | Kiểu dữ liệu | Mô tả |
|---|---|---|
| id | UUID | PK, tự sinh |
| username | VARCHAR | Unique toàn hệ thống, case-insensitive |
| email | VARCHAR | Unique toàn hệ thống |
| password_hash | VARCHAR | Hash Argon2id — **không lưu plain-text** |
| role | ENUM | `ADMIN` hoặc `USER` |
| commune_id | UUID | FK → Commune — tenant scope |
| is_active | BOOLEAN | Trạng thái tài khoản |
| is_locked | BOOLEAN | Bị khoá do login quá giới hạn |
| failed_login_count | INT | Đếm số lần đăng nhập sai |
| token_version | INT | Tăng khi password/role đổi → revoke tất cả JWT cũ |
| must_change_password | BOOLEAN | Bắt buộc đổi mật khẩu lần đăng nhập kế tiếp |

#### 📋 AuthSession (Refresh Token)

| Cột | Kiểu dữ liệu | Mô tả |
|---|---|---|
| id | UUID | PK |
| user_id | UUID | FK → User |
| token_hash | VARCHAR | HMAC-SHA-256 hash của refresh token (có pepper) |
| previous_token_hash | VARCHAR | Token trước đó (detect replay attack) |
| expires_at | DATETIME | Hết hạn sau 30 ngày |
| revoked_at | DATETIME | NULL nếu chưa revoke |

#### 📄 Document & DocumentFile

| Cột | Kiểu dữ liệu | Mô tả |
|---|---|---|
| id | UUID | PK |
| workspace_id | UUID | FK → Workspace |
| commune_id | UUID | Tenant scope |
| owner_id | UUID | FK → User (người upload) |
| original_filename | VARCHAR | Tên file gốc |
| file_extension | VARCHAR | `.pdf` hoặc `.docx` |
| sha256_checksum | VARCHAR(64) | Chống upload trùng lặp |
| processing_status | ENUM | `UPLOADED` / `PROCESSING` / `COMPLETED` / `FAILED` |
| document_type | ENUM | `TEXT_BASED` / `SCANNED` / `HYBRID` |
| is_deleted | BOOLEAN | Soft-delete |
| storage_key | VARCHAR | Key trên MinIO/S3 |

#### ⚖️ Regulatory Change Intelligence

| Bảng | Mô tả |
|---|---|
| `regulatory_document_families` | Nhóm các phiên bản của cùng một văn bản |
| `regulatory_document_versions` | Phiên bản bất biến (immutable) — không bao giờ ghi đè |
| `regulatory_sections` | Cấu trúc Chương / Điều / Khoản / Điểm |
| `regulatory_changes` | Thay đổi có kiểu: `VALUE_CHANGED`, `RESPONSIBILITY_CHANGED`, `UNCHANGED` |
| `regulatory_projects` | Dự án/đề án có thể bị tác động |
| `regulatory_impacts` | Tác động với evidence hai phía (văn bản + dự án) |
| `regulatory_agent_runs` | Mỗi lần phân tích = 1 run, không ghi đè run cũ |
| `regulatory_agent_tasks` | 8 task trong mỗi run |
| `regulatory_agent_outputs` | Output của từng task |
| `regulatory_verification_results` | Kết quả kiểm tra chéo của VerificationAgent |

> 💡 **Lưu ý thiết kế:** Mọi kết quả phân tích AI đều được persist dưới dạng immutable. Retry tạo `AgentRun` mới; run cũ không bị ghi đè để phục vụ audit và tái lập kết quả.

---

## 9. ✨ Tính Năng Hệ Thống

### 9.1 Chức Năng Dành Cho Người Dùng

#### 📄 Quản Lý Tài Liệu

- **Upload tài liệu** — Tải lên PDF hoặc DOCX. Hệ thống tự động kiểm tra MIME type, magic bytes, extension, kích thước (tối đa 50 MB) và SHA-256 checksum chống trùng lặp.
- **Phân loại tự động** — Nhận diện tài liệu `TEXT_BASED`, `SCANNED` hay `HYBRID` để quyết định có cần OCR hay không.
- **OCR tiếng Việt** — PaddleOCR xử lý trang scan, giữ lại bounding box cho từng block/table.
- **Cấu trúc pháp lý** — Tự động parse theo **Chương → Điều → Khoản → Điểm** thay vì cắt văn bản tuỳ ý.
- **Xem trạng thái xử lý** — Theo dõi pipeline progress: `UPLOADED` → `PROCESSING` → `COMPLETED` / `FAILED`.
- **Xử lý lại** — Retry toàn bộ pipeline nếu xử lý lần đầu thất bại.
- **Soft-delete & Restore** — Xoá mềm tài liệu; Admin có thể khôi phục.

#### 🤖 Phân Tích AI

- **Tóm tắt có trích dẫn** — AI tạo bản tóm tắt, mỗi claim đều có citation với document ID, chunk ID, quote gốc, trang và vị trí bounding box.
- **Knowledge Graph** — Trích xuất entity và relation từ văn bản, tạo biểu đồ tri thức trực quan.
- **Red Flags** — Phát hiện rủi ro pháp lý, điểm cần lưu ý trong văn bản.
- **Critical Questions** — Tạo câu hỏi phản biện giúp cán bộ hiểu sâu nội dung văn bản.

#### 💬 RAG Chat (Hỏi-Đáp)

- **Truy vấn tự nhiên** — Đặt câu hỏi bằng tiếng Việt, AI trả lời dựa trên nội dung tài liệu thực.
- **Hybrid retrieval** — Kết hợp semantic search (pgvector) + keyword search + metadata filter.
- **Reranking** — Sắp xếp lại kết quả search để chọn chunk liên quan nhất.
- **SSE Streaming** — Câu trả lời được stream real-time qua Server-Sent Events.
- **Quản lý session** — Tạo, xem lịch sử, xoá các phiên hỏi đáp.

#### ⚖️ Regulatory Change Intelligence

- **So sánh phiên bản** — Upload 2 phiên bản của cùng văn bản, hệ thống tự phát hiện sự khác biệt.
- **Semantic Diff có kiểu** — Phân biệt rõ: `VALUE_CHANGED` (thay đổi giá trị), `RESPONSIBILITY_CHANGED` (thay đổi trách nhiệm), `UNCHANGED`.
- **Tác động dự án** — Ánh xạ thay đổi pháp lý đến dự án/đề án bị ảnh hưởng bằng multi-signal scoring.
- **Đề xuất hành động** — Chỉ ra phòng ban nào cần làm gì dựa trên thay đổi.
- **Expert review** — Chuyên gia có thể `ACCEPTED`, `REJECTED` hoặc yêu cầu `NEEDS_HUMAN_REVIEW`.

#### 👤 Tài Khoản Người Dùng

- **Đăng nhập** — Xác thực bằng username hoặc email + password. Tài khoản bị khoá sau 5 lần sai trong 15 phút.
- **Đổi mật khẩu** — Thay đổi mật khẩu trực tiếp, tự động revoke tất cả session cũ.
- **Đăng xuất** — Revoke session hiện tại hoặc toàn bộ session (`logout-all`).
- **Xem hồ sơ** — Endpoint `/api/v1/auth/me` trả thông tin user đang đăng nhập.

### 9.2 Chức Năng Admin

#### 👥 Quản Lý Tài Khoản (`/api/v1/admin/users`)

- Tạo tài khoản mới cho người dùng trong cùng tenant (xã/phường).
- Liệt kê toàn bộ tài khoản trong tenant dưới dạng danh sách có phân trang.
- Khoá (`lock`) / Mở khoá (`unlock`) tài khoản — không được tự khoá hoặc khoá Admin cuối cùng.
- Reset mật khẩu cho tài khoản bị quên — tự revoke session và bắt đổi password lần đăng nhập tiếp.

#### 📊 Audit Log (`/api/v1/admin/audit-logs`)

- Xem toàn bộ lịch sử thao tác trong tenant — mô hình **append-only**.
- Mỗi record chứa: action, actor, target resource, timestamp, metadata.
- Không thể sửa hoặc xoá audit log — có ORM guard và PostgreSQL trigger bảo vệ.

#### 📈 Dashboard

- Thống kê tổng quan: số tài liệu, số người dùng, số phiên phân tích.
- Giao diện React với biểu đồ Recharts.

---

## 10. 🔗 URL Routes & APIs

### 🌐 Secure API — Bật mặc định (20 operations)

#### 🔐 Authentication (`/api/v1/auth`)

| Method | URL | Mô tả |
|---|---|---|
| POST | `/api/v1/auth/login` | Đăng nhập bằng username hoặc email |
| POST | `/api/v1/auth/refresh` | Xoay refresh token và cấp cặp token mới |
| POST | `/api/v1/auth/logout` | Revoke session hiện tại |
| POST | `/api/v1/auth/logout-all` | Revoke toàn bộ session của user |
| POST | `/api/v1/auth/change-password` | Đổi mật khẩu, revoke session cũ |
| GET | `/api/v1/auth/me` | Đọc thông tin user đang đăng nhập |

#### 👥 Admin Users (`/api/v1/admin`)

| Method | URL | Mô tả |
|---|---|---|
| POST | `/api/v1/admin/users` | Tạo tài khoản trong tenant |
| GET | `/api/v1/admin/users` | Danh sách tài khoản trong tenant |
| GET | `/api/v1/admin/users/{user_id}` | Chi tiết một tài khoản |
| PATCH | `/api/v1/admin/users/{user_id}/lock` | Khoá tài khoản |
| PATCH | `/api/v1/admin/users/{user_id}/unlock` | Mở khoá tài khoản |
| POST | `/api/v1/admin/users/{user_id}/reset-password` | Reset mật khẩu |

#### 📄 Documents (`/api/v1/documents`)

| Method | URL | Mô tả |
|---|---|---|
| GET | `/api/v1/documents` | Danh sách tài liệu visible cho caller |
| GET | `/api/v1/documents/{document_id}` | Chi tiết một tài liệu |
| DELETE | `/api/v1/documents/{document_id}` | Soft-delete tài liệu (owner) |
| POST | `/api/v1/documents/{document_id}/restore` | Khôi phục tài liệu (Admin) |

#### 🔍 Khác

| Method | URL | Mô tả |
|---|---|---|
| GET | `/api/v1/staff-directory` | Danh bạ nhân viên trong tenant |
| GET | `/api/v1/admin/audit-logs` | Audit log trong tenant (Admin) |
| GET | `/api/v1/admin/audit-logs/{audit_log_id}` | Chi tiết một audit record |

### 🔧 Legacy Compatibility API — Tắt mặc định (49 operations bổ sung)

> ⚠️ Chỉ bật khi `VADS_LEGACY_API_ENABLED=true` ở local. **Không bật ở staging/production.**

#### 📦 Document Pipeline

| Method | URL | Mô tả |
|---|---|---|
| POST | `/api/workspaces/{id}/documents` | Upload PDF/DOCX qua legacy flow |
| GET | `/api/documents/{id}/status` | Trạng thái xử lý pipeline |
| GET | `/api/documents/{id}/pages` | Danh sách trang đã trích xuất |
| GET | `/api/documents/{id}/pages/{pageIndex}` | Trang + blocks + OCR data |
| GET | `/api/documents/{id}/sections` | Cây cấu trúc pháp lý |
| GET | `/api/documents/{id}/chunks` | Chunks phân trang |
| POST | `/api/documents/{id}/reprocess` | Retry pipeline |

#### 🧠 AI Analysis

| Method | URL | Mô tả |
|---|---|---|
| POST | `/api/documents/{id}/analysis` | Chạy full AI analysis workflow |
| POST | `/api/documents/{id}/summaries/generate` | Tạo cited summary |
| GET | `/api/documents/{id}/summaries` | Lịch sử summary |
| POST | `/api/documents/{id}/knowledge-graph/generate` | Tạo knowledge graph |
| GET | `/api/documents/{id}/knowledge-graph` | Graph hiện tại |
| GET | `/api/documents/{id}/red-flags` | Red flags đã verified |
| POST | `/api/documents/{id}/critical-questions/generate` | Tạo câu hỏi phản biện |

#### ⚖️ Regulatory Intelligence

| Method | URL | Mô tả |
|---|---|---|
| POST | `/api/documents` | Upload + metadata regulatory |
| GET | `/api/documents/{id}/versions` | Tất cả phiên bản |
| GET | `/api/documents/{id}/timeline` | Giá trị qua thời gian |
| GET | `/api/documents/{id}/changes` | Typed semantic changes |
| POST | `/api/documents/{id}/analyze` | Chạy version diff + impact mapping |
| POST | `/api/projects` | Tạo project knowledge record |
| GET | `/api/impacts` | Tác động (filter by project/department) |
| PATCH | `/api/impacts/{id}/review` | Accept/Reject/Human Review |
| GET | `/api/agent-runs/{id}` | Chi tiết 8 tasks + outputs + verification |
| POST | `/api/agent-runs/{id}/retry` | Retry tạo attempt mới |

#### 💬 Chat & Retrieval

| Method | URL | Mô tả |
|---|---|---|
| POST | `/api/documents/{id}/index` | Build embedding index |
| POST | `/api/retrieval/search` | Hybrid semantic/keyword search |
| POST | `/api/workspaces/{id}/chat/sessions` | Tạo chat session |
| POST | `/api/chat/sessions/{id}/messages` | Q&A có trích dẫn (hỗ trợ SSE) |

---

## 11. 🔐 Xác Thực & Phân Quyền

### Luồng Đăng Nhập

```
Người dùng submit POST /api/v1/auth/login
       │
       ▼
Verify Argon2id password hash
  → Kiểm tra user.is_active == true
  → Kiểm tra user.is_locked == false
  → Kiểm tra failed_login_count < 5 (trong 15 phút)
       │
       ├── ❌ Sai mật khẩu → Tăng failed_login_count
       │     → Đạt 5 lần → Khoá tài khoản 15 phút
       │     → Response không tiết lộ user có tồn tại không
       │
       └── ✅ Thành công → Tạo cặp token:
                       │
                       ├── 🔑 Access Token (JWT HS256)
                       │     → Hết hạn 10 phút
                       │     → Chứa: user_id, role, commune_id, token_version
                       │     → Claims: iss, aud, kid, type=access
                       │
                       └── 🔄 Refresh Token (Opaque 256-bit)
                             → Hết hạn 30 ngày
                             → Lưu HMAC-SHA-256 hash vào DB (có pepper riêng)
                             → Rotation: mỗi lần dùng sinh token mới, huỷ token cũ
```

### Cấu Trúc JWT Access Token

```json
{
  "sub": "user-uuid",
  "role": "ADMIN",
  "commune_id": "commune-uuid",
  "token_version": 3,
  "type": "access",
  "iss": "vads-api",
  "aud": "vads-client",
  "kid": "vads-hs256-v1",
  "exp": 1721376600,
  "iat": 1721376000
}
```

### Kiểm Tra Phân Quyền (7 lớp)

```
JWT access hợp lệ (signature, iss, aud, type, exp)
  AND user active, token_version khớp
  AND auth_session còn hiệu lực
  AND role có action permission
  AND resource.commune_id == user.commune_id    ← tenant isolation
  AND ownership hoặc explicit grant phù hợp
  AND resource state cho phép (chưa bị delete, đúng trạng thái)
```

### Permission Matrix

| Permission | ADMIN | USER | Điều kiện bổ sung |
|---|:---:|:---:|---|
| `users:create` | ✓ | — | Backend ép role USER, commune của actor |
| `users:read_commune` | ✓ | — | Query cùng commune |
| `users:update_status` | ✓ | — | Không self-lock / last-admin lock |
| `users:reset_password` | ✓ | — | Revoke session target |
| `documents:create` | ✓ | ✓ | USER qua feature flag |
| `documents:read_own` | ✓ | ✓ | Owner + cùng xã |
| `documents:read_commune` | ✓ | — | Vẫn bắt buộc cùng xã |
| `documents:delete_own` | ✓ | ✓ | State policy check |
| `documents:delete_commune` | ✓ | — | Cùng xã, chưa deleted |
| `documents:restore_commune` | ✓ | — | Cùng xã, đang soft-delete |
| `audit_logs:read_commune` | ✓ | — | Audit cùng xã |

### 🛡️ Bảo Mật Chống Tấn Công

| Rủi ro | Kiểm soát trong VADS |
|---|---|
| IDOR qua UUID xã khác | Tenant-scoped repository + policy; trả 404 cho tài nguyên ngoài scope |
| Access token cũ sau khi khoá | JWT 10 phút + kiểm tra `token_version` trong database |
| Refresh token bị phát lại | Opaque 256-bit, HMAC hash, rotation và revoke toàn family khi reuse |
| Password spraying | Argon2id, đếm lần thất bại, lock 15 phút, response không làm lộ identifier |
| Mass assignment | Pydantic `extra=forbid`; commune, owner và role do server quyết định |
| Sửa/xoá audit | ORM guard + PostgreSQL trigger mô hình append-only |

---

## 12. 🧠 Quy Trình AI & Phân Tích

### Quy trình 8-Agent Regulatory Change

```
DocumentIntakeAgent        → Trích xuất text, phân loại PDF, parse legal hierarchy
  → VersionResolutionAgent → Xác định phiên bản cũ/mới trong cùng family
  → SemanticDiffAgent      → So sánh typed facts: VALUE_CHANGED, RESPONSIBILITY_CHANGED, UNCHANGED
  → LegalResearchAgent     → Trích xuất các văn bản pháp luật được viện dẫn
  → KnowledgeGraphAgent    → Tạo biểu đồ tri thức từ nội dung
  → ImpactAnalysisAgent    → Đánh giá mức tác động bằng multi-signal scoring
  → DepartmentAdvisorAgent → Đề xuất hành động cho từng phòng ban
  → VerificationAgent      → Kiểm tra chéo: mọi claim phải có evidence
                             → Đủ bằng chứng → COMPLETED
                             → Thiếu/mơ hồ → NEEDS_HUMAN_REVIEW
```

Mỗi run, task, output, confidence, evidence và verification result đều được persist. Phiên bản cũ không bị ghi đè; retry tạo attempt mới.

### Explainable Impact Scoring

Không dùng một similarity score duy nhất; kết hợp nhiều tín hiệu giải thích được:

| Tín hiệu | Trọng số |
|---|---:|
| Domain match (lĩnh vực) | 0.15 |
| Budget source + value change | 0.25 |
| Project stage (giai đoạn dự án) | 0.20 |
| Department responsibility | 0.20 |
| Legal reference (căn cứ pháp lý) | 0.10 |
| Effective-date overlap | 0.10 |

### Publication Gate — Chống Hallucination

```
Model output
  → Pydantic schema validation (structured output)
  → Citation validation by code
      → Kiểm tra: document ID, chunk ID, quote text, page number, legal hierarchy, bounding box
      │
      ├── Đúng → Publish artifact
      │
      └── Sai → Repair đúng item, tối đa 2 lần
                  │
                  ├── Sửa được → Publish
                  └── Vẫn sai → NEEDS_REVIEW hoặc SUPPRESSED
```

> **Nguyên tắc cốt lõi:** Model đề xuất → Code kiểm chứng → Con người quyết định ở ca không chắc chắn.

---

## 13. 👨‍💼 Admin Panel

### 👥 Quản Lý Tài Khoản (AdminPortal.tsx)

- Liệt kê toàn bộ tài khoản từ bảng User trong tenant hiện tại.
- Hỗ trợ tìm kiếm, phân trang.
- Nút **Khoá** và **Mở khoá** cho từng tài khoản.
- Nút **Reset mật khẩu** — tạo mật khẩu tạm, bắt user đổi lần đăng nhập tiếp.
- Admin có thể **Tạo mới** tài khoản USER trong cùng commune.

### 📊 Dashboard

Dashboard cung cấp cái nhìn tổng quan:

- 👥 Tổng số người dùng đã đăng ký trong tenant
- 📦 Tổng số tài liệu đã tải lên
- 🧠 Số phiên phân tích AI đã chạy
- 📋 Audit log mới nhất

### 🛡️ Kiểm Soát Truy Cập

Mọi trang Admin kiểm tra role từ JWT token. Nếu user không phải `ADMIN`, API trả về 404 (không phải 403 — để không tiết lộ endpoint tồn tại).

---

## 14. 📧 Hệ Thống Xử Lý Tài Liệu

### Pipeline Xử Lý PDF/DOCX

```
Upload file
  │
  ├─ Validate: extension, MIME type, magic bytes, filename, kích thước ≤ 50 MB
  ├─ Tính SHA-256 checksum → chống upload trùng
  ├─ Lưu binary bất biến lên MinIO/S3
  ├─ Commit metadata vào PostgreSQL (Document + DocumentFile + ProcessingJob)
  │
  └─ Celery Worker nhận job:
       │
       ├─ Phân loại: TEXT_BASED / SCANNED / HYBRID
       │   → TEXT_BASED: Trích text layer bằng PyMuPDF (nhanh, chính xác)
       │   → SCANNED: OCR toàn bộ bằng PaddleOCR tiếng Việt
       │   → HYBRID: Text layer cho trang có text, OCR cho trang scan
       │
       ├─ Lưu per-page data: text, blocks, tables, bounding boxes
       │
       ├─ Parse cấu trúc pháp lý:
       │   Chương → Điều → Khoản → Điểm
       │
       ├─ Chunking (300–800 tokens, overlap 75):
       │   Mỗi chunk giữ legal metadata + source anchor
       │
       └─ Vector embedding → pgvector index
```

### Compensating Transaction

Vì không có ACID chung giữa PostgreSQL và MinIO:
1. Upload file lên MinIO trước.
2. Commit metadata vào PostgreSQL.
3. **Nếu commit thất bại** → xoá file đã upload trên MinIO (compensating delete).
4. Job status `UPLOADED` là recovery point — Celery Beat có thể phát lại idempotently.

### Cấu Hình OCR & Chunking

| Biến | Giá trị mặc định | Mô tả |
|---|---|---|
| `VADS_OCR_PROVIDER` | `PADDLEOCR` | Provider OCR |
| `VADS_PDF_TEXT_MIN_CHARACTERS` | `20` | Ngưỡng ký tự tối thiểu để coi là text page |
| `VADS_PDF_TEXT_PAGE_RATIO` | `0.8` | Tỷ lệ trang text để phân loại TEXT_BASED |
| `VADS_RENDER_DPI` | `150` | DPI khi render trang cho OCR |
| `VADS_OCR_REVIEW_CONFIDENCE_THRESHOLD` | `0.7` | Ngưỡng tin cậy OCR |
| `VADS_CHUNK_MIN_TOKENS` | `300` | Chunk tối thiểu |
| `VADS_CHUNK_MAX_TOKENS` | `800` | Chunk tối đa |
| `VADS_CHUNK_OVERLAP_TOKENS` | `75` | Overlap giữa các chunk |

---

## 15. 🎨 Giao Diện Frontend

### Cấu Trúc Layout

Ứng dụng React SPA với routing dựa trên role:

```
┌──────────────────────────────┐
│        App.tsx (Root)         │  ← Auth guard, route protection
├──────────────────────────────┤
│                               │
│  ┌─── Role: ADMIN ─────────┐ │
│  │    AdminPortal.tsx       │ │  ← Dashboard, User management, Audit log
│  └──────────────────────────┘ │
│                               │
│  ┌─── Role: USER ──────────┐ │
│  │    UserPortal.tsx        │ │  ← Document upload, Chat, Analysis
│  │    KnowledgeGraphScreen  │ │  ← Biểu đồ tri thức interactive
│  │    RegulatoryIntelligence│ │  ← So sánh phiên bản, tác động
│  └──────────────────────────┘ │
└──────────────────────────────┘
```

### 🎨 Bảng Màu (Design Tokens từ `theme.css`)

| Biến CSS | Giá trị Light Mode | Mục đích |
|---|---|---|
| `--background` | `#F4F5F7` | Nền trang chính |
| `--foreground` | `#111827` | Màu chữ chính |
| `--primary` | `#0F1623` | Màu primary (sidebar, heading) |
| `--accent` | `#C41E3A` | Màu nhấn / CTA (đỏ thẫm 🔴) |
| `--muted` | `#E8EAED` | Nền phụ |
| `--muted-foreground` | `#6B7280` | Chữ phụ |
| `--card` | `#ffffff` | Nền card |
| `--sidebar` | `#0F1623` | Nền sidebar (tối) |
| `--sidebar-primary` | `#C41E3A` | Active item sidebar |
| `--chart-1` → `--chart-5` | Đỏ, Tối, Xanh dương, Xanh lá, Vàng | Màu biểu đồ |

> Hỗ trợ **Dark Mode** đầy đủ qua `.dark` class với bảng màu oklch riêng.

### 🔤 Typography

- **Font chính:** Inter (Google Fonts)
- **Font size gốc:** 15px
- **Heading weight:** 600 (semibold)
- **Body weight:** 400 (regular)

### Danh Sách File Frontend Chính

| File | Mô tả |
|---|---|
| `App.tsx` | Root component, login form, auth state, routing |
| `AdminPortal.tsx` | Dashboard admin, CRUD tài khoản, audit log viewer |
| `UserPortal.tsx` | Trang chính user: upload, danh sách tài liệu, RAG chat |
| `KnowledgeGraphScreen.tsx` | Hiển thị và tương tác knowledge graph |
| `RegulatoryIntelligence.tsx` | So sánh phiên bản văn bản, xem tác động |
| `api.ts` | API client — tất cả hàm gọi backend |
| `theme.css` | Design tokens, CSS custom properties |

---

## 16. ⚙️ Cấu Hình Hệ Thống

### 🗄️ Cấu hình qua file `.env` (92 biến)

#### Application

```dotenv
VADS_APP_NAME=VADS API
VADS_ENVIRONMENT=local              # local | staging | production
VADS_DEBUG=false                    # Không bật ở production
VADS_API_PREFIX=/api
VADS_CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]
```

#### Database (PostgreSQL)

```dotenv
POSTGRES_IMAGE=pgvector/pgvector:pg16
POSTGRES_DB=vads
POSTGRES_USER=vads
POSTGRES_PASSWORD=replace-with-a-strong-password
VADS_DATABASE_URL=postgresql+psycopg://vads:replace-with-a-strong-password@postgres:5432/vads
```

#### Authentication & Security

```dotenv
VADS_JWT_SECRET_KEY=replace-with-an-independent-random-secret-at-least-32-bytes
VADS_REFRESH_TOKEN_PEPPER=replace-with-a-different-random-secret-at-least-32-bytes
VADS_ACCESS_TOKEN_TTL_MINUTES=10     # JWT access hết hạn sau 10 phút
VADS_REFRESH_TOKEN_TTL_DAYS=30       # Refresh token 30 ngày
VADS_LOGIN_MAX_FAILED_ATTEMPTS=5     # Khoá sau 5 lần sai
VADS_LOGIN_LOCK_MINUTES=15           # Khoá trong 15 phút
```

#### Object Storage (MinIO / S3)

```dotenv
VADS_STORAGE_PROVIDER=MINIO
VADS_S3_ENDPOINT_URL=http://minio:9000
VADS_S3_BUCKET_NAME=vads-documents
MAX_UPLOAD_SIZE_MB=50
```

#### AI Model Gateway

```dotenv
VADS_FPT_AI_ENABLED=false            # Bật nếu có key FPT AI
VADS_FPT_AI_API_KEY=replace-with-fpt-ai-marketplace-key
VADS_FPT_AI_BASE_URL=https://mkp-api.fptcloud.com
VADS_FPT_AI_MAX_TOKENS=4096
VADS_FPT_AI_TEMPERATURE=0
VADS_FPT_AI_ALLOW_PRIVATE_DATA=false  # Không gửi dữ liệu nhạy cảm
```

#### Feature Flags

```dotenv
VADS_LEGACY_API_ENABLED=false         # Chỉ bật cho local demo
VADS_USER_DOCUMENT_UPLOAD_ENABLED=true
```

> ⚠️ **Quan trọng:** Startup sẽ từ chối secret mặc định, debug mode, wildcard CORS và legacy API ở staging/production.

### 🐳 Docker Compose Services

| Service | Image | Port | Health Check |
|---|---|---|---|
| `api` | Build từ Dockerfile | 8000 | `http://127.0.0.1:8000/health/live` |
| `worker` | Build + PaddleOCR | — | — |
| `beat` | Build | — | — |
| `postgres` | `pgvector/pgvector:pg16` | 5432 | `pg_isready` |
| `redis` | `redis:7-alpine` | 6379 | `redis-cli ping` |
| `minio` | `minio/minio:latest` | 9000 / 9001 | — |

### 🚀 Triển Khai Production

| Nền tảng | Hướng dẫn |
|---|---|
| Azure VM (Ubuntu) | [`docs/deploy-azure-vm.md`](docs/deploy-azure-vm.md) — Docker Compose + Caddy tự động HTTPS |
| Railway | [`docs/deploy-railway.md`](docs/deploy-railway.md) — Tách service, private network |

```
Railway architecture:
  frontend ──private network──> api
                                  ├── PostgreSQL/pgvector
                                  ├── Redis <── worker + beat
                                  └── S3-compatible Bucket
```

---

## 17. 👥 Thành Viên Nhóm

Dự án VADS được phát triển bởi nhóm sinh viên tại **Đại học FPT**.

### Liên Kết Dự Án

| Liên kết | URL |
|---|---|
| 📦 Repository chính | https://github.com/nguyenlebinhan/VADS |
| 🔧 Nhánh Backend | https://github.com/nguyenlebinhan/VADS/tree/SU |
| 🖥️ Frontend trên SU | https://github.com/nguyenlebinhan/VADS/tree/SU/frontend |
| 🎨 Figma Prototype | https://www.figma.com/design/b7Egr7gD623CWdrn6JdVpK/VADS---Prototype |
| 📘 API Catalog | [docs/api-catalog.md](docs/api-catalog.md) |
| 🔐 Auth & Security | [docs/authentication-authorization.md](docs/authentication-authorization.md) |
| ⚖️ Regulatory Architecture | [docs/regulatory-change-architecture.md](docs/regulatory-change-architecture.md) |
| 🤖 AI Orchestration | [app/orchestrator/README.md](app/orchestrator/README.md) |
| 👥 Contributors | https://github.com/nguyenlebinhan/VADS/graphs/contributors |

### ⚠️ Lưu Ý & Ranh Giới MVP

| Mức độ | Lưu ý |
|---|---|
| 🟢 Đã hoàn thành | Secure `/api/v1` (20 operations) bật mặc định, JWT + RBAC + Tenant, 110 test cases |
| 🟢 Đã hoàn thành | 8-agent Regulatory Change pipeline với persist audit, publication gate |
| 🟢 Đã hoàn thành | PDF/DOCX pipeline, OCR tiếng Việt, legal hierarchy parsing |
| 🟡 Cần phát triển | Product API chưa hoàn tất tenant scope — cần hoàn thành trước production |
| 🟡 Cần phát triển | Embedding/reranker mặc định là adapter deterministic — cần kết nối provider production |
| 🟡 Cần phát triển | Legal relation đang là `EXTRACTED_NOT_EXTERNALLY_VERIFIED` — chờ connector nguồn pháp luật |
| 🟡 Cần phát triển | Agent dispatch chạy đồng bộ — contract đã persist để chuyển sang Celery |
| 🔴 Chưa có | PostgreSQL RLS defense-in-depth |
| 🔴 Chưa có | CSRF protection cho form-based flows |

### 📝 Kiểm Thử & Chất Lượng

**110 automated test cases** bao phủ các rủi ro khó, không chỉ happy path:

| Nhóm test | Bao phủ |
|---|---|
| Document pipeline | File giả extension/MIME/magic bytes, file rỗng/quá cỡ, duplicate checksum |
| Error recovery | Rollback bù khi storage/database lỗi, state regression, retry, worker failure |
| PDF processing | Text/scan/hybrid, OCR bounding box, legal hierarchy qua nhiều trang |
| AI orchestration | Model routing, retry/fallback, structured output validation |
| Citation validation | Citation sai document, quote không tồn tại, red flag thiếu bằng chứng |
| Regulatory change | Semantic diff 2 phiên bản, impact 2 phía, idempotency, retry audit |
| Security | Login limit, token hết hạn, refresh replay, cross-tenant IDOR, mass assignment |
| Retrieval & Chat | Hybrid retrieval, reranking fallback, chat history, citation, SSE |

Chạy test:

```bash
# Backend
python -m pip install -e '.[dev]'
pytest
ruff check app
ruff format --check app
docker compose config --quiet

# Frontend
cd frontend
npm ci
npm run build
```

---

<div align='center'>

**VADS không chỉ giúp đọc văn bản nhanh hơn — VADS giúp biến thay đổi pháp lý thành hành động có thể kiểm chứng.**

⚖️ Built with Python · FastAPI · PostgreSQL · React · Docker

</div>
