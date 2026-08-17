"use client";

import { FormEvent, useEffect, useState } from "react";
import { BadgeCheck, FileCheck2, Send, ShieldCheck } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { UserDocumentUploader, type UserDocument } from "@/components/user-document-uploader";

type DocumentItem = Pick<UserDocument, "id" | "title" | "status" | "document_type" | "purpose">;
type VerificationItem = {
  id: string;
  consultant_type: "independent" | "company";
  professional_title: string;
  status: "pending" | "approved" | "rejected" | "correction_required";
  admin_note: string;
  created_at: string;
};

const statusLabels = {
  pending: "در انتظار بررسی",
  approved: "تأییدشده",
  rejected: "ردشده",
  correction_required: "نیازمند اصلاح",
};

export default function ConsultantVerificationPage() {
  const [items, setItems] = useState<VerificationItem[]>([]);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selectedDocuments, setSelectedDocuments] = useState<string[]>([]);
  const [consultantType, setConsultantType] = useState<"independent" | "company">("independent");
  const [professionalTitle, setProfessionalTitle] = useState("");
  const [nationalId, setNationalId] = useState("");
  const [licenseNumber, setLicenseNumber] = useState("");
  const [specialties, setSpecialties] = useState("");
  const [experience, setExperience] = useState("");
  const [qualifications, setQualifications] = useState("");
  const [note, setNote] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  const load = () => Promise.all([
    api<VerificationItem[]>("api/v1/consultations/verification/mine"),
    api<DocumentItem[]>("api/v1/portal/documents"),
  ]).then(([requests, uploadedDocuments]) => {
    setItems(requests);
    setDocuments(uploadedDocuments);
  });

  useEffect(() => { void load().catch(() => setMessage("دریافت اطلاعات احراز صلاحیت ممکن نیست.")); }, []);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    try {
      await api("api/v1/consultations/verification", {
        method: "POST",
        body: JSON.stringify({
          consultant_type: consultantType,
          professional_title: professionalTitle,
          national_id: nationalId,
          license_number: licenseNumber,
          specialties: specialties.split("،").map((item) => item.trim()).filter(Boolean),
          years_experience: Number(experience),
          qualifications,
          document_ids: selectedDocuments,
          applicant_note: note,
        }),
      });
      setMessage("درخواست با موفقیت ثبت شد و در صف بررسی مدیر قرار گرفت.");
      await load();
    } catch (error) {
      setMessage(error instanceof ApiError ? error.message : "ثبت درخواست انجام نشد.");
    } finally {
      setBusy(false);
    }
  }

  const hasActiveRequest = items.some((item) => item.status === "pending" || item.status === "approved");
  const requiredDocuments = consultantType === "independent" ? [["national_card","کارت ملی"],["education_certificate","مدرک تحصیلی مرتبط"],["resume","رزومه حرفه‌ای"]] : [["company_registration","آگهی ثبت یا آخرین تغییرات شرکت"],["company_national_id","شناسه ملی شرکت"],["representative_card","کارت ملی نماینده شرکت"]];
  const selectedTypes = new Set(documents.filter(item => selectedDocuments.includes(item.id) && item.purpose === "consultant_verification").map(item => item.document_type));
  const missingDocuments = requiredDocuments.filter(([type]) => !selectedTypes.has(type));
  return <div className="space-y-7">
    <header className="rounded-[2rem] bg-gradient-to-l from-emerald-600 via-teal-600 to-cyan-600 p-8 text-white shadow-xl shadow-teal-900/15">
      <p className="text-sm text-emerald-50">همکاری حرفه‌ای با چکاه</p>
      <h1 className="mt-2 text-3xl font-black">احراز صلاحیت مشاور</h1>
      <p className="mt-3 max-w-2xl text-sm leading-7 text-emerald-50">اطلاعات حرفه‌ای و مدارک خود را ثبت کنید؛ نتیجه بررسی و توضیحات اصلاحی همین‌جا نمایش داده می‌شود.</p>
    </header>

    {items.length > 0 && <section className="space-y-3">{items.map((item) => <Card key={item.id} className="border-emerald-100 bg-white"><CardContent className="flex flex-wrap items-center justify-between gap-4 p-5"><div><p className="font-black">{item.professional_title}</p><p className="mt-1 text-xs text-slate-500">{item.consultant_type === "independent" ? "مشاور مستقل" : "مشاور شرکت"} · {new Date(item.created_at).toLocaleDateString("fa-IR")}</p>{item.admin_note && <p className="mt-3 rounded-xl bg-amber-50 p-3 text-sm text-amber-900">{item.admin_note}</p>}</div><Badge variant={item.status === "approved" ? "default" : item.status === "rejected" ? "destructive" : "secondary"}>{statusLabels[item.status]}</Badge></CardContent></Card>)}</section>}

    <Card className="border-sky-100 bg-white">
      <CardHeader><CardTitle className="flex items-center gap-2"><ShieldCheck className="text-teal-600" /> درخواست جدید</CardTitle><CardDescription>{hasActiveRequest ? "درخواست فعال شما ابتدا باید تعیین تکلیف شود." : "اطلاعات باید دقیق و قابل استناد باشد."}</CardDescription></CardHeader>
      <CardContent><form onSubmit={submit} className="grid gap-4 sm:grid-cols-2">
        <label className="space-y-2 text-sm"><span>نوع همکاری</span><select value={consultantType} onChange={(event) => setConsultantType(event.target.value as "independent" | "company")} className="h-10 w-full rounded-lg border bg-white px-3"><option value="independent">مشاور مستقل</option><option value="company">مشاور شرکت</option></select></label>
        <label className="space-y-2 text-sm"><span>عنوان حرفه‌ای</span><Input value={professionalTitle} onChange={(event) => setProfessionalTitle(event.target.value)} placeholder="مثلاً مشاور ارشد مالیاتی" required minLength={3} /></label>
        <label className="space-y-2 text-sm"><span>کد ملی</span><Input dir="ltr" inputMode="numeric" value={nationalId} onChange={(event) => setNationalId(event.target.value.replace(/\D/g, "").slice(0, 12))} placeholder="اختیاری" /></label>
        <label className="space-y-2 text-sm"><span>شماره مجوز یا عضویت</span><Input value={licenseNumber} onChange={(event) => setLicenseNumber(event.target.value)} placeholder="در صورت وجود" /></label>
        <label className="space-y-2 text-sm"><span>تخصص‌ها</span><Input value={specialties} onChange={(event) => setSpecialties(event.target.value)} placeholder="مالیات مستقیم، ارزش افزوده" required /></label>
        <label className="space-y-2 text-sm"><span>سابقه فعالیت</span><Input type="number" min="0" max="70" value={experience} onChange={(event) => setExperience(event.target.value)} placeholder="تعداد سال" required /></label>
        <label className="space-y-2 text-sm sm:col-span-2"><span>سوابق و صلاحیت‌های حرفه‌ای</span><Textarea value={qualifications} onChange={(event) => setQualifications(event.target.value)} className="min-h-28" placeholder="تحصیلات، گواهی‌ها و تجربه‌های مرتبط را توضیح دهید." required minLength={10} /></label>
        <div className="space-y-4 rounded-2xl border border-sky-200 bg-sky-50/40 p-4 sm:col-span-2"><div><p className="flex items-center gap-2 text-sm font-black"><FileCheck2 className="size-4 text-blue-600" /> مدارک لازم برای {consultantType === "independent" ? "مشاور مستقل" : "مشاور شرکت"}</p><div className="mt-3 grid gap-2 sm:grid-cols-3">{requiredDocuments.map(([type,label])=><div key={type} className={`rounded-xl border p-3 text-xs font-bold ${selectedTypes.has(type)?"border-emerald-200 bg-emerald-50 text-emerald-800":"border-amber-200 bg-amber-50 text-amber-900"}`}>{selectedTypes.has(type)?"✓ ":"الزامی: "}{label}</div>)}</div><p className="mt-2 text-xs leading-6 text-slate-600">مجوز حرفه‌ای و گواهی‌های تکمیلی اختیاری‌اند، اما به ارزیابی دقیق‌تر و نمایش بهتر پروفایل کمک می‌کنند.</p></div><div className="rounded-xl border bg-white p-4"><p className="mb-3 text-sm font-black">بارگذاری مدرک از همین صفحه</p><UserDocumentUploader presetPurpose="consultant_verification" presetReviewer="consultant_management" compact onUploaded={(document)=>{setDocuments(current=>[document,...current]);setSelectedDocuments(current=>[...new Set([...current,document.id])])}}/></div>{documents.length>0&&<div><p className="mb-2 text-sm font-bold">مدارک انتخاب‌شده برای این درخواست</p><div className="grid gap-2 sm:grid-cols-2">{documents.filter(document=>document.purpose==="consultant_verification").map((document)=><label key={document.id} className="flex items-center gap-2 rounded-xl bg-white p-3 text-sm"><input type="checkbox" checked={selectedDocuments.includes(document.id)} onChange={(event)=>setSelectedDocuments(current=>event.target.checked?[...new Set([...current,document.id])]:current.filter(id=>id!==document.id))}/>{document.title}</label>)}</div></div>}</div>
        <label className="space-y-2 text-sm sm:col-span-2"><span>توضیحات تکمیلی</span><Textarea value={note} onChange={(event) => setNote(event.target.value)} placeholder="توضیح اختیاری برای مدیر بررسی‌کننده" /></label>
        {missingDocuments.length>0&&<p className="rounded-xl bg-amber-50 p-3 text-sm text-amber-900 sm:col-span-2">برای ارسال درخواست، این مدارک را بارگذاری و انتخاب کنید: {missingDocuments.map(([,label])=>label).join("، ")}</p>}
        <Button className="bg-teal-600 hover:bg-teal-700 sm:col-span-2" disabled={busy || hasActiveRequest || missingDocuments.length>0}><Send /> ثبت درخواست احراز صلاحیت</Button>
      </form>{message && <p className="mt-4 rounded-xl bg-sky-50 p-3 text-sm text-sky-800">{message}</p>}</CardContent>
    </Card>
    <div className="rounded-2xl border border-emerald-100 bg-emerald-50 p-4 text-sm leading-7 text-emerald-900"><BadgeCheck className="ml-2 inline size-5" />تأیید صلاحیت به معنی فعال‌شدن پنل تخصصی است و دسترسی‌های آن فقط به پرونده‌های مرتبط محدود می‌شود.</div>
  </div>;
}
