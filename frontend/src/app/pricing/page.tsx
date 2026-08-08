import type { Metadata } from "next";
import Link from "next/link";
import { Check } from "lucide-react";
import { PublicFooter } from "@/components/public-footer";
import { PublicHeader } from "@/components/public-header";

export const metadata: Metadata = { title: "تعرفه و پلن‌های اشتراک", description: "مقایسه پلن‌های عادی، پلاس و حرفه‌ای دستیار مالیاتی" };
const plans = [
  ["عادی", "رایگان", ["۵ جست‌وجوی قانون", "۱۰ محاسبه مالیاتی", "یک درخواست پشتیبانی"]],
  ["پلاس", "از ۱۴۹ هزار تومان", ["۱۰۰ پرسش هوشمند", "۱۰۰ جست‌وجوی قانون", "۱۰ نامه مالیاتی", "رزرو مشاور مستقل حضوری یا آنلاین"]],
  ["حرفه‌ای", "از ۵۴۹ هزار تومان", ["۱۰۰۰ پرسش هوشمند", "ظرفیت حرفه‌ای ابزارها", "۲۰ سند", "رزرو مشاور مستقل حضوری یا آنلاین"]],
] as const;
export default function PricingPage() { return <main><PublicHeader /><section className="mx-auto max-w-6xl px-5 py-14 text-center"><p className="font-bold text-primary">شفاف و قابل ارتقا</p><h1 className="mt-3 text-4xl font-black">پلن مناسب کار مالیاتی شما</h1><div className="mt-10 grid gap-5 md:grid-cols-3">{plans.map(([title, price, benefits], index) => <article key={title} className={`rounded-3xl border bg-white/90 p-7 text-right shadow-sm ${index === 1 ? "border-primary shadow-primary/10" : ""}`}><h2 className="text-2xl font-black">{title}</h2><p className="mt-3 text-xl font-bold text-primary">{price}</p><ul className="mt-6 space-y-3 text-sm">{benefits.map((benefit) => <li key={benefit} className="flex gap-2"><Check className="size-4 text-emerald-600" />{benefit}</li>)}</ul><Link href="/signup" className="mt-8 block rounded-xl bg-primary px-4 py-3 text-center font-bold text-primary-foreground">انتخاب پلن</Link></article>)}</div></section><PublicFooter /></main>; }
