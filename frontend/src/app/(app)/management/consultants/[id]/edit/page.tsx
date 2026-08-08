"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowRight, Save } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { IranCitySelect } from "@/lib/iran-cities";

type Profile = {
  id: string; full_name: string; email: string; consultant_type: string;
  professional_title: string; bio: string; specialties: string[]; skills: string[];
  qualifications: string; consultation_price: number; is_verified: boolean;
  is_available: boolean; is_online: boolean; offers_in_person: boolean; city: string;
  office_address: string; years_experience: number; bank_account_holder: string;
  bank_iban: string; contract_number: string; contract_start?: string | null;
  contract_end?: string | null; contract_status: string;
};
type Details = { profile: Profile };

const empty: Profile = {
  id: "", full_name: "", email: "", consultant_type: "independent",
  professional_title: "", bio: "", specialties: [], skills: [], qualifications: "",
  consultation_price: 0, is_verified: false, is_available: false, is_online: true,
  offers_in_person: false, city: "", office_address: "", years_experience: 0,
  bank_account_holder: "", bank_iban: "", contract_number: "", contract_start: null,
  contract_end: null, contract_status: "not_set",
};

export default function ConsultantEditPage() {
  const params = useParams<{ id: string }>();
  const [form, setForm] = useState<Profile>(empty);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api<Details>(`api/v1/consultations/manage/profiles/${params.id}/details`)
      .then((result) => setForm(result.profile))
      .catch((reason) => setError(reason instanceof Error ? reason.message : "اطلاعات مشاور دریافت نشد."))
      .finally(() => setLoading(false));
  }, [params.id]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSaving(true); setError(""); setMessage("");
    try {
      await api(`api/v1/consultations/manage/profiles/${params.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          professional_title: form.professional_title,
          bio: form.bio,
          specialties: form.specialties,
          skills: form.skills,
          qualifications: form.qualifications,
          consultation_price: Number(form.consultation_price),
          is_verified: form.is_verified,
          is_available: form.is_available,
          is_online: form.is_online,
          offers_in_person: form.offers_in_person,
          city: form.city,
          office_address: form.office_address,
          years_experience: Number(form.years_experience),
          bank_account_holder: form.bank_account_holder,
          bank_iban: form.bank_iban.trim().toUpperCase(),
          contract_number: form.contract_number,
          contract_start: form.contract_start ? new Date(form.contract_start).toISOString() : null,
          contract_end: form.contract_end ? new Date(form.contract_end).toISOString() : null,
          contract_status: form.contract_status,
        }),
      });
      setMessage("تمام اطلاعات مشاور با موفقیت ذخیره شد.");
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : "ذخیره اطلاعات انجام نشد.");
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <p className="rounded-2xl border bg-white p-10 text-center">در حال دریافت اطلاعات مشاور…</p>;
  return <div className="space-y-6">
    <header className="flex flex-wrap items-center justify-between gap-4"><div><p className="text-sm font-bold text-blue-600">مدیریت مشاوران</p><h1 className="mt-1 text-3xl font-black">ویرایش کامل مشاور</h1><p className="mt-2 text-slate-500">{form.full_name} · {form.email}</p></div><Link href="/management/consultants" className="flex items-center gap-2 rounded-xl border bg-white px-4 py-2 text-sm font-bold"><ArrowRight className="size-4" /> بازگشت</Link></header>
    {error && <p className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{error}</p>}
    {message && <p className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700">{message}</p>}
    <form onSubmit={submit} className="space-y-5">
      <Section title="اطلاعات حرفه‌ای"><Field label="عنوان تخصصی"><Input required minLength={3} value={form.professional_title} onChange={(e) => setForm({ ...form, professional_title: e.target.value })} /></Field><Field label="سال سابقه"><Input type="number" min={0} max={70} value={form.years_experience} onChange={(e) => setForm({ ...form, years_experience: Number(e.target.value) })} /></Field><Field label="شهر"><IranCitySelect value={form.city} onChange={(value) => setForm({ ...form, city: value })} /></Field><Field label="هزینه هر جلسه (تومان)"><Input type="number" min={0} value={form.consultation_price} onChange={(e) => setForm({ ...form, consultation_price: Number(e.target.value) })} /></Field><Field wide label="معرفی مشاور"><Textarea className="min-h-28" value={form.bio} onChange={(e) => setForm({ ...form, bio: e.target.value })} /></Field><Field wide label="سوابق و مدارک"><Textarea className="min-h-28" value={form.qualifications} onChange={(e) => setForm({ ...form, qualifications: e.target.value })} /></Field><Field label="حوزه‌های تخصصی (با ویرگول جدا کنید)"><Input value={form.specialties.join("، ")} onChange={(e) => setForm({ ...form, specialties: split(e.target.value) })} /></Field><Field label="مهارت‌ها (با ویرگول جدا کنید)"><Input value={form.skills.join("، ")} onChange={(e) => setForm({ ...form, skills: split(e.target.value) })} /></Field><Field wide label="آدرس دفتر"><Input value={form.office_address} onChange={(e) => setForm({ ...form, office_address: e.target.value })} /></Field></Section>
      <Section title="وضعیت و شیوه ارائه خدمت"><Checks form={form} setForm={setForm} /></Section>
      <Section title="اطلاعات بانکی"><Field label="نام صاحب حساب"><Input value={form.bank_account_holder} onChange={(e) => setForm({ ...form, bank_account_holder: e.target.value })} /></Field><Field label="شماره شبا"><Input dir="ltr" placeholder="IR000000000000000000000000" value={form.bank_iban} onChange={(e) => setForm({ ...form, bank_iban: e.target.value.toUpperCase() })} /></Field></Section>
      <Section title="قرارداد همکاری"><Field label="شماره قرارداد"><Input value={form.contract_number} onChange={(e) => setForm({ ...form, contract_number: e.target.value })} /></Field><Field label="وضعیت قرارداد"><select className="h-10 w-full rounded-lg border bg-white px-3 text-sm" value={form.contract_status} onChange={(e) => setForm({ ...form, contract_status: e.target.value })}><option value="not_set">ثبت نشده</option><option value="draft">پیش‌نویس</option><option value="active">فعال</option><option value="expired">منقضی</option><option value="terminated">خاتمه‌یافته</option></select></Field><Field label="شروع قرارداد"><Input type="date" value={form.contract_start?.slice(0, 10) ?? ""} onChange={(e) => setForm({ ...form, contract_start: e.target.value || null })} /></Field><Field label="پایان قرارداد"><Input type="date" value={form.contract_end?.slice(0, 10) ?? ""} onChange={(e) => setForm({ ...form, contract_end: e.target.value || null })} /></Field></Section>
      <Button className="w-full py-6 text-base" disabled={saving}><Save /> {saving ? "در حال ذخیره…" : "ذخیره تمام تغییرات"}</Button>
    </form>
  </div>;
}

function split(value: string) { return value.split(/[،,]/).map((item) => item.trim()).filter(Boolean); }
function Section({ title, children }: { title: string; children: React.ReactNode }) { return <Card className="border-sky-100 bg-white"><CardHeader><CardTitle>{title}</CardTitle></CardHeader><CardContent className="grid gap-4 sm:grid-cols-2">{children}</CardContent></Card>; }
function Field({ label, wide, children }: { label: string; wide?: boolean; children: React.ReactNode }) { return <label className={`space-y-2 text-sm font-bold ${wide ? "sm:col-span-2" : ""}`}><span>{label}</span>{children}</label>; }
function Checks({ form, setForm }: { form: Profile; setForm: (value: Profile) => void }) { return <>{[["is_verified", "صلاحیت تأییدشده"], ["is_available", "آماده پذیرش"], ["is_online", "مشاوره آنلاین"], ["offers_in_person", "مشاوره حضوری"]].map(([key, label]) => <label key={key} className="flex items-center gap-3 rounded-xl border p-4 text-sm font-bold"><input type="checkbox" checked={Boolean(form[key as keyof Profile])} onChange={(e) => setForm({ ...form, [key]: e.target.checked })} />{label}</label>)}</>; }
