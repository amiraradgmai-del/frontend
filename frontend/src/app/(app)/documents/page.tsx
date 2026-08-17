import Link from "next/link";
import { ArrowLeft, BookOpenCheck, Bot, CheckCircle2, FileCheck2, FileUp, Search, ShieldCheck } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const steps = [
  { icon: Search, title: "۱. پیدا کردن منبع", text: "قانون، بخشنامه یا راهنمای تأییدشده موردنیاز را در مرکز قوانین پیدا کنید." },
  { icon: FileUp, title: "۲. افزودن مدرک شخصی", text: "برگ تشخیص، رأی، نامه یا فایل پرونده خود را در فضای محرمانه اسناد شخصی بارگذاری کنید." },
  { icon: Bot, title: "۳. پرسیدن سؤال دقیق", text: "در گفت‌وگوی مالیاتی سؤال را با موضوع، سال، نوع مؤدی و جزئیات لازم مطرح کنید." },
  { icon: CheckCircle2, title: "۴. کنترل پاسخ", text: "منبع و شماره ماده پاسخ را بررسی کنید و برای تصمیم حساس از مشاور کمک بگیرید." },
];

export default function DocumentsPage() {
  return <div className="space-y-7">
    <header className="relative overflow-hidden rounded-[2rem] bg-gradient-to-l from-slate-900 via-blue-900 to-blue-700 p-8 text-white shadow-xl shadow-blue-900/15">
      <BookOpenCheck className="size-11 text-cyan-200" />
      <p className="mt-5 text-sm font-bold text-cyan-200">پشتوانه پاسخ‌های چکاه</p>
      <h1 className="mt-1 text-3xl font-black">منابع و اسناد دقیقاً برای چیست؟</h1>
      <p className="mt-4 max-w-3xl text-sm leading-8 text-blue-50">این بخش توضیح می‌دهد پاسخ‌های دستیار از چه منابعی ساخته می‌شوند و شما مدارک پرونده خود را کجا قرار دهید. «منابع رسمی» بانک دانش عمومی سامانه‌اند؛ «اسناد شخصی من» فقط برای پرونده خود شماست و عمومی نمایش داده نمی‌شود.</p>
    </header>

    <section className="grid gap-4 md:grid-cols-2">
      <Card className="border-blue-100 bg-gradient-to-br from-white to-blue-50"><CardHeader><div className="flex size-11 items-center justify-center rounded-xl bg-blue-100 text-blue-700"><BookOpenCheck /></div><CardTitle>منابع رسمی سامانه</CardTitle></CardHeader><CardContent className="space-y-4 text-sm leading-7 text-slate-600"><p>قوانین، آیین‌نامه‌ها، بخشنامه‌ها و راهنماهایی که مدیر سامانه بررسی و تأیید کرده است. ربات برای پاسخ مستند، بخش مرتبط این منابع را بازیابی می‌کند.</p><Link href="/app/laws" className="inline-flex items-center gap-2 font-bold text-blue-700">جست‌وجو در مرکز قوانین <ArrowLeft className="size-4" /></Link></CardContent></Card>
      <Card className="border-emerald-100 bg-gradient-to-br from-white to-emerald-50"><CardHeader><div className="flex size-11 items-center justify-center rounded-xl bg-emerald-100 text-emerald-700"><ShieldCheck /></div><CardTitle>اسناد شخصی من</CardTitle></CardHeader><CardContent className="space-y-4 text-sm leading-7 text-slate-600"><p>مدارک اختصاصی مانند برگ تشخیص، رأی هیئت، اظهارنامه، مکاتبه و مستندات پرونده. این فایل‌ها محرمانه‌اند و فقط شما و تیم مجاز بررسی به آن‌ها دسترسی دارید.</p><Link href="/my-documents" className="inline-flex items-center gap-2 font-bold text-emerald-700">ورود به گاوصندوق اسناد <ArrowLeft className="size-4" /></Link></CardContent></Card>
    </section>

    <section><p className="text-sm font-bold text-blue-600">مسیر پیشنهادی</p><h2 className="mt-1 text-xl font-black">چطور از این بخش نتیجه بگیرید؟</h2><div className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{steps.map(({ icon: Icon, title, text }) => <Card key={title} className="border-slate-100"><CardContent className="p-5"><Icon className="size-6 text-blue-600" /><h3 className="mt-4 font-black">{title}</h3><p className="mt-2 text-xs leading-6 text-slate-600">{text}</p></CardContent></Card>)}</div></section>

    <Card className="border-amber-200 bg-amber-50/70"><CardContent className="p-5"><div className="flex gap-3"><FileCheck2 className="mt-1 size-5 shrink-0 text-amber-700" /><div><h2 className="font-black text-amber-950">قبل از استفاده بدانید</h2><ul className="mt-2 list-inside list-disc space-y-1 text-sm leading-7 text-amber-900"><li>فقط نسخه خوانا و کامل فایل را بارگذاری کنید و اطلاعات ورود، رمز کارت یا رمز سامانه‌های دولتی را داخل فایل نگذارید.</li><li>اعتبار زمانی قانون و ارتباط آن با سال مالی پرونده مهم است؛ جدیدترین نسخه همیشه برای همه سال‌ها قابل اعمال نیست.</li><li>پاسخ چکاه ابزار تصمیم‌یار است و جای امضا یا نظر نهایی مشاور رسمی را نمی‌گیرد.</li></ul></div></div></CardContent></Card>
  </div>;
}
