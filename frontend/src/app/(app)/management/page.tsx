"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  BarChart3,
  Bell,
  BookOpen,
  ChevronLeft,
  ClipboardCheck,
  CreditCard,
  Database,
  FileText,
  History,
  LayoutGrid,
  MessageCircleQuestion,
  Newspaper,
  Plus,
  Search,
  Settings,
  ShieldCheck,
  Tags,
  TicketCheck,
  UserCog,
  Users,
  WalletCards,
} from "lucide-react";
import { api } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

type Stats = {
  users: number;
  payments: number;
  revenue: number;
  active_subscriptions: number;
  open_tickets: number;
  user_documents: number;
  conversations: number;
};

const sections = [
  {
    title: "کاربران و دسترسی‌ها",
    description: "حساب‌ها، نقش‌ها، پروفایل‌ها و کارشناسان",
    color: "from-blue-600 to-cyan-500",
    items: [
      { href: "/management/users", label: "مدیریت کاربران", description: "ساخت، ویرایش، نقش و وضعیت حساب", icon: Users, keywords: "کاربر نقش ادمین مدیر دسترسی" },
      { href: "/management/consultants", label: "مدیریت مشاوران", description: "تأیید، ویرایش، قرارداد، مدارک و وضعیت همکاری", icon: UserCog, keywords: "مشاور کارشناس تایید همکاری قرارداد ویرایش" },
      { href: "/management/audit", label: "فعالیت مدیران", description: "تاریخچه عملیات و تغییرات حساس", icon: History, keywords: "لاگ تاریخچه امنیت مدیر" },
    ],
  },
  {
    title: "مالی و اشتراک",
    description: "پرداخت‌ها، کیف پول، پلن‌ها و تخفیف",
    color: "from-emerald-600 to-teal-500",
    items: [
      { href: "/management/payments", label: "پرداخت‌ها", description: "تراکنش‌ها، وضعیت و کد رهگیری", icon: CreditCard, keywords: "پرداخت تراکنش درگاه فاکتور" },
      { href: "/management/subscriptions", label: "اشتراک‌ها", description: "پلن فعال، بسته و تاریخ انقضا", icon: ShieldCheck, keywords: "اشتراک پلن بسته گولد سیلور دایموند" },
      { href: "/management/discounts", label: "کدهای تخفیف", description: "ساخت و مدیریت کمپین‌های تخفیف", icon: Tags, keywords: "تخفیف کد کمپین درصد" },
      { href: "/management/reports", label: "گزارش مالی و مصرف", description: "درآمد، هزینه API و مصرف کاربران", icon: BarChart3, keywords: "گزارش درآمد سود هزینه مصرف" },
      { href: "/management/consultant-settlements", label: "تسویه مشاوران", description: "شبا، سهم سامانه و ثبت شماره پیگیری", icon: WalletCards, keywords: "تسویه مشاور شبا درآمد پرداخت" },
    ],
  },
  {
    title: "محتوا و دانش",
    description: "قوانین، دیتاست، اسناد و پاسخ هوشمند",
    color: "from-violet-600 to-fuchsia-500",
    items: [
      { href: "/management/datasets", label: "دیتاست و بانک دانش", description: "بارگذاری، پردازش و انتشار منابع", icon: Database, keywords: "دیتاست بانک دانش آپلود سند منبع" },
      { href: "/management/laws", label: "مدیریت قوانین", description: "مواد، دسته‌بندی و به‌روزرسانی قانون", icon: BookOpen, keywords: "قانون ماده تبصره اصلاحیه" },
      { href: "/management/content", label: "صفحات و بلاگ", description: "مطلب، صفحه، سئو، زمان‌بندی، تصویر و نظرات", icon: Newspaper, keywords: "بلاگ محتوا صفحه مطلب سئو نظر انتشار" },
      { href: "/management/customer-documents", label: "اسناد کاربران", description: "مدارک بارگذاری‌شده و وضعیت بررسی", icon: FileText, keywords: "سند مدرک فایل کاربران" },
      { href: "/management/chats", label: "نظارت گفتگوها", description: "کیفیت پاسخ‌ها و بازخورد کاربران", icon: MessageCircleQuestion, keywords: "چت گفتگو پاسخ ربات کیفیت" },
    ],
  },
  {
    title: "پشتیبانی و ارتباطات",
    description: "تیکت، مشاوره و اعلان عمومی",
    color: "from-orange-500 to-rose-500",
    items: [
      { href: "/management/tickets", label: "تیکت‌ها", description: "صف پاسخ‌گویی و پیگیری درخواست‌ها", icon: TicketCheck, keywords: "تیکت پشتیبانی پاسخ" },
      { href: "/management/consultations", label: "مدیریت مشاوره‌ها", description: "ارجاع، رزرو و وضعیت پرونده", icon: ClipboardCheck, keywords: "مشاوره رزرو پرونده ارجاع" },
      { href: "/management/announcements", label: "اعلان عمومی", description: "ارسال پیام و اطلاعیه به کاربران", icon: Bell, keywords: "اعلان پیام اطلاعیه نوتیفیکیشن" },
    ],
  },
  {
    title: "ظاهر و تنظیمات سامانه",
    description: "برند، رنگ، سئو، قابلیت‌ها و اطلاعات تماس",
    color: "from-sky-600 to-blue-700",
    items: [
      { href: "/management/settings", label: "تنظیمات کل سامانه", description: "همه تنظیمات عمومی در یک صفحه", icon: Settings, keywords: "تنظیمات سایت عمومی قابلیت تماس" },
    ],
  },
] as const;

export default function ManagementControlCenter() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [query, setQuery] = useState("");

  useEffect(() => {
    api<Stats>("api/v1/admin/summary").then(setStats).catch(() => setStats(null));
  }, []);

  const normalizedQuery = query.trim().toLocaleLowerCase("fa");
  const visibleSections = useMemo(() => sections.map((section) => ({
    ...section,
    items: section.items.filter((item) => !normalizedQuery || `${item.label} ${item.description} ${item.keywords}`.toLocaleLowerCase("fa").includes(normalizedQuery)),
  })).filter((section) => section.items.length), [normalizedQuery]);

  const quickStats = [
    { label: "کاربران", value: stats?.users ?? 0, icon: Users, href: "/management/users", tone: "bg-blue-50 text-blue-700" },
    { label: "اشتراک فعال", value: stats?.active_subscriptions ?? 0, icon: ShieldCheck, href: "/management/subscriptions", tone: "bg-emerald-50 text-emerald-700" },
    { label: "تیکت باز", value: stats?.open_tickets ?? 0, icon: TicketCheck, href: "/management/tickets", tone: "bg-orange-50 text-orange-700" },
    { label: "گفتگوها", value: stats?.conversations ?? 0, icon: MessageCircleQuestion, href: "/management/chats", tone: "bg-violet-50 text-violet-700" },
  ];

  return <div className="space-y-8">
    <header className="relative overflow-hidden rounded-[2rem] bg-gradient-to-l from-blue-700 via-blue-600 to-cyan-500 p-7 text-white shadow-2xl shadow-blue-900/15 sm:p-9">
      <div className="absolute -left-16 -top-24 size-64 rounded-full bg-white/10" />
      <div className="absolute -bottom-24 right-1/3 size-56 rounded-full bg-cyan-200/10" />
      <div className="relative flex flex-col gap-7 xl:flex-row xl:items-end xl:justify-between">
        <div>
          <Badge className="border-white/20 bg-white/15 text-white hover:bg-white/15"><LayoutGrid className="size-3.5" /> مرکز کنترل چکاه</Badge>
          <h1 className="mt-4 text-3xl font-black sm:text-4xl">همه امکانات سایت، یک‌جا</h1>
          <p className="mt-3 max-w-2xl leading-8 text-blue-50">مثل پیشخوان وردپرس، هر بخش را جست‌وجو کنید و مستقیم وارد تنظیمات یا مدیریت آن شوید.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link href="/management/announcements" className="flex items-center gap-2 rounded-xl bg-white px-4 py-3 text-sm font-bold text-blue-700 shadow-lg"><Plus className="size-4" /> اعلان جدید</Link>
          <Link href="/management/settings" className="flex items-center gap-2 rounded-xl border border-white/30 bg-white/10 px-4 py-3 text-sm font-bold backdrop-blur"><Settings className="size-4" /> تنظیمات سایت</Link>
        </div>
      </div>
      <div className="relative mt-8 max-w-2xl">
        <Search className="absolute right-4 top-1/2 size-5 -translate-y-1/2 text-blue-600" />
        <Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="جست‌وجو در امکانات؛ مثلاً رنگ، کاربر، پرداخت یا دیتاست..." className="h-14 border-0 bg-white pr-12 text-sm text-slate-900 shadow-xl placeholder:text-slate-400" />
      </div>
    </header>

    <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {quickStats.map((item) => <Link key={item.label} href={item.href}><Card className="h-full border-white/70 bg-white/90 transition hover:-translate-y-1 hover:shadow-lg"><CardContent className="flex items-center gap-4 p-5"><span className={`flex size-12 items-center justify-center rounded-2xl ${item.tone}`}><item.icon className="size-5" /></span><div><p className="text-2xl font-black">{item.value.toLocaleString("fa-IR")}</p><p className="text-xs text-slate-500">{item.label}</p></div></CardContent></Card></Link>)}
    </section>

    <section className="space-y-8">
      {visibleSections.map((section) => <div key={section.title}>
        <div className="mb-4 flex items-end justify-between gap-4">
          <div><h2 className="text-xl font-black text-slate-900">{section.title}</h2><p className="mt-1 text-sm text-slate-500">{section.description}</p></div>
          <span className={`hidden h-1 w-24 rounded-full bg-gradient-to-l sm:block ${section.color}`} />
        </div>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {section.items.map((item) => <Link key={item.href + item.label} href={item.href} className="group rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm transition hover:-translate-y-1 hover:border-blue-200 hover:shadow-xl hover:shadow-blue-900/5">
            <div className="flex items-start justify-between gap-4">
              <span className={`flex size-11 items-center justify-center rounded-2xl bg-gradient-to-br text-white shadow-lg ${section.color}`}><item.icon className="size-5" /></span>
              <ChevronLeft className="size-5 text-slate-300 transition group-hover:-translate-x-1 group-hover:text-blue-600" />
            </div>
            <h3 className="mt-5 font-black text-slate-900">{item.label}</h3>
            <p className="mt-2 text-xs leading-6 text-slate-500">{item.description}</p>
          </Link>)}
        </div>
      </div>)}
      {!visibleSections.length && <div className="rounded-3xl border border-dashed border-sky-200 bg-white p-14 text-center"><Activity className="mx-auto size-8 text-slate-300" /><p className="mt-4 font-bold">بخشی با این عبارت پیدا نشد</p><button type="button" onClick={() => setQuery("")} className="mt-3 text-sm font-bold text-blue-600">پاک‌کردن جست‌وجو</button></div>}
    </section>
  </div>;
}
