# Deploy VADS lên Railway

Railway không chạy nguyên `docker-compose.yml` như máy local. Mỗi process được tạo thành một
service riêng trong cùng project:

- `api`: FastAPI và Alembic.
- `worker`: Celery worker.
- `beat`: Celery scheduler.
- `frontend`: Vite build được phục vụ bởi Caddy.
- `Postgres`: dùng image/template có extension `pgvector`.
- `Redis`: Railway Redis.
- `Bucket`: Railway Storage Bucket (S3-compatible).

## 1. Tạo hạ tầng

Trong một Railway project trống:

1. Tạo PostgreSQL từ template `pgvector` và đặt tên service là `Postgres`.
2. Tạo Redis và đặt tên `Redis`.
3. Tạo Storage Bucket và đặt tên `Bucket`.
4. Tạo bốn service từ cùng GitHub repository, đặt tên chính xác là `api`, `worker`, `beat`,
   `frontend`.

Không dùng PostgreSQL template thường nếu server đó không có extension `vector`, vì migration
`20260718_0004_product_api` cần `CREATE EXTENSION vector`.

## 2. Chọn config cho từng service

Giữ Root Directory là `/` cho cả bốn service vì Docker build cần file ở repository root.

| Service | Config file path |
|---|---|
| `api` | `/railway.json` (được nhận tự động) |
| `worker` | `/.railway/worker.json` |
| `beat` | `/.railway/beat.json` |
| `frontend` | `/.railway/frontend.json` |

API chạy migration bằng pre-deploy command và lắng nghe `PORT`. Frontend proxy `/api/*` qua
private network tới `api.railway.internal:8000`.

## 3. Variables dùng chung cho API, worker và beat

Tạo các giá trị dưới đây dưới dạng Shared Variables rồi liên kết vào cả ba service. Thay hai
placeholder secret bằng hai chuỗi ngẫu nhiên độc lập, mỗi chuỗi ít nhất 32 byte.

```dotenv
VADS_APP_NAME=VADS API
VADS_ENVIRONMENT=production
VADS_DEBUG=false
VADS_API_PREFIX=/api
VADS_DATABASE_ECHO=false
VADS_DATABASE_URL=${{Postgres.DATABASE_URL}}

VADS_JWT_SECRET_KEY=<RANDOM_SECRET_AT_LEAST_32_BYTES>
VADS_REFRESH_TOKEN_PEPPER=<DIFFERENT_RANDOM_SECRET_AT_LEAST_32_BYTES>
VADS_LEGACY_API_ENABLED=false
VADS_USER_DOCUMENT_UPLOAD_ENABLED=false

VADS_REDIS_URL=${{Redis.REDIS_URL}}
VADS_CELERY_BROKER_URL=${{Redis.REDIS_URL}}
VADS_CELERY_RESULT_BACKEND=${{Redis.REDIS_URL}}
VADS_CELERY_TASK_ALWAYS_EAGER=false
VADS_DOCUMENT_PROCESSING_QUEUE=document-processing

VADS_STORAGE_PROVIDER=S3
VADS_S3_ENDPOINT_URL=${{Bucket.ENDPOINT}}
VADS_S3_ACCESS_KEY=${{Bucket.ACCESS_KEY_ID}}
VADS_S3_SECRET_KEY=${{Bucket.SECRET_ACCESS_KEY}}
VADS_S3_BUCKET_NAME=${{Bucket.BUCKET}}
VADS_S3_REGION=${{Bucket.REGION}}
VADS_S3_FORCE_PATH_STYLE=false

VADS_UPLOAD_SPOOL_MEMORY_MB=8
VADS_DELETE_OBJECT_ON_SOFT_DELETE=false
VADS_OCR_PROVIDER=MOCK
VADS_CORS_ORIGINS=["https://${{frontend.RAILWAY_PUBLIC_DOMAIN}}"]
```

Đặt riêng `PORT=8000` trên service `api`. Không tạo public domain cho `worker` hoặc `beat`.

Để tạo secret trên máy local:

```powershell
.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
```

Chạy lệnh hai lần để lấy hai giá trị khác nhau.

## 4. Variables cho frontend

```dotenv
VITE_API_BASE_URL=/api/v1
VADS_API_UPSTREAM=api.railway.internal:8000
```

Tạo public domain cho `frontend`. Có thể tạo thêm public domain cho `api` để dùng Swagger/Postman;
Swagger nằm tại `https://<api-domain>/api/docs`.

## 5. Seed hai tài khoản demo trên Railway (một lần)

Không dùng mật khẩu mặc định local trên môi trường public. Trên service `api`, đặt tạm:

```dotenv
VADS_ALLOW_DEMO_ACCOUNT_SEED=true
VADS_DEMO_ADMIN_PASSWORD=<STRONG_ADMIN_PASSWORD>
VADS_DEMO_USER_PASSWORD=<STRONG_USER_PASSWORD>
```

Sau khi API deploy thành công, chạy trong container bằng Railway CLI:

```bash
railway ssh --service api python -m app.seed_demo_accounts
```

Sau đó xóa `VADS_ALLOW_DEMO_ACCOUNT_SEED` và hai biến mật khẩu khỏi Railway Variables. Username
mặc định là `admin.demo` và `user.demo`.

## 6. Kiểm tra

```text
GET https://<api-domain>/health/live
GET https://<api-domain>/api/docs
GET https://<frontend-domain>/
```

Nếu build vẫn báo cache mount thiếu `id`, deployment đang dùng commit cũ. Dockerfile hiện tại
không dùng cache mount nên chỉ cần push commit mới và Redeploy.
