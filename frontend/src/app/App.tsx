import { useEffect, useState } from "react";
import { Loader2, Scale } from "lucide-react";

import {
  ApiError,
  clearSession,
  getCurrentUser,
  hasStoredSession,
  login,
  logout,
  type UserPublic,
} from "../api";
import AdminPortal from "./AdminPortal";
import UserPortal from "./UserPortal";

function Login({ onSuccess }: { onSuccess: (user: UserPublic) => void }) {
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      await login(identifier, password);
      onSuccess(await getCurrentUser());
    } catch (reason) {
      setError(
        reason instanceof ApiError
          ? reason.message
          : "Không thể đăng nhập vào hệ thống.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#f4f5f7] p-4">
      <div className="w-full max-w-[400px]">
        <div className="mb-8 text-center">
          <div className="mb-4 inline-flex h-14 w-14 items-center justify-center rounded-lg bg-[#0f1623] shadow-xl">
            <Scale className="h-7 w-7 text-white" />
          </div>
          <p className="text-[10px] font-semibold uppercase text-gray-400">
            Vietnamese Administrative Document System
          </p>
          <h1 className="mt-1 text-3xl font-bold text-gray-900">VADS</h1>
        </div>
        <form onSubmit={submit} className="space-y-4 rounded-lg border border-black/5 bg-white p-8 shadow-xl">
          <h2 className="mb-5 font-bold text-gray-900">Đăng nhập hệ thống</h2>
          <label className="block text-xs font-semibold uppercase text-gray-600">
            Tài khoản
            <input
              className="mt-2 w-full rounded-lg border border-gray-200 bg-gray-50 px-3.5 py-2.5 text-sm"
              value={identifier}
              onChange={event => setIdentifier(event.target.value)}
              autoComplete="username"
              required
            />
          </label>
          <label className="block text-xs font-semibold uppercase text-gray-600">
            Mật khẩu
            <input
              type="password"
              className="mt-2 w-full rounded-lg border border-gray-200 bg-gray-50 px-3.5 py-2.5 text-sm"
              value={password}
              onChange={event => setPassword(event.target.value)}
              autoComplete="current-password"
              required
            />
          </label>
          {error && <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-xs text-red-600">{error}</p>}
          <button disabled={loading} className="flex w-full items-center justify-center gap-2 rounded-lg bg-[#c41e3a] py-3 text-sm font-bold text-white hover:bg-[#a8172f] disabled:opacity-60">
            {loading && <Loader2 className="h-4 w-4 animate-spin" />}
            {loading ? "Đang xác thực..." : "Đăng nhập"}
          </button>
        </form>
      </div>
    </div>
  );
}

export default function App() {
  const [user, setUser] = useState<UserPublic | null>(null);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    let cancelled = false;
    if (!hasStoredSession()) {
      setChecking(false);
      return;
    }
    getCurrentUser()
      .then(currentUser => {
        if (!cancelled) setUser(currentUser);
      })
      .catch(() => clearSession())
      .finally(() => {
        if (!cancelled) setChecking(false);
      });
    const expireSession = () => setUser(null);
    window.addEventListener("vads:session-expired", expireSession);
    return () => {
      cancelled = true;
      window.removeEventListener("vads:session-expired", expireSession);
    };
  }, []);

  async function handleLogout() {
    await logout();
    setUser(null);
  }

  if (checking) {
    return (
      <div className="grid min-h-screen place-items-center bg-[#f4f5f7]">
        <Loader2 className="animate-spin text-[#c41e3a]" />
      </div>
    );
  }
  if (!user) return <Login onSuccess={setUser} />;
  return user.role === "ADMIN" ? (
    <AdminPortal currentUser={user} onLogout={handleLogout} />
  ) : (
    <UserPortal currentUser={user} onLogout={handleLogout} />
  );
}
