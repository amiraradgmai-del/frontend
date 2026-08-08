"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { ArrowLeft, BadgeCheck, MapPin, Search, Star, UserRoundSearch } from "lucide-react";
import type { ConsultantProfile } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";

export function AdvisorDirectory({ items }: { items: ConsultantProfile[] }) {
  const [query, setQuery] = useState("");
  const [city, setCity] = useState("all");
  const [specialty, setSpecialty] = useState("all");
  const cities = useMemo(() => [...new Set(items.map((item) => item.city).filter(Boolean))].sort(), [items]);
  const specialties = useMemo(() => [...new Set(items.flatMap((item) => item.specialties))].sort(), [items]);
  const visible = useMemo(() => items.filter((item) => {
    const text = `${item.full_name} ${item.professional_title} ${item.specialties.join(" ")}`;
    return text.includes(query.trim()) && (city === "all" || item.city === city) && (specialty === "all" || item.specialties.includes(specialty));
  }), [items, query, city, specialty]);

  return <section className="mx-auto max-w-6xl px-5 py-12">
    <div><p className="text-sm font-bold text-orange-600">مشاوران تأییدشده</p><h1 className="mt-2 text-3xl font-black">فهرست و رزرو مشاوران مالیاتی</h1><p className="mt-3 text-sm text-slate-500">مشاهده پروفایل برای همه آزاد است؛ ثبت نهایی رزرو پس از ورود انجام می‌شود.</p></div>
    <div className="mt-8 grid gap-3 rounded-2xl border border-sky-100 bg-sky-50/50 p-4 md:grid-cols-3">
      <label className="relative"><Search className="absolute right-3 top-3 size-4 text-slate-400" /><Input className="pr-10" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="نام یا تخصص مشاور" /></label>
      <select className="h-10 rounded-lg border bg-white px-3 text-sm" value={city} onChange={(event) => setCity(event.target.value)}><option value="all">همه شهرها</option>{cities.map((item) => <option key={item}>{item}</option>)}</select>
      <select className="h-10 rounded-lg border bg-white px-3 text-sm" value={specialty} onChange={(event) => setSpecialty(event.target.value)}><option value="all">همه تخصص‌ها</option>{specialties.map((item) => <option key={item}>{item}</option>)}</select>
    </div>
    <p className="mt-4 text-xs text-slate-500">{visible.length.toLocaleString("fa-IR")} مشاور پیدا شد</p>
    <div className="mt-6 space-y-3">{visible.map((advisor) => <Link key={advisor.id} href={`/advisors/${advisor.slug}`} className="group flex flex-col gap-4 rounded-2xl border border-sky-100 bg-white p-5 shadow-sm transition hover:border-blue-200 hover:shadow-lg md:flex-row md:items-center">
      <span className="flex size-12 shrink-0 items-center justify-center rounded-2xl bg-blue-50 text-blue-600"><UserRoundSearch /></span>
      <div className="min-w-0 flex-1"><div className="flex flex-wrap items-center gap-2"><h2 className="font-black">{advisor.full_name}</h2>{advisor.is_verified && <Badge className="bg-emerald-50 text-emerald-700"><BadgeCheck className="size-3" /> تأییدشده</Badge>}</div><p className="mt-1 text-sm text-slate-500">{advisor.professional_title}</p></div>
      <p className="flex items-center gap-2 text-sm"><Star className="size-4 fill-amber-400 text-amber-500" />{advisor.rating.toLocaleString("fa-IR")}</p>
      <p className="flex items-center gap-2 text-sm"><MapPin className="size-4 text-blue-500" />{advisor.city || "آنلاین"}</p>
      <div className="flex flex-wrap gap-1.5 md:max-w-72">{advisor.specialties.slice(0, 3).map((item) => <Badge variant="secondary" key={item}>{item}</Badge>)}</div>
      <ArrowLeft className="size-5 text-blue-600 transition group-hover:-translate-x-1" />
    </Link>)}{!visible.length && <div className="rounded-2xl border border-dashed p-12 text-center text-slate-500">مشاوری با این مشخصات پیدا نشد.</div>}</div>
  </section>;
}
