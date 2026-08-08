"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, Clock3, RefreshCw, Save, ShieldAlert } from "lucide-react";
import { api } from "@/lib/api";
import type { Consultation } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";

const statusLabels: Record<string, string> = {
  submitted: "جدید", in_review: "در حال بررسی", waiting_for_user: "منتظر کاربر",
  resolved: "پاسخ داده‌شده", closed: "بسته‌شده",
};

type ConsultantOption = { id: string; full_name: string; email: string };

export default function AdminConsultationsPage() {
  const [items, setItems] = useState<Consultation[]>([]);
  const [consultants, setConsultants] = useState<ConsultantOption[]>([]);
  const [filter, setFilter] = useState("open");
  const [busyId, setBusyId] = useState("");
  const [error, setError] = useState("");

  function load() {
    Promise.all([
      api<Consultation[]>("api/v1/consultations/manage/all"),
      api<ConsultantOption[]>("api/v1/consultations/manage/consultants"),
    ]).then(([requests, options]) => { setItems(requests); setConsultants(options); setError(""); })
      .catch(() => setError("دریافت درخواست‌های مشاوره ممکن نیست."));
  }

  useEffect(() => {
    Promise.all([
      api<Consultation[]>("api/v1/consultations/manage/all"),
      api<ConsultantOption[]>("api/v1/consultations/manage/consultants"),
    ]).then(([requests, options]) => { setItems(requests); setConsultants(options); setError(""); })
      .catch(() => setError("دریافت درخواست‌های مشاوره ممکن نیست."));
  }, []);

  async function update(item: Consultation, changes: Partial<Consultation> & { note?: string }) {
    setBusyId(item.id); setError("");
    try {
      const updated = await api<Consultation>(`api/v1/consultations/manage/${item.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          status: changes.status ?? item.status,
          priority: changes.priority ?? item.priority,
          assigned_to: changes.assigned_to !== undefined ? changes.assigned_to : item.assigned_to,
          internal_note: changes.internal_note ?? item.internal_note ?? "",
          resolution: changes.resolution ?? item.resolution ?? "",
          note: changes.note ?? "",
        }),
      });
      setItems((requests) => requests.map((request) => request.id === updated.id ? updated : request));
    } catch { setError("ذخیره تغییرات انجام نشد؛ برای وضعیت پاسخ‌داده‌شده، متن پاسخ الزامی است."); }
    finally { setBusyId(""); }
  }

  const visible = items.filter((item) => filter === "all" || (filter === "open" ? !["resolved", "closed"].includes(item.status) : item.status === filter));

  return (
    <div className="space-y-7">
      <header className="flex flex-wrap items-end justify-between gap-4"><div><p className="text-sm font-medium text-primary">بررسی انسانی</p><h1 className="mt-1 text-3xl font-black">پنل مشاور مالیاتی</h1><p className="mt-2 text-muted-foreground">درخواست‌ها را بررسی و پاسخ نهایی را برای کاربر ثبت کنید.</p></div><Button variant="outline" onClick={load}><RefreshCw /> بروزرسانی</Button></header>
      <div className="grid gap-4 sm:grid-cols-3"><Summary icon={Clock3} label="در انتظار بررسی" value={items.filter((item) => ["submitted", "in_review", "waiting_for_user"].includes(item.status)).length} /><Summary icon={ShieldAlert} label="اولویت بالا" value={items.filter((item) => item.priority === "high" && !["resolved", "closed"].includes(item.status)).length} /><Summary icon={CheckCircle2} label="پاسخ داده‌شده" value={items.filter((item) => item.status === "resolved").length} /></div>
      <div className="flex flex-wrap gap-2">{[["open", "باز"], ["submitted", "جدید"], ["in_review", "در بررسی"], ["resolved", "پاسخ‌داده‌شده"], ["all", "همه"]].map(([value, label]) => <Button key={value} size="sm" variant={filter === value ? "default" : "outline"} onClick={() => setFilter(value)}>{label}</Button>)}</div>
      {error && <p className="rounded-xl bg-red-50 p-4 text-sm text-red-700">{error}</p>}
      <section className="space-y-4">{visible.map((item) => <ConsultationCard key={item.id} item={item} consultants={consultants} busy={busyId === item.id} onUpdate={update} />)}{visible.length === 0 && <div className="rounded-2xl border border-dashed bg-white/60 p-14 text-center text-muted-foreground">درخواستی در این بخش وجود ندارد.</div>}</section>
    </div>
  );
}

function ConsultationCard({ item, consultants, busy, onUpdate }: { item: Consultation; consultants: ConsultantOption[]; busy: boolean; onUpdate: (item: Consultation, changes: Partial<Consultation> & { note?: string }) => Promise<void> }) {
  const [internalNote, setInternalNote] = useState(item.internal_note ?? "");
  const [resolution, setResolution] = useState(item.resolution ?? "");
  return <Card className="border-white/70 bg-white/85"><CardHeader><div className="flex flex-wrap items-start justify-between gap-4"><div><div className="flex flex-wrap items-center gap-2"><CardTitle>{item.subject}</CardTitle>{item.priority === "high" && <Badge variant="destructive">فوری</Badge>}<Badge variant="secondary">{statusLabels[item.status] ?? item.status}</Badge></div><CardDescription className="mt-2">ثبت‌شده در {new Date(item.created_at).toLocaleString("fa-IR")}</CardDescription></div><div className="flex flex-wrap gap-2"><select value={item.assigned_to ?? ""} onChange={(event) => void onUpdate(item, { assigned_to: event.target.value || null, status: event.target.value ? "in_review" : item.status })} className="h-9 rounded-lg border bg-white px-3 text-sm"><option value="">بدون مشاور</option>{consultants.map((consultant) => <option value={consultant.id} key={consultant.id}>{consultant.full_name}</option>)}</select><select value={item.priority} onChange={(event) => void onUpdate(item, { priority: event.target.value })} className="h-9 rounded-lg border bg-white px-3 text-sm"><option value="normal">اولویت عادی</option><option value="high">اولویت بالا</option></select><select value={item.status} onChange={(event) => void onUpdate(item, { status: event.target.value, resolution })} className="h-9 rounded-lg border bg-white px-3 text-sm"><option value="submitted">جدید</option><option value="in_review">در حال بررسی</option><option value="waiting_for_user">منتظر کاربر</option><option value="resolved">پاسخ داده‌شده</option><option value="closed">بسته‌شده</option></select></div></div></CardHeader><CardContent className="space-y-4"><div className="rounded-xl bg-slate-50 p-4 text-sm leading-7"><p className="mb-1 text-xs font-semibold text-muted-foreground">شرح کاربر</p>{item.description}</div><div className="grid gap-4 lg:grid-cols-2"><label className="space-y-2 text-sm font-medium"><span>یادداشت داخلی</span><Textarea value={internalNote} onChange={(event) => setInternalNote(event.target.value)} className="min-h-28" placeholder="فقط تیم مجاز می‌بیند" /></label><label className="space-y-2 text-sm font-medium"><span>پاسخ قابل‌نمایش به کاربر</span><Textarea value={resolution} onChange={(event) => setResolution(event.target.value)} className="min-h-28" placeholder="نتیجه بررسی تخصصی" /></label></div><div className="flex flex-wrap gap-2"><Button size="sm" disabled={busy} onClick={() => void onUpdate(item, { status: resolution.trim() ? "resolved" : item.status, internal_note: internalNote, resolution, note: resolution.trim() ? "پاسخ مشاور ثبت شد" : "یادداشت‌ها بروزرسانی شد" })}><Save /> {resolution.trim() ? "ثبت پاسخ نهایی" : "ذخیره یادداشت"}</Button>{item.status === "resolved" && <Button size="sm" variant="secondary" disabled={busy} onClick={() => void onUpdate(item, { status: "closed", internal_note: internalNote, resolution, note: "درخواست بسته شد" })}>بستن درخواست</Button>}</div></CardContent></Card>;
}

function Summary({ icon: Icon, label, value }: { icon: typeof Clock3; label: string; value: number }) {
  return <Card className="border-white/70 bg-white/80"><CardContent className="flex items-center gap-4 p-5"><span className="flex size-11 items-center justify-center rounded-xl bg-primary/10 text-primary"><Icon /></span><div><p className="text-2xl font-black">{value}</p><p className="text-sm text-muted-foreground">{label}</p></div></CardContent></Card>;
}
