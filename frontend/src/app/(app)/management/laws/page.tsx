"use client";

import { FormEvent, useEffect, useState } from "react";
import { Archive, BookOpen, Check, Database, Plus, RefreshCw, X } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

type Dashboard = { active_laws: number; archived_laws: number; sources: number; pending_updates: number };
type Category = { id: string; code: string; title: string; is_active: boolean };
type Law = { id: string; law_name: string; article_number: string; official_text: string; category_id: string | null; category_title: string | null; is_active: boolean };
type Source = { id: string; title: string; base_url: string; is_enabled: boolean; last_status: string; last_checked_at: string | null; last_content_length: number };
type Candidate = { id: string; title: string; article_number: string; proposed_text: string; status: string };

export default function LegalManagementPage() {
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);
  const [laws, setLaws] = useState<Law[]>([]);
  const [sources, setSources] = useState<Source[]>([]);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [lawName, setLawName] = useState(""); const [article, setArticle] = useState(""); const [text, setText] = useState(""); const [categoryId, setCategoryId] = useState("");
  const [categoryTitle, setCategoryTitle] = useState(""); const [categoryCode, setCategoryCode] = useState("");
  const [sourceTitle, setSourceTitle] = useState(""); const [sourceUrl, setSourceUrl] = useState("");
  const [busy, setBusy] = useState(false); const [message, setMessage] = useState("");
  const summaryCards = [
    { label: "مواد فعال", value: dashboard?.active_laws ?? 0, icon: BookOpen },
    { label: "بایگانی", value: dashboard?.archived_laws ?? 0, icon: Archive },
    { label: "منابع", value: dashboard?.sources ?? 0, icon: Database },
    { label: "در انتظار بررسی", value: dashboard?.pending_updates ?? 0, icon: RefreshCw },
  ];

  async function load() {
    try {
      const [summary, categoryItems, lawItems, sourceItems, candidateItems] = await Promise.all([
        api<Dashboard>("api/v1/legal/manage/dashboard"), api<Category[]>("api/v1/legal/manage/categories"),
        api<Law[]>("api/v1/legal/manage/laws?include_archived=true"), api<Source[]>("api/v1/legal/manage/sources"),
        api<Candidate[]>("api/v1/legal/manage/candidates"),
      ]);
      setDashboard(summary); setCategories(categoryItems); setLaws(lawItems); setSources(sourceItems); setCandidates(candidateItems); setMessage("");
    } catch (caught) { setMessage(caught instanceof ApiError ? caught.message : "دریافت اطلاعات مدیریت قوانین انجام نشد."); }
  }
  useEffect(() => {
    Promise.all([
      api<Dashboard>("api/v1/legal/manage/dashboard"), api<Category[]>("api/v1/legal/manage/categories"),
      api<Law[]>("api/v1/legal/manage/laws?include_archived=true"), api<Source[]>("api/v1/legal/manage/sources"),
      api<Candidate[]>("api/v1/legal/manage/candidates"),
    ]).then(([summary, categoryItems, lawItems, sourceItems, candidateItems]) => {
      setDashboard(summary); setCategories(categoryItems); setLaws(lawItems); setSources(sourceItems); setCandidates(candidateItems);
    }).catch(() => setMessage("دریافت اطلاعات مدیریت قوانین انجام نشد."));
  }, []);

  async function addLaw(event: FormEvent) {
    event.preventDefault(); setBusy(true);
    try {
      await api("api/v1/legal/manage/laws", { method: "POST", body: JSON.stringify({ law_name: lawName, chapter: "", article_number: article, official_text: text, keywords: "", category_id: categoryId || null, publication_date: null, effective_date: null, source_info: "", source_url: "" }) });
      setLawName(""); setArticle(""); setText(""); await load();
    } catch (caught) { setMessage(caught instanceof ApiError ? caught.message : "ثبت ماده انجام نشد."); } finally { setBusy(false); }
  }
  async function addCategory(event: FormEvent) {
    event.preventDefault(); setBusy(true);
    try { await api("api/v1/legal/manage/categories", { method: "POST", body: JSON.stringify({ code: categoryCode, title: categoryTitle, description: "", sort_order: categories.length * 10 + 10, is_active: true }) }); setCategoryCode(""); setCategoryTitle(""); await load(); }
    catch (caught) { setMessage(caught instanceof ApiError ? caught.message : "ثبت دسته‌بندی انجام نشد."); } finally { setBusy(false); }
  }
  async function addSource(event: FormEvent) {
    event.preventDefault(); setBusy(true);
    try { await api("api/v1/legal/manage/sources", { method: "POST", body: JSON.stringify({ title: sourceTitle, base_url: sourceUrl, source_type: "website", is_enabled: true }) }); setSourceTitle(""); setSourceUrl(""); await load(); }
    catch (caught) { setMessage(caught instanceof ApiError ? caught.message : "ثبت منبع انجام نشد."); } finally { setBusy(false); }
  }
  async function checkSources() {
    setBusy(true); setMessage("");
    try {
      await api("api/v1/legal/manage/sources/check", { method: "POST" });
      setMessage("بررسی منابع در صف اجرا قرار گرفت؛ نتیجه تا چند دقیقه دیگر نمایش داده می‌شود.");
      window.setTimeout(() => void load(), 8000);
    } catch (caught) {
      setMessage(caught instanceof ApiError ? caught.message : "شروع بررسی منابع انجام نشد.");
    } finally { setBusy(false); }
  }
  async function archive(id: string) { if (!window.confirm("این ماده بایگانی شود؟")) return; await api(`api/v1/legal/manage/laws/${id}`, { method: "DELETE" }); await load(); }
  async function review(id: string, decision: "approved" | "rejected") {
    await api(`api/v1/legal/manage/candidates/${id}/review`, { method: "POST", body: JSON.stringify({ decision, note: decision === "rejected" ? "نیازمند بازبینی" : "", category_id: categoryId || null }) }); await load();
  }

  return <div className="space-y-7">
    <header className="flex flex-wrap items-end justify-between gap-4"><div><p className="text-sm font-bold text-blue-600">کنترل محتوای حقوقی</p><h1 className="mt-1 text-3xl font-black">مدیریت قوانین و به‌روزرسانی‌ها</h1><p className="mt-2 text-sm text-slate-500">منابع هر ۷۲ ساعت پایش می‌شوند و هیچ تغییر بیرونی بدون تأیید مدیر منتشر نمی‌شود.</p></div><div className="flex gap-2"><Button disabled={busy} onClick={() => void checkSources()}><RefreshCw /> بررسی اکنون</Button><Button variant="outline" onClick={() => void load()}><RefreshCw /> تازه‌سازی</Button></div></header>
    {message && <p className="rounded-xl bg-red-50 p-4 text-sm text-red-700">{message}</p>}
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {summaryCards.map(({ label, value, icon: Icon }) => <Card key={label} className="border-sky-100 bg-gradient-to-br from-white to-sky-50"><CardContent className="flex items-center justify-between p-5"><div><p className="text-xs text-slate-500">{label}</p><p className="mt-2 text-2xl font-black">{value}</p></div><Icon className="text-blue-600" /></CardContent></Card>)}
    </div>
    <div className="grid gap-6 xl:grid-cols-2">
      <Card><CardHeader><CardTitle>ثبت ماده جدید</CardTitle></CardHeader><CardContent><form onSubmit={addLaw} className="space-y-3"><Input value={lawName} onChange={(event) => setLawName(event.target.value)} placeholder="عنوان قانون" required /><div className="grid gap-3 sm:grid-cols-2"><Input value={article} onChange={(event) => setArticle(event.target.value)} placeholder="شماره ماده" required /><select value={categoryId} onChange={(event) => setCategoryId(event.target.value)} className="h-10 rounded-lg border bg-white px-3 text-sm"><option value="">بدون دسته‌بندی</option>{categories.filter((item) => item.is_active).map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}</select></div><Textarea value={text} onChange={(event) => setText(event.target.value)} placeholder="متن رسمی ماده" className="min-h-32" required /><Button className="w-full" disabled={busy}><Plus /> ثبت ماده</Button></form></CardContent></Card>
      <Card><CardHeader><CardTitle>دسته‌بندی و منبع پایش</CardTitle></CardHeader><CardContent className="space-y-6"><form onSubmit={addCategory} className="grid gap-2 sm:grid-cols-[1fr_1fr_auto]"><Input value={categoryTitle} onChange={(event) => setCategoryTitle(event.target.value)} placeholder="عنوان دسته" required /><Input dir="ltr" value={categoryCode} onChange={(event) => setCategoryCode(event.target.value.toLowerCase())} placeholder="category-code" required /><Button disabled={busy}>ثبت</Button></form><div className="flex flex-wrap gap-2">{categories.map((item) => <Badge key={item.id} variant={item.is_active ? "secondary" : "outline"}>{item.title}</Badge>)}</div><form onSubmit={addSource} className="grid gap-2 sm:grid-cols-[1fr_1fr_auto]"><Input value={sourceTitle} onChange={(event) => setSourceTitle(event.target.value)} placeholder="نام منبع پایش" required /><Input dir="ltr" value={sourceUrl} onChange={(event) => setSourceUrl(event.target.value)} placeholder="https://..." required /><Button disabled={busy}>افزودن</Button></form><div className="max-h-96 space-y-2 overflow-y-auto pl-1">{sources.map((item) => <div key={item.id} className="rounded-xl border p-3 text-sm"><div className="flex items-center justify-between gap-3"><span className="font-semibold">{item.title}</span><Badge variant="outline">{item.last_status === "not_checked" ? "بررسی‌نشده" : item.last_status === "up_to_date" ? "به‌روز" : item.last_status === "change_detected" ? "تغییر شناسایی شد" : "خطا"}</Badge></div><p className="mt-2 text-xs text-slate-500">{item.last_checked_at ? `آخرین بررسی: ${new Date(item.last_checked_at).toLocaleString("fa-IR")}` : "هنوز بررسی نشده"}{item.last_content_length > 0 ? ` · ${item.last_content_length.toLocaleString("fa-IR")} نویسه` : ""}</p></div>)}</div></CardContent></Card>
    </div>
    <Card><CardHeader><CardTitle>صف بررسی به‌روزرسانی‌ها</CardTitle></CardHeader><CardContent className="space-y-3">{candidates.map((item) => <div key={item.id} className="rounded-2xl border p-4"><div className="flex flex-wrap items-center justify-between gap-3"><div><p className="font-bold">{item.title} {item.article_number && `- ماده ${item.article_number}`}</p><p className="mt-2 line-clamp-3 text-xs leading-6 text-slate-500">{item.proposed_text}</p></div><div className="flex gap-2">{item.status === "pending" ? <><Button size="sm" onClick={() => void review(item.id, "approved")}><Check /> تأیید</Button><Button size="sm" variant="destructive" onClick={() => void review(item.id, "rejected")}><X /> رد</Button></> : <Badge>{item.status === "approved" ? "تأییدشده" : "ردشده"}</Badge>}</div></div></div>)}{!candidates.length && <p className="py-8 text-center text-sm text-slate-500">به‌روزرسانی در انتظار بررسی وجود ندارد.</p>}</CardContent></Card>
    <Card><CardHeader><CardTitle>فهرست مواد</CardTitle></CardHeader><CardContent className="space-y-2">{laws.map((item) => <div key={item.id} className="flex items-center justify-between gap-4 rounded-xl border p-4"><div><p className="font-bold">{item.law_name} · ماده {item.article_number}</p><p className="mt-1 line-clamp-1 text-xs text-slate-500">{item.official_text}</p></div>{item.is_active ? <Button variant="outline" size="icon" onClick={() => void archive(item.id)} aria-label="بایگانی"><Archive /></Button> : <Badge variant="outline">بایگانی</Badge>}</div>)}</CardContent></Card>
  </div>;
}
