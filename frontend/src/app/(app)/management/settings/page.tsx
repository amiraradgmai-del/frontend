"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Bot, Database, Eye, Palette, RotateCcw, Save, Search, ServerCog, UploadCloud } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { applyTheme } from "@/components/site-theme-provider";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

type SiteConfig = {
  theme: { primary_color: string; accent_color: string; background_color: string; font_family: "Vazirmatn" | "Tahoma" | "Arial" | "serif"; border_radius: number };
  branding: { site_name: string; short_description: string; logo_url: string; support_email: string; support_phone: string; support_mobile: string; office_address: string; working_hours: string; legal_name: string; map_url: string; instagram_url: string; whatsapp_url: string; telegram_url: string };
  seo: { default_title: string; default_description: string; keywords: string };
  features: { maintenance_mode: boolean; registration_enabled: boolean; chatbot_enabled: boolean; consultations_enabled: boolean };
  ai_policy: { generation_model: "gemini-2.5-flash-lite" | "gemini-2.5-flash" | "gemini-3.5-flash"; general_knowledge_enabled: boolean; general_knowledge_weight: number; casual_chat_enabled: boolean; require_sources_for_sensitive_answers: boolean; monthly_api_budget_toman: number; estimated_cost_per_message_toman: number };
};
type ManageData = {
  published_version: number;
  draft: SiteConfig;
  published: SiteConfig;
  updated_at: string;
  services: { environment: string; ai_provider: string; ai_configured: boolean; generation_model: string; embedding_model: string; email_mode: string; storage_backend: string };
  dataset: { documents: number; versions: number; chunks: number; starter_records: number };
};
type Version = { version: number; note: string; created_at: string };

export default function SiteSettingsPage() {
  const [data, setData] = useState<ManageData | null>(null);
  const [config, setConfig] = useState<SiteConfig | null>(null);
  const [versions, setVersions] = useState<Version[]>([]);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  async function load() {
    try {
      const [settings, history] = await Promise.all([api<ManageData>("api/v1/site/manage"), api<Version[]>("api/v1/site/manage/versions")]);
      setData(settings); setConfig(settings.draft); setVersions(history); setMessage("");
    } catch (error) { setMessage(error instanceof ApiError ? error.message : "دریافت تنظیمات ممکن نیست."); }
  }
  useEffect(() => {
    Promise.all([api<ManageData>("api/v1/site/manage"), api<Version[]>("api/v1/site/manage/versions")])
      .then(([settings, history]) => { setData(settings); setConfig(settings.draft); setVersions(history); setMessage(""); })
      .catch((error) => setMessage(error instanceof ApiError ? error.message : "دریافت تنظیمات ممکن نیست."));
  }, []);

  async function saveDraft() {
    if (!config) return; setBusy(true);
    try { await api("api/v1/site/manage/draft", { method: "PATCH", body: JSON.stringify({ configuration: config }) }); setMessage("پیش‌نویس تنظیمات ذخیره شد."); }
    catch (error) { setMessage(error instanceof ApiError ? error.message : "ذخیره انجام نشد."); }
    finally { setBusy(false); }
  }

  async function publish() {
    if (!config) return; setBusy(true);
    try {
      await api("api/v1/site/manage/draft", { method: "PATCH", body: JSON.stringify({ configuration: config }) });
      await api("api/v1/site/manage/publish", { method: "POST", body: JSON.stringify({ note: "انتشار از پنل مدیر سیستم" }) });
      applyTheme(config.theme); await load(); setMessage("تنظیمات با موفقیت منتشر شد.");
    } catch (error) { setMessage(error instanceof ApiError ? error.message : "انتشار انجام نشد."); }
    finally { setBusy(false); }
  }

  async function rollback(version: number) {
    if (!window.confirm(`نسخه ${version.toLocaleString("fa-IR")} دوباره منتشر شود؟`)) return;
    setBusy(true);
    try { await api("api/v1/site/manage/rollback", { method: "POST", body: JSON.stringify({ version, note: `بازگشت به نسخه ${version}` }) }); await load(); setMessage("نسخه انتخابی بازیابی شد."); }
    catch (error) { setMessage(error instanceof ApiError ? error.message : "بازیابی نسخه انجام نشد."); }
    finally { setBusy(false); }
  }

  if (!config || !data) return <div className="p-12 text-center text-muted-foreground">در حال دریافت تنظیمات سامانه...</div>;
  const setTheme = (key: keyof SiteConfig["theme"], value: string | number) => setConfig((current) => current ? { ...current, theme: { ...current.theme, [key]: value } } : current);
  const setBranding = (key: keyof SiteConfig["branding"], value: string) => setConfig((current) => current ? { ...current, branding: { ...current.branding, [key]: value } } : current);
  const setSeo = (key: keyof SiteConfig["seo"], value: string) => setConfig((current) => current ? { ...current, seo: { ...current.seo, [key]: value } } : current);
  const setFeature = (key: keyof SiteConfig["features"], value: boolean) => setConfig((current) => current ? { ...current, features: { ...current.features, [key]: value } } : current);
  const setAiPolicy = (key: keyof SiteConfig["ai_policy"], value: boolean | number | string) => setConfig((current) => current ? { ...current, ai_policy: { ...current.ai_policy, [key]: value } } : current);

  return <div className="space-y-7"><header className="flex flex-wrap items-end justify-between gap-4"><div><p className="text-sm font-bold text-primary">کنترل کامل سامانه</p><h1 className="mt-2 text-3xl font-black">تنظیمات مدیر سیستم</h1><p className="mt-2 text-muted-foreground">ظاهر، برند، سئو، قابلیت‌ها، سرویس‌ها و دیتاست را از یک نقطه مدیریت کنید.</p></div><Badge variant="secondary">نسخه منتشرشده {data.published_version.toLocaleString("fa-IR")}</Badge></header>{message && <p className="rounded-xl bg-primary/5 p-4 text-sm text-primary">{message}</p>}
    <div className="grid gap-6 xl:grid-cols-2">
      <Card className="border-white/70 bg-white/90"><CardHeader><CardTitle className="flex gap-2"><Palette className="text-primary" /> ظاهر و فونت</CardTitle><CardDescription>تغییرات را ابتدا پیش‌نمایش و سپس منتشر کنید.</CardDescription></CardHeader><CardContent className="grid gap-4 sm:grid-cols-2"><ColorField label="رنگ اصلی" value={config.theme.primary_color} onChange={(value) => setTheme("primary_color", value)} /><ColorField label="رنگ مکمل" value={config.theme.accent_color} onChange={(value) => setTheme("accent_color", value)} /><ColorField label="پس‌زمینه" value={config.theme.background_color} onChange={(value) => setTheme("background_color", value)} /><label className="space-y-2 text-sm"><span>فونت سایت</span><select value={config.theme.font_family} onChange={(event) => setTheme("font_family", event.target.value)} className="h-10 w-full rounded-lg border bg-white px-3"><option value="Vazirmatn">Vazirmatn</option><option value="Tahoma">Tahoma</option><option value="Arial">Arial</option><option value="serif">رسمی Serif</option></select></label><label className="space-y-2 text-sm sm:col-span-2"><span>گردی کارت‌ها: {config.theme.border_radius}</span><Input type="range" min="6" max="28" value={config.theme.border_radius} onChange={(event) => setTheme("border_radius", Number(event.target.value))} /></label><Button type="button" variant="outline" className="sm:col-span-2" onClick={() => applyTheme(config.theme)}><Eye /> پیش‌نمایش روی همین صفحه</Button></CardContent></Card>
      <Card className="border-white/70 bg-white/90"><CardHeader><CardTitle>برند و ارتباط</CardTitle><CardDescription>نام، اطلاعات تماس و شبکه‌های اجتماعی رسمی سامانه.</CardDescription></CardHeader><CardContent className="grid gap-4 sm:grid-cols-2"><Input value={config.branding.site_name} onChange={(event) => setBranding("site_name", event.target.value)} placeholder="نام سایت" /><Input value={config.branding.logo_url} onChange={(event) => setBranding("logo_url", event.target.value)} placeholder="آدرس لوگو" dir="ltr" /><Input value={config.branding.short_description} onChange={(event) => setBranding("short_description", event.target.value)} placeholder="توضیح کوتاه" className="sm:col-span-2" /><Input value={config.branding.support_email} onChange={(event) => setBranding("support_email", event.target.value)} placeholder="ایمیل پشتیبانی" dir="ltr" /><Input value={config.branding.support_phone} onChange={(event) => setBranding("support_phone", event.target.value)} placeholder="تلفن پشتیبانی" dir="ltr" /><Input value={config.branding.instagram_url} onChange={(event) => setBranding("instagram_url", event.target.value)} placeholder="لینک اینستاگرام" dir="ltr" /><Input value={config.branding.whatsapp_url} onChange={(event) => setBranding("whatsapp_url", event.target.value)} placeholder="لینک واتساپ" dir="ltr" /><Input value={config.branding.telegram_url} onChange={(event) => setBranding("telegram_url", event.target.value)} placeholder="لینک تلگرام" dir="ltr" className="sm:col-span-2" /></CardContent></Card>
      <Card className="border-white/70 bg-white/90"><CardHeader><CardTitle>اطلاعات تکمیلی تماس</CardTitle><CardDescription>مشخصات رسمی، نشانی دفتر و ساعات پاسخ‌گویی که در بخش‌های عمومی نمایش داده می‌شود.</CardDescription></CardHeader><CardContent className="grid gap-4 sm:grid-cols-2"><Input value={config.branding.legal_name} onChange={(event) => setBranding("legal_name", event.target.value)} placeholder="نام حقوقی مجموعه" /><Input value={config.branding.support_mobile} onChange={(event) => setBranding("support_mobile", event.target.value)} placeholder="موبایل پشتیبانی" dir="ltr" /><Input value={config.branding.working_hours} onChange={(event) => setBranding("working_hours", event.target.value)} placeholder="ساعات پاسخ‌گویی" /><Input value={config.branding.map_url} onChange={(event) => setBranding("map_url", event.target.value)} placeholder="لینک نقشه" dir="ltr" /><Input value={config.branding.office_address} onChange={(event) => setBranding("office_address", event.target.value)} placeholder="نشانی کامل دفتر" className="sm:col-span-2" /></CardContent></Card>
      <Card className="border-white/70 bg-white/90"><CardHeader><CardTitle className="flex gap-2"><Search className="text-primary" /> تنظیمات سئو</CardTitle><CardDescription>مقادیر پیش‌فرض صفحات عمومی و نتایج جست‌وجو.</CardDescription></CardHeader><CardContent className="space-y-4"><Input value={config.seo.default_title} onChange={(event) => setSeo("default_title", event.target.value)} placeholder="عنوان پیش‌فرض" /><Input value={config.seo.default_description} onChange={(event) => setSeo("default_description", event.target.value)} placeholder="توضیحات متا" /><Input value={config.seo.keywords} onChange={(event) => setSeo("keywords", event.target.value)} placeholder="کلمات کلیدی با ، جدا شوند" /></CardContent></Card>
      <Card className="border-white/70 bg-white/90"><CardHeader><CardTitle>قابلیت‌های سامانه</CardTitle><CardDescription>فعال‌سازی کنترل‌شده بخش‌های اصلی.</CardDescription></CardHeader><CardContent className="space-y-3"><Toggle label="حالت تعمیرات" checked={config.features.maintenance_mode} onChange={(value) => setFeature("maintenance_mode", value)} /><Toggle label="ثبت‌نام کاربران" checked={config.features.registration_enabled} onChange={(value) => setFeature("registration_enabled", value)} /><Toggle label="چت‌بات" checked={config.features.chatbot_enabled} onChange={(value) => setFeature("chatbot_enabled", value)} /><Toggle label="درخواست مشاور" checked={config.features.consultations_enabled} onChange={(value) => setFeature("consultations_enabled", value)} /></CardContent></Card>
      <Card id="ai-model" className="scroll-mt-8 border-white/70 bg-white/90 xl:col-span-2"><CardHeader><CardTitle className="flex gap-2"><Bot className="text-primary" /> مدل و سیاست پاسخ هوشمند چکاه</CardTitle><CardDescription>سامانه پرسش‌های ساده، مستند و پیچیده را به مدل مناسب هدایت می‌کند.</CardDescription></CardHeader><CardContent className="grid gap-4 lg:grid-cols-2"><label className="space-y-3 rounded-xl border border-blue-100 bg-blue-50/50 p-4 text-sm"><span className="font-bold">مدل فعال پاسخ‌گویی</span><select value={config.ai_policy.generation_model} onChange={(event) => setAiPolicy("generation_model", event.target.value)} className="h-11 w-full rounded-xl border border-blue-200 bg-white px-3"><option value="gemini-2.5-flash-lite">Gemini 2.5 Flash Lite — سریع و اقتصادی</option><option value="gemini-2.5-flash">Gemini 2.5 Flash — متعادل و مستند</option><option value="gemini-3.5-flash">Gemini 3.5 Flash — تحلیل پیچیده</option></select><p className="text-xs leading-6 text-slate-500">مسیریابی خودکار فعال است و مدل انتخابی، مدل اصلی پاسخ‌های مستند خواهد بود.</p></label><div className="space-y-3"><Toggle label="استفاده محدود از دانش عمومی چکاه" checked={config.ai_policy.general_knowledge_enabled} onChange={(value) => setAiPolicy("general_knowledge_enabled", value)} /><Toggle label="پاسخ عادی به سلام و گفت‌وگوی روزمره" checked={config.ai_policy.casual_chat_enabled} onChange={(value) => setAiPolicy("casual_chat_enabled", value)} /><Toggle label="الزام منبع برای نرخ، ماده، مبلغ و مهلت" checked={config.ai_policy.require_sources_for_sensitive_answers} onChange={(value) => setAiPolicy("require_sources_for_sensitive_answers", value)} /></div><label className="space-y-3 rounded-xl border p-4 text-sm lg:col-span-2"><span className="flex items-center justify-between"><b>سهم دانش عمومی چکاه</b><Badge variant="secondary">{config.ai_policy.general_knowledge_weight.toLocaleString("fa-IR")}٪</Badge></span><Input type="range" min="0" max="40" step="5" value={config.ai_policy.general_knowledge_weight} onChange={(event) => setAiPolicy("general_knowledge_weight", Number(event.target.value))} /><span className="block text-xs leading-6 text-muted-foreground">مقدار پیشنهادی ۲۰٪ است. پاسخ‌های حساس و عددی بدون پشتوانه بانک دانش تولید نمی‌شوند.</span></label><label className="space-y-2 rounded-xl border p-4 text-sm"><span className="font-bold">سقف هزینه ماهانه API (تومان)</span><Input type="number" min="100000" step="100000" value={config.ai_policy.monthly_api_budget_toman} onChange={(event) => setAiPolicy("monthly_api_budget_toman", Number(event.target.value))} /></label><label className="space-y-2 rounded-xl border p-4 text-sm"><span className="font-bold">هزینه تخمینی هر پیام (تومان)</span><Input type="number" min="1" step="10" value={config.ai_policy.estimated_cost_per_message_toman} onChange={(event) => setAiPolicy("estimated_cost_per_message_toman", Number(event.target.value))} /></label></CardContent></Card>
    </div>
    <div className="grid gap-6 lg:grid-cols-2"><Card className="border-white/70 bg-white/90"><CardHeader><CardTitle className="flex gap-2"><Database className="text-primary" /> وضعیت دیتاست</CardTitle></CardHeader><CardContent><div className="grid grid-cols-2 gap-3 sm:grid-cols-4"><Metric label="اسناد" value={data.dataset.documents} /><Metric label="نسخه‌ها" value={data.dataset.versions} /><Metric label="قطعه‌ها" value={data.dataset.chunks} /><Metric label="داده پایه" value={data.dataset.starter_records} /></div><Link href="/management/datasets" className="mt-5 flex h-9 w-full items-center justify-center gap-2 rounded-lg bg-primary px-3 text-sm font-medium text-primary-foreground transition hover:bg-primary/80"><UploadCloud className="size-4" /> مدیریت و بروزرسانی دیتاست</Link></CardContent></Card><Card className="border-white/70 bg-white/90"><CardHeader><CardTitle className="flex gap-2"><ServerCog className="text-primary" /> وضعیت سرویس‌ها</CardTitle></CardHeader><CardContent className="grid gap-3 sm:grid-cols-2"><Service label="هوش مصنوعی" value={`${data.services.ai_provider} · ${data.services.ai_configured ? "فعال" : "بدون کلید"}`} icon={Bot} /><Service label="مدل پاسخ" value={data.services.generation_model} icon={Bot} /><Service label="ایمیل" value={data.services.email_mode} icon={ServerCog} /><Service label="فضای ذخیره‌سازی" value={data.services.storage_backend} icon={Database} /></CardContent></Card></div>
    <Card className="border-white/70 bg-white/90"><CardHeader><CardTitle>انتشار و تاریخچه</CardTitle><CardDescription>کلیدهای محرمانه از پنل نمایش داده نمی‌شوند و فقط از متغیرهای امن سرور خوانده می‌شوند.</CardDescription></CardHeader><CardContent><div className="flex flex-wrap gap-3"><Button variant="outline" disabled={busy} onClick={saveDraft}><Save /> ذخیره پیش‌نویس</Button><Button disabled={busy} onClick={publish}>انتشار تغییرات</Button></div><div className="mt-5 divide-y rounded-xl border">{versions.map((item) => <div key={item.version} className="flex flex-wrap items-center justify-between gap-3 p-3 text-sm"><div><p className="font-semibold">نسخه {item.version.toLocaleString("fa-IR")}</p><p className="text-xs text-muted-foreground">{item.note || "بدون توضیح"} · {new Date(item.created_at).toLocaleString("fa-IR")}</p></div><Button size="sm" variant="ghost" disabled={busy || item.version === data.published_version} onClick={() => rollback(item.version)}><RotateCcw /> بازیابی</Button></div>)}</div></CardContent></Card>
  </div>;
}

function ColorField({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) { return <label className="space-y-2 text-sm"><span>{label}</span><div className="flex gap-2"><Input type="color" value={value} onChange={(event) => onChange(event.target.value)} className="w-14 p-1" /><Input value={value} onChange={(event) => onChange(event.target.value)} dir="ltr" /></div></label>; }
function Toggle({ label, checked, onChange }: { label: string; checked: boolean; onChange: (value: boolean) => void }) { return <label className="flex items-center justify-between rounded-xl border p-3 text-sm"><span>{label}</span><input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} className="size-5 accent-primary" /></label>; }
function Metric({ label, value }: { label: string; value: number }) { return <div className="rounded-xl bg-primary/5 p-3 text-center"><p className="text-2xl font-black text-primary">{value.toLocaleString("fa-IR")}</p><p className="text-xs text-muted-foreground">{label}</p></div>; }
function Service({ label, value, icon: Icon }: { label: string; value: string; icon: typeof Bot }) { return <div className="flex items-center gap-3 rounded-xl border p-3"><Icon className="size-5 text-primary" /><div><p className="text-xs text-muted-foreground">{label}</p><p className="text-sm font-semibold">{value}</p></div></div>; }
