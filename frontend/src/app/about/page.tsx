import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeft, BookOpenCheck, Bot, Scale, ShieldCheck, UserRoundCheck } from "lucide-react";
import { PublicFooter } from "@/components/public-footer";
import { PublicHeader } from "@/components/public-header";

export const metadata: Metadata = { title: "درباره چکاه", description: "ماموریت، خدمات و اصول دستیار هوشمند مالیاتی چکاه" };
const values = [
  { icon: BookOpenCheck, title: "پاسخ مبتنی بر منبع", text: "قانون، ماده و محتوای تأییدشده مبنای پاسخ قرار می‌گیرد و نتیجه بدون پشتوانه قانونی به‌عنوان حکم قطعی ارائه نمی‌شود." },
  { icon: ShieldCheck, title: "محرمانگی اطلاعات", text: "دسترسی به اسناد و اطلاعات پرونده کنترل می‌شود و مدارک شخصی در فهرست عمومی قرار نمی‌گیرند." },
  { icon: UserRoundCheck, title: "ارتباط با متخصص", text: "موضوعات حساس، مهلت‌دار یا وابسته به جزئیات پرونده می‌توانند برای بررسی انسانی به مشاور مالیاتی ارجاع شوند." },
];

export default function AboutPage() { return <main><PublicHeader />
  <section className="bg-gradient-to-b from-blue-50 to-white"><div className="mx-auto grid max-w-6xl items-center gap-10 px-5 py-16 lg:grid-cols-[1.1fr_.9fr]"><div><p className="font-bold text-blue-600">درباره چکاه</p><h1 className="mt-3 text-4xl font-black leading-[1.5]">فناوری در خدمت تصمیم مالیاتی مسئولانه</h1><p className="mt-5 max-w-2xl text-base leading-9 text-slate-600">چکاه یک دستیار و مرکز خدمات مالیاتی است که جست‌وجوی قوانین، پاسخ‌گویی هوشمند، ابزارهای محاسباتی، مدیریت اسناد و دسترسی به مشاوران را در یک فضای یکپارچه در اختیار کاربران قرار می‌دهد.</p><div className="mt-7 flex flex-wrap gap-3"><Link href="/signup" className="flex items-center gap-2 rounded-xl bg-blue-600 px-5 py-3 font-bold text-white">شروع استفاده <ArrowLeft className="size-4" /></Link><Link href="/advisors" className="rounded-xl border border-blue-200 bg-white px-5 py-3 font-bold text-blue-700">مشاهده مشاوران</Link></div></div><div className="rounded-[2rem] bg-gradient-to-br from-blue-700 to-cyan-500 p-8 text-white shadow-xl"><Scale className="size-12 text-cyan-100" /><h2 className="mt-5 text-2xl font-black">هدف ما چیست؟</h2><p className="mt-3 text-sm leading-8 text-blue-50">کاهش سردرگمی کاربران در میان قوانین و فرایندهای مالیاتی، ارائه مسیر روشن برای اقدام و مشخص‌کردن زمان‌هایی که نظر یک متخصص ضروری است.</p></div></div></section>
  <section className="mx-auto max-w-6xl px-5 py-14"><p className="text-sm font-bold text-blue-600">اصول چکاه</p><h2 className="mt-2 text-2xl font-black">اعتماد با شفافیت ساخته می‌شود</h2><div className="mt-7 grid gap-5 md:grid-cols-3">{values.map(({ icon: Icon, title, text }) => <article key={title} className="rounded-3xl border border-sky-100 bg-white p-6 shadow-sm"><span className="flex size-12 items-center justify-center rounded-2xl bg-blue-50 text-blue-700"><Icon /></span><h3 className="mt-5 text-lg font-black">{title}</h3><p className="mt-3 text-sm leading-8 text-slate-600">{text}</p></article>)}</div></section>
  <section className="mx-auto max-w-6xl px-5 pb-16"><div className="rounded-[2rem] border border-sky-100 bg-slate-50 p-7"><Bot className="text-blue-600" /><h2 className="mt-4 text-xl font-black">مرز مسئولیت چکاه</h2><p className="mt-3 text-sm leading-8 text-slate-600">پاسخ هوش مصنوعی و محاسبات سامانه ابزار تصمیم‌یار هستند و جایگزین بررسی کامل اسناد، امضای متخصص یا اقدام در سامانه‌های رسمی کشور نیستند. نتیجه نهایی هر پرونده به نوع مؤدی، دوره مالی، اسناد و آخرین مقررات وابسته است.</p></div></section>
  <PublicFooter /></main>; }
