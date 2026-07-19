import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  AlertCircle, Bell, Brain, CheckCircle2, FileText, LayoutDashboard,
  Loader2, Lock, LogOut, Menu, MessageSquare, Network, RefreshCw, RotateCcw,
  Scale, Search, Send, Trash2, Upload, X,
} from 'lucide-react';

import {
  changePassword, deleteDocument, listDocuments, queryDocumentRag,
  reprocessDocument, uploadDocument, type DocumentPublic, type RagQueryResult,
  type UserPublic,
} from '../api';
import { passwordStrengthError } from '../password';
import KnowledgeGraphScreen from './KnowledgeGraphScreen';
import RegulatoryIntelligence from './RegulatoryIntelligence';

type Screen = 'dashboard' | 'documents' | 'regulatory' | 'knowledge-graph' | 'assistant';
type NoticeKind = 'error' | 'success' | 'info';

interface NoticeState {
  kind: NoticeKind;
  message: string;
}

interface ChatMessage {
  id: string;
  role: 'assistant' | 'user';
  text: string;
  retrievalMode?: string;
  sources?: RagQueryResult['sources'];
}

const STATUS_LABELS: Record<DocumentPublic['status'], string> = {
  UPLOADED: 'Đã tải lên', QUEUED: 'Đang chờ', PROCESSING: 'Đang xử lý',
  COMPLETED: 'Hoàn tất', FAILED: 'Xử lý lỗi', CANCELLED: 'Đã hủy',
  NEEDS_REVIEW: 'Cần kiểm tra',
};

const STATUS_STYLES: Record<DocumentPublic['status'], string> = {
  UPLOADED: 'bg-sky-50 text-sky-700', QUEUED: 'bg-violet-50 text-violet-700',
  PROCESSING: 'bg-amber-50 text-amber-700', COMPLETED: 'bg-emerald-50 text-emerald-700',
  FAILED: 'bg-red-50 text-red-700', CANCELLED: 'bg-gray-100 text-gray-600',
  NEEDS_REVIEW: 'bg-orange-50 text-orange-700',
};

const APPROVAL_LABELS: Record<DocumentPublic['approval_status'], string> = {
  DRAFT: 'Bản nháp', PENDING_APPROVAL: 'Chờ duyệt',
  APPROVED: 'Đã duyệt', REJECTED: 'Từ chối',
};

const PROCESSING_STATUSES = new Set<DocumentPublic['status']>([
  'UPLOADED', 'QUEUED', 'PROCESSING',
]);

const RAG_READY_STATUSES = new Set<DocumentPublic['status']>([
  'COMPLETED', 'NEEDS_REVIEW',
]);

const NAV_ITEMS: Array<{ id: Screen; label: string; icon: React.ElementType }> = [
  { id: 'dashboard', label: 'Tổng quan', icon: LayoutDashboard },
  { id: 'documents', label: 'Tài liệu', icon: FileText },
  { id: 'regulatory', label: 'Thay đổi pháp lý', icon: Scale },
  { id: 'knowledge-graph', label: 'Đồ thị tri thức', icon: Network },
  { id: 'assistant', label: 'Trợ lý AI', icon: MessageSquare },
];

function messageOf(reason: unknown): string {
  return reason instanceof Error ? reason.message : 'Không thể kết nối tới máy chủ.';
}

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'Không có ngày';
  return new Intl.DateTimeFormat('vi-VN', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  }).format(date);
}

function initials(name: string): string {
  const words = name.trim().split(/\s+/).filter(Boolean);
  if (words.length === 0) return 'U';
  if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
  return `${words[0][0]}${words.at(-1)?.[0] ?? ''}`.toUpperCase();
}

function Notice({ notice, onClose }: { notice: NoticeState; onClose?: () => void }) {
  const Icon = notice.kind === 'success' ? CheckCircle2 : AlertCircle;
  const styles = notice.kind === 'success'
    ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
    : notice.kind === 'error'
      ? 'border-red-200 bg-red-50 text-red-700'
      : 'border-sky-200 bg-sky-50 text-sky-700';
  return (
    <div className={`flex items-start gap-2.5 rounded-xl border px-4 py-3 text-sm ${styles}`}>
      <Icon className='mt-0.5 h-4 w-4 flex-shrink-0' />
      <span className='flex-1'>{notice.message}</span>
      {onClose && <button type='button' onClick={onClose} className='rounded p-0.5 opacity-60 hover:opacity-100'><X className='h-3.5 w-3.5' /></button>}
    </div>
  );
}

function EmptyState({ icon: Icon, title, description, action }: {
  icon: React.ElementType; title: string; description: string; action?: React.ReactNode;
}) {
  return (
    <div className='flex min-h-64 flex-col items-center justify-center rounded-2xl border border-dashed border-gray-200 bg-white px-6 py-12 text-center'>
      <div className='mb-4 grid h-12 w-12 place-items-center rounded-2xl bg-gray-100 text-gray-400'><Icon className='h-5 w-5' /></div>
      <h3 className='text-sm font-bold text-gray-800'>{title}</h3>
      <p className='mt-1 max-w-md text-xs leading-5 text-gray-500'>{description}</p>
      {action && <div className='mt-5'>{action}</div>}
    </div>
  );
}

function Modal({ children, onClose, width = 'max-w-xl' }: {
  children: React.ReactNode; onClose: () => void; width?: string;
}) {
  return (
    <div className='fixed inset-0 z-50 grid place-items-center bg-black/45 p-4' onMouseDown={onClose}>
      <div className={`max-h-[90vh] w-full overflow-y-auto rounded-2xl bg-white shadow-2xl ${width}`} onMouseDown={event => event.stopPropagation()}>{children}</div>
    </div>
  );
}

function ChangePasswordForm({ onChanged }: { onChanged: () => void }) {
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setError('');
    const passwordError = passwordStrengthError(newPassword);
    if (passwordError) {
      setError(passwordError);
      return;
    }
    if (newPassword !== confirmation) {
      setError('Mật khẩu xác nhận không khớp.');
      return;
    }
    setSubmitting(true);
    try {
      await changePassword(currentPassword, newPassword);
      onChanged();
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setSubmitting(false);
    }
  }

  const fields: Array<{
    label: string;
    value: string;
    setter: React.Dispatch<React.SetStateAction<string>>;
    autoComplete: string;
  }> = [
    { label: 'Mật khẩu hiện tại', value: currentPassword, setter: setCurrentPassword, autoComplete: 'current-password' },
    { label: 'Mật khẩu mới', value: newPassword, setter: setNewPassword, autoComplete: 'new-password' },
    { label: 'Xác nhận mật khẩu mới', value: confirmation, setter: setConfirmation, autoComplete: 'new-password' },
  ];

  return (
    <form onSubmit={submit} className='space-y-4 border-t border-gray-100 pt-5'>
      <h3 className='text-sm font-bold text-gray-800'>Đổi mật khẩu</h3>
      {fields.map(field => (
        <label key={field.label} className='block'>
          <span className='mb-1.5 block text-xs font-semibold text-gray-600'>{field.label}</span>
          <input
            type='password'
            value={field.value}
            onChange={event => field.setter(event.target.value)}
            autoComplete={field.autoComplete}
            required
            className='h-10 w-full rounded-lg border border-gray-200 px-3 text-sm outline-none focus:border-[#c41e3a] focus:ring-2 focus:ring-[#c41e3a]/10'
          />
        </label>
      ))}
      {error && <Notice notice={{ kind: 'error', message: error }} />}
      <button disabled={submitting} className='flex w-full items-center justify-center gap-2 rounded-lg bg-[#0f1623] py-2.5 text-sm font-bold text-white disabled:opacity-60'>
        {submitting && <Loader2 className='h-4 w-4 animate-spin' />}
        {submitting ? 'Đang cập nhật...' : 'Cập nhật mật khẩu'}
      </button>
    </form>
  );
}

function ProfileModal({ currentUser, onClose, onPasswordChanged }: {
  currentUser: UserPublic;
  onClose: () => void;
  onPasswordChanged: () => void;
}) {
  const [showPasswordForm, setShowPasswordForm] = useState(currentUser.must_change_password);
  const rows = [
    ['Tên đăng nhập', currentUser.username],
    ['Email', currentUser.email],
    ['Chức vụ', currentUser.position || 'Chưa cập nhật'],
    ['Phòng ban', currentUser.department || 'Chưa cập nhật'],
    ['Vai trò', currentUser.role],
    ['Mã đơn vị', currentUser.commune_id],
  ];
  return (
    <Modal onClose={onClose}>
      <div className='flex items-center justify-between border-b border-gray-100 px-6 py-4'>
        <div>
          <h2 className='font-bold text-gray-900'>Thông tin tài khoản</h2>
          <p className='mt-1 text-xs text-gray-400'>Dữ liệu từ phiên đăng nhập hiện tại.</p>
        </div>
        <button type='button' onClick={onClose} className='rounded-lg p-2 text-gray-400 hover:bg-gray-100'><X className='h-4 w-4' /></button>
      </div>
      <div className='p-6'>
        <div className='mb-5 flex items-center gap-3'>
          <div className='grid h-12 w-12 place-items-center rounded-full bg-[#c41e3a] text-sm font-bold text-white'>{initials(currentUser.full_name)}</div>
          <div>
            <p className='font-bold text-gray-900'>{currentUser.full_name}</p>
            <p className='text-xs text-gray-500'>{currentUser.is_active ? 'Đang hoạt động' : 'Tài khoản bị khóa'}</p>
          </div>
        </div>
        <div className='overflow-hidden rounded-xl border border-gray-100'>
          {rows.map(([label, value], index) => (
            <div key={label} className={`grid grid-cols-[140px_1fr] gap-3 px-4 py-3 text-xs ${index > 0 ? 'border-t border-gray-100' : ''}`}>
              <span className='font-semibold text-gray-500'>{label}</span>
              <span className='break-all text-gray-800'>{value}</span>
            </div>
          ))}
        </div>
        {!showPasswordForm && (
          <button type='button' onClick={() => setShowPasswordForm(true)} className='mt-5 flex items-center gap-2 text-sm font-semibold text-[#c41e3a]'>
            <Lock className='h-4 w-4' />Đổi mật khẩu
          </button>
        )}
        {showPasswordForm && <ChangePasswordForm onChanged={onPasswordChanged} />}
      </div>
    </Modal>
  );
}

function UploadModal({ onClose, onUpload }: {
  onClose: () => void;
  onUpload: (files: File[]) => Promise<void>;
}) {
  const [files, setFiles] = useState<File[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  function appendFiles(values: FileList | null) {
    if (!values) return;
    setFiles(current => {
      const next = [...current];
      for (const file of Array.from(values)) {
        if (!next.some(existing => existing.name === file.name && existing.size === file.size)) next.push(file);
      }
      return next;
    });
  }

  async function submit() {
    if (files.length === 0) return;
    setSubmitting(true);
    setError('');
    try {
      await onUpload(files);
      onClose();
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal onClose={submitting ? () => undefined : onClose}>
      <div className='flex items-center justify-between border-b border-gray-100 px-6 py-4'>
        <div>
          <h2 className='font-bold text-gray-900'>Tải tài liệu lên</h2>
          <p className='mt-1 text-xs text-gray-400'>Mỗi tệp được gửi trực tiếp tới API xử lý tài liệu.</p>
        </div>
        <button type='button' onClick={onClose} disabled={submitting} className='rounded-lg p-2 text-gray-400 hover:bg-gray-100 disabled:opacity-40'><X className='h-4 w-4' /></button>
      </div>
      <div className='space-y-4 p-6'>
        <button
          type='button'
          onClick={() => inputRef.current?.click()}
          onDragOver={event => event.preventDefault()}
          onDrop={event => { event.preventDefault(); appendFiles(event.dataTransfer.files); }}
          className='flex min-h-40 w-full flex-col items-center justify-center rounded-2xl border-2 border-dashed border-gray-200 bg-gray-50 text-center hover:border-[#c41e3a]/40 hover:bg-red-50/30'
        >
          <Upload className='mb-3 h-7 w-7 text-[#c41e3a]' />
          <span className='text-sm font-bold text-gray-700'>Chọn hoặc kéo thả tệp</span>
          <span className='mt-1 text-xs text-gray-400'>PDF và DOCX</span>
        </button>
        <input
          ref={inputRef}
          type='file'
          accept='.pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document'
          multiple
          className='hidden'
          onChange={event => { appendFiles(event.target.files); event.target.value = ''; }}
        />
        {files.length > 0 && (
          <div className='space-y-2'>
            {files.map(file => (
              <div key={`${file.name}-${file.size}`} className='flex items-center gap-3 rounded-xl border border-gray-100 px-3 py-2.5'>
                <FileText className='h-4 w-4 flex-shrink-0 text-[#c41e3a]' />
                <div className='min-w-0 flex-1'>
                  <p className='truncate text-xs font-semibold text-gray-800'>{file.name}</p>
                  <p className='text-[10px] text-gray-400'>{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                </div>
                <button type='button' onClick={() => setFiles(current => current.filter(value => value !== file))} className='rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-600'><X className='h-3.5 w-3.5' /></button>
              </div>
            ))}
          </div>
        )}
        {error && <Notice notice={{ kind: 'error', message: error }} />}
      </div>
      <div className='flex justify-end gap-3 border-t border-gray-100 bg-gray-50 px-6 py-4'>
        <button type='button' onClick={onClose} disabled={submitting} className='rounded-lg border border-gray-200 px-4 py-2 text-sm font-semibold text-gray-600 disabled:opacity-40'>Hủy</button>
        <button type='button' onClick={() => void submit()} disabled={files.length === 0 || submitting} className='flex items-center gap-2 rounded-lg bg-[#c41e3a] px-5 py-2 text-sm font-bold text-white disabled:opacity-50'>
          {submitting && <Loader2 className='h-4 w-4 animate-spin' />}
          {submitting ? 'Đang tải...' : `Tải lên ${files.length} tệp`}
        </button>
      </div>
    </Modal>
  );
}

function Sidebar({ screen, currentUser, mobileOpen, onCloseMobile, onNavigate, onUpload, onProfile, onLogout }: {
  screen: Screen;
  currentUser: UserPublic;
  mobileOpen: boolean;
  onCloseMobile: () => void;
  onNavigate: (screen: Screen) => void;
  onUpload: () => void;
  onProfile: () => void;
  onLogout: () => void | Promise<void>;
}) {
  function navigate(next: Screen) {
    onNavigate(next);
    onCloseMobile();
  }
  return (
    <>
      {mobileOpen && <button type='button' aria-label='Đóng menu' onClick={onCloseMobile} className='fixed inset-0 z-30 bg-black/30 lg:hidden' />}
      <aside className={`fixed inset-y-0 left-0 z-40 flex w-64 flex-col bg-[#0f1623] transition-transform lg:translate-x-0 ${mobileOpen ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className='flex h-16 items-center gap-3 border-b border-white/10 px-5'>
          <div className='grid h-9 w-9 place-items-center rounded-xl bg-[#c41e3a] text-white'><FileText className='h-4 w-4' /></div>
          <div><p className='font-bold tracking-wide text-white'>VADS</p><p className='text-[9px] uppercase tracking-widest text-white/35'>Document Intelligence</p></div>
        </div>
        <div className='px-4 py-4'>
          <button type='button' onClick={onUpload} className='flex w-full items-center justify-center gap-2 rounded-xl bg-[#c41e3a] px-4 py-2.5 text-sm font-bold text-white hover:bg-[#a8172f]'><Upload className='h-4 w-4' />Tải tài liệu</button>
        </div>
        <nav className='flex-1 space-y-1 px-3'>
          {NAV_ITEMS.map(({ id, label, icon: Icon }) => (
            <button type='button' key={id} onClick={() => navigate(id)} className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm transition ${screen === id ? 'bg-white/10 font-semibold text-white' : 'text-white/55 hover:bg-white/5 hover:text-white'}`}>
              <Icon className='h-4 w-4' />{label}
            </button>
          ))}
        </nav>
        <div className='border-t border-white/10 p-4'>
          <div className='flex items-center gap-3'>
            <button type='button' onClick={onProfile} className='grid h-9 w-9 flex-shrink-0 place-items-center rounded-full bg-[#c41e3a] text-xs font-bold text-white'>{initials(currentUser.full_name)}</button>
            <button type='button' onClick={onProfile} className='min-w-0 flex-1 text-left'>
              <p className='truncate text-xs font-bold text-white'>{currentUser.full_name}</p>
              <p className='truncate text-[10px] text-white/40'>{currentUser.position || currentUser.department || currentUser.username}</p>
            </button>
            <button type='button' title='Đăng xuất' onClick={() => void onLogout()} className='rounded-lg p-2 text-white/35 hover:bg-white/10 hover:text-white'><LogOut className='h-4 w-4' /></button>
          </div>
        </div>
      </aside>
    </>
  );
}

function Header({ title, documents, search, loading, onSearch, onNavigate, onRefresh, onOpenMobile }: {
  title: string;
  documents: DocumentPublic[];
  search: string;
  loading: boolean;
  onSearch: (value: string) => void;
  onNavigate: (screen: Screen) => void;
  onRefresh: () => void;
  onOpenMobile: () => void;
}) {
  const [showNotifications, setShowNotifications] = useState(false);
  const notifications = documents.filter(document => document.status !== 'COMPLETED').slice(0, 5);
  return (
    <header className='sticky top-0 z-20 flex h-16 items-center gap-3 border-b border-gray-200 bg-white px-4 lg:px-7'>
      <button type='button' onClick={onOpenMobile} className='rounded-lg p-2 text-gray-500 hover:bg-gray-100 lg:hidden'><Menu className='h-5 w-5' /></button>
      <h1 className='hidden min-w-fit text-lg font-bold text-gray-900 sm:block'>{title}</h1>
      <div className='relative ml-auto w-full max-w-md'>
        <Search className='pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400' />
        <input
          value={search}
          onFocus={() => onNavigate('documents')}
          onChange={event => { onSearch(event.target.value); onNavigate('documents'); }}
          placeholder='Tìm trong tài liệu của bạn'
          className='h-9 w-full rounded-lg border border-gray-200 bg-gray-50 pl-9 pr-3 text-sm outline-none focus:border-[#c41e3a] focus:ring-2 focus:ring-[#c41e3a]/10'
        />
      </div>
      <button type='button' title='Làm mới' onClick={onRefresh} disabled={loading} className='rounded-lg p-2 text-gray-500 hover:bg-gray-100 disabled:opacity-40'><RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} /></button>
      <div className='relative'>
        <button type='button' title='Thông báo' onClick={() => setShowNotifications(value => !value)} className='relative rounded-lg p-2 text-gray-500 hover:bg-gray-100'>
          <Bell className='h-4 w-4' />
          {notifications.length > 0 && <span className='absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-[#c41e3a]' />}
        </button>
        {showNotifications && (
          <div className='absolute right-0 top-full mt-2 w-80 overflow-hidden rounded-xl border border-gray-200 bg-white shadow-xl'>
            <div className='border-b border-gray-100 px-4 py-3 text-xs font-bold uppercase tracking-wide text-gray-600'>Trạng thái tài liệu</div>
            {notifications.length === 0 ? (
              <p className='px-4 py-8 text-center text-xs text-gray-400'>Không có trạng thái cần chú ý.</p>
            ) : notifications.map(document => (
              <button type='button' key={document.id} onClick={() => { onNavigate('documents'); setShowNotifications(false); }} className='flex w-full items-start gap-3 border-b border-gray-50 px-4 py-3 text-left hover:bg-gray-50'>
                <FileText className='mt-0.5 h-4 w-4 flex-shrink-0 text-[#c41e3a]' />
                <span className='min-w-0 flex-1'>
                  <span className='block truncate text-xs font-semibold text-gray-800'>{document.title}</span>
                  <span className='mt-1 block text-[10px] text-gray-400'>{STATUS_LABELS[document.status]}</span>
                </span>
              </button>
            ))}
          </div>
        )}
      </div>
    </header>
  );
}

function StatusBadge({ status }: { status: DocumentPublic['status'] }) {
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[10px] font-bold ${STATUS_STYLES[status]}`}>
      {PROCESSING_STATUSES.has(status) && <Loader2 className='h-3 w-3 animate-spin' />}
      {STATUS_LABELS[status]}
    </span>
  );
}

function Dashboard({ documents, loading, onUpload, onNavigate, onAsk }: {
  documents: DocumentPublic[];
  loading: boolean;
  onUpload: () => void;
  onNavigate: (screen: Screen) => void;
  onAsk: (documentId?: string) => void;
}) {
  const stats = [
    { label: 'Tổng tài liệu', value: documents.length, icon: FileText, color: 'bg-sky-50 text-sky-700' },
    { label: 'Đang xử lý', value: documents.filter(document => PROCESSING_STATUSES.has(document.status)).length, icon: Loader2, color: 'bg-amber-50 text-amber-700' },
    { label: 'Sẵn sàng hỏi đáp', value: documents.filter(document => RAG_READY_STATUSES.has(document.status)).length, icon: Brain, color: 'bg-emerald-50 text-emerald-700' },
    { label: 'Cần chú ý', value: documents.filter(document => ['FAILED', 'CANCELLED', 'NEEDS_REVIEW'].includes(document.status)).length, icon: AlertCircle, color: 'bg-red-50 text-red-700' },
  ];
  const recent = documents.slice(0, 5);
  return (
    <div className='space-y-6'>
      <section className='overflow-hidden rounded-2xl bg-[#0f1623] p-7 text-white shadow-sm'>
        <div className='max-w-2xl'>
          <p className='text-xs font-semibold uppercase tracking-[0.2em] text-white/45'>Workspace của bạn</p>
          <h2 className='mt-2 text-2xl font-bold'>Phân tích tài liệu bằng dữ liệu thật</h2>
          <p className='mt-2 text-sm leading-6 text-white/60'>Tải PDF hoặc DOCX, theo dõi trạng thái xử lý và đặt câu hỏi trên chính các tài liệu đã hoàn tất.</p>
          <div className='mt-5 flex flex-wrap gap-3'>
            <button type='button' onClick={onUpload} className='flex items-center gap-2 rounded-xl bg-[#c41e3a] px-4 py-2.5 text-sm font-bold hover:bg-[#a8172f]'><Upload className='h-4 w-4' />Tải tài liệu</button>
            <button type='button' onClick={() => onAsk()} className='flex items-center gap-2 rounded-xl border border-white/15 px-4 py-2.5 text-sm font-semibold text-white/80 hover:bg-white/10'><MessageSquare className='h-4 w-4' />Mở trợ lý AI</button>
          </div>
        </div>
      </section>
      <section className='grid gap-4 sm:grid-cols-2 xl:grid-cols-4'>
        {stats.map(({ label, value, icon: Icon, color }) => (
          <div key={label} className='rounded-2xl border border-gray-200 bg-white p-5 shadow-sm'>
            <div className={`mb-4 grid h-10 w-10 place-items-center rounded-xl ${color}`}><Icon className={`h-4 w-4 ${label === 'Đang xử lý' && value > 0 ? 'animate-spin' : ''}`} /></div>
            <p className='text-2xl font-bold text-gray-900'>{loading && documents.length === 0 ? '—' : value}</p>
            <p className='mt-1 text-xs text-gray-500'>{label}</p>
          </div>
        ))}
      </section>
      <section className='rounded-2xl border border-gray-200 bg-white shadow-sm'>
        <div className='flex items-center justify-between border-b border-gray-100 px-5 py-4'>
          <div><h3 className='text-sm font-bold text-gray-900'>Tài liệu gần đây</h3><p className='mt-1 text-xs text-gray-400'>Cập nhật trực tiếp từ API.</p></div>
          <button type='button' onClick={() => onNavigate('documents')} className='text-xs font-bold text-[#c41e3a]'>Xem tất cả</button>
        </div>
        {loading && recent.length === 0 ? (
          <div className='flex items-center justify-center gap-2 py-16 text-xs text-gray-400'><Loader2 className='h-4 w-4 animate-spin' />Đang tải...</div>
        ) : recent.length === 0 ? (
          <div className='p-5'><EmptyState icon={FileText} title='Chưa có tài liệu' description='Danh sách sẽ xuất hiện sau khi API tiếp nhận tệp đầu tiên.' action={<button type='button' onClick={onUpload} className='rounded-lg bg-[#c41e3a] px-4 py-2 text-xs font-bold text-white'>Tải tệp đầu tiên</button>} /></div>
        ) : (
          <div className='divide-y divide-gray-100'>
            {recent.map(document => (
              <div key={document.id} className='flex items-center gap-4 px-5 py-4'>
                <div className='grid h-9 w-9 flex-shrink-0 place-items-center rounded-xl bg-red-50 text-[#c41e3a]'><FileText className='h-4 w-4' /></div>
                <div className='min-w-0 flex-1'><p className='truncate text-sm font-semibold text-gray-900'>{document.title}</p><p className='mt-1 text-[11px] text-gray-400'>{formatDate(document.created_at)}</p></div>
                <StatusBadge status={document.status} />
                {RAG_READY_STATUSES.has(document.status) && <button type='button' onClick={() => onAsk(document.id)} className='hidden rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-semibold text-gray-600 hover:border-[#c41e3a] hover:text-[#c41e3a] sm:block'>Hỏi AI</button>}
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function DocumentsScreen({ documents, loading, search, onSearch, onRefresh, onUpload, onReprocess, onDelete, onAsk }: {
  documents: DocumentPublic[];
  loading: boolean;
  search: string;
  onSearch: (value: string) => void;
  onRefresh: () => void;
  onUpload: () => void;
  onReprocess: (documentId: string) => Promise<void>;
  onDelete: (documentId: string) => Promise<void>;
  onAsk: (documentId: string) => void;
}) {
  const [status, setStatus] = useState<'ALL' | DocumentPublic['status']>('ALL');
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState('');
  const filtered = useMemo(() => {
    const query = search.trim().toLocaleLowerCase('vi');
    return documents.filter(document => {
      const matchesSearch = !query || document.title.toLocaleLowerCase('vi').includes(query);
      const matchesStatus = status === 'ALL' || document.status === status;
      return matchesSearch && matchesStatus;
    });
  }, [documents, search, status]);

  async function run(documentId: string, action: () => Promise<void>) {
    setBusyId(documentId);
    setError('');
    try {
      await action();
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setBusyId(null);
    }
  }

  async function confirmDelete(document: DocumentPublic) {
    if (!window.confirm(`Xóa tài liệu ${document.title}?`)) return;
    await run(document.id, () => onDelete(document.id));
  }

  return (
    <div className='space-y-5'>
      <div className='flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between'>
        <div><h2 className='text-xl font-bold text-gray-900'>Tài liệu của tôi</h2><p className='mt-1 text-xs text-gray-500'>{documents.length} tài liệu từ API bảo mật.</p></div>
        <div className='flex gap-2'>
          <button type='button' onClick={onRefresh} disabled={loading} className='flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-3.5 py-2 text-xs font-bold text-gray-600 disabled:opacity-50'><RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />Làm mới</button>
          <button type='button' onClick={onUpload} className='flex items-center gap-2 rounded-lg bg-[#c41e3a] px-3.5 py-2 text-xs font-bold text-white'><Upload className='h-3.5 w-3.5' />Tải lên</button>
        </div>
      </div>
      <div className='flex flex-col gap-3 rounded-xl border border-gray-200 bg-white p-4 sm:flex-row'>
        <div className='relative flex-1'>
          <Search className='absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400' />
          <input value={search} onChange={event => onSearch(event.target.value)} placeholder='Tìm theo tên tài liệu' className='h-10 w-full rounded-lg border border-gray-200 pl-9 pr-3 text-sm outline-none focus:border-[#c41e3a]' />
        </div>
        <select value={status} onChange={event => setStatus(event.target.value as typeof status)} className='h-10 rounded-lg border border-gray-200 bg-white px-3 text-sm text-gray-600 outline-none focus:border-[#c41e3a]'>
          <option value='ALL'>Tất cả trạng thái</option>
          {Object.entries(STATUS_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
      </div>
      {error && <Notice notice={{ kind: 'error', message: error }} onClose={() => setError('')} />}
      {loading && documents.length === 0 ? (
        <div className='flex min-h-72 items-center justify-center gap-2 rounded-2xl border border-gray-200 bg-white text-sm text-gray-400'><Loader2 className='h-5 w-5 animate-spin' />Đang tải tài liệu...</div>
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={FileText}
          title='Không có dữ liệu phù hợp'
          description={documents.length === 0 ? 'API chưa trả về tài liệu nào cho tài khoản này.' : 'Không có tài liệu khớp bộ lọc hiện tại.'}
          action={documents.length === 0 ? <button type='button' onClick={onUpload} className='rounded-lg bg-[#c41e3a] px-4 py-2 text-xs font-bold text-white'>Tải tài liệu</button> : undefined}
        />
      ) : (
        <div className='overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm'>
          <div className='overflow-x-auto'>
            <table className='w-full min-w-[860px] text-left'>
              <thead className='bg-gray-50 text-[10px] font-bold uppercase tracking-wide text-gray-500'>
                <tr><th className='px-5 py-3'>Tài liệu</th><th className='px-5 py-3'>Trạng thái</th><th className='px-5 py-3'>Phê duyệt</th><th className='px-5 py-3'>Cập nhật</th><th className='px-5 py-3 text-right'>Thao tác</th></tr>
              </thead>
              <tbody>
                {filtered.map(document => (
                  <tr key={document.id} className='border-t border-gray-100 hover:bg-gray-50/60'>
                    <td className='px-5 py-4'>
                      <div className='flex items-center gap-3'>
                        <div className='grid h-9 w-9 flex-shrink-0 place-items-center rounded-xl bg-red-50 text-[#c41e3a]'><FileText className='h-4 w-4' /></div>
                        <div className='min-w-0'><p className='max-w-md truncate text-sm font-semibold text-gray-900'>{document.title}</p><p className='mt-1 font-mono text-[10px] text-gray-400'>{document.id}</p></div>
                      </div>
                    </td>
                    <td className='px-5 py-4'><StatusBadge status={document.status} /></td>
                    <td className='px-5 py-4 text-xs text-gray-600'>{APPROVAL_LABELS[document.approval_status]}</td>
                    <td className='px-5 py-4 text-xs text-gray-500'>{formatDate(document.updated_at)}</td>
                    <td className='px-5 py-4'>
                      <div className='flex justify-end gap-1.5'>
                        {RAG_READY_STATUSES.has(document.status) && <button type='button' title='Hỏi AI' onClick={() => onAsk(document.id)} className='rounded-lg p-2 text-gray-500 hover:bg-violet-50 hover:text-violet-700'><MessageSquare className='h-4 w-4' /></button>}
                        {['FAILED', 'CANCELLED'].includes(document.status) && (
                          <button type='button' title='Xử lý lại' disabled={busyId === document.id} onClick={() => void run(document.id, () => onReprocess(document.id))} className='rounded-lg p-2 text-gray-500 hover:bg-amber-50 hover:text-amber-700 disabled:opacity-40'>
                            {busyId === document.id ? <Loader2 className='h-4 w-4 animate-spin' /> : <RotateCcw className='h-4 w-4' />}
                          </button>
                        )}
                        <button type='button' title='Xóa' disabled={busyId === document.id} onClick={() => void confirmDelete(document)} className='rounded-lg p-2 text-gray-500 hover:bg-red-50 hover:text-red-700 disabled:opacity-40'><Trash2 className='h-4 w-4' /></button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function AssistantScreen({ documents, initialDocumentId }: {
  documents: DocumentPublic[];
  initialDocumentId: string | null;
}) {
  const readyDocuments = useMemo(
    () => documents.filter(document => RAG_READY_STATUSES.has(document.status)),
    [documents],
  );
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [question, setQuestion] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    setSelectedIds(current => current.filter(id => readyDocuments.some(document => document.id === id)));
  }, [readyDocuments]);

  useEffect(() => {
    if (!initialDocumentId || !readyDocuments.some(document => document.id === initialDocumentId)) return;
    setSelectedIds(current => current.includes(initialDocumentId) ? current : [...current, initialDocumentId]);
  }, [initialDocumentId, readyDocuments]);

  function toggleDocument(documentId: string) {
    setSelectedIds(current => current.includes(documentId)
      ? current.filter(id => id !== documentId)
      : [...current, documentId]);
  }

  async function send(event: React.FormEvent) {
    event.preventDefault();
    const value = question.trim();
    if (!value || selectedIds.length === 0 || asking) return;
    setMessages(current => [...current, {
      id: crypto.randomUUID(), role: 'user', text: value,
    }]);
    setQuestion('');
    setAsking(true);
    setError('');
    try {
      const result = await queryDocumentRag(value, selectedIds);
      setMessages(current => [...current, {
        id: crypto.randomUUID(), role: 'assistant', text: result.answer,
        retrievalMode: result.retrieval_mode, sources: result.sources,
      }]);
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setAsking(false);
    }
  }

  return (
    <div className='grid min-h-[calc(100vh-7.5rem)] gap-5 xl:grid-cols-[320px_1fr]'>
      <aside className='rounded-2xl border border-gray-200 bg-white p-4 shadow-sm'>
        <div className='mb-4'><h2 className='text-sm font-bold text-gray-900'>Nguồn hỏi đáp</h2><p className='mt-1 text-xs leading-5 text-gray-400'>Chọn tối đa 20 tài liệu đã xử lý xong.</p></div>
        {readyDocuments.length === 0 ? (
          <EmptyState icon={FileText} title='Chưa có nguồn dữ liệu' description='Trợ lý chỉ hoạt động khi backend đã tạo chunk cho ít nhất một tài liệu.' />
        ) : (
          <div className='max-h-[calc(100vh-13rem)] space-y-2 overflow-y-auto pr-1'>
            {readyDocuments.map(document => {
              const checked = selectedIds.includes(document.id);
              return (
                <label key={document.id} className={`flex cursor-pointer items-start gap-3 rounded-xl border p-3 transition ${checked ? 'border-[#c41e3a]/40 bg-red-50/40' : 'border-gray-100 hover:bg-gray-50'}`}>
                  <input type='checkbox' checked={checked} disabled={!checked && selectedIds.length >= 20} onChange={() => toggleDocument(document.id)} className='mt-0.5 accent-[#c41e3a]' />
                  <span className='min-w-0'><span className='block truncate text-xs font-semibold text-gray-800'>{document.title}</span><span className='mt-1 block text-[10px] text-gray-400'>{STATUS_LABELS[document.status]}</span></span>
                </label>
              );
            })}
          </div>
        )}
      </aside>
      <section className='flex min-h-[620px] flex-col overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm'>
        <div className='flex items-center justify-between border-b border-gray-100 px-5 py-4'>
          <div className='flex items-center gap-3'>
            <div className='grid h-9 w-9 place-items-center rounded-xl bg-violet-50 text-violet-700'><Brain className='h-4 w-4' /></div>
            <div><h2 className='text-sm font-bold text-gray-900'>Trợ lý tài liệu</h2><p className='mt-0.5 text-[10px] text-gray-400'>{selectedIds.length} nguồn đang được chọn</p></div>
          </div>
          {messages.length > 0 && <button type='button' onClick={() => setMessages([])} className='text-xs font-semibold text-gray-400 hover:text-red-600'>Xóa hội thoại</button>}
        </div>
        <div className='flex-1 space-y-4 overflow-y-auto bg-gray-50/60 p-5'>
          {messages.length === 0 && <EmptyState icon={MessageSquare} title='Chưa có câu hỏi' description='Chọn tài liệu ở cột bên trái rồi gửi câu hỏi. Câu trả lời và nguồn trích dẫn đều đến từ API RAG.' />}
          {messages.map(message => (
            <div key={message.id} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[88%] rounded-2xl px-4 py-3 text-sm leading-6 ${message.role === 'user' ? 'bg-[#0f1623] text-white' : 'border border-gray-200 bg-white text-gray-700'}`}>
                <p className='whitespace-pre-wrap'>{message.text}</p>
                {message.retrievalMode && <p className='mt-2 text-[10px] uppercase tracking-wide text-gray-400'>Chế độ truy xuất: {message.retrievalMode}</p>}
                {message.sources && message.sources.length > 0 && (
                  <div className='mt-3 space-y-2 border-t border-gray-100 pt-3'>
                    {message.sources.map((source, index) => (
                      <div key={`${source.chunk_id}-${index}`} className='rounded-xl bg-gray-50 p-3'>
                        <div className='flex items-center justify-between gap-3 text-[10px] font-semibold text-gray-500'>
                          <span className='truncate'>{source.document_title}</span>
                          <span className='flex-shrink-0'>{source.page_number ? `Trang ${source.page_number}` : 'Không có số trang'}</span>
                        </div>
                        {(source.article || source.clause) && <p className='mt-1 text-[10px] text-violet-600'>{[source.article, source.clause].filter(Boolean).join(' · ')}</p>}
                        <p className='mt-1.5 text-xs leading-5 text-gray-600'>{source.quote}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
          {asking && <div className='flex items-center gap-2 text-xs text-gray-400'><Loader2 className='h-4 w-4 animate-spin' />Đang truy xuất và tạo câu trả lời...</div>}
          {error && <Notice notice={{ kind: 'error', message: error }} onClose={() => setError('')} />}
        </div>
        <form onSubmit={send} className='flex gap-3 border-t border-gray-100 p-4'>
          <input
            value={question}
            onChange={event => setQuestion(event.target.value)}
            disabled={selectedIds.length === 0 || asking}
            placeholder={selectedIds.length > 0 ? 'Nhập câu hỏi về tài liệu đã chọn' : 'Chọn ít nhất một tài liệu để bắt đầu'}
            className='h-11 min-w-0 flex-1 rounded-xl border border-gray-200 bg-gray-50 px-4 text-sm outline-none focus:border-[#c41e3a] disabled:cursor-not-allowed disabled:opacity-60'
          />
          <button disabled={!question.trim() || selectedIds.length === 0 || asking} className='grid h-11 w-11 place-items-center rounded-xl bg-[#c41e3a] text-white disabled:opacity-40'>
            {asking ? <Loader2 className='h-4 w-4 animate-spin' /> : <Send className='h-4 w-4' />}
          </button>
        </form>
      </section>
    </div>
  );
}

export default function UserPortal({ currentUser, onLogout }: {
  currentUser: UserPublic;
  onLogout: () => void | Promise<void>;
}) {
  const [screen, setScreen] = useState<Screen>('dashboard');
  const [documents, setDocuments] = useState<DocumentPublic[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState<NoticeState | null>(null);
  const [search, setSearch] = useState('');
  const [showUpload, setShowUpload] = useState(false);
  const [showProfile, setShowProfile] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [assistantDocumentId, setAssistantDocumentId] = useState<string | null>(null);

  const loadDocuments = useCallback(async () => {
    setLoading(true);
    try {
      setDocuments(await listDocuments());
      setError('');
    } catch (reason) {
      setError(messageOf(reason));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadDocuments();
  }, [loadDocuments]);

  useEffect(() => {
    if (!documents.some(document => PROCESSING_STATUSES.has(document.status))) return;
    const timer = window.setInterval(() => void loadDocuments(), 5000);
    return () => window.clearInterval(timer);
  }, [documents, loadDocuments]);

  async function handleUpload(files: File[]) {
    const acceptedIds: string[] = [];
    for (const file of files) {
      const result = await uploadDocument(file);
      acceptedIds.push(result.document_id);
    }
    await loadDocuments();
    setScreen('documents');
    setNotice({ kind: 'success', message: `${acceptedIds.length} tài liệu đã được API tiếp nhận. Trạng thái sẽ tự động cập nhật.` });
  }

  async function handleReprocess(documentId: string) {
    await reprocessDocument(documentId);
    await loadDocuments();
    setNotice({ kind: 'success', message: 'Đã gửi yêu cầu xử lý lại tài liệu.' });
  }

  async function handleDelete(documentId: string) {
    await deleteDocument(documentId);
    await loadDocuments();
    setNotice({ kind: 'success', message: 'Đã xóa tài liệu khỏi danh sách hiển thị.' });
  }

  function openAssistant(documentId?: string) {
    setAssistantDocumentId(documentId ?? null);
    setScreen('assistant');
  }

  const title = NAV_ITEMS.find(item => item.id === screen)?.label ?? 'VADS';

  return (
    <div className='min-h-screen bg-[#f4f5f7]'>
      <Sidebar
        screen={screen}
        currentUser={currentUser}
        mobileOpen={mobileOpen}
        onCloseMobile={() => setMobileOpen(false)}
        onNavigate={setScreen}
        onUpload={() => setShowUpload(true)}
        onProfile={() => setShowProfile(true)}
        onLogout={onLogout}
      />
      <div className='min-h-screen lg:pl-64'>
        <Header
          title={title}
          documents={documents}
          search={search}
          loading={loading}
          onSearch={setSearch}
          onNavigate={setScreen}
          onRefresh={() => void loadDocuments()}
          onOpenMobile={() => setMobileOpen(true)}
        />
        <main className='p-4 lg:p-7'>
          <div className='mx-auto max-w-7xl space-y-5'>
            {currentUser.must_change_password && <Notice notice={{ kind: 'info', message: 'Tài khoản đang dùng mật khẩu tạm thời. Hãy mở hồ sơ và đổi mật khẩu trước khi tiếp tục.' }} />}
            {error && <Notice notice={{ kind: 'error', message: error }} onClose={() => setError('')} />}
            {notice && <Notice notice={notice} onClose={() => setNotice(null)} />}
            {screen === 'dashboard' && (
              <Dashboard documents={documents} loading={loading} onUpload={() => setShowUpload(true)} onNavigate={setScreen} onAsk={openAssistant} />
            )}
            {screen === 'documents' && (
              <DocumentsScreen
                documents={documents}
                loading={loading}
                search={search}
                onSearch={setSearch}
                onRefresh={() => void loadDocuments()}
                onUpload={() => setShowUpload(true)}
                onReprocess={handleReprocess}
                onDelete={handleDelete}
                onAsk={openAssistant}
              />
            )}
            {screen === 'assistant' && <AssistantScreen documents={documents} initialDocumentId={assistantDocumentId} />}
            {screen === 'regulatory' && <RegulatoryIntelligence onDocumentsChanged={loadDocuments} />}
            {screen === 'knowledge-graph' && <KnowledgeGraphScreen documents={documents} />}
          </div>
        </main>
      </div>
      {showUpload && <UploadModal onClose={() => setShowUpload(false)} onUpload={handleUpload} />}
      {showProfile && <ProfileModal currentUser={currentUser} onClose={() => setShowProfile(false)} onPasswordChanged={() => void onLogout()} />}
    </div>
  );
}
