export type UserRole = "ADMIN" | "USER";

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  expires_in: number;
  refresh_expires_at: string;
  must_change_password: boolean;
}

export interface UserPublic {
  id: string;
  commune_id: string;
  username: string;
  email: string;
  full_name: string;
  position: string | null;
  department: string | null;
  role: UserRole;
  is_active: boolean;
  must_change_password: boolean;
}

export interface StaffDirectoryEntry {
  full_name: string;
  position: string | null;
  department: string | null;
  commune_name: string;
}

export interface AdminUserCreateInput {
  username: string;
  email: string;
  full_name: string;
  position?: string | null;
  department?: string | null;
  temporary_password: string;
}

export type ProcessingStatus =
  | "UPLOADED"
  | "QUEUED"
  | "PROCESSING"
  | "COMPLETED"
  | "FAILED"
  | "CANCELLED"
  | "NEEDS_REVIEW";

export type DocumentApprovalStatus =
  | "DRAFT"
  | "PENDING_APPROVAL"
  | "APPROVED"
  | "REJECTED";

export interface DocumentPublic {
  id: string;
  commune_id: string;
  owner_id: string | null;
  title: string;
  status: ProcessingStatus;
  approval_status: DocumentApprovalStatus;
  meeting_id: string | null;
  is_deleted: boolean;
  created_at: string;
  updated_at: string;
}

export interface DocumentUploadResult {
  document_id: string;
  workspace_id: string;
  status: ProcessingStatus;
  progress: number;
}

export interface RagSource {
  document_id: string;
  document_title: string;
  chunk_id: string;
  page_number: number | null;
  article: string | null;
  clause: string | null;
  quote: string;
  score: number;
}

export interface RagQueryResult {
  answer: string;
  retrieval_mode: string;
  sources: RagSource[];
}

interface ErrorEnvelope {
  error?: {
    code?: string;
    message?: string;
    details?: unknown;
  };
  detail?: unknown;
}

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "/api/v1").replace(/\/$/, "");
const ACCESS_TOKEN_KEY = "vads.accessToken";
const REFRESH_TOKEN_KEY = "vads.refreshToken";

let refreshInFlight: Promise<void> | null = null;

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code?: string,
    readonly details?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function accessToken(): string | null {
  return sessionStorage.getItem(ACCESS_TOKEN_KEY);
}

function refreshToken(): string | null {
  return sessionStorage.getItem(REFRESH_TOKEN_KEY);
}

function saveTokens(tokens: TokenPair): void {
  sessionStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token);
  sessionStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
}

export function hasStoredSession(): boolean {
  return Boolean(accessToken() && refreshToken());
}

export function clearSession(notify = false): void {
  sessionStorage.removeItem(ACCESS_TOKEN_KEY);
  sessionStorage.removeItem(REFRESH_TOKEN_KEY);
  if (notify) window.dispatchEvent(new Event("vads:session-expired"));
}

async function apiError(response: Response): Promise<ApiError> {
  let payload: ErrorEnvelope = {};
  try {
    payload = (await response.json()) as ErrorEnvelope;
  } catch {
    // An empty or non-JSON error response is represented by its HTTP status.
  }
  const message =
    payload.error?.message ||
    (typeof payload.detail === "string" ? payload.detail : undefined) ||
    (response.status === 401
      ? "Phiên đăng nhập không hợp lệ."
      : response.status === 403
        ? "Bạn không có quyền thực hiện thao tác này."
        : "Không thể kết nối tới máy chủ.");
  return new ApiError(message, response.status, payload.error?.code, payload.error?.details);
}

async function rotateRefreshToken(): Promise<void> {
  const token = refreshToken();
  if (!token) {
    clearSession(true);
    throw new ApiError("Phiên đăng nhập đã hết hạn.", 401, "SESSION_EXPIRED");
  }

  const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: token }),
  });
  if (!response.ok) {
    clearSession(true);
    throw await apiError(response);
  }
  saveTokens((await response.json()) as TokenPair);
}

async function refreshOnce(): Promise<void> {
  if (!refreshInFlight) {
    refreshInFlight = rotateRefreshToken().finally(() => {
      refreshInFlight = null;
    });
  }
  return refreshInFlight;
}

async function request<T>(
  path: string,
  init: RequestInit = {},
  retryAfterRefresh = true,
): Promise<T> {
  const headers = new Headers(init.headers);
  const token = accessToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers });
  if (response.status === 401 && retryAfterRefresh && refreshToken()) {
    await refreshOnce();
    return request<T>(path, init, false);
  }
  if (!response.ok) throw await apiError(response);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export async function login(identifier: string, password: string): Promise<TokenPair> {
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      identifier,
      password,
      device_name: "VADS Web",
    }),
  });
  if (!response.ok) throw await apiError(response);
  const tokens = (await response.json()) as TokenPair;
  saveTokens(tokens);
  return tokens;
}

export async function logout(): Promise<void> {
  try {
    if (accessToken()) await request<void>("/auth/logout", { method: "POST" });
  } finally {
    clearSession();
  }
}

export function getCurrentUser(): Promise<UserPublic> {
  return request<UserPublic>("/auth/me");
}

export async function listDocuments(): Promise<DocumentPublic[]> {
  const documents: DocumentPublic[] = [];
  const pageSize = 100;
  let offset = 0;

  while (true) {
    const page = await request<DocumentPublic[]>(`/documents?offset=${offset}&limit=${pageSize}`);
    documents.push(...page);
    if (page.length < pageSize) return documents;
    offset += pageSize;
  }
}

async function listAll<T>(path: string): Promise<T[]> {
  const values: T[] = [];
  const pageSize = 100;
  let offset = 0;

  while (true) {
    const separator = path.includes("?") ? "&" : "?";
    const page = await request<T[]>(`${path}${separator}offset=${offset}&limit=${pageSize}`);
    values.push(...page);
    if (page.length < pageSize) return values;
    offset += pageSize;
  }
}

export function listAdminUsers(): Promise<UserPublic[]> {
  return listAll<UserPublic>("/admin/users");
}

export function listStaffDirectory(): Promise<StaffDirectoryEntry[]> {
  return listAll<StaffDirectoryEntry>("/staff-directory");
}

export function createAdminUser(input: AdminUserCreateInput): Promise<UserPublic> {
  return request<UserPublic>("/admin/users", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function setAdminUserActive(userId: string, active: boolean): Promise<UserPublic> {
  return request<UserPublic>(`/admin/users/${encodeURIComponent(userId)}/${active ? "unlock" : "lock"}`, {
    method: "PATCH",
  });
}

export function uploadDocument(file: File): Promise<DocumentUploadResult> {
  const body = new FormData();
  body.append("file", file);
  return request<DocumentUploadResult>("/documents", {
    method: "POST",
    body,
  });
}

export function reprocessDocument(documentId: string): Promise<DocumentUploadResult> {
  return request<DocumentUploadResult>(`/documents/${encodeURIComponent(documentId)}/reprocess`, {
    method: "POST",
  });
}

export function queryDocumentRag(
  question: string,
  documentIds: string[],
): Promise<RagQueryResult> {
  return request<RagQueryResult>("/rag/query", {
    method: "POST",
    body: JSON.stringify({
      question,
      document_ids: documentIds,
      top_k: 5,
    }),
  });
}

export async function changePassword(
  currentPassword: string,
  newPassword: string,
): Promise<void> {
  await request<void>("/auth/change-password", {
    method: "POST",
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
    }),
  });
  clearSession();
}
