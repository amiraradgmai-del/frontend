"use client";

import { FormEvent, useEffect, useState } from "react";
import { BookOpen, ChevronDown, FileSearch, MessageCircleQuestion, Search, X } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

type Category = { id: string; title: string; description: string; law_count: number };
type SuggestedQuestion = { question: string; answer: string };
type Law = { id: string; law_name: string; chapter: string; article_number: string; official_text: string; category_title: string | null; publication_date: string | null; effective_date: string | null; suggested_questions: SuggestedQuestion[] };

export default function LegalCenterPage() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [laws, setLaws] = useState<Law[]>([]);
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [expandedId, setExpandedId] = useState("");
  const [openQuestion, setOpenQuestion] = useState("");
  const [hasMore, setHasMore] = useState(false);

  async function load(search = query, categoryId = category, offset = 0) {
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams();
      if (search.trim()) params.set("q", search.trim());
      if (categoryId) params.set("category_id", categoryId);
      params.set("offset", String(offset));
      params.set("limit", "20");
      const result = await api<Law[]>(`api/v1/legal/search?${params}`);
      setLaws((items) => offset ? [...items, ...result] : result);
      setHasMore(result.length === 20);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "دریافت قوانین انجام نشد. دوباره تلاش کنید.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    Promise.all([api<Category[]>("api/v1/legal/categories"), api<Law[]>("api/v1/legal/search")])
      .then(([categoryItems, lawItems]) => {
        setCategories(categoryItems);
        setLaws(lawItems);
        setHasMore(lawItems.length === 20);
      })
      .catch(() => setError("مرکز قوانین در دسترس نیست."))
      .finally(() => setLoading(false));
  }, []);

  function submit(event: FormEvent) {
    event.preventDefault();
    void load();
  }

  function clearFilters() {
    setQuery("");
    setCategory("");
    void load("", "");
  }

  return <div className="space-y-6">
    <header className="relative overflow-hidden rounded-[2rem] bg-gradient-to-l from-blue-700 via-blue-600 to-cyan-500 p-7 text-white shadow-xl shadow-blue-900/15 sm:p-9">
      <div className="absolute -left-12 -top-16 size-52 rounded-full bg-white/10" />
      <div className="relative">
        <span className="flex size-12 items-center justify-center rounded-2xl bg-white/15"><BookOpen /></span>
        <p className="mt-5 text-sm font-bold text-cyan-100">مرجع یکپارچه و قابل جست‌وجو</p>
        <h1 className="mt-1 text-2xl font-black sm:text-3xl">مرکز قوانین و مقررات مالیاتی</h1>
        <p className="mt-3 max-w-2xl text-sm leading-7 text-blue-50">نام قانون، شماره ماده یا بخشی از متن موردنظر را وارد کنید تا دقیق‌ترین نتیجه نمایش داده شود.</p>
      </div>
    </header>

    <Card className="border-sky-100 bg-white/95 shadow-sm"><CardContent className="pt-6">
      <form onSubmit={submit} className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_260px_auto]">
        <div className="relative"><Search className="absolute right-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" /><Input className="pr-10" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="مثلاً: ماده ۲۳۸ یا مالیات بر ارزش افزوده" /></div>
        <select aria-label="دسته‌بندی قانون" value={category} onChange={(event) => { setCategory(event.target.value); void load(query, event.target.value); }} className="h-10 rounded-lg border border-input bg-white px-3 text-sm">
          <option value="">همه دسته‌بندی‌ها</option>
          {categories.filter((item) => item.law_count > 0).map((item) => <option key={item.id} value={item.id}>{item.title} ({item.law_count.toLocaleString("fa-IR")})</option>)}
        </select>
        <Button disabled={loading}><Search /> {loading ? "در حال جست‌وجو…" : "جست‌وجو"}</Button>
      </form>
      {(query || category) && <button type="button" onClick={clearFilters} className="mt-3 inline-flex items-center gap-1 text-xs font-bold text-slate-500 hover:text-blue-700"><X className="size-3.5" /> پاک‌کردن فیلترها</button>}
    </CardContent></Card>

    {error && <p role="alert" className="rounded-xl border border-red-100 bg-red-50 p-4 text-sm text-red-700">{error}</p>}
    {!loading && laws.length > 0 && <p className="text-sm text-slate-500"><span className="font-bold text-slate-800">{laws.length.toLocaleString("fa-IR")}</span> نتیجه پیدا شد</p>}
    <div className="grid gap-4">
      {laws.map((law) => {
        const expanded = expandedId === law.id;
        return <article key={law.id} className="overflow-hidden rounded-2xl border border-sky-100 bg-white shadow-sm transition hover:border-blue-200 hover:shadow-md">
          <button type="button" aria-expanded={expanded} onClick={() => { setExpandedId(expanded ? "" : law.id); setOpenQuestion(""); }} className="w-full p-5 text-right sm:p-6">
            <div className="flex items-start justify-between gap-4"><div><div className="flex flex-wrap items-center gap-2"><Badge className="text-sm">ماده {law.article_number}</Badge>{law.category_title && <Badge variant="outline">{law.category_title}</Badge>}</div><h2 className="mt-4 text-lg font-black text-slate-900">{law.law_name}</h2>{law.chapter && <p className="mt-1 text-xs font-medium text-slate-500">{law.chapter}</p>}<p className="mt-3 line-clamp-2 text-sm leading-7 text-slate-600">{law.official_text}</p></div><ChevronDown className={`mt-2 size-5 shrink-0 text-blue-600 transition ${expanded ? "rotate-180" : ""}`} /></div>
          </button>
          {expanded && <div className="border-t border-slate-100 bg-slate-50/50 p-5 sm:p-6">
            <div className="rounded-2xl border bg-white p-5"><p className="mb-3 text-xs font-black text-blue-700">متن رسمی ماده</p><p className="whitespace-pre-line text-sm leading-9 text-slate-800">{law.official_text}</p></div>
            <div className="mt-5"><p className="flex items-center gap-2 text-sm font-black text-slate-800"><MessageCircleQuestion className="size-4 text-blue-600" /> پرسش‌های کاربردی این ماده</p><div className="mt-3 space-y-2">{law.suggested_questions.map((item, index) => { const key = `${law.id}-${index}`; const questionOpen = openQuestion === key; return <div key={key} className="overflow-hidden rounded-xl border bg-white"><button type="button" onClick={() => setOpenQuestion(questionOpen ? "" : key)} className="flex w-full items-center justify-between gap-3 p-4 text-right text-sm font-bold"><span>{item.question}</span><ChevronDown className={`size-4 shrink-0 text-blue-600 transition ${questionOpen ? "rotate-180" : ""}`} /></button>{questionOpen && <p className="whitespace-pre-line border-t bg-blue-50/40 p-4 text-sm leading-8 text-slate-700">{item.answer}</p>}</div>; })}</div></div>
          </div>}
        </article>;
      })}
    </div>

    {!loading && !laws.length && !error && <div className="rounded-3xl border border-dashed border-sky-200 bg-white/70 py-14 text-center"><FileSearch className="mx-auto size-10 text-sky-300" /><p className="mt-3 font-bold text-slate-700">قانونی با این مشخصات پیدا نشد</p><p className="mt-1 text-sm text-slate-500">شماره ماده را بدون کلمه «ماده» نیز امتحان کنید.</p></div>}
    {loading && <div className="py-10 text-center text-sm text-slate-500">در حال دریافت قوانین…</div>}
    {!loading && hasMore && <div className="text-center"><Button variant="outline" onClick={() => void load(query, category, laws.length)}>نمایش قوانین بیشتر</Button></div>}
  </div>;
}
