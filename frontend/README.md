# VADS Frontend

React/Vite frontend của VADS. Mọi dữ liệu nghiệp vụ hiển thị trong portal được lấy từ API;
frontend không chứa danh sách văn bản, nội dung pháp luật, summary, timeline hoặc câu trả lời AI
mẫu.

## API contract

Base URL mặc định là `/api/v1` và có thể đổi bằng `VITE_API_BASE_URL`.

| Chức năng | Endpoint |
|---|---|
| Đăng nhập và phiên | `/auth/login`, `/auth/refresh`, `/auth/me`, `/auth/logout` |
| Hồ sơ và mật khẩu | `/auth/me`, `/auth/change-password` |
| Tài liệu | `GET/POST /documents`, `DELETE /documents/{id}` |
| Xử lý lại | `POST /documents/{id}/reprocess` |
| Hỏi đáp có nguồn | `POST /rag/query` |
| Quản trị người dùng | `/admin/users`, `/staff-directory` |

### Điều kiện để hỏi đáp RAG hoạt động

Frontend gọi `POST /rag/query`; backend hiện cần một trong hai biến `OPENAI_API_KEY` hoặc
`VADS_OPENAI_API_KEY`. Có thể cấu hình thêm `VADS_OPENAI_BASE_URL` và `VADS_OPENAI_CHAT_MODEL`.
Nếu thiếu khóa, API sẽ trả `503 RAG_MODEL_NOT_CONFIGURED`; frontend chỉ hiển thị lỗi thật từ API và
không chèn câu trả lời mẫu.

Khi API trả danh sách rỗng hoặc lỗi, giao diện hiển thị trạng thái empty/error tương ứng và không
thay thế bằng dữ liệu demo.

## Chạy local

```bash
npm ci
npm run dev
```

Vite mở cổng `5173` và proxy `/api` tới `http://localhost:8000`.

## Build production

```bash
npm run build
```

Output được ghi vào `dist/`. Khi deploy nơi khác, cấu hình ví dụ:

```dotenv
VITE_API_BASE_URL=https://api.example.gov.vn/api/v1
```
