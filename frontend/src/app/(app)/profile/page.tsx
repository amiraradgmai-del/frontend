"use client";

import { FormEvent, useEffect, useState } from "react";
import { Save } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

type Profile = {
  email: string; phone: string; alternate_phone: string; alternate_email: string; phone_verified: boolean;
  province: string; city: string; postal_code: string; address: string; birth_date: string | null;
  company_name: string; job_title: string; business_type: string; economic_code: string;
  website: string; taxpayer_type: string; preferred_contact_method: "phone" | "sms" | "email";
  marketing_notifications: boolean; service_notifications: boolean; bio: string;
  profile_score: number; reward_points: number; referral_code: string;
};

const empty: Profile = {
  email: "", phone: "", alternate_phone: "", alternate_email: "", phone_verified: false, province: "", city: "",
  postal_code: "", address: "", birth_date: null, company_name: "", job_title: "", business_type: "",
  economic_code: "", website: "", taxpayer_type: "individual", preferred_contact_method: "phone",
  marketing_notifications: false, service_notifications: true, bio: "", profile_score: 10,
  reward_points: 0, referral_code: "",
};

export default function ProfilePage() {
  const [form, setForm] = useState<Profile>(empty);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    api<Profile>("api/v1/portal/profile").then(setForm)
      .catch((error) => setMessage(error instanceof ApiError ? error.message : "دریافت اطلاعات پروفایل ممکن نیست."))
      .finally(() => setLoading(false));
  }, []);

  function update<K extends keyof Profile>(key: K, value: Profile[K]) {
    setForm((current) => ({ ...current, [key]: value }));
    setMessage("");
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    try {
      const payload = { ...form, birth_date: form.birth_date || null };
      const result = await api<Profile>("api/v1/portal/profile", { method: "PATCH", body: JSON.stringify(payload) });
      setForm(result);
      setMessage("اطلاعات پروفایل با موفقیت ذخیره شد.");
    } catch (error) {
      setMessage(error instanceof ApiError ? error.message : "ذخیره اطلاعات انجام نشد.");
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <p className="p-10 text-center text-muted-foreground">در حال دریافت اطلاعات...</p>;

  return (
    <Card className="border-slate-200 bg-white shadow-sm">
      <CardHeader>
        <CardTitle>اطلاعات تکمیلی</CardTitle>
        <CardDescription>اطلاعات پروفایل خود را کامل کنید. موارد اختیاری کنار عنوان فیلد مشخص شده‌اند.</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={submit} className="grid gap-x-6 gap-y-5 md:grid-cols-2">
          {message && <p className="rounded-xl border border-blue-100 bg-blue-50 p-3 text-sm text-blue-800 md:col-span-2">{message}</p>}

          <Field label="ایمیل">
            <Input value={form.email} disabled dir="ltr" />
          </Field>
          <Field label="شماره موبایل">
            <Input value={form.phone} onChange={(event) => update("phone", event.target.value)} placeholder="شماره موبایل خود را وارد کنید" dir="ltr" />
            <Badge className="mt-2" variant="outline">{form.phone_verified ? "تأییدشده" : "تأییدنشد‌ه"}</Badge>
          </Field>
          <Field label="شماره تماس جایگزین" optional>
            <Input value={form.alternate_phone} onChange={(event) => update("alternate_phone", event.target.value)} placeholder="شماره تماس جایگزین" dir="ltr" />
          </Field>
          <Field label="نوع مؤدی">
            <Select value={form.taxpayer_type} onChange={(value) => update("taxpayer_type", value)} options={[["individual", "شخص حقیقی"], ["company", "شخص حقوقی"]]} />
          </Field>
          <Field label="روش ارتباط ترجیحی">
            <Select value={form.preferred_contact_method} onChange={(value) => update("preferred_contact_method", value as Profile["preferred_contact_method"])} options={[["phone", "تماس تلفنی"], ["sms", "پیامک"], ["email", "ایمیل"]]} />
          </Field>
          <Field label="استان">
            <Input value={form.province} onChange={(event) => update("province", event.target.value)} placeholder="استان محل سکونت" />
          </Field>
          <Field label="شهر">
            <Input value={form.city} onChange={(event) => update("city", event.target.value)} placeholder="شهر محل سکونت" />
          </Field>
          <Field label="تاریخ تولد" optional>
            <Input type="date" value={form.birth_date || ""} onChange={(event) => update("birth_date", event.target.value || null)} dir="ltr" />
          </Field>
          <Field label="نام شرکت یا محل فعالیت" optional>
            <Input value={form.company_name} onChange={(event) => update("company_name", event.target.value)} placeholder="نام شرکت یا محل فعالیت خود را وارد کنید" />
          </Field>
          <Field label="عنوان شغلی" optional>
            <Input value={form.job_title} onChange={(event) => update("job_title", event.target.value)} placeholder="عنوان شغلی خود را وارد کنید" />
          </Field>
          <Field label="نوع فعالیت" optional>
            <Input value={form.business_type} onChange={(event) => update("business_type", event.target.value)} placeholder="حوزه فعالیت خود را وارد کنید" />
          </Field>
          <Field label="وب‌سایت" optional>
            <Input value={form.website} onChange={(event) => update("website", event.target.value)} placeholder="https://example.com" dir="ltr" />
          </Field>
          <Field label="نشانی کامل" optional>
            <Input value={form.address} onChange={(event) => update("address", event.target.value)} placeholder="نشانی محل سکونت یا فعالیت" />
          </Field>
          <Field label="درباره شما و نیازهای مالیاتی" optional wide>
            <Textarea className="min-h-32" value={form.bio} onChange={(event) => update("bio", event.target.value)} placeholder="نیازها و حوزه فعالیت خود را کوتاه توضیح دهید" />
          </Field>

          <div className="grid gap-3 rounded-xl border bg-slate-50 p-4 md:col-span-2 sm:grid-cols-2">
            <Toggle label="اعلان‌های خدمات و پرداخت" checked={form.service_notifications} onChange={(value) => update("service_notifications", value)} />
            <Toggle label="پیشنهادها و خبرهای سامانه" checked={form.marketing_notifications} onChange={(value) => update("marketing_notifications", value)} />
          </div>

          <Button type="submit" className="md:col-span-2" disabled={saving}>
            <Save /> {saving ? "در حال ذخیره..." : "ذخیره و تکمیل پروفایل"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

function Field({ label, optional, wide, children }: { label: string; optional?: boolean; wide?: boolean; children: React.ReactNode }) {
  return (
    <label className={`space-y-2 text-sm ${wide ? "md:col-span-2" : ""}`}>
      <span className="font-semibold">
        {label}
        {optional && <span className="mr-1 text-xs font-normal text-slate-400">(اختیاری)</span>}
      </span>
      {children}
    </label>
  );
}

function Select({ value, onChange, options }: { value: string; onChange: (value: string) => void; options: [string, string][] }) {
  return <select value={value} onChange={(event) => onChange(event.target.value)} className="h-10 w-full rounded-lg border bg-white px-3 text-sm">{options.map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select>;
}

function Toggle({ label, checked, onChange }: { label: string; checked: boolean; onChange: (value: boolean) => void }) {
  return <label className="flex items-center justify-between gap-4 text-sm"><span>{label}</span><input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} className="size-5 accent-primary" /></label>;
}
