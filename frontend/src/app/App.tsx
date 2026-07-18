import { useEffect, useState } from "react";
import { Loader2, Scale } from "lucide-react";
import AdminPortal from "./AdminPortal";
import UserPortal from "./UserPortal";
import { authApi, type CurrentUser } from "../lib/api";

function Login({ onSuccess }: { onSuccess: (user: CurrentUser) => void }) {
  const [identifier, setIdentifier] = useState("user.test");
  const [password, setPassword] = useState("UserTest123");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  async function submit(event: React.FormEvent) {
    event.preventDefault(); setLoading(true); setError("");
    try { onSuccess(await authApi.login(identifier, password)); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Đăng nhập không thành công."); }
    finally { setLoading(false); }
  }
  return <div className="min-h-screen bg-[#f4f5f7] flex items-center justify-center p-4"><div className="w-full max-w-[400px]">
    <div className="text-center mb-8"><div className="inline-flex w-14 h-14 items-center justify-center rounded-2xl bg-[#0f1623] shadow-xl mb-4"><Scale className="w-7 h-7 text-white" /></div><p className="text-[10px] uppercase tracking-[.2em] text-gray-400 font-semibold">Vietnamese Administrative Document System</p><h1 className="text-3xl font-bold text-gray-900 mt-1">VADS</h1></div>
    <form onSubmit={submit} className="bg-white rounded-2xl shadow-xl border border-black/5 p-8 space-y-4"><h2 className="font-bold text-gray-900 mb-5">Đăng nhập hệ thống</h2>
      <label className="block text-xs font-semibold text-gray-600 uppercase tracking-wide">Tài khoản<input className="mt-2 w-full px-3.5 py-2.5 text-sm border border-gray-200 rounded-xl bg-gray-50" value={identifier} onChange={(e) => setIdentifier(e.target.value)} autoComplete="username" /></label>
      <label className="block text-xs font-semibold text-gray-600 uppercase tracking-wide">Mật khẩu<input type="password" className="mt-2 w-full px-3.5 py-2.5 text-sm border border-gray-200 rounded-xl bg-gray-50" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" /></label>
      {error && <p role="alert" className="text-xs text-red-600 bg-red-50 rounded-lg px-3 py-2">{error}</p>}
      <button disabled={loading} className="w-full bg-[#c41e3a] hover:bg-[#a8172f] disabled:opacity-60 text-white py-3 rounded-xl text-sm font-bold flex items-center justify-center gap-2">{loading && <Loader2 className="w-4 h-4 animate-spin" />}{loading ? "Đang xác thực..." : "Đăng nhập"}</button>
    </form></div></div>;
}

export default function App() {
  const [user, setUser] = useState<CurrentUser | null>(null); const [checking, setChecking] = useState(true);
  useEffect(() => { if (!authApi.hasSession()) { setChecking(false); return; } authApi.me().then(setUser).catch(() => authApi.clear()).finally(() => setChecking(false)); }, []);
  async function logout() { await authApi.logout(); setUser(null); }
  if (checking) return <div className="min-h-screen grid place-items-center"><Loader2 className="animate-spin" /></div>;
  if (!user) return <Login onSuccess={setUser} />;
  return user.role === "ADMIN" ? <AdminPortal currentUser={user} onLogout={logout} /> : <UserPortal currentUser={user} onLogout={logout} />;
}

