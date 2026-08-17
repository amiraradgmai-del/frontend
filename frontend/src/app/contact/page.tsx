import type { Metadata } from "next";
import Link from "next/link";
import { cookies } from "next/headers";
import { Clock3, Mail, MessageCircleQuestion, ShieldCheck } from "lucide-react";
import { PublicFooter } from "@/components/public-footer";
import { PublicHeader } from "@/components/public-header";
import { ContactDetails } from "@/components/site-theme-provider";
import { accessCookie, refreshCookie } from "@/lib/backend";

export const metadata: Metadata = { title: "تماس با ما", description: "راه‌های ارتباط با پشتیبانی چکاه" };
export default async function ContactPage() { const store = await cookies(); const loggedIn = store.has(accessCookie) || store.has(refreshCookie); return <main><PublicHeader />
  <section className="bg-gradient-to-b from-sky-50 to-white"><div className="mx-auto max-w-5xl px-5 py-14"><p className="font-bold text-blue-600">پاسخ‌گویی و پیگیری</p><h1 className="mt-3 text-4xl font-black">ارتباط با چکاه</h1><p className="mt-4 max-w-2xl text-sm leading-8 text-slate-600">برای مسائل حساب، پرداخت، خطای سامانه یا پیگیری خدمات از تیکت استفاده کنید تا درخواست شما ثبت و قابل پیگیری باشد. برای سؤال تخصصی مالیاتی، از بخش مشاوران کمک بگیرید.</p>
    <div className="mt-9 grid gap-5 md:grid-cols-3"><article className="rounded-3xl border border-sky-100 bg-white p-6 shadow-sm"><Mail className="text-blue-600" /><h2 className="mt-4 font-black">اطلاعات تماس</h2><div className="mt-3 text-sm leading-7 text-slate-600"><ContactDetails /></div></article><article className="rounded-3xl border border-blue-100 bg-white p-6 shadow-sm"><MessageCircleQuestion className="text-blue-600" /><h2 className="mt-4 font-black">تیکت پشتیبانی</h2><p className="mt-3 text-sm leading-7 text-slate-600">موضوع را دقیق بنویسید و تصویر یا رسید مرتبط را در همان گفتگو بفرستید.</p><Link href={loggedIn ? "/app/tickets" : "/login?next=/app/tickets"} className="mt-5 inline-block rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-bold text-white">{loggedIn ? "ورود به پشتیبانی" : "ورود و ثبت درخواست"}</Link></article><article className="rounded-3xl border border-emerald-100 bg-white p-6 shadow-sm"><ShieldCheck className="text-emerald-600" /><h2 className="mt-4 font-black">مشاوره مالیاتی</h2><p className="mt-3 text-sm leading-7 text-slate-600">برای بررسی پرونده، اعتراض یا تصمیم تخصصی، مشاور مناسب را از فهرست انتخاب کنید.</p><Link href="/advisors" className="mt-5 inline-block text-sm font-bold text-emerald-700">مشاهده مشاوران</Link></article></div>
    <div className="mt-7 flex gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-5"><Clock3 className="mt-1 shrink-0 text-slate-600" /><p className="text-sm leading-7 text-slate-600">پاسخ پرسش‌های پرتکرار در تیکت به‌صورت فوری نمایش داده می‌شود. درخواست‌های دیگر تا زمان پاسخ پشتیبانی در همان گفت‌وگو قابل پیگیری هستند.</p></div>
  </div></section><PublicFooter /></main>; }
