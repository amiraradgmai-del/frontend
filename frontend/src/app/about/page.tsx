import type { Metadata } from "next";
import { PublicFooter } from "@/components/public-footer";
import { PublicHeader } from "@/components/public-header";
export const metadata: Metadata = { title: "درباره ما", description: "ماموریت و اصول دستیار هوشمند مالیاتی" };
export default function AboutPage() { return <main><PublicHeader /><article className="mx-auto max-w-3xl px-5 py-14"><p className="font-bold text-primary">درباره سامانه</p><h1 className="mt-3 text-4xl font-black">فناوری در خدمت تصمیم مالیاتی مسئولانه</h1><div className="mt-8 space-y-5 leading-9 text-muted-foreground"><p>این سامانه برای دسترسی سریع‌تر به قوانین، مدیریت اسناد و دریافت پاسخ‌های قابل ردیابی طراحی شده است.</p><p>پاسخ هوش مصنوعی جایگزین بررسی تخصصی پرونده نیست؛ موارد حساس برای بررسی انسانی قابل ارجاع هستند.</p><p>اصل‌های ما شامل حفظ محرمانگی، شفافیت منبع، کنترل دسترسی و ثبت تغییرات مدیریتی است.</p></div></article><PublicFooter /></main>; }
