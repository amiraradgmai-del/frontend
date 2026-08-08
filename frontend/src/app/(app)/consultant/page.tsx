"use client";

import { FormEvent, useEffect, useState } from "react";
import { ArrowDown, BriefcaseBusiness, CalendarDays, CheckCircle2, Clock3, MapPin, Phone, Save, TicketCheck, UserRound, XCircle } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import type { Consultation } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";

type Booking = {
  id: string;
  scheduled_at: string;
  duration_minutes: number;
  mode: string;
  status: string;
  price: number;
  notes: string;
  session_report: string;
  client: { full_name: string; phone: string; city: string; company_name: string; job_title: string; taxpayer_type: string };
};

export default function ConsultantHome() {
  const [items, setItems] = useState<Consultation[]>([]);
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [message, setMessage] = useState("");
  const load = () => Promise.all([api<Consultation[]>("api/v1/consultations/assigned/me"), api<Booking[]>("api/v1/consultations/bookings/consultant/me")]).then(([cases, reservations]) => { setItems(cases); setBookings(reservations); }).catch((error) => setMessage(error instanceof ApiError ? error.message : "دریافت اطلاعات میزکار ممکن نیست."));
  useEffect(() => { void load(); }, []);
  const upcoming = bookings.filter((item) => item.status === "reserved" && new Date(item.scheduled_at) >= new Date());
  return <div className="space-y-7">
    <header className="relative overflow-hidden rounded-[2rem] bg-gradient-to-l from-blue-700 via-blue-600 to-cyan-500 p-8 text-white shadow-xl">
      <div className="absolute -left-16 -top-20 size-56 rounded-full bg-white/10" />
      <div className="relative"><p className="text-sm text-blue-50">مرکز کنترل مشاور مالیاتی</p><h1 className="mt-2 text-3xl font-black">برنامه کاری و پرونده‌های من</h1><p className="mt-2 text-blue-50">رزروها، اطلاعات ضروری مراجعان، پرونده‌ها و تیکت‌ها را سریع مدیریت کنید.</p></div>
      <div className="relative mt-7 grid gap-3 sm:grid-cols-3">
        <a href="#consultant-calendar" className="flex items-center justify-between rounded-2xl bg-white/15 p-4 text-sm font-bold backdrop-blur transition hover:bg-white/25"><span className="flex items-center gap-2"><CalendarDays className="size-5" /> تقویم رزرو</span><ArrowDown className="size-4" /></a>
        <a href="#consultant-cases" className="flex items-center justify-between rounded-2xl bg-white/15 p-4 text-sm font-bold backdrop-blur transition hover:bg-white/25"><span className="flex items-center gap-2"><BriefcaseBusiness className="size-5" /> پرونده‌ها</span><ArrowDown className="size-4" /></a>
        <a href="/consultant/tickets" className="flex items-center justify-between rounded-2xl bg-white p-4 text-sm font-bold text-blue-700 shadow-lg"><span className="flex items-center gap-2"><TicketCheck className="size-5" /> تیکت‌ها</span><span>←</span></a>
      </div>
    </header>
    {message && <p className="rounded-xl bg-red-50 p-4 text-sm text-red-700">{message}</p>}
    <section className="grid gap-4 sm:grid-cols-3"><Metric icon={CalendarDays} label="رزرو آینده" value={upcoming.length} /><Metric icon={BriefcaseBusiness} label="پرونده فعال" value={items.filter((item) => !["resolved", "closed"].includes(item.status)).length} /><Metric icon={CheckCircle2} label="جلسه تکمیل‌شده" value={bookings.filter((item) => item.status === "completed").length} /></section>
    <section id="consultant-calendar" className="scroll-mt-8"><div className="mb-4"><p className="text-sm font-bold text-blue-600">تقویم رزرو</p><h2 className="mt-1 text-2xl font-black">جلسه‌های پیش رو</h2></div><div className="grid gap-4 xl:grid-cols-2">{upcoming.map((booking) => <BookingCard key={booking.id} booking={booking} reload={load} />)}{!upcoming.length && <div className="rounded-2xl border border-dashed bg-white/70 p-10 text-center text-slate-500 xl:col-span-2"><CalendarDays className="mx-auto mb-3" />رزروی برای روزهای آینده ندارید.</div>}</div></section>
    <section id="consultant-cases" className="scroll-mt-8"><div className="mb-4"><p className="text-sm font-bold text-blue-600">پرونده‌ها</p><h2 className="mt-1 text-2xl font-black">پرونده‌های ارجاع‌شده به من</h2></div><div className="space-y-4">{items.map((item) => <CaseCard key={item.id} item={item} reload={load} />)}{!items.length && <div className="rounded-2xl border border-dashed bg-white/60 p-14 text-center text-muted-foreground"><BriefcaseBusiness className="mx-auto mb-3" />پرونده‌ای به شما ارجاع نشده است.</div>}</div></section>
  </div>;
}

function Metric({ icon: Icon, label, value }: { icon: typeof CalendarDays; label: string; value: number }) { return <Card className="border-sky-100 bg-white"><CardContent className="flex items-center gap-4 p-5"><span className="flex size-12 items-center justify-center rounded-2xl bg-blue-100 text-blue-700"><Icon /></span><div><p className="text-2xl font-black">{value.toLocaleString("fa-IR")}</p><p className="text-sm text-slate-500">{label}</p></div></CardContent></Card>; }

function BookingCard({ booking, reload }: { booking: Booking; reload: () => Promise<void> }) {
  const [busy, setBusy] = useState(false);
  const [sessionReport, setSessionReport] = useState(booking.session_report ?? "");
  async function update(status: "completed" | "cancelled") { setBusy(true); try { await api(`api/v1/consultations/bookings/consultant/${booking.id}`, { method: "PATCH", body: JSON.stringify({ status, session_report: sessionReport }) }); await reload(); } finally { setBusy(false); } }
  return <Card className="overflow-hidden border-sky-100 bg-white"><div className="h-1.5 bg-gradient-to-l from-blue-600 to-cyan-400" /><CardContent className="p-5"><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="flex items-center gap-2 font-black"><UserRound className="size-4 text-blue-600" />{booking.client.full_name}</p><p className="mt-2 flex items-center gap-2 text-sm text-slate-600"><Clock3 className="size-4" />{new Date(booking.scheduled_at).toLocaleString("fa-IR")} · {booking.duration_minutes.toLocaleString("fa-IR")} دقیقه</p></div><Badge variant="secondary">{booking.mode === "in_person" ? "حضوری" : booking.mode === "phone" ? "تلفنی" : "آنلاین"}</Badge></div><div className="mt-4 grid gap-2 rounded-2xl bg-sky-50 p-4 text-xs text-slate-600 sm:grid-cols-2">{booking.client.phone && <p className="flex items-center gap-2"><Phone className="size-3.5" />{booking.client.phone}</p>}{booking.client.city && <p className="flex items-center gap-2"><MapPin className="size-3.5" />{booking.client.city}</p>}<p>{booking.client.company_name || "شخص حقیقی"}</p><p>{booking.client.job_title || "عنوان شغلی ثبت نشده"}</p></div>{booking.notes && <p className="mt-3 rounded-xl border p-3 text-sm leading-6">{booking.notes}</p>}<Textarea value={sessionReport} onChange={(event) => setSessionReport(event.target.value)} className="mt-3 min-h-24" placeholder="گزارش جلسه، جمع‌بندی و اقدامات بعدی" /><div className="mt-4 flex gap-2"><Button size="sm" disabled={busy || !sessionReport.trim()} onClick={() => void update("completed")}><CheckCircle2 /> ثبت گزارش و تکمیل جلسه</Button><Button size="sm" variant="outline" disabled={busy} onClick={() => void update("cancelled")}><XCircle /> لغو جلسه</Button></div></CardContent></Card>;
}

function CaseCard({ item, reload }: { item: Consultation; reload: () => Promise<void> }) {
  const [internalNote, setInternalNote] = useState(item.internal_note ?? "");
  const [resolution, setResolution] = useState(item.resolution ?? "");
  const [status, setStatus] = useState(item.status === "submitted" ? "in_review" : item.status);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function save(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError("");
    try { await api(`api/v1/consultations/assigned/${item.id}`, { method: "PATCH", body: JSON.stringify({ status, internal_note: internalNote, resolution, note: "بروزرسانی توسط مشاور" }) }); await reload(); }
    catch (requestError) { setError(requestError instanceof ApiError ? requestError.message : "ذخیره پرونده انجام نشد."); }
    finally { setBusy(false); }
  }
  return <Card className="border-white/70 bg-white/85"><CardHeader><div className="flex flex-wrap items-center justify-between gap-3"><CardTitle>{item.subject}</CardTitle><Badge variant={item.priority === "high" ? "destructive" : "secondary"}>{item.priority === "high" ? "فوری" : "عادی"}</Badge></div></CardHeader><CardContent><p className="rounded-xl bg-slate-50 p-4 text-sm leading-7">{item.description}</p>{error && <p className="mt-3 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}<form onSubmit={save} className="mt-4 grid gap-4 lg:grid-cols-2"><Textarea value={internalNote} onChange={(event) => setInternalNote(event.target.value)} placeholder="یادداشت داخلی" /><Textarea value={resolution} onChange={(event) => setResolution(event.target.value)} placeholder="پاسخ قابل نمایش به کاربر" /><select value={status} onChange={(event) => setStatus(event.target.value)} className="h-10 rounded-lg border bg-white px-3 text-sm"><option value="in_review">در حال بررسی</option><option value="waiting_for_user">منتظر کاربر</option><option value="resolved">پاسخ داده‌شده</option><option value="closed">بسته‌شده</option></select><Button disabled={busy || (status === "resolved" && !resolution.trim())}><Save /> ذخیره پرونده</Button></form></CardContent></Card>;
}
