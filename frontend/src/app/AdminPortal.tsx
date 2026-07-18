import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertCircle, Building2, CheckCircle2, Eye, EyeOff, Loader2,
  LockKeyhole, LogOut, RefreshCw, ShieldCheck, UserPlus, Users, X,
} from "lucide-react";
import {
  changePassword, createAdminUser, listAdminUsers, listStaffDirectory,
  setAdminUserActive, type AdminUserCreateInput, type StaffDirectoryEntry,
  type UserPublic,
} from "../api";

type Screen = "users" | "create" | "directory";

const messageOf = (reason: unknown) =>
  reason instanceof Error ? reason.message : "Không thể kết nối tới máy chủ.";

function initials(name: string) {
  const words = name.trim().split(/\s+/).filter(Boolean);
  return (words.length > 1
    ? `${words[0][0]}${words.at(-1)?.[0] ?? ""}`
    : words[0]?.slice(0, 2) || "U").toUpperCase();
}

function directoryKey(value: Pick<UserPublic, "full_name" | "position" | "department">) {
  return [value.full_name, value.position ?? "", value.department ?? ""]
    .join("|").toLocaleLowerCase("vi");
}

function Notice({ kind, children }: {
  kind: "error" | "success";
  children: React.ReactNode;
}) {
  const Icon = kind === "error" ? AlertCircle : CheckCircle2;
  return <div className={`flex items-start gap-2.5 rounded-lg border px-3.5 py-3 text-sm ${
    kind === "error"
      ? "border-red-200 bg-red-50 text-red-700"
      : "border-emerald-200 bg-emerald-50 text-emerald-700"
  }`}><Icon size={16} className="mt-0.5 flex-shrink-0" /><span>{children}</span></div>;
}

function Field({ label, value, onChange, type = "text", placeholder, autoComplete }: {
  label: string; value: string; onChange: (value: string) => void;
  type?: string; placeholder?: string; autoComplete?: string;
}) {
  return <label className="block">
    <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-gray-500">{label}</span>
    <input value={value} onChange={(event) => onChange(event.target.value)}
      type={type} placeholder={placeholder} autoComplete={autoComplete}
      className="h-11 w-full rounded-lg border border-gray-200 bg-white px-3.5 text-sm outline-none transition focus:border-[#cc1515] focus:ring-2 focus:ring-[#cc1515]/15" />
  </label>;
}

function CreateUserScreen({ onCreated }: { onCreated: (user: UserPublic) => void }) {
  const [form, setForm] = useState({
    username: "", email: "", fullName: "", position: "", department: "",
    password: "", confirmPassword: "",
  });
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const set = (key: keyof typeof form) => (value: string) =>
    setForm((current) => ({ ...current, [key]: value }));

  async function submit(event: React.FormEvent) {
    event.preventDefault(); setError("");
    if (!/^[a-zA-Z0-9._-]{3,64}$/.test(form.username))
      return setError("Tên đăng nhập cần 3–64 ký tự và chỉ gồm chữ, số, dấu chấm, gạch dưới hoặc gạch ngang.");
    if (!form.fullName.trim() || !/^\S+@\S+\.\S+$/.test(form.email))
      return setError("Vui lòng nhập đầy đủ họ tên và email hợp lệ.");
    if (form.password.length < 12)
      return setError("Mật khẩu tạm thời phải có ít nhất 12 ký tự.");
    if (form.password !== form.confirmPassword)
      return setError("Mật khẩu xác nhận không khớp.");
    const payload: AdminUserCreateInput = {
      username: form.username.trim(), email: form.email.trim(),
      full_name: form.fullName.trim(), position: form.position.trim() || null,
      department: form.department.trim() || null, temporary_password: form.password,
    };
    setSubmitting(true);
    try { onCreated(await createAdminUser(payload)); }
    catch (reason) { setError(messageOf(reason)); }
    finally { setSubmitting(false); }
  }

  return <div className="h-full overflow-y-auto">
    <div className="border-b border-gray-200 bg-white px-8 py-5">
      <h1 className="text-xl font-bold text-gray-900">Thêm tài khoản</h1>
      <p className="mt-1 text-sm text-gray-500">Tài khoản mới tự động thuộc xã/phường của quản trị viên hiện tại.</p>
    </div>
    <div className="mx-auto max-w-3xl p-8"><form onSubmit={submit}
      className="overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm">
      <div className="border-b border-gray-100 bg-gray-50 px-6 py-4">
        <p className="text-xs font-bold uppercase tracking-widest text-gray-500">Thông tin tài khoản</p>
      </div>
      <div className="grid grid-cols-1 gap-5 p-6 md:grid-cols-2">
        <Field label='Tên đăng nhập' value={form.username} onChange={set('username')} placeholder='Nhập tên đăng nhập' autoComplete='off' />
        <Field label='Email' value={form.email} onChange={set('email')} type='email' placeholder='Nhập email' autoComplete='off' />
        <div className='md:col-span-2'><Field label='Họ và tên' value={form.fullName} onChange={set('fullName')} placeholder='Nhập họ và tên' /></div>
        <Field label='Chức vụ' value={form.position} onChange={set('position')} placeholder='Nhập chức vụ' />
        <Field label='Phòng ban' value={form.department} onChange={set('department')} placeholder='Nhập phòng ban' />
        <div className="relative"><Field label="Mật khẩu tạm thời" value={form.password}
          onChange={set("password")} type={showPassword ? "text" : "password"} autoComplete="new-password" />
          <button type="button" onClick={() => setShowPassword((value) => !value)}
            className="absolute bottom-3 right-3 text-gray-400 hover:text-gray-700">
            {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}</button></div>
        <Field label="Xác nhận mật khẩu" value={form.confirmPassword} onChange={set("confirmPassword")}
          type={showPassword ? "text" : "password"} autoComplete="new-password" />
        <p className="text-xs text-gray-400 md:col-span-2">Người dùng sẽ được yêu cầu đổi mật khẩu tạm thời sau khi đăng nhập.</p>
        {error && <div className="md:col-span-2"><Notice kind="error">{error}</Notice></div>}
      </div>
      <div className="flex justify-end border-t border-gray-100 bg-gray-50 px-6 py-4">
        <button disabled={submitting} className="flex items-center gap-2 rounded-lg bg-[#cc1515] px-5 py-2.5 text-sm font-bold text-white disabled:opacity-60">
          {submitting ? <Loader2 size={16} className="animate-spin" /> : <UserPlus size={16} />}
          {submitting ? "Đang tạo..." : "Tạo tài khoản"}</button>
      </div>
    </form></div>
  </div>;
}

function UsersScreen({ currentUser, users, directory, loading, error, onRefresh, onUserChanged }: {
  currentUser: UserPublic; users: UserPublic[]; directory: StaffDirectoryEntry[];
  loading: boolean; error: string; onRefresh: () => void;
  onUserChanged: (user: UserPublic) => void;
}) {
  const [search, setSearch] = useState("");
  const [pendingId, setPendingId] = useState<string | null>(null);
  const [actionError, setActionError] = useState("");
  const communeByUser = useMemo(() => new Map(directory.map((entry) => [
    directoryKey({ full_name: entry.full_name, position: entry.position, department: entry.department }),
    entry.commune_name,
  ])), [directory]);
  const filtered = useMemo(() => {
    const query = search.trim().toLocaleLowerCase("vi");
    if (!query) return users;
    return users.filter((user) =>
      [user.full_name, user.username, user.email, user.position, user.department]
        .some((value) => value?.toLocaleLowerCase("vi").includes(query)));
  }, [search, users]);

  async function toggle(user: UserPublic) {
    setPendingId(user.id); setActionError("");
    try { onUserChanged(await setAdminUserActive(user.id, !user.is_active)); }
    catch (reason) { setActionError(messageOf(reason)); }
    finally { setPendingId(null); }
  }

  const stats: Array<[string, number, React.ElementType]> = [
    ["Tổng tài khoản", users.length, Users],
    ["Đang hoạt động", users.filter((user) => user.is_active).length, CheckCircle2],
    ["Cần đổi mật khẩu", users.filter((user) => user.must_change_password).length, LockKeyhole],
  ];

  return <div className="flex h-full flex-col">
    <div className="flex items-center justify-between border-b border-gray-200 bg-white px-8 py-5">
      <div><h1 className="text-xl font-bold text-gray-900">Quản lý tài khoản</h1>
        <p className="mt-1 text-sm text-gray-500">Dữ liệu trực tiếp từ API trong phạm vi xã/phường của bạn.</p></div>
      <button onClick={onRefresh} disabled={loading}
        className="flex items-center gap-2 rounded-lg border border-gray-200 px-3.5 py-2 text-sm font-semibold text-gray-600 disabled:opacity-50">
        <RefreshCw size={15} className={loading ? "animate-spin" : ""} />Làm mới</button>
    </div>
    <div className="flex-1 overflow-y-auto p-8">
      <div className="mb-5 grid grid-cols-3 gap-4">{stats.map(([label, value, Icon]) =>
        <div key={label} className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
          <div className="mb-3 flex h-9 w-9 items-center justify-center rounded-lg bg-[#cc1515]/10 text-[#cc1515]"><Icon size={17} /></div>
          <p className="text-2xl font-bold text-gray-900">{value}</p><p className="mt-0.5 text-xs text-gray-500">{label}</p>
        </div>)}</div>
      {(error || actionError) && <div className="mb-4"><Notice kind="error">{actionError || error}</Notice></div>}
      <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
        <div className="flex items-center justify-between border-b border-gray-100 px-5 py-4">
          <p className="text-sm font-bold text-gray-800">Danh sách người dùng</p>
          <input value={search} onChange={(event) => setSearch(event.target.value)}
            placeholder="Tìm tên, username, email..."
            className="w-64 rounded-lg border border-gray-200 px-3 py-2 text-xs outline-none focus:border-[#cc1515]" />
        </div>
        {loading && users.length === 0 ?
          <div className="flex items-center justify-center gap-2 py-20 text-sm text-gray-400"><Loader2 size={18} className="animate-spin" />Đang tải dữ liệu...</div>
        : filtered.length === 0 ?
          <div className="py-20 text-center text-sm text-gray-400">Không có tài khoản phù hợp.</div>
        : <div className="overflow-x-auto"><table className="w-full text-left text-sm">
          <thead className="bg-gray-50 text-[11px] uppercase tracking-wide text-gray-500"><tr>
            <th className="px-5 py-3">Người dùng</th><th className="px-5 py-3">Tài khoản</th>
            <th className="px-5 py-3">Đơn vị</th><th className="px-5 py-3">Vai trò</th>
            <th className="px-5 py-3">Trạng thái</th><th className="px-5 py-3 text-right">Thao tác</th>
          </tr></thead><tbody>{filtered.map((user) => <tr key={user.id} className="border-t border-gray-100 hover:bg-gray-50/60">
            <td className="px-5 py-3.5"><div className="flex items-center gap-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-[#141414] text-[10px] font-bold text-white">{initials(user.full_name)}</div>
              <div><p className="font-semibold text-gray-900">{user.full_name}</p><p className="text-xs text-gray-400">{user.position || "Chưa cập nhật chức vụ"}</p></div>
            </div></td>
            <td className="px-5 py-3.5"><p className="font-mono text-xs text-gray-700">{user.username}</p><p className="mt-1 text-xs text-gray-400">{user.email}</p></td>
            <td className="px-5 py-3.5"><p className="text-xs font-medium text-gray-700">{user.department || "Chưa cập nhật phòng ban"}</p>
              <p className="mt-1 text-[11px] text-gray-400">{communeByUser.get(directoryKey(user)) || `Mã xã: ${user.commune_id.slice(0, 8)}…`}</p></td>
            <td className="px-5 py-3.5"><span className="rounded-full bg-gray-100 px-2.5 py-1 text-[10px] font-bold text-gray-600">{user.role === "ADMIN" ? "Quản trị" : "Người dùng"}</span></td>
            <td className="px-5 py-3.5"><div className="flex flex-col items-start gap-1">
              <span className={`rounded-full px-2.5 py-1 text-[10px] font-bold ${user.is_active ? "bg-emerald-50 text-emerald-700" : "bg-red-50 text-red-700"}`}>{user.is_active ? "Hoạt động" : "Đã khóa"}</span>
              {user.must_change_password && <span className="text-[10px] text-amber-600">Cần đổi mật khẩu</span>}
            </div></td>
            <td className="px-5 py-3.5 text-right"><button onClick={() => void toggle(user)}
              disabled={user.id === currentUser.id || pendingId === user.id}
              className={`rounded-lg px-3 py-1.5 text-xs font-semibold disabled:cursor-not-allowed disabled:opacity-40 ${user.is_active ? "bg-red-50 text-red-700" : "bg-emerald-50 text-emerald-700"}`}>
              {pendingId === user.id ? "Đang lưu..." : user.is_active ? "Khóa" : "Mở khóa"}</button></td>
          </tr>)}</tbody></table></div>}
      </div>
    </div>
  </div>;
}

function DirectoryScreen({ entries, loading, error, onRefresh }: {
  entries: StaffDirectoryEntry[]; loading: boolean; error: string; onRefresh: () => void;
}) {
  const [search, setSearch] = useState("");
  const filtered = useMemo(() => {
    const query = search.trim().toLocaleLowerCase("vi");
    return query ? entries.filter((entry) =>
      [entry.full_name, entry.position, entry.department, entry.commune_name]
        .some((value) => value?.toLocaleLowerCase("vi").includes(query))) : entries;
  }, [entries, search]);
  return <div className="flex h-full flex-col">
    <div className="flex items-center justify-between border-b border-gray-200 bg-white px-8 py-5">
      <div><h1 className="text-xl font-bold text-gray-900">Danh bạ cán bộ</h1>
        <p className="mt-1 text-sm text-gray-500">Danh bạ trong phạm vi tỉnh được backend cho phép.</p></div>
      <button onClick={onRefresh} disabled={loading}
        className="flex items-center gap-2 rounded-lg border border-gray-200 px-3.5 py-2 text-sm font-semibold text-gray-600 disabled:opacity-50">
        <RefreshCw size={15} className={loading ? "animate-spin" : ""} />Làm mới</button>
    </div>
    <div className="flex-1 overflow-y-auto p-8">
      {error && <div className="mb-4"><Notice kind="error">{error}</Notice></div>}
      <div className="rounded-xl border border-gray-200 bg-white shadow-sm">
        <div className="flex items-center justify-between border-b border-gray-100 px-5 py-4">
          <p className="text-sm font-bold text-gray-800">{entries.length} cán bộ</p>
          <input value={search} onChange={(event) => setSearch(event.target.value)}
            placeholder="Tìm trong danh bạ..."
            className="w-64 rounded-lg border border-gray-200 px-3 py-2 text-xs outline-none focus:border-[#cc1515]" />
        </div>
        {loading && entries.length === 0 ?
          <div className="flex justify-center gap-2 py-20 text-sm text-gray-400"><Loader2 size={18} className="animate-spin" />Đang tải danh bạ...</div>
        : filtered.length === 0 ?
          <div className="py-20 text-center text-sm text-gray-400">Danh bạ chưa có dữ liệu.</div>
        : <div className="grid grid-cols-1 gap-3 p-5 md:grid-cols-2 xl:grid-cols-3">
          {filtered.map((entry, index) => <div key={`${entry.full_name}-${entry.commune_name}-${index}`}
            className="rounded-xl border border-gray-100 bg-gray-50 p-4">
            <div className="flex items-center gap-3"><div className="flex h-10 w-10 items-center justify-center rounded-full bg-[#cc1515] text-xs font-bold text-white">{initials(entry.full_name)}</div>
              <div className="min-w-0"><p className="truncate text-sm font-bold text-gray-900">{entry.full_name}</p><p className="truncate text-xs text-gray-500">{entry.position || "Chưa cập nhật chức vụ"}</p></div></div>
            <div className="mt-3 space-y-1 border-t border-gray-200 pt-3 text-xs text-gray-500">
              <p className="flex items-center gap-2"><Building2 size={13} />{entry.department || "Chưa cập nhật phòng ban"}</p>
              <p className="flex items-center gap-2"><ShieldCheck size={13} />{entry.commune_name}</p>
            </div></div>)}</div>}
      </div>
    </div>
  </div>;
}

function ChangePasswordModal({ onClose, onChanged }: { onClose: () => void; onChanged: () => void }) {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  async function submit(event: React.FormEvent) {
    event.preventDefault(); setError("");
    if (newPassword.length < 12) return setError("Mật khẩu mới phải có ít nhất 12 ký tự.");
    if (newPassword !== confirmPassword) return setError("Mật khẩu xác nhận không khớp.");
    setSubmitting(true);
    try { await changePassword(currentPassword, newPassword); onChanged(); }
    catch (reason) { setError(messageOf(reason)); setSubmitting(false); }
  }
  return <div className="fixed inset-0 z-50 grid place-items-center bg-black/45 p-4" onMouseDown={onClose}>
    <form onSubmit={submit} onMouseDown={(event) => event.stopPropagation()}
      className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl">
      <div className="mb-5 flex items-center justify-between"><div><h2 className="font-bold text-gray-900">Đổi mật khẩu</h2>
        <p className="mt-1 text-xs text-gray-400">Bạn sẽ cần đăng nhập lại sau khi đổi.</p></div>
        <button type="button" onClick={onClose} className="rounded-lg p-2 text-gray-400 hover:bg-gray-100"><X size={17} /></button></div>
      <div className="space-y-4">
        <Field label="Mật khẩu hiện tại" value={currentPassword} onChange={setCurrentPassword} type="password" autoComplete="current-password" />
        <Field label="Mật khẩu mới" value={newPassword} onChange={setNewPassword} type="password" autoComplete="new-password" />
        <Field label="Xác nhận mật khẩu mới" value={confirmPassword} onChange={setConfirmPassword} type="password" autoComplete="new-password" />
        {error && <Notice kind="error">{error}</Notice>}
        <button disabled={submitting} className="flex w-full items-center justify-center gap-2 rounded-lg bg-[#141414] py-2.5 text-sm font-bold text-white disabled:opacity-60">
          {submitting && <Loader2 size={16} className="animate-spin" />}{submitting ? "Đang đổi..." : "Đổi mật khẩu"}</button>
      </div>
    </form>
  </div>;
}

export default function AdminPortal({ currentUser, onLogout }: {
  currentUser: UserPublic;
  onLogout: () => void | Promise<void>;
}) {
  const [screen, setScreen] = useState<Screen>("users");
  const [users, setUsers] = useState<UserPublic[]>([]);
  const [directory, setDirectory] = useState<StaffDirectoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const [userRows, directoryRows] = await Promise.all([
        listAdminUsers(), listStaffDirectory(),
      ]);
      setUsers(userRows); setDirectory(directoryRows);
    } catch (reason) { setError(messageOf(reason)); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { void load(); }, [load]);

  function userCreated(user: UserPublic) {
    setUsers((current) => [...current.filter((item) => item.id !== user.id), user]);
    setSuccess(`Đã tạo tài khoản ${user.username} thành công.`);
    setScreen("users"); void load();
  }

  const navItems: Array<{ id: Screen; label: string; icon: React.ElementType }> = [
    { id: "users", label: "Quản lý tài khoản", icon: Users },
    { id: "create", label: "Thêm tài khoản", icon: UserPlus },
    { id: "directory", label: "Danh bạ cán bộ", icon: Building2 },
  ];

  return <div className="flex h-screen w-screen overflow-hidden bg-[#f4f5f7] font-[Inter,sans-serif]">
    <aside className="flex w-72 flex-shrink-0 flex-col bg-[#141414]">
      <div className="border-b border-white/[0.06] px-5 py-6"><div className="flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#cc1515]"><ShieldCheck size={17} className="text-white" /></div>
        <div><p className="text-sm font-bold text-white">VADS Admin</p><p className="mt-0.5 text-[10px] text-white/40">Dữ liệu quản trị trực tiếp</p></div>
      </div></div>
      <nav className="flex-1 space-y-1 px-3 py-4"><p className="mb-3 px-3 text-[10px] font-semibold uppercase tracking-widest text-white/30">Menu chính</p>
        {navItems.map(({ id, label, icon: Icon }) => <button key={id}
          onClick={() => { setScreen(id); setSuccess(""); }}
          className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition ${screen === id ? "bg-[#cc1515] text-white" : "text-white/60 hover:bg-white/[0.06] hover:text-white"}`}>
          <Icon size={16} />{label}</button>)}</nav>
      <div className="space-y-3 border-t border-white/[0.06] px-5 py-4">
        <div className="flex items-center gap-3"><div className="flex h-9 w-9 items-center justify-center rounded-full bg-[#cc1515]/20 text-[10px] font-bold text-[#ff6b6b]">{initials(currentUser.full_name)}</div>
          <div className="min-w-0"><p className="truncate text-xs font-bold text-white/80">{currentUser.full_name}</p><p className="truncate text-[10px] text-white/35">{currentUser.email}</p></div></div>
        <button onClick={() => setShowPassword(true)} className="flex w-full items-center gap-2 rounded-lg bg-white/[0.06] px-3 py-2 text-xs font-semibold text-white/60 hover:text-white"><LockKeyhole size={13} />Đổi mật khẩu</button>
        <button onClick={() => void onLogout()} className="flex w-full items-center gap-2 rounded-lg bg-[#cc1515] px-3 py-2 text-xs font-bold text-white"><LogOut size={13} />Đăng xuất</button>
      </div>
    </aside>
    <main className="min-w-0 flex-1 overflow-hidden">
      {success && <div className="fixed right-6 top-6 z-40 w-80 shadow-lg"><Notice kind="success">{success}</Notice></div>}
      {screen === "users" && <UsersScreen currentUser={currentUser} users={users}
        directory={directory} loading={loading} error={error} onRefresh={() => void load()}
        onUserChanged={(updated) => setUsers((current) => current.map((user) => user.id === updated.id ? updated : user))} />}
      {screen === "create" && <CreateUserScreen onCreated={userCreated} />}
      {screen === "directory" && <DirectoryScreen entries={directory} loading={loading} error={error} onRefresh={() => void load()} />}
    </main>
    {showPassword && <ChangePasswordModal onClose={() => setShowPassword(false)} onChanged={() => void onLogout()} />}
  </div>;
}
