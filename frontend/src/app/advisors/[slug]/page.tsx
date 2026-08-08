import type { Metadata } from "next";
import Link from "next/link";
import { cookies } from "next/headers";
import { notFound } from "next/navigation";
import { ArrowLeft, ArrowRight, BadgeCheck, Clock3, MapPin, Star, UsersRound, Video } from "lucide-react";
import { PublicFooter } from "@/components/public-footer";
import { PublicHeader } from "@/components/public-header";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { accessCookie, refreshCookie } from "@/lib/backend";
import type { ConsultantProfile } from "@/lib/types";

async function advisor(slug: string): Promise<ConsultantProfile | null> {
  try {
    const response = await fetch(`${process.env.BACKEND_URL ?? "http://localhost:8000"}/api/v1/consultations/public/advisors/${encodeURIComponent(slug)}`, { next: { revalidate: 60 } });
    return response.ok ? response.json() : null;
  } catch {
    return null;
  }
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const item = await advisor((await params).slug);
  return { title: item ? `${item.full_name} | مشاور مالیاتی` : "مشاور مالیاتی", description: item?.professional_title };
}

export default async function AdvisorPage({ params }: { params: Promise<{ slug: string }> }) {
  const slug = (await params).slug;
  const item = await advisor(slug);
  if (!item) notFound();
  const store = await cookies();
  const loggedIn = store.has(accessCookie) || store.has(refreshCookie);
  const target = `/app/consultations/independent/${item.slug}`;
  return <main><PublicHeader /><section className="mx-auto max-w-5xl px-5 py-12"><Link href="/advisors" className="flex items-center gap-2 text-sm text-blue-600"><ArrowRight className="size-4" /> بازگشت به فهرست مشاوران</Link><div className="mt-6 grid gap-6 lg:grid-cols-[1fr_.55fr]"><Card className="overflow-hidden border-orange-100"><div className="h-2 bg-gradient-to-l from-orange-400 to-rose-500" /><CardContent className="p-7"><div className="flex flex-wrap items-start justify-between gap-4"><div><div className="flex items-center gap-2"><h1 className="text-3xl font-black">{item.full_name}</h1><Badge className="bg-emerald-50 text-emerald-700"><BadgeCheck /> تأییدشده</Badge></div><p className="mt-2 text-slate-500">{item.professional_title}</p></div><span className="flex items-center gap-1 rounded-xl bg-amber-50 px-4 py-2 font-black text-amber-700"><Star className="fill-amber-400" />{item.rating.toLocaleString("fa-IR")}</span></div><p className="mt-7 leading-8 text-slate-600">{item.bio || "اطلاعات تکمیلی این مشاور در حال بروزرسانی است."}</p><div className="mt-6 flex flex-wrap gap-2">{item.specialties.map((value) => <Badge variant="secondary" key={value}>{value}</Badge>)}</div><div className="mt-7 grid gap-3 sm:grid-cols-3"><Info icon={Clock3} text={`${item.years_experience.toLocaleString("fa-IR")} سال سابقه`} />{item.is_online && <Info icon={Video} text="مشاوره آنلاین" />}{item.offers_in_person && <Info icon={UsersRound} text="مشاوره حضوری" />}</div>{item.city && <p className="mt-5 flex items-center gap-2 text-sm text-slate-600"><MapPin className="size-4 text-orange-500" />{item.city}</p>}</CardContent></Card><Card className="h-fit border-sky-100 bg-sky-50/50"><CardContent className="p-6"><p className="text-sm text-slate-500">هزینه جلسه ۳۰ دقیقه‌ای</p><p className="mt-2 text-2xl font-black text-blue-700">{item.consultation_price.toLocaleString("fa-IR")} تومان</p><p className="mt-5 text-sm leading-7 text-slate-600">زمان‌های آزاد، نوع جلسه و پرداخت در مرحله بعد نمایش داده می‌شود.</p><Link href={loggedIn ? target : `/login?next=${encodeURIComponent(target)}`} className="mt-6 flex items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-3 font-bold text-white">{loggedIn ? "انتخاب زمان و رزرو" : "ورود برای رزرو"}<ArrowLeft className="size-4" /></Link></CardContent></Card></div></section><PublicFooter /></main>;
}

function Info({ icon: Icon, text }: { icon: typeof Clock3; text: string }) { return <div className="flex items-center gap-2 rounded-xl bg-orange-50 p-3 text-sm text-orange-800"><Icon className="size-4" />{text}</div>; }
