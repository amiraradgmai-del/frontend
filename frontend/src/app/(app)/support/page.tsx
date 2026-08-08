"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Bell, Building2, ChevronLeft, ClipboardCheck, CreditCard, FileText, Headphones, Search, TicketCheck, Users } from "lucide-react";
import { api } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

type Stats = { users: number; payments: number; revenue: number; active_subscriptions: number; open_tickets: number; user_documents: number; conversations: number };

const tools = [
  { href: "/support/consultant-approvals#add-consultant", title: "مدیریت مشاوران", description: "افزودن، تأیید، ویرایش و مدیریت مشاوران مستقل و شرکتی", icon: Building2, color: "from-cyan-500 to-blue-600", keywords: "مشاور مستقل شرکتی کارشناس افزودن حساب پروفایل تأیید" },
  { href: "/support/consultant-approvals", title: "صلاحیت مشاوران", description: "تأیید، رد، درخواست اصلاح، تعلیق و حذف مشاوران", icon: Users, color: "from-emerald-500 to-teal-600", keywords: "تایید رد صلاحیت حذف مشاور کارشناس" },
  { href: "/support/consultant-settlements", title: "تسویه مشاوران", description: "محاسبه سهم سامانه، ثبت پرداخت و شماره پیگیری", icon: CreditCard, color: "from-amber-500 to-orange-600", keywords: "تسویه درآمد شبا پرداخت مشاور" },
  { href: "/support/tickets", title: "تیکت‌های کاربران", description: "پاسخ‌گویی، پیگیری و بستن درخواست‌های پشتیبانی", icon: TicketCheck, color: "from-blue-600 to-cyan-500", keywords: "تیکت پشتیبانی پاسخ درخواست" },
  { href: "/support/consultations", title: "ارجاع مشاوره‌ها", description: "بررسی اولیه و تخصیص پرونده به کارشناس مناسب", icon: ClipboardCheck, color: "from-violet-600 to-fuchsia-500", keywords: "مشاوره ارجاع پرونده کارشناس" },
  { href: "/support/documents", title: "مدارک کاربران", description: "بررسی اسناد ارسالی و ثبت وضعیت رسیدگی", icon: FileText, color: "from-emerald-600 to-teal-500", keywords: "مدرک سند فایل بررسی" },
  { href: "/support/payments", title: "پرداخت و بازپرداخت", description: "پیگیری تراکنش‌های ناموفق و درخواست‌های مالی", icon: CreditCard, color: "from-orange-500 to-rose-500", keywords: "پرداخت تراکنش بازپرداخت مالی" },
  { href: "/support/announcements", title: "ارسال اعلان", description: "اطلاع‌رسانی هدفمند و پیام عمومی به کاربران", icon: Bell, color: "from-sky-600 to-blue-700", keywords: "اعلان پیام اطلاعیه کاربران" },
] as const;

export default function SupportHome() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [query, setQuery] = useState("");
  useEffect(() => { api<Stats>("api/v1/admin/summary").then(setStats).catch(() => setStats(null)); }, []);
  const filteredTools = useMemo(() => {
    const value = query.trim().toLocaleLowerCase("fa");
    return tools.filter((item) => !value || `${item.title} ${item.description} ${item.keywords}`.toLocaleLowerCase("fa").includes(value));
  }, [query]);

  return <div className="space-y-8">
    <header className="relative overflow-hidden rounded-[2rem] bg-gradient-to-l from-blue-700 via-blue-600 to-cyan-500 p-8 text-white shadow-2xl shadow-blue-900/15">
      <div className="absolute -left-20 -top-24 size-64 rounded-full bg-white/10" />
      <div className="relative"><p className="flex items-center gap-2 text-sm text-cyan-100"><Headphones className="size-4" /> مرکز عملیات ادمین</p><h1 className="mt-3 text-3xl font-black">پیشخوان پاسخ‌گویی</h1><p className="mt-3 max-w-2xl leading-8 text-blue-50">تمام ابزارهای رسیدگی به درخواست‌های کاربران، مشاوره‌ها و پرداخت‌ها در یک میزکار سریع.</p></div>
      <div className="relative mt-7 max-w-xl"><Search className="absolute right-4 top-1/2 size-5 -translate-y-1/2 text-blue-600" /><Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="جست‌وجو در ابزارهای پاسخ‌گویی..." className="h-13 border-0 bg-white pr-12 text-slate-900 shadow-xl" /></div>
    </header>

    <section className="grid gap-3 sm:grid-cols-3">
      <Stat icon={TicketCheck} label="تیکت باز" value={stats?.open_tickets ?? 0} tone="bg-orange-50 text-orange-700" />
      <Stat icon={FileText} label="مدارک کاربران" value={stats?.user_documents ?? 0} tone="bg-emerald-50 text-emerald-700" />
      <Stat icon={Users} label="کل کاربران" value={stats?.users ?? 0} tone="bg-blue-50 text-blue-700" />
    </section>

    <section>
      <div className="mb-4"><p className="text-sm font-bold text-blue-600">دسترسی سریع</p><h2 className="mt-1 text-2xl font-black">ابزارهای ادمین</h2></div>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{filteredTools.map((item) => <Link href={item.href} key={item.href} className="group rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm transition hover:-translate-y-1 hover:border-blue-200 hover:shadow-xl">
        <div className="flex items-start justify-between"><span className={`flex size-12 items-center justify-center rounded-2xl bg-gradient-to-br text-white shadow-lg ${item.color}`}><item.icon /></span><ChevronLeft className="size-5 text-slate-300 transition group-hover:-translate-x-1 group-hover:text-blue-600" /></div>
        <h3 className="mt-5 font-black">{item.title}</h3><p className="mt-2 text-xs leading-6 text-slate-500">{item.description}</p>
      </Link>)}</div>
      {!filteredTools.length && <div className="rounded-3xl border border-dashed bg-white p-12 text-center text-sm text-slate-500">ابزاری با این عبارت پیدا نشد.</div>}
    </section>
  </div>;
}

function Stat({ icon: Icon, label, value, tone }: { icon: typeof Users; label: string; value: number; tone: string }) {
  return <Card className="border-white/70 bg-white/90"><CardContent className="flex items-center gap-4 p-5"><span className={`flex size-12 items-center justify-center rounded-2xl ${tone}`}><Icon className="size-5" /></span><div><p className="text-2xl font-black">{value.toLocaleString("fa-IR")}</p><p className="text-xs text-slate-500">{label}</p></div></CardContent></Card>;
}
