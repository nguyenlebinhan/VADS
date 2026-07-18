# Thiết kế Authentication và Authorization cho VADS

Tài liệu này mô tả thiết kế mục tiêu và implementation trong repository. API mới dùng prefix
/api/v1. Route legacy /api chưa có tenant authorization chỉ được bật bằng biến
VADS_LEGACY_API_ENABLED=true; mặc định là false và không được bật ở staging/production.

## 1. Phân tích Authentication và Authorization

Authentication trả lời “người gọi là ai”; authorization trả lời “người đó được làm hành động
gì trên đúng tài nguyên nào, trong trạng thái nào”. Quyết định cho tài liệu là giao của:

~~~text
JWT access hợp lệ
AND user active, token_version khớp
AND auth_session còn hiệu lực
AND role có action permission
AND resource.commune_id == user.commune_id
AND ownership hoặc explicit grant phù hợp
AND resource state cho phép
AND response chỉ chứa field được phép
~~~

Threat model chính gồm IDOR bằng UUID xã khác, mass assignment commune/owner/role, JWT còn hạn
sau khi khóa tài khoản, refresh replay, password spraying, ADMIN bị hiểu nhầm là quản trị toàn
hệ thống, dữ liệu AI/meeting dẫn xuất lọt tenant, và audit log bị sửa hoặc chứa credential.

UUID chỉ giảm khả năng đoán tuần tự. UUID đã lộ qua URL, log hoặc citation vẫn phải đi qua
authorization đầy đủ.

## 2. Những điểm chưa rõ hoặc dễ gây lỗi

Các quyết định an toàn được chọn:

1. ADMIN xã chỉ tạo USER. ADMIN đầu tiên hoặc ADMIN bổ sung phải được provisioning bằng quy
   trình vận hành có thẩm quyền cao hơn ngoài API của xã.
2. ADMIN không được tự khóa hoặc khóa ADMIN active cuối cùng của xã.
3. Username và email unique toàn hệ thống, case-insensitive. Nếu chỉ unique trong xã thì login
   cần thêm commune selector để không mơ hồ.
4. Code hiện dùng mật khẩu tạm trong JSON body khi reset, response không trả password, và đặt
   must_change_password=true. Production nên chuyển sang reset link một lần có TTL ngắn.
5. USER có grant documents:create nhưng còn phải qua feature flag upload.
6. Grant READ/ASK không trao quyền xóa tài liệu của người khác.
7. Directory chỉ trả tên, chức vụ, phòng ban, tên xã. Email/điện thoại cần permission riêng.
8. Approval transition, meeting membership và AI visibility cần state machine riêng; mọi bảng
   dẫn xuất phải mang commune_id hoặc composite join về parent.
9. Dùng 404 cho absent/outside tenant/not allowed to know; dùng 403 cho action/state bị cấm
   trên tài nguyên cùng tenant đã biết.
10. Hai refresh đồng thời làm request thứ hai bị xem là reuse; client phải single-flight.
11. Migration gom dữ liệu cũ vào tenant LEGACY và vô hiệu hóa mọi user legacy. Chỉ được
    activate lại sau khi operator remap đúng commune.

## 3. Kiến trúc bảo mật đề xuất

~~~text
Client
  -> Router
  -> Authentication dependency
       -> verify JWT signature, iss, aud, type, exp
       -> load User + AuthSession
       -> compare token_version, role, commune_id
  -> Permission dependency
  -> Service
       -> tenant-scoped repository lookup
       -> policy: tenant + ownership + state
       -> mutation + audit transaction
  -> Repository
  -> PostgreSQL
~~~

Backend là policy enforcement point. Frontend chỉ hỗ trợ UX.

Các lớp phòng vệ gồm JWT access 10 phút; opaque refresh 256-bit trong 30 ngày; HMAC-SHA-256
refresh hash với pepper độc lập; history token đã rotate; FOR UPDATE khi login/refresh/status
mutation; Argon2id chạy ngoài event loop; composite FK chống grant chéo xã; audit append-only
ở ORM và PostgreSQL trigger; security-change trigger revoke session khi role/password/active
đổi; route legacy mặc định tắt.

PostgreSQL RLS có thể bổ sung defense-in-depth nhưng không thay policy code. Nếu dùng RLS phải
SET LOCAL tenant trong từng transaction và reset đúng khi trả connection về pool.

## 4. Permission matrix ADMIN và USER

| Permission | ADMIN | USER | Điều kiện bổ sung |
|---|:---:|:---:|---|
| users:create | ✓ | — | Backend ép role USER, commune của actor |
| users:read_commune | ✓ | — | Query cùng commune |
| users:update_status | ✓ | — | Cùng xã; không self/last-admin lock |
| users:reset_password | ✓ | — | Cùng xã; revoke session target |
| staff_directory:read_province | ✓ | — | Chỉ public directory fields |
| documents:create | ✓ | ✓ | USER còn qua feature flag |
| documents:read_own | ✓ | ✓ | Owner và cùng xã |
| documents:read_granted | ✓ | ✓ | Explicit grant cùng xã |
| documents:read_commune | ✓ | — | Vẫn bắt buộc cùng xã |
| documents:delete_own | ✓ | ✓ | USER qua toàn bộ state policy |
| documents:delete_commune | ✓ | — | Cùng xã, chưa deleted |
| documents:restore_commune | ✓ | — | Cùng xã, đang soft-delete |
| documents:analyze_ai | ✓ | — | Readable document cùng xã |
| documents:ask_ai | ✓ | ✓ | Readable hoặc granted |
| documents:read_legal_basis | ✓ | ✓ | Readable document |
| audit_logs:read_commune | ✓ | — | Audit cùng xã |
| meetings:read_commune | ✓ | ✓ | Meeting/document cùng xã |
| meetings:manage_commune | ✓ | — | Meeting cùng xã |

Role grant chỉ là điều kiện cần. ADMIN có documents:delete_commune vẫn nhận 404 khi ID thuộc
xã khác.

## 5. Database schema

Model nằm tại app/model/tenancy.py, app/model/users.py, app/model/security.py và
app/model/documents.py. Migration là revision 20260718_0006.

- provinces: UUID, name/code unique, timestamps.
- communes: FK province RESTRICT; code unique; unique province/name; index province.
- users: FK commune RESTRICT; username/email case-insensitive unique; role; Argon2 hash;
  active/must-change/failed/lock/token-version; self-FK created_by; check counter và version;
  index commune/role/active.
- auth_sessions: FK user; unique refresh hash; family/device/IP/UA; expiry/last-use/revoke;
  indexes user/revoked, family, expiry.
- refresh_token_history: unique old hash, FK session cascade, ROTATED/REVOKED, used_at.
- documents: FK commune/owner/deleted_by; approval/meeting/deletion state; indexes
  commune/deleted và commune/owner; check flag nhất quán deleted_at.
- display_name là title nghiệp vụ; binary location được chuẩn hóa ở
  document_files.object_key thay vì trả file_path nội bộ qua document API.
- document_permissions: thêm commune_id và composite FK document+commune, user+commune;
  unique document/user/permission. DB không thể commit grant chéo xã.
- audit_logs: commune/actor/action/resource/result/reason/request context/sanitized JSON;
  indexes commune/time, resource và actor; không có updated_at.

Audit login của identifier không tồn tại có commune và actor null, chỉ lưu HMAC fingerprint.
Writer redact key chứa password, token, authorization, cookie, secret hoặc credential.
PostgreSQL trigger từ chối UPDATE/DELETE audit. DB role ứng dụng cũng nên chỉ có SELECT/INSERT.

Meeting, AI result, chunk, embedding, legal basis và chat session phải có commune_id NOT NULL
và composite FK, hoặc luôn join parent bằng cả parent_id lẫn commune_id. Không query result chỉ
bằng result_id/document_id.

## 6. Luồng đăng nhập

1. Nhận JSON identifier/password/device; không nhận credential qua URL.
2. Normalize identifier và khóa user row.
3. Identifier không tồn tại vẫn verify dummy Argon2 hash để giảm timing enumeration.
4. Kiểm tra active và lock. Sai password tăng counter; lần thứ 5 khóa 15 phút, trả 429 và
   Retry-After.
5. Verify Argon2id và rehash khi parameters thay đổi.
6. Tạo session UUID và family UUID.
7. Sinh opaque refresh, chỉ lưu HMAC hash, expiry tuyệt đối 30 ngày.
8. Sinh access JWT đúng 10 phút với sub/role/commune/session/token_version/type/iat/nbf/exp/jti
   cộng iss/aud.
9. Ghi audit và commit session cùng transaction.
10. Trả token qua TLS; không log body auth.

Production cần thêm Redis/API-gateway limit theo IP và identifier trước Argon2 để chống spray
trên identifier không tồn tại; counter DB theo account đã có trong implementation.

## 7. Luồng refresh token rotation

Refresh được chọn là opaque token thay vì JWT. Refresh luôn cần DB cho rotation/revoke/reuse,
nên JWT không giảm query và dễ tạo ảo tưởng stateless.

~~~text
v1.<session_uuid>.<256-bit-random-secret>
~~~

Session UUID chỉ là selector; random suffix là bearer secret.

1. Parse selector, khóa auth_session bằng FOR UPDATE.
2. HMAC và constant-time compare với current hash.
3. Nếu khớp: lưu current hash vào history ROTATED; sinh token mới; thay current hash; cập nhật
   last-used; sinh access JWT mới; commit. Rotation không kéo dài absolute expiry.
4. Nếu không khớp nhưng hash có trong history: reuse. Revoke cả family, ghi audit
   high-severity, trả 401.
5. Session revoked/expired hoặc user inactive trả 401.

Logout một thiết bị revoke session hiện tại. Logout-all, lock, password change/reset hoặc role
change revoke session và tăng token_version theo chính sách. PostgreSQL trigger thực thi lại
quy tắc này nếu thay đổi bảo mật được thực hiện ngoài service.

## 8. Luồng kiểm tra quyền cho mỗi request

1. Decode JWT bằng algorithm allowlist, issuer, audience và required claims.
2. Token malformed/sai chữ ký/type/expired trả 401.
3. Load user từ verified sub và session theo session_id+user_id.
4. So token_version, role, commune claim với DB; DB là nguồn sự thật.
5. Kiểm tra active và must-change.
6. Kiểm tra action permission.
7. Repository query id AND commune_id; miss trả 404.
8. Policy kiểm ownership/share/state.
9. Service mới mutate; server tự gán commune/owner/creator/deleter.
10. Audit success/denied và mutation commit cùng transaction.
11. Pydantic schema allowlist serialize response.

Anti-IDOR bắt buộc:

~~~python
select(Document).where(
    Document.id == document_id,
    Document.commune_id == actor.commune_id,
    Document.is_deleted.is_(False),
)
~~~

Ngoại lệ global lookup duy nhất là login và self lookup từ verified JWT, với tên hàm thể hiện
rõ lý do.

## 9. Cấu trúc thư mục dự án

~~~text
app/
├── api/v1/              # HTTP contract/status/dependency
├── core/                # permission, Argon2/JWT/refresh, audit
├── database/            # AsyncEngine/AsyncSession
├── dependencies/        # auth, permission, tenant
├── model/               # SQLAlchemy models
├── schemas/             # Pydantic v2 allowlist, extra=forbid
├── repositories/        # tenant-scoped queries
├── policies/            # RBAC + tenant + owner + state
├── services/            # authorization lại, transaction, audit
└── tests/security/      # unit và async integration tests
~~~

Router không quyết định nghiệp vụ. Dependency xác thực principal/permission chung. Policy là
quyết định thuần. Service authorization lần cuối và mutate. Repository không commit, không có
get_all/get_by_id_without_scope.

## 10. Code FastAPI hoàn chỉnh theo từng file

| Yêu cầu | Vị trí |
|---|---|
| UserRole, Permission, matrix | app/core/permissions.py |
| User/AuthSession/Document model | app/model/users.py, security.py, documents.py |
| Schema không lộ sensitive | app/schemas |
| Argon2id, JWT 10 phút, refresh/HMAC | app/core/security.py |
| get_current_user và active | app/dependencies/auth.py |
| Permission và denied audit | app/dependencies/permissions.py |
| Tenant check | scoped repositories, app/dependencies/tenant.py |
| USER delete policy | DocumentPolicy.can_delete |
| Login/refresh/logout/change | app/services/auth_service.py, API auth router |
| ADMIN create/lock/unlock/reset | app/services/user_service.py, admin router |
| Soft delete/restore | app/services/document_service.py |
| Audit writer/redaction | record_audit |
| Global exception handlers | app/exceptions/handlers.py |
| Migration/constraint/trigger | revision 20260718_0006 |
| Unit/integration tests | app/tests/security |

Request schema dùng extra=forbid. Client thêm commune_id, owner_id, role hoặc created_by nhận
422; backend không áp dụng các field này.

## 11. Danh sách API endpoint

Đã triển khai:

~~~text
POST  /api/v1/auth/login
POST  /api/v1/auth/refresh
POST  /api/v1/auth/logout
POST  /api/v1/auth/logout-all
POST  /api/v1/auth/change-password
GET   /api/v1/auth/me

POST  /api/v1/admin/users
GET   /api/v1/admin/users
GET   /api/v1/admin/users/{user_id}
PATCH /api/v1/admin/users/{user_id}/lock
PATCH /api/v1/admin/users/{user_id}/unlock
POST  /api/v1/admin/users/{user_id}/reset-password
GET   /api/v1/staff-directory

GET    /api/v1/documents
GET    /api/v1/documents/{document_id}
DELETE /api/v1/documents/{document_id}
POST   /api/v1/documents/{document_id}/restore

GET /api/v1/admin/audit-logs
GET /api/v1/admin/audit-logs/{audit_log_id}
~~~

Không có PATCH/PUT/DELETE audit log.

Contract cần nối với module nghiệp vụ:

~~~text
POST /api/v1/documents
POST /api/v1/documents/{document_id}/analyze
POST /api/v1/documents/{document_id}/ask
GET  /api/v1/documents/{document_id}/legal-basis
~~~

Upload/AI legacy đang dùng sync session và chưa scope toàn bộ bảng dẫn xuất, nên không expose
production. Khi nối phải authorize document trước và thêm tenant scope cho chunk/citation/AI.
Không trả 501 giả hoặc chạy AI rồi mới authorize.

Status: 400 semantic input; 401 auth/token/session; 403 permission/state; 404 absent hoặc
opaque tenant miss; 409 duplicate/state conflict; 422 schema/mass assignment; 429 rate limit.

## 12. Các tình huống authorization

| # | Kết quả và điều kiện | HTTP | Audit |
|---:|---|---:|---|
| 1 | ADMIN A xem doc A: live session, read_commune, same tenant | 200 | Có |
| 2 | ADMIN A xem doc B: scoped lookup miss | 404 | Có, denied |
| 3 | ADMIN A khóa USER A: same tenant, not self/last admin | 200 | Có, revoke |
| 4 | ADMIN A khóa USER B: target query scoped A | 404 | Có |
| 5 | USER A xem shared doc A: same tenant + READ grant | 200 | Có |
| 6 | USER A đoán UUID doc B | 404 | Có |
| 7 | USER xóa own draft, no meeting, not deleted | 204 | Có, soft delete |
| 8 | USER xóa own approved/pending | 403 | Có |
| 9 | USER xóa doc người khác | 403 | Có |
| 10 | ADMIN xóa doc cùng xã | 204 | Có |
| 11 | ADMIN xóa audit: không có route | 405 | Gateway/access log |
| 12 | Account khóa dùng JWT cũ: version/session revoked | 401 | Lock có audit |
| 13 | Refresh cũ reuse: revoke family | 401 | Có, high severity |
| 14 | ADMIN xem directory xã khác cùng tỉnh, field allowlist | 200 | Có |
| 15 | Dùng directory để manage xã khác | 404 | Có |
| 16 | Thêm commune_id vào body: extra=forbid | 422 | Access log |
| 17 | Thêm role vào body: extra=forbid | 422 | Access log |
| 18 | GET soft-deleted document | 404 | Có |
| 19 | ADMIN restore deleted doc cùng xã | 200 | Có |
| 20 | USER restore: thiếu restore permission | 403 | Có, denied |

## 13. Unit test và integration test

app/tests/security tạo ADMIN/USER xã A và B, nhiều owner và approval state. Test dùng HTTPX
AsyncClient, AsyncSession và SQLite async.

Authentication coverage: login đúng/sai, 429, access/refresh expired, rotation, reuse revoke
family, logout one/all, password change invalidates session, account lock invalidates JWT.

Authorization coverage: ADMIN chỉ manage cùng xã; USER không gọi admin; shared document; UUID
xã khác 404; đủ delete state; ADMIN delete/restore tenant-scoped; audit không có mutation;
directory field allowlist; inject commune/role/created_by 422.

CI production cần thêm PostgreSQL integration cho FOR UPDATE, concurrent refresh, composite
FK, partial index và append-only trigger vì SQLite không mô phỏng hết.

## 14. Các lỗ hổng bảo mật thường gặp

- Chỉ kiểm role hoặc ẩn nút frontend.
- Query document theo ID rồi mới so commune.
- Tin role/commune JWT mà không so DB/token_version.
- JWT dài hạn; thiếu iss/aud/type/algorithm allowlist.
- Refresh JWT không rotation; lưu refresh rõ.
- Rotation không khóa row.
- Log password/bearer/reset credential.
- model_dump body có commune/owner/role vào ORM.
- Quên lọc soft-delete ở list/search/AI.
- Grant table không composite tenant FK.
- Directory tái dùng UserPublic làm lộ email/status.
- Audit có CRUD hoặc cascade delete.
- Chỉ rate-limit account, không rate theo IP/identifier.
- Refresh song song không có client single-flight.
- CORS wildcard với credential hoặc lưu refresh trong localStorage.
- Bật legacy routes để tạm chạy.
- Không scope AI result, embedding, citation, meeting và presigned object URL.

## 15. Checklist trước production

### Secret và transport

- [ ] Hai secret độc lập ít nhất 32 random byte trong secret manager.
- [ ] Quy trình rotate JWT key/kid và refresh pepper.
- [ ] TLS, HSTS, không log body auth.
- [ ] CORS allowlist, security headers, trusted proxy/IP đúng.

### Database và tenant

- [ ] Chạy migration trên staging snapshot; xử lý duplicate email case-insensitive.
- [ ] Remap toàn bộ LEGACY sang xã thật rồi mới activate từng user.
- [ ] Xác nhận commune_id NOT NULL, không orphan/null document.
- [ ] Tenant scope/composite FK cho meeting, AI, legal basis, chunk, embedding, chat.
- [ ] DB role không UPDATE/DELETE audit; test trigger.
- [ ] Backup/restore, retention audit, UTC clock.
- [ ] Cân nhắc/test RLS với transaction-local context.

### Authentication

- [ ] JWT access đúng 10 phút; refresh absolute TTL.
- [ ] Redis/gateway rate limit theo IP + identifier trước Argon2.
- [ ] Test concurrent refresh và client single-flight.
- [ ] Cleanup expired session/history nhưng không xóa audit.
- [ ] Reset link một lần khi delivery service sẵn sàng.
- [ ] Mọi role change tăng token_version và revoke session.

### Authorization và vận hành

- [ ] VADS_LEGACY_API_ENABLED=false; OpenAPI không expose route cũ.
- [ ] Nối upload/analyze/ask/legal-basis qua secure service.
- [ ] Object key/presigned URL tenant-scope, TTL ngắn.
- [ ] Negative tests cho user/document/meeting/AI/audit/deleted/grant.
- [ ] 404 response/timing không phân biệt cross-tenant với absent.
- [ ] Central SIEM alert reuse, cross-tenant probe, lock/reset/role change.
- [ ] PostgreSQL integration, load test, backup và incident response drill.
- [ ] Security review/penetration test trước khi onboard xã thứ hai.
