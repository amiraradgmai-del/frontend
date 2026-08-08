"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ArrowLeft, ArrowRight, BadgeCheck, MapPin, RotateCcw, Search, SlidersHorizontal, Star, UserRoundSearch, UsersRound, Video } from "lucide-react";
import { api } from "@/lib/api";
import type { ConsultantProfile } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

type Booking = { id: string; consultant_name: string; scheduled_at: string; mode: string; status: string; price: number; reviewed: boolean };

export default function IndependentConsultantsPage() {
  const [items, setItems] = useState<ConsultantProfile[]>([]);
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [query, setQuery] = useState("");
  const [city, setCity] = useState("all");
  const [specialty, setSpecialty] = useState("all");
  const [minimumRating, setMinimumRating] = useState("0");
  const [mode, setMode] = useState("all");

  const loadBookings = () => api<Booking[]>("api/v1/consultations/bookings/mine").then(setBookings);
  useEffect(() => { void Promise.all([api<ConsultantProfile[]>("api/v1/consultations/advisors?type=independent").then(setItems), loadBookings()]); }, []);

  const cities = useMemo(() => [...new Set(items.map((item) => item.city).filter(Boolean))].sort(), [items]);
  const specialties = useMemo(() => [...new Set(items.flatMap((item) => item.specialties))].sort(), [items]);
  const visible = useMemo(() => items.filter((item) => {
    const textMatches = `${item.full_name} ${item.professional_title} ${item.specialties.join(" ")} ${item.city}`.includes(query.trim());
    const cityMatches = city === "all" || item.city === city;
    const specialtyMatches = specialty === "all" || item.specialties.includes(specialty);
    const ratingMatches = item.rating >= Number(minimumRating);
    const modeMatches = mode === "all" || (mode === "online" ? item.is_online : item.offers_in_person);
    return textMatches && cityMatches && specialtyMatches && ratingMatches && modeMatches;
  }), [items, query, city, specialty, minimumRating, mode]);

  function resetFilters() { setQuery(""); setCity("all"); setSpecialty("all"); setMinimumRating("0"); setMode("all"); }

  return <div className="space-y-7">
    <header><Link href="/app/consultations" className="mb-3 flex items-center gap-2 text-sm text-blue-600"><ArrowRight className="size-4" /> مرکز مشاوران</Link><p className="text-sm font-bold text-orange-600">انتخاب و رزرو مستقیم</p><h1 className="mt-1 text-3xl font-black">مشاوران مستقل مالیاتی</h1><p className="mt-2 text-slate-500">مشاور مناسب را براساس تخصص، شهر، امتیاز و نوع جلسه پیدا کنید.</p></header>

    {bookings.length > 0 && <section className="rounded-3xl border border-blue-100 bg-white p-5"><h2 className="font-black">رزروهای من</h2><div className="mt-4 grid gap-3 lg:grid-cols-2">{bookings.map((booking) => <div key={booking.id} className="rounded-2xl bg-sky-50 p-4"><div className="flex items-center justify-between"><div><p className="font-bold">{booking.consultant_name}</p><p className="mt-1 text-xs text-slate-500">{new Date(booking.scheduled_at).toLocaleString("fa-IR")} · {booking.status === "completed" ? "انجام‌شده" : booking.status === "cancelled" ? "لغوشده" : "رزروشده"}</p></div><Badge variant="secondary">{booking.mode === "in_person" ? "حضوری" : "آنلاین"}</Badge></div>{booking.status === "reserved" && <div className="mt-4 flex gap-2"><Button size="sm" variant="outline" onClick={async () => { const value = window.prompt("زمان جدید را به قالب 2026-08-01T10:00 وارد کنید"); if (value) { await api(`api/v1/consultations/bookings/${booking.id}/reschedule`, { method: "PATCH", body: JSON.stringify({ scheduled_at: value }) }); await loadBookings(); } }}>تغییر زمان</Button><Button size="sm" variant="destructive" onClick={async () => { if (window.confirm("رزرو لغو شود؟")) { await api(`api/v1/consultations/bookings/${booking.id}/cancel`, { method: "POST" }); await loadBookings(); } }}>لغو رزرو</Button></div>}{booking.status === "completed" && !booking.reviewed && <Button className="mt-4" size="sm" onClick={async () => { const value = Number(window.prompt("امتیاز از ۱ تا ۵")); if (value >= 1 && value <= 5) { await api(`api/v1/consultations/bookings/${booking.id}/review`, { method: "POST", body: JSON.stringify({ rating: value, comment: "" }) }); await loadBookings(); } }}><Star /> ثبت امتیاز</Button>}</div>)}</div></section>}

    <section className="rounded-3xl border border-sky-100 bg-gradient-to-br from-white to-sky-50/70 p-5 shadow-lg shadow-slate-900/5">
      <div className="mb-4 flex items-center justify-between"><h2 className="flex items-center gap-2 font-black"><SlidersHorizontal className="size-5 text-blue-600" /> فیلتر جست‌وجو</h2><Button type="button" variant="ghost" size="sm" onClick={resetFilters}><RotateCcw className="size-4" /> پاک‌کردن</Button></div>
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
        <label className="relative xl:col-span-2"><Search className="absolute right-4 top-3 size-4 text-slate-400" /><Input value={query} onChange={(event) => setQuery(event.target.value)} className="pr-11" placeholder="نام، عنوان یا تخصص مشاور" /></label>
        <FilterSelect value={city} onChange={setCity} label="همه شهرها" options={cities} />
        <FilterSelect value={specialty} onChange={setSpecialty} label="همه تخصص‌ها" options={specialties} />
        <select value={minimumRating} onChange={(event) => setMinimumRating(event.target.value)} className="h-10 rounded-xl border border-input bg-white px-3 text-sm"><option value="0">همه امتیازها</option><option value="4">امتیاز ۴ به بالا</option><option value="4.5">امتیاز ۴٫۵ به بالا</option></select>
        <select value={mode} onChange={(event) => setMode(event.target.value)} className="h-10 rounded-xl border border-input bg-white px-3 text-sm"><option value="all">حضوری یا آنلاین</option><option value="online">فقط آنلاین</option><option value="in_person">فقط حضوری</option></select>
      </div>
      <p className="mt-4 text-xs text-slate-500">{visible.length.toLocaleString("fa-IR")} مشاور مطابق انتخاب شما</p>
    </section>

    <section className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">{visible.map((advisor) => <Link href={`/app/consultations/independent/${advisor.slug}`} key={advisor.id} className="group overflow-hidden rounded-3xl border border-orange-100 bg-white shadow-lg shadow-slate-900/5 transition hover:-translate-y-1 hover:shadow-2xl"><div className="h-2 bg-gradient-to-l from-orange-400 to-rose-500" /><div className="p-6"><div className="flex items-start justify-between"><span className="flex size-14 items-center justify-center rounded-2xl bg-orange-50 text-orange-600"><UserRoundSearch /></span>{advisor.is_verified && <Badge className="bg-emerald-50 text-emerald-700"><BadgeCheck /> تأییدشده</Badge>}</div><h2 className="mt-5 text-xl font-black">{advisor.full_name}</h2><p className="mt-1 text-sm text-slate-500">{advisor.professional_title}</p><div className="mt-4 flex flex-wrap items-center gap-3 text-xs"><span className="flex items-center gap-1 font-bold text-amber-600"><Star className="size-4 fill-amber-400" />{advisor.rating.toLocaleString("fa-IR")}</span><span>{advisor.years_experience.toLocaleString("fa-IR")} سال سابقه</span>{advisor.city && <span className="flex items-center gap-1"><MapPin className="size-3.5" />{advisor.city}</span>}</div><div className="mt-4 flex flex-wrap gap-2">{advisor.specialties.slice(0, 3).map((item) => <Badge variant="secondary" key={item}>{item}</Badge>)}</div><div className="mt-4 flex gap-2 text-[11px]">{advisor.is_online && <span className="flex items-center gap-1 rounded-full bg-sky-50 px-2 py-1 text-sky-700"><Video className="size-3" /> آنلاین</span>}{advisor.offers_in_person && <span className="flex items-center gap-1 rounded-full bg-orange-50 px-2 py-1 text-orange-700"><UsersRound className="size-3" /> حضوری</span>}</div><div className="mt-6 flex items-center justify-between border-t pt-4"><div><p className="text-xs text-slate-400">هر جلسه ۳۰ دقیقه</p><p className="mt-1 font-black">{advisor.consultation_price.toLocaleString("fa-IR")} تومان</p></div><ArrowLeft className="text-orange-500 transition group-hover:-translate-x-1" /></div></div></Link>)}{!visible.length && <div className="rounded-3xl border border-dashed p-12 text-center text-sm text-slate-500 md:col-span-2 xl:col-span-3">مشاوری با این مشخصات پیدا نشد.</div>}</section>
  </div>;
}

function FilterSelect({ value, onChange, label, options }: { value: string; onChange: (value: string) => void; label: string; options: string[] }) {
  return <select value={value} onChange={(event) => onChange(event.target.value)} className="h-10 rounded-xl border border-input bg-white px-3 text-sm"><option value="all">{label}</option>{options.map((option) => <option key={option} value={option}>{option}</option>)}</select>;
}
