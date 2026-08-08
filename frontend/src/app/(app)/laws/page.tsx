"use client";

import { FormEvent, useEffect, useState } from "react";
import { BookOpen, Search } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

type Category = { id: string; title: string; description: string };
type Law = { id: string; law_name: string; chapter: string; article_number: string; official_text: string; category_title: string | null; publication_date: string | null; effective_date: string | null };

export default function LegalCenterPage() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [laws, setLaws] = useState<Law[]>([]);
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load(search = query, categoryId = category) {
    setLoading(true); setError("");
    try {
      const params = new URLSearchParams();
      if (search.trim()) params.set("q", search.trim());
      if (categoryId) params.set("category_id", categoryId);
      setLaws(await api<Law[]>(`api/v1/legal/search?${params}`));
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "دریافت قوانین انجام نشد.");
    } finally { setLoading(false); }
  }

  useEffect(() => {
    Promise.all([api<Category[]>("api/v1/legal/categories"), api<Law[]>("api/v1/legal/search")])
      .then(([categoryItems, lawItems]) => { setCategories(categoryItems); setLaws(lawItems); })
      .catch(() => setError("مرکز قوانین در دسترس نیست."))
      .finally(() => setLoading(false));
  }, []);

  function submit(event: FormEvent) { event.preventDefault(); void load(); }
  return <div className="space-y-7">
    <header className="overflow-hidden rounded-[2rem] bg-gradient-to-l from-cyan-600 via-blue-600 to-indigo-600 p-8 text-white shadow-xl shadow-blue-200/60">
      <BookOpen className="size-10 text-cyan-100" />
      <p className="mt-4 text-sm text-cyan-100">مرجع یکپارچه و قابل جست‌وجو</p>
      <h1 className="mt-1 text-3xl font-black">مرکز قوانین و مقررات</h1>
      <p className="mt-3 max-w-2xl text-sm leading-7 text-blue-50">مواد قانونی را با عنوان، شماره ماده یا کلیدواژه پیدا کنید.</p>
    </header>
    <Card className="border-sky-100 bg-white/90"><CardContent className="pt-6">
      <form onSubmit={submit} className="grid gap-3 md:grid-cols-[1fr_240px_auto]">
        <Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="عنوان، شماره ماده یا کلیدواژه" />
        <select value={category} onChange={(event) => { setCategory(event.target.value); void load(query, event.target.value); }} className="h-10 rounded-lg border border-input bg-white px-3 text-sm">
          <option value="">همه دسته‌بندی‌ها</option>
          {categories.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}
        </select>
        <Button disabled={loading}><Search /> جست‌وجو</Button>
      </form>
    </CardContent></Card>
    {error && <p className="rounded-xl bg-red-50 p-4 text-sm text-red-700">{error}</p>}
    <div className="space-y-3">
      {laws.map((law) => <article key={law.id} className="rounded-2xl border border-sky-100 bg-white px-5 py-5 shadow-sm transition hover:border-blue-200 hover:shadow-md sm:px-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start">
          <div className="flex shrink-0 flex-wrap items-center gap-2 lg:w-52"><Badge>ماده {law.article_number}</Badge>{law.category_title && <Badge variant="outline">{law.category_title}</Badge>}</div>
          <div className="min-w-0 flex-1"><h2 className="text-base font-black sm:text-lg">{law.law_name}</h2>{law.chapter && <p className="mt-1 text-xs text-slate-500">{law.chapter}</p>}<p className="mt-3 whitespace-pre-line text-sm leading-8 text-slate-700">{law.official_text}</p></div>
        </div>
      </article>)}
    </div>
    {!loading && !laws.length && <div className="rounded-3xl border border-dashed border-sky-200 bg-white/70 py-16 text-center text-sm text-slate-500">موردی با این مشخصات پیدا نشد.</div>}
    {loading && <div className="py-12 text-center text-sm text-slate-500">در حال دریافت قوانین…</div>}
  </div>;
}
