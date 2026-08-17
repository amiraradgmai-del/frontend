"use client";

import { FormEvent, useEffect, useState } from "react";
import Image from "next/image";
import { BadgeCheck, BriefcaseBusiness, Clock3, Rocket, Save, ShieldAlert, Upload, UserRound } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

type Review = { id: string; status: "pending" | "approved" | "rejected" | "correction_required"; admin_note: string; created_at: string };
type Profile = {
  full_name: string; email: string; consultant_type: "independent" | "company"; professional_title: string; bio: string;
  specialties: string[]; skills: string[]; qualifications: string; education: Array<{ title?: string }>;
  certifications: Array<{ title?: string }>; work_history: Array<{ title?: string }>; weekly_schedule: { notes?: string };
  profile_image_url: string; years_experience: number; consultation_price: number; city: string; office_address: string;
  is_online: boolean; offers_in_person: boolean; is_verified: boolean; boosted_until?: string | null; verification_requests: Review[];
};

const statusLabel = { pending: "در انتظار بررسی", approved: "تأییدشده", rejected: "ردشده", correction_required: "نیازمند اصلاح" };
const lines = (value: string) => value.split("\n").map((item) => item.trim()).filter(Boolean);
const records = (value: string) => lines(value).map((title) => ({ title }));

export default function ConsultantProfilePage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [form, setForm] = useState({
    professional_title: "", bio: "", specialties: "", skills: "", qualifications: "", education: "",
    certifications: "", work_history: "", weekly_schedule: "", profile_image_url: "", years_experience: "",
    consultation_price: "", city: "", office_address: "", is_online: true, offers_in_person: true,
  });
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [uploadingPhoto, setUploadingPhoto] = useState(false);

  useEffect(() => {
    api<Profile>("api/v1/consultations/profile/mine").then((data) => {
      setProfile(data);
      setForm({
        professional_title: data.professional_title, bio: data.bio, specialties: data.specialties.join("، "),
        skills: data.skills.join("، "), qualifications: data.qualifications,
        education: data.education.map((item) => item.title ?? "").filter(Boolean).join("\n"),
        certifications: data.certifications.map((item) => item.title ?? "").filter(Boolean).join("\n"),
        work_history: data.work_history.map((item) => item.title ?? "").filter(Boolean).join("\n"),
        weekly_schedule: data.weekly_schedule?.notes ?? "", profile_image_url: data.profile_image_url,
        years_experience: String(data.years_experience), consultation_price: String(data.consultation_price),
        city: data.city, office_address: data.office_address, is_online: data.is_online, offers_in_person: data.offers_in_person,
      });
    }).catch((error) => setMessage(error instanceof ApiError ? error.message : "دریافت پروفایل ممکن نیست."));
  }, []);

  const latest = profile?.verification_requests[0];
  const pending = profile?.verification_requests.some((item) => item.status === "pending");
  const set = (key: keyof typeof form, value: string | boolean) => setForm((current) => ({ ...current, [key]: value }));

  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setMessage("");
    try {
      await api("api/v1/consultations/verification", {
        method: "POST",
        body: JSON.stringify({
          consultant_type: profile?.consultant_type ?? "independent",
          professional_title: form.professional_title,
          specialties: form.specialties.split("،").map((item) => item.trim()).filter(Boolean),
          years_experience: Number(form.years_experience),
          qualifications: form.qualifications,
          applicant_note: "درخواست بررسی تغییرات پروفایل حرفه‌ای",
          bio: form.bio,
          skills: form.skills.split("،").map((item) => item.trim()).filter(Boolean),
          education: records(form.education), certifications: records(form.certifications), work_history: records(form.work_history),
          weekly_schedule: { notes: form.weekly_schedule }, profile_image_url: form.profile_image_url,
          consultation_price: Number(form.consultation_price), city: form.city, office_address: form.office_address,
          is_online: form.is_online, offers_in_person: form.offers_in_person,
        }),
      });
      setMessage("تغییرات برای بررسی مدیر ارسال شد. نسخه عمومی تا زمان تأیید تغییر نمی‌کند.");
      const refreshed = await api<Profile>("api/v1/consultations/profile/mine");
      setProfile(refreshed);
    } catch (error) { setMessage(error instanceof ApiError ? error.message : "ارسال تغییرات انجام نشد."); }
    finally { setBusy(false); }
  }

  async function boost() {
    if (!window.confirm("با پرداخت ۹۹٬۰۰۰ تومان، پروفایل شما هفت روز در بالای فهرست نمایش داده شود؟")) return;
    setBusy(true); setMessage("");
    try {
      const result = await api<{ boosted_until: string }>("api/v1/consultations/profile/boost", { method: "POST" });
      setProfile((current) => current ? { ...current, boosted_until: result.boosted_until } : current);
      setMessage("پروفایل شما با موفقیت برای هفت روز ارتقا یافت.");
    } catch (error) { setMessage(error instanceof ApiError ? error.message : "ارتقای پروفایل انجام نشد."); }
    finally { setBusy(false); }
  }

  async function uploadPhoto(file: File) {
    setUploadingPhoto(true); setMessage("");
    try {
      const body = new FormData();
      body.append("file", file);
      const result = await api<{ url: string }>("api/v1/consultations/profile/photo", { method: "POST", body });
      set("profile_image_url", result.url);
      setMessage("عکس بارگذاری شد. برای انتشار عمومی، تغییرات پروفایل را برای تأیید ارسال کنید.");
    } catch (error) {
      setMessage(error instanceof ApiError ? error.message : "بارگذاری عکس انجام نشد.");
    } finally { setUploadingPhoto(false); }
  }

  if (!profile) return <div className="rounded-2xl bg-white p-10 text-center text-sm text-slate-500">{message || "در حال دریافت پروفایل..."}</div>;

  return <div className="space-y-7">
    <header className="rounded-[2rem] bg-gradient-to-l from-blue-700 via-indigo-600 to-cyan-500 p-8 text-white shadow-xl"><p className="text-sm text-blue-50">هویت حرفه‌ای مشاور</p><h1 className="mt-2 text-3xl font-black">پروفایل و تنظیمات همکاری</h1><p className="mt-2 text-blue-50">اطلاعات عمومی، قیمت، سوابق و شیوه پذیرش خود را مدیریت کنید.</p></header>

    <section className="grid gap-4 md:grid-cols-3">
      <Summary icon={UserRound} label="نام مشاور" value={profile.full_name} />
      <Summary icon={BadgeCheck} label="وضعیت عمومی" value={profile.is_verified ? "تأییدشده" : "غیرفعال"} />
      <Summary icon={Clock3} label="آخرین بررسی" value={latest ? statusLabel[latest.status] : "بدون درخواست"} />
    </section>

    {latest?.admin_note && <div className="rounded-2xl border border-amber-200 bg-amber-50 p-5 text-sm leading-7 text-amber-950"><p className="flex items-center gap-2 font-black"><ShieldAlert className="size-5" /> توضیح مدیر</p><p className="mt-2">{latest.admin_note}</p></div>}
    {message && <p className="rounded-xl bg-sky-50 p-4 text-sm text-sky-800">{message}</p>}

    <Card className="border-amber-200 bg-gradient-to-l from-amber-50 to-white"><CardContent className="flex flex-wrap items-center justify-between gap-4 p-5"><div><p className="flex items-center gap-2 font-black"><Rocket className="text-amber-600" /> نردبان پروفایل</p><p className="mt-1 text-sm text-slate-600">نمایش در بالای فهرست مشاوران برای ۷ روز؛ هزینه ۹۹٬۰۰۰ تومان از کیف پول.</p>{profile.boosted_until && new Date(profile.boosted_until) > new Date() && <p className="mt-2 text-xs font-bold text-emerald-700">فعال تا {new Date(profile.boosted_until).toLocaleString("fa-IR")}</p>}</div><Button type="button" variant="outline" disabled={busy || !profile.is_verified} onClick={() => void boost()}>ارتقای پروفایل</Button></CardContent></Card>

    <Card className="border-white/70 bg-white/95"><CardHeader><CardTitle>اطلاعات پروفایل</CardTitle><CardDescription>هر خط در سوابق و مدارک به‌عنوان یک مورد جدا ثبت می‌شود.</CardDescription></CardHeader><CardContent>
      <form onSubmit={submit} className="grid gap-4 sm:grid-cols-2">
        <Field label="عنوان حرفه‌ای"><Input value={form.professional_title} onChange={(e) => set("professional_title", e.target.value)} required /></Field>
        <Field label="شهر"><Input value={form.city} onChange={(e) => set("city", e.target.value)} /></Field>
        <Field label="سال سابقه"><Input type="number" min="0" max="70" value={form.years_experience} onChange={(e) => set("years_experience", e.target.value)} required /></Field>
        <Field label="هزینه جلسه به تومان"><Input inputMode="numeric" value={form.consultation_price} onChange={(e) => set("consultation_price", e.target.value.replace(/\D/g, ""))} required /></Field>
        <Field label="حوزه‌های تخصصی"><Input value={form.specialties} onChange={(e) => set("specialties", e.target.value)} placeholder="با ، جدا کنید" required /></Field>
        <Field label="مهارت‌ها"><Input value={form.skills} onChange={(e) => set("skills", e.target.value)} placeholder="با ، جدا کنید" /></Field>
        <Field label="عکس پروفایل"><div className="flex items-center gap-3">{form.profile_image_url ? <Image src={form.profile_image_url} width={64} height={64} alt="پیش‌نمایش عکس پروفایل" className="size-16 rounded-2xl border object-cover" unoptimized /> : <span className="flex size-16 items-center justify-center rounded-2xl bg-slate-100"><UserRound /></span>}<label className={`flex cursor-pointer items-center gap-2 rounded-xl border px-4 py-2 font-bold ${uploadingPhoto ? "pointer-events-none opacity-50" : ""}`}><Upload className="size-4" />{uploadingPhoto ? "در حال بارگذاری..." : "انتخاب عکس"}<input type="file" accept="image/png,image/jpeg,image/webp" className="hidden" onChange={(e) => e.target.files?.[0] && void uploadPhoto(e.target.files[0])} /></label></div><p className="text-xs text-slate-500">PNG، JPG یا WebP؛ حداکثر ۸ مگابایت</p></Field>
        <Field label="آدرس دفتر"><Input value={form.office_address} onChange={(e) => set("office_address", e.target.value)} /></Field>
        <Field label="معرفی کوتاه" wide><Textarea className="min-h-24" value={form.bio} onChange={(e) => set("bio", e.target.value)} /></Field>
        <Field label="صلاحیت‌ها و توضیحات حرفه‌ای" wide><Textarea className="min-h-24" value={form.qualifications} onChange={(e) => set("qualifications", e.target.value)} required /></Field>
        <Field label="تحصیلات"><Textarea value={form.education} onChange={(e) => set("education", e.target.value)} /></Field>
        <Field label="گواهی‌ها و مدارک"><Textarea value={form.certifications} onChange={(e) => set("certifications", e.target.value)} /></Field>
        <Field label="سوابق کاری"><Textarea value={form.work_history} onChange={(e) => set("work_history", e.target.value)} /></Field>
        <Field label="روزها و ساعات کاری"><Textarea value={form.weekly_schedule} onChange={(e) => set("weekly_schedule", e.target.value)} placeholder="مثلاً شنبه تا چهارشنبه، ۹ تا ۱۷" /></Field>
        <div className="flex flex-wrap gap-5 rounded-2xl bg-sky-50 p-4 text-sm sm:col-span-2"><label className="flex items-center gap-2"><input type="checkbox" checked={form.is_online} onChange={(e) => set("is_online", e.target.checked)} /> پذیرش آنلاین</label><label className="flex items-center gap-2"><input type="checkbox" checked={form.offers_in_person} onChange={(e) => set("offers_in_person", e.target.checked)} /> پذیرش حضوری</label></div>
        <Button className="sm:col-span-2" disabled={busy || pending}><Save /> {pending ? "در انتظار بررسی مدیر" : "ارسال تغییرات برای تأیید"}</Button>
      </form>
    </CardContent></Card>
  </div>;
}

function Field({ label, wide = false, children }: { label: string; wide?: boolean; children: React.ReactNode }) { return <label className={`space-y-2 text-sm ${wide ? "sm:col-span-2" : ""}`}><span>{label}</span>{children}</label>; }
function Summary({ icon: Icon, label, value }: { icon: typeof BriefcaseBusiness; label: string; value: string }) { return <Card className="border-sky-100 bg-white"><CardContent className="flex items-center gap-3 p-5"><span className="flex size-11 items-center justify-center rounded-2xl bg-blue-100 text-blue-700"><Icon /></span><div><p className="font-black">{value}</p><p className="text-xs text-slate-500">{label}</p></div></CardContent></Card>; }
