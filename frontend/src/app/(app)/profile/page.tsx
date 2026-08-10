"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { CheckCircle2, Circle, Info, KeyRound, Save, ShieldCheck } from "lucide-react";

import { FormFeedbackDialog } from "@/components/form-feedback-dialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { api, ApiError } from "@/lib/api";
import { IRAN_CITIES, IRAN_PROVINCES } from "@/lib/iran-cities";

type Profile = {
  email: string;
  phone: string;
  phone_verified: boolean;
  province: string;
  city: string;
  taxpayer_type: string;
  preferred_contact_method: "phone" | "sms" | "email" | "both";
  bio: string;
  profile_score: number;
  reward_points: number;
  referral_code: string;
  profile_complete: boolean;
  missing_required_fields: string[];
};

type Feedback = { title: string; message: string; kind: "error" | "success" | "info" } | null;
type VerificationRequest = { request_id: string; expires_in: number; resend_after: number };

const empty: Profile = {
  email: "", phone: "", phone_verified: false, province: "", city: "",
  taxpayer_type: "", profile_score: 10, reward_points: 0,
  preferred_contact_method: "phone", bio: "",
  referral_code: "", profile_complete: false, missing_required_fields: [],
};

export default function ProfilePage() {
  const [form, setForm] = useState<Profile>(empty);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState<Feedback>(null);
  const [verificationId, setVerificationId] = useState("");
  const [verificationCode, setVerificationCode] = useState("");
  const [resendSeconds, setResendSeconds] = useState(0);

  async function loadProfile() {
    try {
      setForm(await api<Profile>("api/v1/portal/profile"));
    } catch (error) {
      setFeedback({ title: "دریافت اطلاعات انجام نشد", message: error instanceof ApiError ? error.message : "ارتباط با سرور برقرار نشد.", kind: "error" });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const timer = window.setTimeout(() => void loadProfile(), 0);
    return () => window.clearTimeout(timer);
  }, []);
  useEffect(() => {
    if (resendSeconds <= 0) return;
    const timer = window.setInterval(() => setResendSeconds((value) => Math.max(0, value - 1)), 1000);
    return () => window.clearInterval(timer);
  }, [resendSeconds]);

  const completedRequired = useMemo(() => 4 - form.missing_required_fields.length, [form.missing_required_fields]);
  const requiredPercent = Math.max(0, Math.round((completedRequired / 4) * 100));

  function update<K extends keyof Profile>(key: K, value: Profile[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function validateRequired(): string | null {
    if (form.email.trim() && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim())) return "ایمیل واردشده معتبر نیست.";
    const phone = form.phone.replace(/[\s()-]/g, "");
    if (!/^09\d{9}$/.test(phone)) return "شماره موبایل را به‌صورت ۱۱ رقمی و با 09 وارد کنید.";
    if (!form.phone_verified) return "ابتدا شماره موبایل را با کد پیامکی تأیید کنید.";
    if (!form.province.trim()) return "استان را انتخاب کنید.";
    if (!form.city.trim()) return "شهر را انتخاب کنید.";
    if (!form.taxpayer_type.trim()) return "نوع مؤدی را انتخاب کنید.";
    return null;
  }

  function payload() {
    return {
      email: form.email.trim() || null,
      phone: form.phone,
      province: form.province,
      city: form.city,
      taxpayer_type: form.taxpayer_type,
      preferred_contact_method: form.preferred_contact_method,
      bio: form.bio,
    };
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    const validation = validateRequired();
    if (validation) {
      setFeedback({ title: "اطلاعات ضروری کامل نیست", message: validation, kind: "error" });
      return;
    }
    setSaving(true);
    try {
      const result = await api<Profile>("api/v1/portal/profile", { method: "PATCH", body: JSON.stringify(payload()) });
      setForm(result);
      setFeedback({ title: "پروفایل ذخیره شد", message: "اطلاعات ضروری تکمیل شد و همه بخش‌های حساب شما در دسترس است.", kind: "success" });
    } catch (error) {
      setFeedback({ title: "ذخیره انجام نشد", message: error instanceof ApiError ? error.message : "دوباره تلاش کنید.", kind: "error" });
    } finally {
      setSaving(false);
    }
  }

  async function sendVerificationCode() {
    if (!/^09\d{9}$/.test(form.phone.replace(/[\s()-]/g, ""))) {
      setFeedback({ title: "شماره موبایل نامعتبر است", message: "شماره را مانند 09123456789 وارد کنید.", kind: "error" });
      return;
    }
    try {
      const result = await api<VerificationRequest>("api/v1/portal/profile/phone/send-code", { method: "POST", body: JSON.stringify({ phone: form.phone }) });
      setVerificationId(result.request_id);
      setResendSeconds(result.resend_after);
      setFeedback({ title: "کد ارسال شد", message: "کد شش‌رقمی ارسال‌شده را در کادر تأیید وارد کنید.", kind: "info" });
    } catch (error) {
      setFeedback({ title: "ارسال کد انجام نشد", message: error instanceof ApiError ? error.message : "دوباره تلاش کنید.", kind: "error" });
    }
  }

  async function verifyPhone() {
    if (!verificationId || !/^\d{6}$/.test(verificationCode)) {
      setFeedback({ title: "کد تأیید کامل نیست", message: "کد شش‌رقمی پیامک‌شده را وارد کنید.", kind: "error" });
      return;
    }
    try {
      await api("api/v1/portal/profile/phone/verify", { method: "POST", body: JSON.stringify({ request_id: verificationId, code: verificationCode }) });
      setVerificationCode("");
      setVerificationId("");
      await loadProfile();
      setFeedback({ title: "شماره تأیید شد", message: "شماره موبایل شما با موفقیت تأیید شد.", kind: "success" });
    } catch (error) {
      setFeedback({ title: "تأیید انجام نشد", message: error instanceof ApiError ? error.message : "کد را دوباره بررسی کنید.", kind: "error" });
    }
  }

  if (loading) return <p className="p-10 text-center text-muted-foreground">در حال دریافت اطلاعات پروفایل...</p>;

  return (
    <div className="space-y-6">
      <Card className="overflow-hidden border-blue-100 bg-gradient-to-l from-blue-700 via-blue-600 to-cyan-500 text-white shadow-xl">
        <CardContent className="grid gap-5 p-6 md:grid-cols-[1fr_280px] md:items-center">
          <div><p className="text-sm font-bold text-cyan-100">راهنمای شروع استفاده</p><h1 className="mt-2 text-3xl font-black">تکمیل اطلاعات ضروری حساب</h1><p className="mt-3 text-sm leading-7 text-blue-50">برای حفظ امنیت حساب و رزرو دقیق خدمات، موارد ضروری را تکمیل کنید. بقیه اطلاعات اختیاری هستند.</p></div>
          <div className="rounded-2xl bg-white/15 p-4 backdrop-blur"><div className="flex items-center justify-between"><span className="text-sm font-bold">پیشرفت ضروری</span><b>{requiredPercent.toLocaleString("fa-IR")}٪</b></div><div className="mt-3 h-2 overflow-hidden rounded-full bg-white/20"><span className="block h-full rounded-full bg-amber-300 transition-all" style={{ width: `${requiredPercent}%` }} /></div><p className="mt-3 text-xs text-blue-50">{form.profile_complete ? "حساب شما آماده استفاده است." : `${form.missing_required_fields.length.toLocaleString("fa-IR")} مورد باقی مانده است.`}</p></div>
        </CardContent>
      </Card>

      <Card className="border-amber-200 bg-amber-50/70"><CardHeader><CardTitle className="flex items-center gap-2 text-lg"><Info className="text-amber-600" /> چه اطلاعاتی لازم است؟</CardTitle><CardDescription>بعد از تکمیل این چهار مورد، تمام امکانات کاربری فعال می‌شود.</CardDescription></CardHeader><CardContent className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">{["شماره موبایل تأییدشده", "استان", "شهر", "نوع مؤدی"].map((item) => { const missing = form.missing_required_fields.includes(item); return <div key={item} className={`flex items-center gap-2 rounded-xl border p-3 text-sm font-bold ${missing ? "border-amber-200 bg-white text-amber-900" : "border-emerald-200 bg-emerald-50 text-emerald-700"}`}>{missing ? <Circle className="size-4" /> : <CheckCircle2 className="size-4" />}{item}</div>; })}</CardContent></Card>

      <Card className="border-slate-200 bg-white shadow-sm">
        <CardHeader><CardTitle>اطلاعات حساب</CardTitle><CardDescription>فقط موارد ضروری با نشان «ضروری» مشخص شده‌اند؛ سایر فیلدها اختیاری هستند.</CardDescription></CardHeader>
        <CardContent>
          <form noValidate onSubmit={submit} className="grid gap-x-6 gap-y-5 md:grid-cols-2">
            <Field label="ایمیل (اختیاری)"><Input type="email" value={form.email} onChange={(event) => update("email", event.target.value)} placeholder="name@example.com" autoComplete="email" dir="ltr" /></Field>
            <Field label="شماره موبایل" required><div className="flex gap-2"><Input value={form.phone} onChange={(event) => update("phone", event.target.value)} placeholder="09123456789" dir="ltr" /><Button type="button" variant="outline" onClick={() => void sendVerificationCode()} disabled={resendSeconds > 0 || form.phone_verified}>{form.phone_verified ? <><ShieldCheck /> تأییدشده</> : resendSeconds > 0 ? `${resendSeconds.toLocaleString("fa-IR")} ثانیه` : "ارسال کد"}</Button></div></Field>
            {verificationId && <div className="grid gap-2 rounded-2xl border border-blue-200 bg-blue-50 p-4 md:col-span-2 sm:grid-cols-[1fr_auto]"><Input inputMode="numeric" maxLength={6} value={verificationCode} onChange={(event) => setVerificationCode(event.target.value.replace(/\D/g, ""))} placeholder="کد شش‌رقمی" dir="ltr" /><Button type="button" onClick={() => void verifyPhone()}><KeyRound /> تأیید شماره</Button></div>}
            <Field label="نوع مؤدی" required><Select value={form.taxpayer_type} onChange={(value) => update("taxpayer_type", value)} options={[["", "انتخاب نوع مؤدی"], ["individual", "شخص حقیقی"], ["company", "شخص حقوقی"]]} /></Field>
            <Field label="روش ارتباط ترجیحی"><Select value={form.preferred_contact_method} onChange={(value) => update("preferred_contact_method", value as Profile["preferred_contact_method"])} options={[["phone", "تماس تلفنی"], ["sms", "پیامک"], ["email", "ایمیل"], ["both", "هر دو (تماس و پیامک)"]]} /></Field>
            <Field label="استان" required><select value={form.province} onChange={(event) => update("province", event.target.value)} className="h-10 w-full rounded-lg border bg-white px-3 text-sm"><option value="">انتخاب استان</option>{IRAN_PROVINCES.map((province) => <option key={province} value={province}>{province}</option>)}</select></Field>
            <Field label="شهر" required><select value={form.city} onChange={(event) => update("city", event.target.value)} className="h-10 w-full rounded-lg border bg-white px-3 text-sm"><option value="">انتخاب شهر</option>{IRAN_CITIES.map((city) => <option key={city} value={city}>{city}</option>)}</select></Field>
            <Field label="درباره شما و نیازهای مالیاتی" wide><Textarea className="min-h-32" value={form.bio} onChange={(event) => update("bio", event.target.value)} placeholder="اختیاری؛ نیازها و حوزه فعالیت خود را کوتاه توضیح دهید" /></Field>
            <Button type="submit" className="md:col-span-2" disabled={saving}><Save /> {saving ? "در حال ذخیره..." : "ذخیره و فعال‌سازی حساب"}</Button>
          </form>
        </CardContent>
      </Card>
      <FormFeedbackDialog open={Boolean(feedback)} title={feedback?.title ?? ""} message={feedback?.message ?? ""} kind={feedback?.kind} onClose={() => setFeedback(null)} />
    </div>
  );
}

function Field({ label, required = false, wide = false, children }: { label: string; required?: boolean; wide?: boolean; children: React.ReactNode }) {
  return <label className={`space-y-2 text-sm ${wide ? "md:col-span-2" : ""}`}><span className="font-semibold">{label}{required ? <span className="mr-1 rounded-md bg-rose-50 px-1.5 py-0.5 text-[10px] font-bold text-rose-600">ضروری</span> : null}</span>{children}</label>;
}

function Select({ value, onChange, options }: { value: string; onChange: (value: string) => void; options: [string, string][] }) {
  return <select value={value} onChange={(event) => onChange(event.target.value)} className="h-10 w-full rounded-lg border bg-white px-3 text-sm">{options.map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select>;
}
