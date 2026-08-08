import type { Metadata } from "next";
import Link from "next/link";
import { Mail, MessageCircleQuestion } from "lucide-react";
import { PublicFooter } from "@/components/public-footer";
import { PublicHeader } from "@/components/public-header";
import { ContactDetails } from "@/components/site-theme-provider";
export const metadata: Metadata = { title: "تماس با ما", description: "راه‌های ارتباط با پشتیبانی دستیار مالیاتی" };
export default function ContactPage() { return <main><PublicHeader /><section className="mx-auto max-w-4xl px-5 py-14"><h1 className="text-4xl font-black">ارتباط با ما</h1><p className="mt-4 text-muted-foreground">برای پیگیری فنی یا مالی از پنل تیکت استفاده کنید.</p><div className="mt-8 grid gap-5 sm:grid-cols-2"><div className="rounded-2xl border bg-white p-6"><Mail className="text-primary" /><h2 className="mt-4 font-bold">اطلاعات پشتیبانی</h2><ContactDetails /></div><div className="rounded-2xl border bg-white p-6"><MessageCircleQuestion className="text-primary" /><h2 className="mt-4 font-bold">تیکت آنلاین</h2><Link href="/app/tickets" className="mt-2 inline-block text-sm font-semibold text-primary">ورود به مرکز پشتیبانی</Link></div></div></section><PublicFooter /></main>; }
