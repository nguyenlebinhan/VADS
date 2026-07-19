import { useEffect, useState } from "react";
import {
  UserPlus,
  Users,
  Upload,
  Eye,
  EyeOff,
  Pencil,
  ChevronRight,
  X,
  ShieldCheck,
  Phone,
  Mail,
  MapPin,
  User,
  Building2,
  Home,
  Search,
} from "lucide-react";
import {
  changePassword,
  createAdminUser,
  listAdminUsers,
  type UserPublic,
} from "../api";

// ─── Types ───────────────────────────────────────────────────────────────────

interface Account {
  id: string;
  fullName: string;
  email: string;
  phone: string;
  village: string;
  commune: string;
  province: string;
  password: string;
  chucVu: string;
  phongBan: string;
}

type Screen = "add" | "manage";

// ─── Sample Data ─────────────────────────────────────────────────────────────

function accountFromUser(user: UserPublic): Account {
  return {
    id: user.id,
    fullName: user.full_name,
    email: user.email,
    phone: "—",
    village: "—",
    commune: user.commune_id,
    province: "Đơn vị quản lý",
    password: "Được bảo mật",
    chucVu: user.position ?? "—",
    phongBan: user.department ?? "—",
  };
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function groupByProvince(accounts: Account[]) {
  const map: Record<string, Record<string, Account[]>> = {};
  for (const acc of accounts) {
    if (!map[acc.province]) map[acc.province] = {};
    if (!map[acc.province][acc.commune]) map[acc.province][acc.commune] = [];
    map[acc.province][acc.commune].push(acc);
  }
  return map;
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function FormField({
  label,
  id,
  type = "text",
  placeholder,
  value,
  onChange,
  icon: Icon,
  suffix,
}: {
  label: string;
  id: string;
  type?: string;
  placeholder: string;
  value: string;
  onChange: (v: string) => void;
  icon?: React.ElementType;
  suffix?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-sm font-medium text-foreground">
        {label}
      </label>
      <div className="relative flex items-center">
        {Icon && (
          <Icon size={15} className="absolute left-3 text-muted-foreground pointer-events-none" />
        )}
        <input
          id={id}
          type={type}
          placeholder={placeholder}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className={`w-full h-10 rounded-md border border-border bg-white text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-[#cc1515]/30 focus:border-[#cc1515] transition-all ${Icon ? "pl-9" : "pl-3"} ${suffix ? "pr-10" : "pr-3"}`}
        />
        {suffix && <div className="absolute right-3">{suffix}</div>}
      </div>
    </div>
  );
}

function PasswordField({
  label,
  id,
  placeholder,
  value,
  onChange,
}: {
  label: string;
  id: string;
  placeholder: string;
  value: string;
  onChange: (v: string) => void;
}) {
  const [show, setShow] = useState(false);
  return (
    <FormField
      label={label}
      id={id}
      type={show ? "text" : "password"}
      placeholder={placeholder}
      value={value}
      onChange={onChange}
      icon={ShieldCheck}
      suffix={
        <button
          type="button"
          onClick={() => setShow((s) => !s)}
          className="text-muted-foreground hover:text-foreground transition-colors"
        >
          {show ? <EyeOff size={15} /> : <Eye size={15} />}
        </button>
      }
    />
  );
}

// ─── Screen 1: Add Account ────────────────────────────────────────────────────

function AddAccountScreen({ onAdd }: { onAdd: (acc: Account) => Promise<boolean> }) {
  const [form, setForm] = useState({
    fullName: "", email: "", phone: "", village: "", commune: "", province: "", password: "", confirmPassword: "", chucVu: "", phongBan: "",
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [success, setSuccess] = useState(false);

  function set(key: string) {
    return (val: string) => setForm((f) => ({ ...f, [key]: val }));
  }

  function validate() {
    const e: Record<string, string> = {};
    if (!form.fullName.trim()) e.fullName = "Vui lòng nhập họ và tên";
    if (!form.email.trim() || !/\S+@\S+\.\S+/.test(form.email)) e.email = "Email không hợp lệ";
    if (!form.phone.trim() || !/^0\d{9}$/.test(form.phone)) e.phone = "Số điện thoại không hợp lệ";
    if (!form.village.trim()) e.village = "Vui lòng nhập thôn";
    if (!form.commune.trim()) e.commune = "Vui lòng nhập xã";
    if (!form.province.trim()) e.province = "Vui lòng nhập tỉnh";
    if (form.password.length < 6) e.password = "Mật khẩu tối thiểu 6 ký tự";
    if (form.password !== form.confirmPassword) e.confirmPassword = "Mật khẩu không khớp";
    return e;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const errs = validate();
    setErrors(errs);
    if (Object.keys(errs).length > 0) return;

    const newAcc: Account = {
      id: `USR${String(Date.now()).slice(-4)}`,
      fullName: form.fullName,
      email: form.email,
      phone: form.phone,
      village: form.village,
      commune: form.commune,
      province: form.province,
      password: form.password,
      chucVu: form.chucVu,
      phongBan: form.phongBan,
    };
    if (!await onAdd(newAcc)) return;
    setSuccess(true);
    setForm({ fullName: "", email: "", phone: "", village: "", commune: "", province: "", password: "", confirmPassword: "" });
    setTimeout(() => setSuccess(false), 3000);
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-8 py-5 border-b border-border bg-white">
        <div>
          <h1 className="text-xl font-semibold text-foreground">Thêm tài khoản</h1>
          <p className="text-sm text-muted-foreground mt-0.5">Tạo mới tài khoản người dùng trong hệ thống</p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 rounded-md border border-border bg-white hover:bg-muted text-sm font-medium text-foreground transition-colors">
          <Upload size={15} />
          Import tài liệu (.csv)
        </button>
      </div>

      {/* Form */}
      <div className="flex-1 overflow-y-auto p-8">
        {success && (
          <div className="mb-6 flex items-center gap-3 px-4 py-3 rounded-md bg-green-50 border border-green-200 text-green-700 text-sm font-medium">
            <ShieldCheck size={16} />
            Tài khoản đã được tạo thành công!
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="bg-white rounded-xl border border-border shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-border bg-[#fafafa]">
              <h2 className="text-sm font-semibold text-foreground uppercase tracking-wider">Thông tin tài khoản</h2>
            </div>

            <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-5">
              {/* Full Name */}
              <div>
                <FormField label="Họ và tên" id="fullName" placeholder="Nguyễn Văn A" value={form.fullName} onChange={set("fullName")} icon={User} />
                {errors.fullName && <p className="mt-1 text-xs text-[#cc1515]">{errors.fullName}</p>}
              </div>

              {/* Email */}
              <div>
                <FormField label="Email" id="email" type="email" placeholder="example@email.com" value={form.email} onChange={set("email")} icon={Mail} />
                {errors.email && <p className="mt-1 text-xs text-[#cc1515]">{errors.email}</p>}
              </div>

              {/* Phone */}
              <div>
                <FormField label="Số điện thoại" id="phone" placeholder="0912345678" value={form.phone} onChange={set("phone")} icon={Phone} />
                {errors.phone && <p className="mt-1 text-xs text-[#cc1515]">{errors.phone}</p>}
              </div>

              {/* Province */}
              <div>
                <FormField label="Tỉnh / Thành phố" id="province" placeholder="Hà Nội" value={form.province} onChange={set("province")} icon={Building2} />
                {errors.province && <p className="mt-1 text-xs text-[#cc1515]">{errors.province}</p>}
              </div>

              {/* Commune */}
              <div>
                <FormField label="Xã / Phường" id="commune" placeholder="Xã Hòa Bình" value={form.commune} onChange={set("commune")} icon={MapPin} />
                {errors.commune && <p className="mt-1 text-xs text-[#cc1515]">{errors.commune}</p>}
              </div>

              {/* Village */}
              <div>
                <FormField label="Thôn / Xóm" id="village" placeholder="Thôn Đông" value={form.village} onChange={set("village")} icon={Home} />
                {errors.village && <p className="mt-1 text-xs text-[#cc1515]">{errors.village}</p>}
              </div>

              {/* Chức vụ */}
              <div>
                <FormField label="Chức vụ" id="chucVu" placeholder="Trưởng phòng, Nhân viên..." value={form.chucVu} onChange={set("chucVu")} icon={ShieldCheck} />
              </div>

              {/* Phòng ban */}
              <div>
                <FormField label="Phòng ban" id="phongBan" placeholder="Phòng Kỹ thuật, Phòng Nhân sự..." value={form.phongBan} onChange={set("phongBan")} icon={Building2} />
              </div>
            </div>

            <div className="px-6 pb-6 pt-1 border-t border-border mt-2">
              <div className="px-6 py-4 -mx-6 -mt-1 mb-5 bg-[#fafafa] border-b border-border">
                <h2 className="text-sm font-semibold text-foreground uppercase tracking-wider">Bảo mật</h2>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                <div>
                  <PasswordField label="Mật khẩu" id="password" placeholder="Tối thiểu 6 ký tự" value={form.password} onChange={set("password")} />
                  {errors.password && <p className="mt-1 text-xs text-[#cc1515]">{errors.password}</p>}
                </div>
                <div>
                  <PasswordField label="Nhập lại mật khẩu" id="confirmPassword" placeholder="Xác nhận mật khẩu" value={form.confirmPassword} onChange={set("confirmPassword")} />
                  {errors.confirmPassword && <p className="mt-1 text-xs text-[#cc1515]">{errors.confirmPassword}</p>}
                </div>
              </div>
            </div>
          </div>

          <div className="mt-6 flex justify-end">
            <button
              type="submit"
              className="flex items-center gap-2 px-6 py-2.5 rounded-md bg-[#cc1515] hover:bg-[#b31212] text-white text-sm font-semibold transition-colors shadow-sm"
            >
              <UserPlus size={15} />
              Thêm tài khoản
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ─── Screen 2: Manage Accounts (drill-down) ──────────────────────────────────

type ManageLevel =
  | { view: "provinces" }
  | { view: "communes"; province: string }
  | { view: "table"; province: string; commune: string };

function DetailModal({ account, onClose }: { account: Account; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" />
      <div
        className="relative bg-white rounded-xl shadow-2xl w-full max-w-md overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 bg-[#141414]">
          <div>
            <h3 className="text-base font-semibold text-white">Chi tiết tài khoản</h3>
            <p className="text-xs text-white/50 mt-0.5">ID: {account.id}</p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-md text-white/50 hover:text-white hover:bg-white/10 transition-colors"
          >
            <X size={16} />
          </button>
        </div>

        {/* Avatar Area */}
        <div className="flex flex-col items-center pt-6 pb-4 border-b border-border">
          <div className="w-16 h-16 rounded-full bg-[#cc1515] flex items-center justify-center text-white text-2xl font-bold shadow-md">
            {account.fullName.charAt(0)}
          </div>
          <p className="mt-3 text-base font-semibold text-foreground">{account.fullName}</p>
          <p className="text-sm text-muted-foreground">{account.email}</p>
        </div>

        {/* Detail Rows */}
        <div className="px-6 py-4 space-y-3">
          {[
            { icon: User, label: "Họ và tên", value: account.fullName },
            { icon: Mail, label: "Email", value: account.email },
            { icon: Phone, label: "Số điện thoại", value: account.phone },
            { icon: ShieldCheck, label: "Chức vụ", value: account.chucVu || "—" },
            { icon: Building2, label: "Phòng ban", value: account.phongBan || "—" },
            { icon: Home, label: "Thôn", value: account.village },
            { icon: MapPin, label: "Xã / Phường", value: account.commune },
            { icon: Building2, label: "Tỉnh / Thành phố", value: account.province },
          ].map(({ icon: Icon, label, value }) => (
            <div key={label} className="flex items-start gap-3">
              <div className="mt-0.5 p-1.5 rounded bg-[#f4f5f7]">
                <Icon size={13} className="text-[#cc1515]" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs text-muted-foreground font-medium">{label}</p>
                <p className="text-sm text-foreground font-medium truncate">{value}</p>
              </div>
            </div>
          ))}
        </div>

        <div className="px-6 pb-5">
          <button
            onClick={onClose}
            className="w-full py-2.5 rounded-md bg-[#141414] hover:bg-[#1e1e1e] text-white text-sm font-semibold transition-colors"
          >
            Đóng
          </button>
        </div>
      </div>
    </div>
  );
}

function EditModal({ account, onClose, onSave }: { account: Account; onClose: () => void; onSave: (acc: Account) => void }) {
  const [form, setForm] = useState({ ...account });

  function set(key: keyof Account) {
    return (val: string) => setForm((f) => ({ ...f, [key]: val }));
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" />
      <div
        className="relative bg-white rounded-xl shadow-2xl w-full max-w-lg overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-6 py-4 bg-[#141414]">
          <div>
            <h3 className="text-base font-semibold text-white">Sửa đổi tài khoản</h3>
            <p className="text-xs text-white/50 mt-0.5">ID: {account.id}</p>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-md text-white/50 hover:text-white hover:bg-white/10 transition-colors">
            <X size={16} />
          </button>
        </div>

        <div className="p-6 grid grid-cols-1 sm:grid-cols-2 gap-4 max-h-[70vh] overflow-y-auto">
          <FormField label="Họ và tên" id="edit-fullName" placeholder="Họ và tên" value={form.fullName} onChange={set("fullName")} icon={User} />
          <FormField label="Email" id="edit-email" type="email" placeholder="Email" value={form.email} onChange={set("email")} icon={Mail} />
          <FormField label="Số điện thoại" id="edit-phone" placeholder="Số điện thoại" value={form.phone} onChange={set("phone")} icon={Phone} />
          <FormField label="Tỉnh / Thành phố" id="edit-province" placeholder="Tỉnh" value={form.province} onChange={set("province")} icon={Building2} />
          <FormField label="Xã / Phường" id="edit-commune" placeholder="Xã" value={form.commune} onChange={set("commune")} icon={MapPin} />
          <FormField label="Thôn / Xóm" id="edit-village" placeholder="Thôn" value={form.village} onChange={set("village")} icon={Home} />
          <FormField label="Chức vụ" id="edit-chucVu" placeholder="Chức vụ" value={form.chucVu} onChange={set("chucVu")} icon={ShieldCheck} />
          <FormField label="Phòng ban" id="edit-phongBan" placeholder="Phòng ban" value={form.phongBan} onChange={set("phongBan")} icon={Building2} />
        </div>

        <div className="px-6 pb-5 flex gap-3">
          <button onClick={onClose} className="flex-1 py-2.5 rounded-md border border-border text-sm font-medium text-foreground hover:bg-muted transition-colors">
            Hủy
          </button>
          <button
            onClick={() => { onSave(form); onClose(); }}
            className="flex-1 py-2.5 rounded-md bg-[#cc1515] hover:bg-[#b31212] text-white text-sm font-semibold transition-colors"
          >
            Lưu thay đổi
          </button>
        </div>
      </div>
    </div>
  );
}


// ─── Province List View ───────────────────────────────────────────────────────

function ProvinceListView({
  grouped,
  totalAccounts,
  onSelect,
}: {
  grouped: Record<string, Record<string, Account[]>>;
  totalAccounts: number;
  onSelect: (province: string) => void;
}) {
  const [search, setSearch] = useState("");
  const allProvinces = Object.keys(grouped).sort((a, b) => a.localeCompare(b, "vi"));
  const sortedProvinces = search.trim()
    ? allProvinces.filter((p) => p.toLowerCase().includes(search.toLowerCase()))
    : allProvinces;

  return (
    <div className="flex flex-col h-full">
      <div className="px-8 py-5 border-b border-border bg-white flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-foreground">Quản lý tài khoản</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            {allProvinces.length} tỉnh · {totalAccounts} tài khoản
          </p>
        </div>
        <div className="relative">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            placeholder="Tìm kiếm tỉnh / thành phố..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 pr-4 py-2 w-64 rounded-md border border-border bg-white text-sm focus:outline-none focus:ring-2 focus:ring-[#cc1515]/30 focus:border-[#cc1515] transition-all"
          />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-8 py-6">
        {sortedProvinces.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-24 text-muted-foreground">
            <Search size={36} className="mb-3 opacity-20" />
            <p className="text-sm">Không tìm thấy tỉnh nào phù hợp</p>
          </div>
        ) : (
        <div className="bg-white rounded-xl border border-border shadow-sm overflow-hidden">
          {sortedProvinces.map((province, idx) => {
            const communeCount = Object.keys(grouped[province]).length;
            const accountCount = Object.values(grouped[province]).flat().length;
            const isLast = idx === sortedProvinces.length - 1;

            return (
              <div key={province}>
                <button
                  onClick={() => onSelect(province)}
                  className="w-full flex items-center gap-4 px-6 py-4 hover:bg-[#f9f9fb] transition-colors text-left group"
                >
                  {/* Province icon */}
                  <div className="w-10 h-10 rounded-lg bg-[#141414] flex items-center justify-center flex-shrink-0 group-hover:bg-[#cc1515] transition-colors">
                    <Building2 size={17} className="text-white" />
                  </div>

                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-foreground">{province}</p>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {communeCount} xã / phường · {accountCount} tài khoản
                    </p>
                  </div>

                  {/* Badges */}
                  <div className="flex items-center gap-3 flex-shrink-0">
                    <span className="text-xs px-2.5 py-1 rounded-full bg-[#f0f1f3] text-muted-foreground font-medium">
                      {communeCount} xã
                    </span>
                    <span className="text-xs px-2.5 py-1 rounded-full bg-[#cc1515]/10 text-[#cc1515] font-semibold">
                      {accountCount}
                    </span>
                    <ChevronRight size={15} className="text-muted-foreground group-hover:text-[#cc1515] transition-colors" />
                  </div>
                </button>

                {!isLast && <div className="mx-6 h-px bg-border" />}
              </div>
            );
          })}
        </div>
        )}
      </div>
    </div>
  );
}

// ─── Commune List View ────────────────────────────────────────────────────────

function CommuneListView({
  province,
  communes,
  onBack,
  onSelect,
}: {
  province: string;
  communes: Record<string, Account[]>;
  onBack: () => void;
  onSelect: (commune: string) => void;
}) {
  const [search, setSearch] = useState("");
  const allCommunes = Object.keys(communes).sort((a, b) => a.localeCompare(b, "vi"));
  const sortedCommunes = search.trim()
    ? allCommunes.filter((c) => c.toLowerCase().includes(search.toLowerCase()))
    : allCommunes;

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-8 py-5 border-b border-border bg-white">
        <button
          onClick={onBack}
          className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-[#cc1515] transition-colors mb-3 font-medium"
        >
          <ChevronRight size={13} className="rotate-180" />
          Danh sách tỉnh
        </button>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-[#141414] flex items-center justify-center">
              <Building2 size={16} className="text-white" />
            </div>
            <div>
              <h1 className="text-xl font-semibold text-foreground">{province}</h1>
              <p className="text-sm text-muted-foreground mt-0.5">{allCommunes.length} xã / phường</p>
            </div>
          </div>
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <input
              type="text"
              placeholder="Tìm kiếm xã / phường..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9 pr-4 py-2 w-60 rounded-md border border-border bg-white text-sm focus:outline-none focus:ring-2 focus:ring-[#cc1515]/30 focus:border-[#cc1515] transition-all"
            />
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-8 py-6">
        {sortedCommunes.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-24 text-muted-foreground">
            <Search size={36} className="mb-3 opacity-20" />
            <p className="text-sm">Không tìm thấy xã / phường nào phù hợp</p>
          </div>
        ) : (
          <div className="bg-white rounded-xl border border-border shadow-sm overflow-hidden">
            {sortedCommunes.map((commune, idx) => {
              const accountCount = communes[commune].length;
              const isLast = idx === sortedCommunes.length - 1;

              return (
                <div key={commune}>
                  <button
                    onClick={() => onSelect(commune)}
                    className="w-full flex items-center gap-4 px-6 py-4 hover:bg-[#f9f9fb] transition-colors text-left group"
                  >
                    <div className="w-10 h-10 rounded-lg bg-[#f0f1f3] flex items-center justify-center flex-shrink-0 group-hover:bg-[#cc1515]/10 transition-colors">
                      <MapPin size={16} className="text-muted-foreground group-hover:text-[#cc1515] transition-colors" />
                    </div>

                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-semibold text-foreground">{commune}</p>
                      <p className="text-xs text-muted-foreground mt-0.5">{accountCount} tài khoản</p>
                    </div>

                    <div className="flex items-center gap-3 flex-shrink-0">
                      <span className="text-xs px-2.5 py-1 rounded-full bg-[#cc1515]/10 text-[#cc1515] font-semibold">
                        {accountCount}
                      </span>
                      <ChevronRight size={15} className="text-muted-foreground group-hover:text-[#cc1515] transition-colors" />
                    </div>
                  </button>
                  {!isLast && <div className="mx-6 h-px bg-border" />}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Table View ───────────────────────────────────────────────────────────────

function TableView({
  province,
  commune,
  accounts,
  onBack,
  onUpdateAccount,
}: {
  province: string;
  commune: string;
  accounts: Account[];
  onBack: () => void;
  onUpdateAccount: (acc: Account) => void;
}) {
  const [search, setSearch] = useState("");
  const [viewAccount, setViewAccount] = useState<Account | null>(null);
  const [editAccount, setEditAccount] = useState<Account | null>(null);
  const [visiblePasswords, setVisiblePasswords] = useState<Set<string>>(new Set());

  function togglePassword(id: string) {
    setVisiblePasswords((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  const filtered = search.trim()
    ? accounts.filter(
        (a) =>
          a.fullName.toLowerCase().includes(search.toLowerCase()) ||
          a.email.toLowerCase().includes(search.toLowerCase()) ||
          a.id.toLowerCase().includes(search.toLowerCase())
      )
    : accounts;

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-8 py-5 border-b border-border bg-white">
        <button
          onClick={onBack}
          className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-[#cc1515] transition-colors mb-3 font-medium"
        >
          <ChevronRight size={13} className="rotate-180" />
          {province}
        </button>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-[#f0f1f3] flex items-center justify-center">
              <MapPin size={16} className="text-[#cc1515]" />
            </div>
            <div>
              <h1 className="text-xl font-semibold text-foreground">{commune}</h1>
              <p className="text-sm text-muted-foreground mt-0.5">{accounts.length} tài khoản</p>
            </div>
          </div>
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <input
              type="text"
              placeholder="Tìm kiếm..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9 pr-4 py-2 w-52 rounded-md border border-border bg-white text-sm focus:outline-none focus:ring-2 focus:ring-[#cc1515]/30 focus:border-[#cc1515] transition-all"
            />
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-8 py-6">
        <div className="bg-white rounded-xl border border-border shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-[#f4f5f7] border-b border-border">
                  <th className="text-left px-5 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider w-24">ID</th>
                  <th className="text-left px-5 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Họ và tên</th>
                  <th className="text-left px-5 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Email</th>
                  <th className="text-left px-5 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Mật khẩu</th>
                  <th className="text-center px-5 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider w-28">Chi tiết</th>
                  <th className="text-center px-5 py-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider w-28">Sửa đổi</th>
                </tr>
              </thead>
              <tbody>
                {filtered.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-5 py-16 text-center text-muted-foreground text-sm">
                      Không tìm thấy tài khoản nào
                    </td>
                  </tr>
                ) : (
                  filtered.map((acc, idx) => (
                    <tr
                      key={acc.id}
                      className={`border-b border-border hover:bg-[#fafafa] transition-colors ${idx % 2 === 0 ? "bg-white" : "bg-[#fdfdfd]"}`}
                    >
                      <td className="px-5 py-3.5">
                        <span className="font-mono text-xs px-2 py-0.5 rounded bg-[#f0f1f3] text-muted-foreground">{acc.id}</span>
                      </td>
                      <td className="px-5 py-3.5">
                        <div className="flex items-center gap-2.5">
                          <div className="w-7 h-7 rounded-full bg-[#cc1515] flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
                            {acc.fullName.charAt(0)}
                          </div>
                          <span className="font-medium text-foreground">{acc.fullName}</span>
                        </div>
                      </td>
                      <td className="px-5 py-3.5 text-muted-foreground">{acc.email}</td>
                      <td className="px-5 py-3.5">
                        <div className="flex items-center gap-2">
                          <span className={`font-mono text-sm text-foreground ${!visiblePasswords.has(acc.id) ? "tracking-[0.3em] text-muted-foreground text-base" : ""}`}>
                            {visiblePasswords.has(acc.id) ? acc.password : "••••••••"}
                          </span>
                          <button
                            onClick={() => togglePassword(acc.id)}
                            className="text-muted-foreground hover:text-[#cc1515] transition-colors flex-shrink-0"
                            title={visiblePasswords.has(acc.id) ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
                          >
                            {visiblePasswords.has(acc.id) ? <EyeOff size={14} /> : <Eye size={14} />}
                          </button>
                        </div>
                      </td>
                      <td className="px-5 py-3.5 text-center">
                        <button
                          onClick={() => setViewAccount(acc)}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium text-[#cc1515] bg-red-50 hover:bg-red-100 transition-colors"
                        >
                          <Eye size={13} />
                          Xem
                        </button>
                      </td>
                      <td className="px-5 py-3.5 text-center">
                        <button
                          onClick={() => setEditAccount(acc)}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium text-[#141414] bg-[#f0f1f3] hover:bg-[#e5e6e8] transition-colors"
                        >
                          <Pencil size={13} />
                          Sửa
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {viewAccount && <DetailModal account={viewAccount} onClose={() => setViewAccount(null)} />}
      {editAccount && (
        <EditModal
          account={editAccount}
          onClose={() => setEditAccount(null)}
          onSave={(updated) => { onUpdateAccount(updated); setEditAccount(null); }}
        />
      )}
    </div>
  );
}

// ─── Manage Accounts Shell ────────────────────────────────────────────────────

function ManageAccountsScreen({
  accounts,
  onUpdateAccount,
}: {
  accounts: Account[];
  onUpdateAccount: (acc: Account) => void;
}) {
  const [level, setLevel] = useState<ManageLevel>({ view: "provinces" });
  const grouped = groupByProvince(accounts);

  if (level.view === "provinces") {
    return (
      <ProvinceListView
        grouped={grouped}
        totalAccounts={accounts.length}
        onSelect={(province) => setLevel({ view: "communes", province })}
      />
    );
  }

  if (level.view === "communes") {
    return (
      <CommuneListView
        province={level.province}
        communes={grouped[level.province] ?? {}}
        onBack={() => setLevel({ view: "provinces" })}
        onSelect={(commune) => setLevel({ view: "table", province: level.province, commune })}
      />
    );
  }

  return (
    <TableView
      province={level.province}
      commune={level.commune}
      accounts={(grouped[level.province] ?? {})[level.commune] ?? []}
      onBack={() => setLevel({ view: "communes", province: level.province })}
      onUpdateAccount={onUpdateAccount}
    />
  );
}

// ─── Change Password Modal ────────────────────────────────────────────────────

function ChangePasswordModal({ onClose, onChanged }: { onClose: () => void; onChanged: () => void }) {
  const [form, setForm] = useState({ current: "", next: "", confirm: "" });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [success, setSuccess] = useState(false);
  const [showCurrent, setShowCurrent] = useState(false);
  const [showNext, setShowNext] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  function validate() {
    const e: Record<string, string> = {};
    if (!form.current) e.current = "Vui lòng nhập mật khẩu hiện tại";
    if (form.next.length < 6) e.next = "Mật khẩu mới tối thiểu 6 ký tự";
    if (form.next !== form.confirm) e.confirm = "Mật khẩu xác nhận không khớp";
    return e;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const errs = validate();
    setErrors(errs);
    if (Object.keys(errs).length > 0) return;
    try {
      await changePassword(form.current, form.next);
      setSuccess(true);
      setTimeout(() => { setSuccess(false); onClose(); onChanged(); }, 1800);
    } catch (reason) {
      setErrors({ current: reason instanceof Error ? reason.message : "Không thể đổi mật khẩu." });
    }
  }

  function PwField({
    id, label, value, show, onToggle, onChange, error,
  }: {
    id: string; label: string; value: string; show: boolean;
    onToggle: () => void; onChange: (v: string) => void; error?: string;
  }) {
    return (
      <div>
        <label htmlFor={id} className="block text-sm font-medium text-foreground mb-1.5">{label}</label>
        <div className="relative flex items-center">
          <ShieldCheck size={15} className="absolute left-3 text-muted-foreground pointer-events-none" />
          <input
            id={id}
            type={show ? "text" : "password"}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            className="w-full h-10 pl-9 pr-10 rounded-md border border-border bg-white text-sm focus:outline-none focus:ring-2 focus:ring-[#cc1515]/30 focus:border-[#cc1515] transition-all"
          />
          <button type="button" onClick={onToggle} className="absolute right-3 text-muted-foreground hover:text-foreground transition-colors">
            {show ? <EyeOff size={14} /> : <Eye size={14} />}
          </button>
        </div>
        {error && <p className="mt-1 text-xs text-[#cc1515]">{error}</p>}
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" />
      <div className="relative bg-white rounded-xl shadow-2xl w-full max-w-sm overflow-hidden" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between px-6 py-4 bg-[#141414]">
          <div>
            <h3 className="text-base font-semibold text-white">Đổi mật khẩu</h3>
            <p className="text-xs text-white/40 mt-0.5">Administrator</p>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-md text-white/50 hover:text-white hover:bg-white/10 transition-colors">
            <X size={16} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="px-6 py-5 space-y-4">
          {success && (
            <div className="flex items-center gap-2 px-3 py-2.5 rounded-md bg-green-50 border border-green-200 text-green-700 text-sm font-medium">
              <ShieldCheck size={15} />
              Đổi mật khẩu thành công!
            </div>
          )}

          <PwField id="cp-current" label="Mật khẩu hiện tại" value={form.current} show={showCurrent}
            onToggle={() => setShowCurrent((s) => !s)} onChange={(v) => setForm((f) => ({ ...f, current: v }))} error={errors.current} />
          <PwField id="cp-next" label="Mật khẩu mới" value={form.next} show={showNext}
            onToggle={() => setShowNext((s) => !s)} onChange={(v) => setForm((f) => ({ ...f, next: v }))} error={errors.next} />
          <PwField id="cp-confirm" label="Xác nhận mật khẩu mới" value={form.confirm} show={showConfirm}
            onToggle={() => setShowConfirm((s) => !s)} onChange={(v) => setForm((f) => ({ ...f, confirm: v }))} error={errors.confirm} />

          <div className="flex gap-3 pt-1">
            <button type="button" onClick={onClose} className="flex-1 py-2.5 rounded-md border border-border text-sm font-medium text-foreground hover:bg-muted transition-colors">
              Hủy
            </button>
            <button type="submit" className="flex-1 py-2.5 rounded-md bg-[#cc1515] hover:bg-[#b31212] text-white text-sm font-semibold transition-colors">
              Xác nhận
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ─── App Shell ────────────────────────────────────────────────────────────────

export default function AdminPortal({ currentUser, onLogout }: { currentUser: UserPublic; onLogout: () => void }) {
  const [screen, setScreen] = useState<Screen>("add");
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [showChangePassword, setShowChangePassword] = useState(false);

  useEffect(() => {
    let cancelled = false;
    void listAdminUsers()
      .then(users => {
        if (!cancelled) setAccounts(users.map(accountFromUser));
      })
      .catch(reason => {
        if (!cancelled) window.alert(reason instanceof Error ? reason.message : "Không thể tải danh sách tài khoản.");
      });
    return () => { cancelled = true; };
  }, []);

  async function addAccount(acc: Account): Promise<boolean> {
    try {
      const username = acc.email.split("@")[0].toLocaleLowerCase("vi").replace(/[^a-z0-9._-]/g, "");
      const created = await createAdminUser({
        username,
        email: acc.email,
        full_name: acc.fullName,
        position: acc.chucVu || null,
        department: acc.phongBan || null,
        temporary_password: acc.password,
      });
      setAccounts((prev) => [...prev, accountFromUser(created)]);
      return true;
    } catch (reason) {
      window.alert(reason instanceof Error ? reason.message : "Không thể tạo tài khoản.");
      return false;
    }
  }

  function updateAccount(updated: Account) {
    setAccounts((prev) => prev.map((a) => (a.id === updated.id ? updated : a)));
  }

  const navItems: { id: Screen; label: string; icon: React.ElementType }[] = [
    { id: "add", label: "Thêm tài khoản", icon: UserPlus },
    { id: "manage", label: "Quản lý tài khoản", icon: Users },
  ];

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-background font-[Inter,sans-serif]">
      {/* Sidebar */}
      <aside className="w-72 flex-shrink-0 bg-[#141414] flex flex-col">
        {/* Brand */}
        <div className="px-5 py-6 border-b border-white/[0.06]">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-[#cc1515] flex items-center justify-center flex-shrink-0">
              <ShieldCheck size={16} className="text-white" />
            </div>
            <div>
              <p className="text-sm font-bold text-white leading-tight">AdminPortal</p>
              <p className="text-[10px] text-white/40 mt-0.5">Hệ thống quản lý</p>
            </div>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-1">
          <p className="text-[10px] font-semibold text-white/30 uppercase tracking-widest px-3 mb-3">Menu chính</p>
          {navItems.map(({ id, label, icon: Icon }) => {
            const active = screen === id;
            return (
              <button
                key={id}
                onClick={() => setScreen(id)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                  active
                    ? "bg-[#cc1515] text-white shadow-md shadow-[#cc1515]/20"
                    : "text-white/60 hover:text-white hover:bg-white/[0.06]"
                }`}
              >
                <Icon size={16} />
                {label}
              </button>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="px-5 py-4 border-t border-white/[0.06] space-y-3">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-full bg-[#cc1515]/20 flex items-center justify-center flex-shrink-0">
              <User size={14} className="text-[#cc1515]" />
            </div>
            <div className="min-w-0">
              <p className="text-xs font-semibold text-white/80 truncate">{currentUser.full_name}</p>
              <p className="text-[10px] text-white/30 truncate">{currentUser.email}</p>
            </div>
          </div>
          <button
            onClick={() => setShowChangePassword(true)}
            className="w-full flex items-center gap-2 px-3 py-2 rounded-md bg-white/[0.06] hover:bg-white/[0.10] text-white/60 hover:text-white text-xs font-medium transition-colors"
          >
            <ShieldCheck size={13} />
            Đổi mật khẩu
          </button>
          <button onClick={onLogout} className="w-full px-3 py-2 rounded-md bg-[#cc1515] hover:bg-[#b31212] text-white text-xs font-semibold transition-colors">Đăng xuất</button>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 min-w-0 overflow-hidden flex flex-col">
        {screen === "add" && <AddAccountScreen onAdd={addAccount} />}
        {screen === "manage" && (
          <ManageAccountsScreen accounts={accounts} onUpdateAccount={updateAccount} />
        )}
      </main>

      {showChangePassword && <ChangePasswordModal onClose={() => setShowChangePassword(false)} onChanged={onLogout} />}
    </div>
  );
}
