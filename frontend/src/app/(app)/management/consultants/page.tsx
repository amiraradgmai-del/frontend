"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { BadgeCheck, Building2, Check, Search, Trash2, UserRoundCheck, X } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

type Stats = { independent: number; company: number; pending: number; approved: number; rejected: number; correction_required: number; active: number; inactive: number };
type Verification = { id: string; full_name: string; email: string; consultant_type: string; professional_title: string; specialties: string[]; years_experience: number; qualifications: string; status: string; admin_note: string; created_at: string; documents?: {id:string;title:string;document_type:string;description:string;status:string;download_url:string}[]; profile_payload?: { bio?: string; consultation_price?: number; city?: string; skills?: string[]; is_online?: boolean; offers_in_person?: boolean } };
type Consultant = { id: string; full_name: string; email: string; consultant_type: string; professional_title: string; specialties: string[]; rating: number; is_verified: boolean; is_available: boolean; account_active: boolean };
type Booking = { id: string; scheduled_at: string; status: string; mode: string; price: number; refund_amount: number; cancelled_by: string; cancellation_reason: string; client: { full_name: string; email: string }; consultant: { full_name: string } };
type Details = { profile: Consultant & { bank_account_holder: string; bank_iban: string; blocked_until?: string; blocked_reason: string; contract_number: string; contract_start?: string; contract_end?: string; contract_status: string }; documents: { id: string; title: string; filename: string; status: string }[]; reviews: { id: string; rating: number; comment: string; status: string }[]; verification_history: Verification[]; stats: { completed_sessions: number; cancelled_sessions: number; gross_revenue: number } };

export default function ConsultantManagementPage() {
  const router = useRouter();
  const [stats, setStats] = useState<Stats | null>(null);
  const [requests, setRequests] = useState<Verification[]>([]);
  const [consultants, setConsultants] = useState<Consultant[]>([]);
  const [deleted, setDeleted] = useState<(Consultant & { deleted_at: string })[]>([]);
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [query, setQuery] = useState("");
  const [type, setType] = useState("all");
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [message, setMessage] = useState("");
  const [details, setDetails] = useState<Details | null>(null);

  const load = () => Promise.all([
    api<Stats>("api/v1/consultations/manage/dashboard"),
    api<Verification[]>("api/v1/consultations/manage/verifications"),
    api<Consultant[]>("api/v1/consultations/manage/profiles"),
    api<(Consultant & { deleted_at: string })[]>("api/v1/consultations/manage/deleted-profiles"),
    api<Booking[]>("api/v1/consultations/manage/bookings"),
  ]).then(([dashboard, verificationRequests, profiles, deletedProfiles, bookingItems]) => {
    setStats(dashboard);
    setRequests(verificationRequests);
    setConsultants(profiles);
    setDeleted(deletedProfiles);
    setBookings(bookingItems);
  });
  useEffect(() => { void load().catch(() => setMessage("دریافت اطلاعات مشاوران ممکن نیست.")); }, []);

  async function review(id: string, status: "approved" | "rejected" | "correction_required") {
    try {
      await api(`api/v1/consultations/manage/verifications/${id}`, { method: "PATCH", body: JSON.stringify({ status, admin_note: notes[id] ?? "" }) });
      setMessage("نتیجه بررسی ذخیره شد.");
      await load();
    } catch (error) { setMessage(error instanceof ApiError ? error.message : "ثبت نتیجه انجام نشد."); }
  }
  async function updateProfile(id: string, changes: Record<string, boolean>) {
    try {
      await api(`api/v1/consultations/manage/profiles/${id}`, { method: "PATCH", body: JSON.stringify(changes) });
      await load();
    } catch (error) { setMessage(error instanceof ApiError ? error.message : "تغییر وضعیت انجام نشد."); }
  }
  async function deleteProfile(id: string, fullName: string) {
    if (!window.confirm(`مشاور «${fullName}» حذف و حساب او غیرفعال شود؟`)) return;
    try {
      await api(`api/v1/consultations/manage/profiles/${id}`, { method: "DELETE" });
      setMessage("مشاور حذف و حساب او غیرفعال شد.");
      await load();
    } catch (error) { setMessage(error instanceof ApiError ? error.message : "حذف مشاور انجام نشد."); }
  }
  async function showDetails(id: string) {
    router.push(`/management/consultants/${id}/edit`);
  }
  async function editDetails() {
    if (!details) return;
    const title = window.prompt("عنوان تخصصی", details.profile.professional_title);
    if (title === null) return;
    const iban = window.prompt("شماره شبا با IR", details.profile.bank_iban);
    if (iban === null) return;
    try { await api(`api/v1/consultations/manage/profiles/${details.profile.id}`, { method: "PATCH", body: JSON.stringify({ professional_title: title, bank_iban: iban.toUpperCase() }) }); await showDetails(details.profile.id); await load(); }
    catch (error) { setMessage(error instanceof Error ? error.message : "ویرایش انجام نشد."); }
  }
  async function editContract() {
    if (!details) return;
    const contract_number = prompt("شماره قرارداد", details.profile.contract_number) ?? details.profile.contract_number;
    const contract_start = prompt("شروع قرارداد (YYYY-MM-DD)", details.profile.contract_start?.slice(0, 10) ?? "") ?? "";
    const contract_end = prompt("پایان قرارداد (YYYY-MM-DD)", details.profile.contract_end?.slice(0, 10) ?? "") ?? "";
    const contract_status = prompt("وضعیت: draft / active / expired / terminated", details.profile.contract_status) ?? details.profile.contract_status;
    try { await api(`api/v1/consultations/manage/profiles/${details.profile.id}`, { method: "PATCH", body: JSON.stringify({ contract_number, contract_start: contract_start ? new Date(contract_start).toISOString() : null, contract_end: contract_end ? new Date(contract_end).toISOString() : null, contract_status }) }); await showDetails(details.profile.id); }
    catch (error) { setMessage(error instanceof Error ? error.message : "ثبت قرارداد انجام نشد."); }
  }
  async function blockProfile() {
    if (!details) return;
    const days = Number(window.prompt("تعداد روز مسدودی", "7") ?? 0);
    const reason = window.prompt("دلیل مسدودی") ?? "";
    if (!days || reason.length < 5) return;
    try { await api(`api/v1/consultations/manage/profiles/${details.profile.id}/block`, { method: "POST", body: JSON.stringify({ days, reason }) }); await showDetails(details.profile.id); await load(); }
    catch (error) { setMessage(error instanceof Error ? error.message : "مسدودی انجام نشد."); }
  }
  async function moderateReview(id: string, status: "published" | "hidden") {
    await api(`api/v1/consultations/manage/reviews/${id}`, { method: "PATCH", body: JSON.stringify({ status }) });
    if (details) await showDetails(details.profile.id);
  }
  async function restoreProfile(id: string) {
    try { await api(`api/v1/consultations/manage/profiles/${id}/restore`, { method: "POST" }); setMessage("مشاور بازیابی شد."); await load(); }
    catch (error) { setMessage(error instanceof Error ? error.message : "بازیابی انجام نشد."); }
  }

  const visible = useMemo(() => consultants.filter((item) => {
    const matchesType = type === "all" || item.consultant_type === type;
    const matchesText = `${item.full_name} ${item.email} ${item.professional_title} ${item.specialties.join(" ")}`.toLowerCase().includes(query.toLowerCase());
    return matchesType && matchesText;
  }), [consultants, query, type]);

  return <div className="space-y-7">
    <header><p className="text-sm font-bold text-blue-600">مدیریت کامل مشاوران</p><h1 className="mt-1 text-3xl font-black">مشاوران و احراز صلاحیت</h1><p className="mt-2 text-slate-500">افزودن، ورود گروهی، تأیید، ویرایش و مدیریت مشاوران مستقل و شرکتی از یک صفحه.</p><div className="mt-4 flex flex-wrap gap-2"><a className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-bold text-white" href="#add-consultant">افزودن یا ورود گروهی مشاور</a><a className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-bold text-white" href="/api/backend/api/v1/admin/export/consultants.xlsx">خروجی Excel مشاوران</a><a className="rounded-lg bg-rose-600 px-4 py-2 text-sm font-bold text-white" href="/api/backend/api/v1/admin/consultants-report.pdf">گزارش PDF مالی</a></div></header>
    <details id="add-consultant" className="scroll-mt-6 rounded-[2rem] border border-blue-100 bg-white p-4 shadow-sm open:p-6">
      <summary className="cursor-pointer list-none text-lg font-black text-blue-700">افزودن یا ورود گروهی مشاور</summary>
      <div className="mt-6"><a href="/support/consultants" className="inline-flex rounded-xl bg-blue-600 px-4 py-3 text-sm font-bold text-white">ورود به فرم افزودن مشاور</a></div>
    </details>
    <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4"><Metric label="مشاور مستقل" value={stats?.independent ?? 0} icon={UserRoundCheck} /><Metric label="مشاور شرکت" value={stats?.company ?? 0} icon={Building2} /><Metric label="در انتظار بررسی" value={stats?.pending ?? 0} icon={BadgeCheck} /><Metric label="مشاور فعال" value={stats?.active ?? 0} icon={Check} /></section>
    {message && <p className="rounded-xl bg-sky-50 p-3 text-sm text-sky-800">{message}</p>}
    <Card className="border-violet-100 bg-white"><CardHeader><CardTitle>رزروهای همه مشاوران</CardTitle></CardHeader><CardContent><div className="max-h-96 space-y-2 overflow-y-auto">{bookings.map((item) => <div key={item.id} className="grid gap-2 rounded-xl border p-3 text-sm md:grid-cols-5"><span className="font-bold">{item.consultant.full_name}</span><span>{item.client.full_name}</span><span>{new Date(item.scheduled_at).toLocaleString("fa-IR")}</span><span>{item.status === "reserved" ? "رزروشده" : item.status === "completed" ? "انجام‌شده" : `لغوشده توسط ${item.cancelled_by === "consultant" ? "مشاور" : "کاربر"}`}</span><span>{item.price.toLocaleString("fa-IR")} تومان{item.refund_amount ? ` · بازگشت ${item.refund_amount.toLocaleString("fa-IR")}` : ""}</span></div>)}{!bookings.length && <p className="py-8 text-center text-sm text-slate-500">هنوز رزروی ثبت نشده است.</p>}</div></CardContent></Card>
    <div data-consultant-editor className="scroll-mt-6" />
    {details && <Card className="border-blue-200 bg-white"><CardHeader><CardTitle className="flex items-center justify-between"><span>جزئیات {details.profile.full_name}</span><Button size="sm" variant="ghost" onClick={() => setDetails(null)}><X /></Button></CardTitle></CardHeader><CardContent className="space-y-5"><div className="grid gap-3 sm:grid-cols-3"><InfoWindow title="عملکرد" lines={[`جلسات: ${details.stats.completed_sessions}`, `لغو: ${details.stats.cancelled_sessions}`, `درآمد: ${details.stats.gross_revenue.toLocaleString("fa-IR")} تومان`]} /><InfoWindow title="تسویه و بانک" lines={[`شبا: ${details.profile.bank_iban || "ثبت نشده"}`, `صاحب حساب: ${details.profile.bank_account_holder || "ثبت نشده"}`]} /><InfoWindow title="قرارداد همکاری" lines={[`شماره: ${details.profile.contract_number || "ثبت نشده"}`, `وضعیت: ${details.profile.contract_status}`, `پایان: ${details.profile.contract_end ? new Date(details.profile.contract_end).toLocaleDateString("fa-IR") : "ثبت نشده"}`]} /></div><div className="flex flex-wrap gap-2"><Button size="sm" onClick={() => void editDetails()}>ویرایش اطلاعات و شبا</Button><Button size="sm" variant="outline" onClick={() => void editContract()}>مدیریت قرارداد</Button><Button size="sm" variant="destructive" onClick={() => void blockProfile()}>مسدودسازی موقت</Button></div><div><h3 className="font-bold">مدارک ({details.documents.length})</h3><div className="mt-2 grid gap-2 sm:grid-cols-2">{details.documents.map((item) => <div key={item.id} className="rounded-xl bg-slate-50 p-3 text-xs">{item.title} · {item.filename} · {item.status}</div>)}</div></div><div><h3 className="font-bold">نظرات کاربران</h3><div className="mt-2 space-y-2">{details.reviews.map((item) => <div key={item.id} className="flex items-center justify-between rounded-xl bg-slate-50 p-3 text-xs"><span>{item.rating} از ۵ · {item.comment || "بدون متن"}</span><Button size="sm" variant="outline" onClick={() => void moderateReview(item.id, item.status === "hidden" ? "published" : "hidden")}>{item.status === "hidden" ? "انتشار" : "پنهان‌کردن"}</Button></div>)}</div></div><p className="text-xs text-slate-500">تاریخچه بررسی صلاحیت: {details.verification_history.length} مورد</p></CardContent></Card>}

    <Card className="border-amber-100 bg-white"><CardHeader><CardTitle>درخواست‌های احراز و تغییر پروفایل</CardTitle></CardHeader><CardContent className="space-y-4">{requests.filter((item) => item.status !== "approved").map((item) => <article key={item.id} className="rounded-2xl border p-5"><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="font-black">{item.full_name}</p><p className="mt-1 text-xs text-slate-500">{item.email} · {item.consultant_type === "independent" ? "مستقل" : "شرکتی"}</p><p className="mt-3 font-bold">{item.professional_title}</p><p className="mt-2 text-sm leading-7 text-slate-600">{item.qualifications}</p>{item.profile_payload && <div className="mt-3 grid gap-2 rounded-xl bg-sky-50 p-3 text-xs sm:grid-cols-2"><p>شهر: {item.profile_payload.city || "ثبت نشده"}</p><p>هزینه جلسه: {(item.profile_payload.consultation_price ?? 0).toLocaleString("fa-IR")} تومان</p><p>آنلاین: {item.profile_payload.is_online ? "بله" : "خیر"}</p><p>حضوری: {item.profile_payload.offers_in_person ? "بله" : "خیر"}</p></div>}<div className="mt-3 flex flex-wrap gap-2">{item.specialties.map((specialty) => <Badge variant="secondary" key={specialty}>{specialty}</Badge>)}</div></div><Badge variant={item.status === "rejected" ? "destructive" : "secondary"}>{item.status}</Badge></div><div className="mt-4 rounded-xl bg-slate-50 p-4"><p className="text-sm font-black">مدارک پیوست ({item.documents?.length??0})</p><div className="mt-2 grid gap-2 sm:grid-cols-2">{item.documents?.map(document=><a key={document.id} href={document.download_url} target="_blank" className="rounded-lg border bg-white p-3 text-xs hover:border-blue-300"><strong>{document.title}</strong><span className="mt-1 block text-slate-500">{document.description}</span><span className="mt-2 block font-bold text-blue-700">مشاهده مدرک</span></a>)}</div></div><Textarea className="mt-4" value={notes[item.id] ?? item.admin_note} onChange={(event) => setNotes((current) => ({ ...current, [item.id]: event.target.value }))} placeholder="توضیح مدیر؛ برای رد یا درخواست اصلاح الزامی است" /><div className="mt-3 flex flex-wrap gap-2"><Button size="sm" onClick={() => void review(item.id, "approved")}><Check /> تأیید</Button><Button size="sm" variant="outline" onClick={() => void review(item.id, "correction_required")}>درخواست اصلاح</Button><Button size="sm" variant="destructive" onClick={() => void review(item.id, "rejected")}><X /> رد</Button></div></article>)}{!requests.some((item) => item.status !== "approved") && <p className="py-8 text-center text-sm text-slate-500">درخواست بررسی‌نشده‌ای وجود ندارد.</p>}</CardContent></Card>

    <Card className="border-sky-100 bg-white"><CardHeader><CardTitle>فهرست مشاوران</CardTitle></CardHeader><CardContent><div className="mb-5 grid gap-3 sm:grid-cols-[1fr_220px]"><label className="relative"><Search className="absolute right-3 top-3 size-4 text-slate-400" /><Input className="pr-10" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="جست‌وجوی نام، ایمیل یا تخصص" /></label><select value={type} onChange={(event) => setType(event.target.value)} className="h-10 rounded-lg border bg-white px-3 text-sm"><option value="all">همه مشاوران</option><option value="independent">مستقل</option><option value="company">شرکتی</option></select></div><div className="space-y-3">{visible.map((item) => <article key={item.id} className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border p-4"><div><div className="flex items-center gap-2"><p className="font-black">{item.full_name}</p>{item.is_verified && <Badge className="bg-emerald-50 text-emerald-700">تأییدشده</Badge>}</div><p className="mt-1 text-xs text-slate-500">{item.email} · {item.professional_title}</p><p className="mt-2 text-xs text-slate-500">{item.specialties.join("، ") || "بدون تخصص ثبت‌شده"}</p></div><div className="flex flex-wrap gap-2"><Button size="sm" variant="outline" onClick={() => void showDetails(item.id)}>جزئیات و ویرایش</Button><Button size="sm" variant="outline" onClick={() => void updateProfile(item.id, { is_available: !item.is_available })}>{item.is_available ? "غیرفعال‌کردن پذیرش" : "فعال‌کردن پذیرش"}</Button><Button size="sm" variant={item.is_verified ? "destructive" : "default"} onClick={() => void updateProfile(item.id, { is_verified: !item.is_verified })}>{item.is_verified ? "تعلیق تأیید" : "تأیید مجدد"}</Button><Button size="sm" variant="destructive" onClick={() => void deleteProfile(item.id, item.full_name)}><Trash2 className="size-4" /> حذف</Button></div></article>)}{!visible.length && <p className="py-8 text-center text-sm text-slate-500">مشاوری پیدا نشد.</p>}</div></CardContent></Card>
    {deleted.length > 0 && <Card className="border-rose-100 bg-white"><CardHeader><CardTitle>مشاوران حذف‌شده</CardTitle></CardHeader><CardContent className="space-y-2">{deleted.map((item) => <div key={item.id} className="flex items-center justify-between rounded-xl bg-rose-50 p-4"><div><p className="font-bold">{item.full_name}</p><p className="text-xs text-slate-500">{item.email}</p></div><Button size="sm" variant="outline" onClick={() => void restoreProfile(item.id)}>بازیابی</Button></div>)}</CardContent></Card>}
  </div>;
}

function Metric({ label, value, icon: Icon }: { label: string; value: number; icon: typeof Check }) { return <Card className="border-sky-100 bg-gradient-to-br from-white to-sky-50"><CardContent className="flex items-center gap-4 p-5"><span className="flex size-11 items-center justify-center rounded-2xl bg-blue-100 text-blue-700"><Icon /></span><div><p className="text-2xl font-black">{value.toLocaleString("fa-IR")}</p><p className="text-xs text-slate-500">{label}</p></div></CardContent></Card>; }
function InfoWindow({ title, lines }: { title: string; lines: string[] }) { return <div className="rounded-2xl border bg-gradient-to-br from-white to-sky-50 p-4"><p className="font-black text-blue-700">{title}</p>{lines.map((line) => <p key={line} className="mt-2 text-xs text-slate-600">{line}</p>)}</div>; }
