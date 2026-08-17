"use client";

import { FormEvent, useState } from "react";
import { Building2, CheckCircle2, Download, Eye, EyeOff, FileSpreadsheet, Upload, UserPlus } from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { IranCitySelect } from "@/lib/iran-cities";

type FormState = {
  consultant_type: "company" | "independent";
  full_name: string; email: string; initial_password: string; phone: string;
  professional_title: string; bio: string; specialties: string; skills: string;
  qualifications: string; education: string; certifications: string; work_history: string;
  years_experience: string; consultation_price: string;
  city: string; office_address: string; profile_image_url: string;
  is_online: boolean; offers_in_person: boolean; is_available: boolean;
  approval_status: "approved" | "pending";
};

const initialForm: FormState = {
  consultant_type: "company",
  full_name: "", email: "", initial_password: "", phone: "",
  professional_title: "", bio: "", specialties: "", skills: "",
  qualifications: "", education: "", certifications: "", work_history: "", years_experience: "", consultation_price: "",
  city: "", office_address: "", profile_image_url: "",
  is_online: true, offers_in_person: false, is_available: true, approval_status: "pending",
};

export function ConsultantCreateForm() {
  const [form, setForm] = useState(initialForm);
  const [showPassword, setShowPassword] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState("");
  const [importErrors, setImportErrors] = useState<{ row: number; error: string }[]>([]);
  const [profilePhoto, setProfilePhoto] = useState<File | null>(null);
  const [documents, setDocuments] = useState<File[]>([]);

  const set = (key: keyof FormState, value: string | boolean) => setForm((current) => ({ ...current, [key]: value }));
  const splitList = (value: string) => value.split(/[،,\n]/).map((item) => item.trim()).filter(Boolean);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSaving(true); setMessage(""); setError("");
    try {
      const result = await api<{ id: string; full_name: string; email: string }>("api/v1/consultations/manage/company-consultants", {
        method: "POST",
        body: JSON.stringify({
          ...form,
          specialties: splitList(form.specialties),
          skills: splitList(form.skills),
          years_experience: Number(form.years_experience || 0),
          consultation_price: Number(form.consultation_price.replaceAll(",", "") || 0),
        }),
      });
      const uploads = [
        ...(profilePhoto ? [{ file: profilePhoto, type: "profile_photo", title: "عکس پروفایل" }] : []),
        ...documents.map((file) => ({ file, type: "other", title: file.name })),
      ];
      for (const upload of uploads) {
        const body = new FormData();
        body.append("file", upload.file);
        body.append("title", upload.title);
        body.append("document_type", upload.type);
        body.append("description", "بارگذاری‌شده توسط مدیر سامانه هنگام ساخت حساب مشاور");
        await api(`api/v1/consultations/manage/profiles/${result.id}/documents`, { method: "POST", body });
      }
      setMessage(`حساب ${result.full_name} با ایمیل ${result.email} ساخته و تأیید شد.`);
      setForm(initialForm);
      setProfilePhoto(null);
      setDocuments([]);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "ساخت حساب انجام نشد.");
    } finally {
      setSaving(false);
    }
  }

  async function importExcel(file: File) {
    setImporting(true); setImportResult(""); setError("");
    try {
      const body = new FormData();
      body.append("file", file);
      const result = await api<{ created: number; failed: number; errors: { row: number; error: string }[] }>("api/v1/consultations/manage/consultants-import", { method: "POST", body });
      setImportErrors(result.errors);
      setImportResult(`${result.created.toLocaleString("fa-IR")} مشاور اضافه شد${result.failed ? ` و ${result.failed.toLocaleString("fa-IR")} ردیف خطا داشت` : ""}.`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "ورود اطلاعات Excel انجام نشد.");
    } finally {
      setImporting(false);
    }
  }

  return <div className="space-y-7">
    <header className="overflow-hidden rounded-[2rem] bg-gradient-to-l from-blue-700 via-blue-600 to-cyan-500 p-8 text-white shadow-xl">
      <div className="flex items-center gap-4"><span className="flex size-14 items-center justify-center rounded-2xl bg-white/15"><Building2 /></span><div><p className="text-sm text-cyan-100">مدیریت تیم مشاوره</p><h1 className="mt-1 text-3xl font-black">افزودن مشاور</h1><p className="mt-2 text-sm text-blue-50">حساب مشاور مستقل یا شرکتی را همراه با پروفایل تأییدشده بسازید.</p></div></div>
    </header>

    <section className="grid gap-4 rounded-[2rem] border border-emerald-200 bg-gradient-to-l from-emerald-50 to-white p-6 shadow-sm lg:grid-cols-[1fr_auto]">
      <div><div className="flex items-center gap-3"><span className="flex size-11 items-center justify-center rounded-xl bg-emerald-100 text-emerald-700"><FileSpreadsheet /></span><div><h2 className="font-black">افزودن گروهی مشاوران با Excel</h2><p className="mt-1 text-sm text-slate-600">قالب راهنما را دانلود کنید، هر مشاور را در یک ردیف بنویسید و فایل تکمیل‌شده را بارگذاری کنید.</p></div></div><p className="mt-4 text-xs leading-6 text-slate-500">نام ستون‌ها را تغییر ندهید. تخصص‌ها و مهارت‌ها را با «،» جدا کنید. نوع مشاور فقط <span dir="ltr">independent</span> یا <span dir="ltr">company</span> باشد.</p>{importResult && <p className="mt-3 rounded-xl bg-emerald-100 p-3 text-sm text-emerald-800">{importResult}</p>}{importErrors.length > 0 && <div className="mt-3 rounded-xl border border-rose-200 bg-rose-50 p-3"><p className="text-sm font-black text-rose-800">خطاهای فایل</p><ul className="mt-2 space-y-1 text-xs text-rose-700">{importErrors.map((item) => <li key={`${item.row}-${item.error}`}>ردیف {item.row.toLocaleString("fa-IR")}: {item.error}</li>)}</ul></div>}</div>
      <div className="flex flex-wrap items-center gap-2"><a href="/api/backend/api/v1/consultations/manage/consultants-import-template.xlsx" className="flex items-center gap-2 rounded-xl border border-emerald-300 bg-white px-4 py-3 text-sm font-bold text-emerald-700"><Download className="size-4" /> دانلود قالب و راهنما</a><label className={`flex cursor-pointer items-center gap-2 rounded-xl bg-emerald-600 px-4 py-3 text-sm font-bold text-white ${importing ? "pointer-events-none opacity-60" : ""}`}><Upload className="size-4" />{importing ? "در حال پردازش…" : "بارگذاری Excel"}<input type="file" accept=".xlsx" className="hidden" onChange={(event) => event.target.files?.[0] && void importExcel(event.target.files[0])} /></label></div>
    </section>

    <form onSubmit={submit} className="space-y-6 rounded-[2rem] border border-sky-100 bg-white p-6 shadow-sm sm:p-8">
      <Section title="اطلاعات حساب">
        <Field label="نوع مشاور *"><select value={form.consultant_type} onChange={(e) => set("consultant_type", e.target.value as "company" | "independent")} className="h-10 w-full rounded-lg border bg-white px-3"><option value="company">مشاور شرکتی</option><option value="independent">مشاور مستقل</option></select></Field>
        <Field label="نام و نام خانوادگی *"><Input required value={form.full_name} onChange={(e) => set("full_name", e.target.value)} placeholder="مثلاً سارا احمدی" /></Field>
        <Field label="ایمیل کاری *"><Input required type="email" dir="ltr" value={form.email} onChange={(e) => set("email", e.target.value)} placeholder="advisor@company.ir" /></Field>
        <Field label="شماره تماس"><Input dir="ltr" value={form.phone} onChange={(e) => set("phone", e.target.value)} placeholder="09xxxxxxxxx" /></Field>
        <Field label="رمز عبور اولیه *"><div className="relative"><Input required minLength={8} type={showPassword ? "text" : "password"} dir="ltr" value={form.initial_password} onChange={(e) => set("initial_password", e.target.value)} placeholder="حداقل ۸ کاراکتر" /><button type="button" onClick={() => setShowPassword((value) => !value)} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">{showPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}</button></div></Field>
      </Section>

      <Section title="مشخصات حرفه‌ای">
        <Field label="عنوان تخصصی *"><Input required value={form.professional_title} onChange={(e) => set("professional_title", e.target.value)} placeholder="مثلاً مشاور ارشد مالیات شرکت‌ها" /></Field>
        <Field label="سابقه کاری (سال)"><Input type="number" min="0" max="70" value={form.years_experience} onChange={(e) => set("years_experience", e.target.value)} placeholder="مثلاً ۸" /></Field>
        <Field label="حوزه‌های تخصصی *"><Input required value={form.specialties} onChange={(e) => set("specialties", e.target.value)} placeholder="ارزش افزوده، مالیات عملکرد، دادرسی" /></Field>
        <Field label="مهارت‌ها"><Input value={form.skills} onChange={(e) => set("skills", e.target.value)} placeholder="تنظیم لایحه، حسابرسی، سامانه مؤدیان" /></Field>
        <Field label="تحصیلات و مدارک" wide><Textarea value={form.qualifications} onChange={(e) => set("qualifications", e.target.value)} placeholder="مدرک تحصیلی، گواهی‌ها و مجوزهای حرفه‌ای" /></Field>
        <Field label="تحصیلات" wide><Textarea value={form.education} onChange={(e) => set("education", e.target.value)} placeholder="رشته، مقطع و دانشگاه" /></Field>
        <Field label="گواهی‌ها و مجوزها" wide><Textarea value={form.certifications} onChange={(e) => set("certifications", e.target.value)} placeholder="عنوان گواهی، صادرکننده و تاریخ" /></Field>
        <Field label="سوابق کاری" wide><Textarea value={form.work_history} onChange={(e) => set("work_history", e.target.value)} placeholder="سمت، مجموعه و مدت همکاری" /></Field>
        <Field label="معرفی و رزومه کوتاه *" wide><Textarea required minLength={20} value={form.bio} onChange={(e) => set("bio", e.target.value)} placeholder="خلاصه تجربه‌ها و خدمات قابل ارائه" /></Field>
      </Section>

      <Section title="خدمات و محل فعالیت">
        <Field label="شهر"><IranCitySelect value={form.city} onChange={(value) => set("city", value)} /></Field>
        <Field label="هزینه جلسه (تومان)"><Input inputMode="numeric" value={form.consultation_price} onChange={(e) => set("consultation_price", e.target.value.replace(/\D/g, ""))} placeholder="مثلاً ۵۰۰۰۰۰" /></Field>
        <Field label="آدرس دفتر" wide><Input value={form.office_address} onChange={(e) => set("office_address", e.target.value)} placeholder="آدرس برای جلسات حضوری" /></Field>
        <Field label="لینک تصویر پروفایل" wide><Input dir="ltr" value={form.profile_image_url} onChange={(e) => set("profile_image_url", e.target.value)} placeholder="https://..." /></Field>
        <Field label="بارگذاری عکس پروفایل"><Input type="file" accept="image/png,image/jpeg,image/webp" onChange={(e) => setProfilePhoto(e.target.files?.[0] ?? null)} /></Field>
        <Field label="مدارک مشاور"><Input type="file" multiple accept=".pdf,.png,.jpg,.jpeg,.webp" onChange={(e) => setDocuments(Array.from(e.target.files ?? []))} /></Field>
        <p className="text-xs leading-6 text-slate-500 sm:col-span-2">مدارک پیشنهادی مشاور مستقل: کارت ملی، مدرک تحصیلی، رزومه و مجوز حرفه‌ای. برای مشاور شرکتی: آگهی ثبت، شناسه ملی شرکت و کارت ملی نماینده.</p>
        <div className="grid gap-3 sm:col-span-2 sm:grid-cols-3">
          <Check label="مشاوره آنلاین" checked={form.is_online} onChange={(value) => set("is_online", value)} />
          <Check label="مشاوره حضوری" checked={form.offers_in_person} onChange={(value) => set("offers_in_person", value)} />
          <Check label="آماده پذیرش" checked={form.is_available} onChange={(value) => set("is_available", value)} />
        </div>
        <Field label="وضعیت اولیه" wide><select value={form.approval_status} onChange={(e) => set("approval_status", e.target.value as "approved" | "pending")} className="h-10 w-full rounded-lg border bg-white px-3"><option value="pending">ارسال به صف بررسی</option><option value="approved">تأیید و انتشار فوری</option></select></Field>
      </Section>

      {message && <p className="flex items-center gap-2 rounded-2xl bg-emerald-50 p-4 text-sm text-emerald-700"><CheckCircle2 className="size-5" />{message}</p>}
      {error && <p className="rounded-2xl bg-rose-50 p-4 text-sm text-rose-700">{error}</p>}
      <Button disabled={saving} className="h-12 w-full rounded-xl bg-blue-600 text-base font-bold hover:bg-blue-700"><UserPlus className="ml-2 size-5" />{saving ? "در حال ساخت حساب..." : "ساخت و تأیید مشاور شرکتی"}</Button>
    </form>
  </div>;
}

export default function CompanyConsultantsPage() {
  return <ConsultantCreateForm />;
}

function Section({ title, children }: { title: string; children: React.ReactNode }) { return <section><h2 className="mb-4 border-r-4 border-blue-500 pr-3 text-lg font-black">{title}</h2><div className="grid gap-4 sm:grid-cols-2">{children}</div></section>; }
function Field({ label, wide = false, children }: { label: string; wide?: boolean; children: React.ReactNode }) { return <label className={wide ? "space-y-2 sm:col-span-2" : "space-y-2"}><span className="text-sm font-bold text-slate-700">{label}</span>{children}</label>; }
function Check({ label, checked, onChange }: { label: string; checked: boolean; onChange: (value: boolean) => void }) { return <label className="flex cursor-pointer items-center gap-3 rounded-xl border border-sky-100 bg-sky-50/50 p-4 text-sm font-bold"><input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} className="size-4 accent-blue-600" />{label}</label>; }
