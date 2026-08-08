"use client";

import { FormEvent, useEffect, useState } from "react";
import { Check, FilePlus2, LoaderCircle, Play, RefreshCw, Trash2, Upload, X } from "lucide-react";
import { api } from "@/lib/api";
import type { DocumentItem, DocumentVersion } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

const statusLabels: Record<string, string> = {
  uploaded: "بارگذاری‌شده", queued: "در صف", extracting: "استخراج متن",
  extracted: "استخراج‌شده", chunking: "قطعه‌بندی", embedding: "بردارسازی",
  needs_review: "نیازمند بازبینی", ready: "آماده", failed: "ناموفق",
};

export default function AdminDocumentsPage() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selected, setSelected] = useState<DocumentItem | null>(null);
  const [versions, setVersions] = useState<DocumentVersion[]>([]);
  const [title, setTitle] = useState("");
  const [documentType, setDocumentType] = useState("قانون");
  const [authority, setAuthority] = useState("");
  const [sourceUrl, setSourceUrl] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function loadDocuments() {
    try {
      const result = await api<DocumentItem[]>("api/v1/documents?limit=100");
      setDocuments(result);
      if (selected) setSelected(result.find((item) => item.id === selected.id) ?? null);
      setError("");
    } catch { setError("دریافت اسناد ممکن نیست."); }
  }

  async function loadVersions(document = selected) {
    if (!document) return;
    try { setVersions(await api<DocumentVersion[]>(`api/v1/documents/${document.id}/versions`)); }
    catch { setError("دریافت نسخه‌های سند ممکن نیست."); }
  }

  useEffect(() => {
    api<DocumentItem[]>("api/v1/documents?limit=100")
      .then((result) => { setDocuments(result); setError(""); })
      .catch(() => setError("دریافت اسناد ممکن نیست."));
  }, []);
  useEffect(() => {
    if (!selected) return;
    api<DocumentVersion[]>(`api/v1/documents/${selected.id}/versions`)
      .then(setVersions)
      .catch(() => setError("دریافت نسخه‌های سند ممکن نیست."));
  }, [selected]);

  async function createDocument(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError("");
    try {
      const created = await api<DocumentItem>("api/v1/documents", {
        method: "POST",
        body: JSON.stringify({ title, document_type: documentType, issuing_authority: authority, source_url: sourceUrl || null, topics: [] }),
      });
      setTitle(""); setAuthority(""); setSourceUrl("");
      await loadDocuments(); setSelected(created);
    } catch { setError("ساخت سند انجام نشد؛ اطلاعات فرم را بررسی کنید."); }
    finally { setBusy(false); }
  }

  async function uploadVersion(event: FormEvent) {
    event.preventDefault();
    if (!selected || !file) return;
    setBusy(true); setError("");
    const form = new FormData(); form.set("file", file);
    try {
      await api(`api/v1/documents/${selected.id}/versions`, { method: "POST", body: form });
      setFile(null); await loadVersions(); await loadDocuments();
    } catch { setError("بارگذاری فایل ناموفق بود. فقط PDF، DOCX یا TXT مجاز است."); }
    finally { setBusy(false); }
  }

  async function process(version: DocumentVersion) {
    setBusy(true); setError("");
    try { await api(`api/v1/documents/versions/${version.id}/process`, { method: "POST" }); await loadVersions(); }
    catch { setError("ارسال نسخه برای پردازش انجام نشد."); }
    finally { setBusy(false); }
  }

  async function review(version: DocumentVersion, decision: "approved" | "rejected") {
    setBusy(true); setError("");
    try {
      await api(`api/v1/documents/versions/${version.id}/review`, { method: "POST", body: JSON.stringify({ decision, note: "" }) });
      await loadVersions();
    } catch { setError("ثبت نتیجه بازبینی انجام نشد."); }
    finally { setBusy(false); }
  }

  async function archiveDocument() {
    if (!selected || !window.confirm(`«${selected.title}» از بانک دانش خارج شود؟ سابقه آن برای گزارش‌های مدیریتی حفظ می‌شود.`)) return;
    setBusy(true); setError("");
    try {
      await api(`api/v1/documents/${selected.id}`, { method: "DELETE" });
      setSelected(null); setVersions([]); await loadDocuments();
    } catch { setError("حذف سند از بانک دانش انجام نشد."); }
    finally { setBusy(false); }
  }

  return (
    <div className="space-y-7">
      <header><p className="text-sm font-medium text-primary">پنل مدیریت</p><h1 className="mt-1 text-3xl font-black">مدیریت اسناد</h1><p className="mt-2 text-muted-foreground">منبع را تعریف، فایل را بارگذاری، پردازش و سپس تأیید کنید.</p></header>
      {error && <p className="rounded-xl bg-red-50 p-4 text-sm text-red-700">{error}</p>}
      <div className="grid gap-6 xl:grid-cols-[.8fr_1.2fr]">
        <div className="space-y-6">
          <Card className="border-white/70 bg-white/85"><CardHeader><CardTitle className="flex items-center gap-2"><FilePlus2 className="text-primary" /> سند جدید</CardTitle><CardDescription>ابتدا مشخصات منبع رسمی را ثبت کنید.</CardDescription></CardHeader><CardContent><form onSubmit={createDocument} className="space-y-4"><Input placeholder="عنوان سند" value={title} onChange={(event) => setTitle(event.target.value)} required minLength={3} /><div className="grid gap-3 sm:grid-cols-2"><Input placeholder="نوع سند" value={documentType} onChange={(event) => setDocumentType(event.target.value)} required /><Input placeholder="مرجع صادرکننده" value={authority} onChange={(event) => setAuthority(event.target.value)} required /></div><Input dir="ltr" type="url" placeholder="لینک منبع (اختیاری)" value={sourceUrl} onChange={(event) => setSourceUrl(event.target.value)} /><Button className="w-full" disabled={busy}>ثبت مشخصات سند</Button></form></CardContent></Card>
          <Card className="border-white/70 bg-white/85"><CardHeader><CardTitle>فهرست اسناد</CardTitle></CardHeader><CardContent className="space-y-2">{documents.map((document) => <button key={document.id} onClick={() => setSelected(document)} className={`w-full rounded-xl border p-4 text-right transition ${selected?.id === document.id ? "border-primary bg-primary/5" : "hover:bg-slate-50"}`}><div className="flex items-center justify-between gap-3"><p className="font-semibold">{document.title}</p><Badge variant="secondary">{document.version_count} نسخه</Badge></div><p className="mt-2 text-xs text-muted-foreground">{document.issuing_authority} · {document.document_type}</p></button>)}{documents.length === 0 && <p className="py-8 text-center text-sm text-muted-foreground">هنوز سندی ثبت نشده است.</p>}</CardContent></Card>
        </div>
        <Card className="h-fit border-white/70 bg-white/85"><CardHeader><div className="flex items-start justify-between gap-4"><div><CardTitle>{selected ? selected.title : "نسخه‌های سند"}</CardTitle><CardDescription>{selected ? "نسخه جدید اضافه کنید یا سند را به‌صورت امن از بانک دانش خارج کنید." : "یک سند را از فهرست انتخاب کنید."}</CardDescription></div>{selected && <div className="flex gap-2"><Button variant="outline" size="icon" onClick={() => void loadVersions()}><RefreshCw /></Button><Button variant="destructive" size="icon" disabled={busy} onClick={() => void archiveDocument()} aria-label="حذف سند از بانک دانش"><Trash2 /></Button></div>}</div></CardHeader><CardContent className="space-y-5">{selected && <form onSubmit={uploadVersion} className="flex flex-col gap-3 rounded-xl border border-dashed p-4 sm:flex-row"><Input type="file" accept=".pdf,.docx,.txt" onChange={(event) => setFile(event.target.files?.[0] ?? null)} required /><Button disabled={busy || !file}><Upload /> بارگذاری نسخه</Button></form>}{versions.map((version) => <div key={version.id} className="rounded-xl border p-4"><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="font-semibold">نسخه {version.version_number}: {version.original_filename}</p><p className="mt-1 text-xs text-muted-foreground">{(version.file_size / 1024).toFixed(1)} KB · {version.chunk_count} قطعه</p></div><Badge variant={version.status === "ready" ? "default" : version.status === "failed" ? "destructive" : "secondary"}>{statusLabels[version.status] ?? version.status}</Badge></div>{version.error_code && <p className="mt-3 text-xs text-red-600">خطا: {version.error_code}</p>}<div className="mt-4 flex flex-wrap gap-2">{["uploaded", "failed"].includes(version.status) && <Button size="sm" onClick={() => void process(version)} disabled={busy}><Play /> شروع پردازش</Button>}{version.status === "needs_review" && <><Button size="sm" onClick={() => void review(version, "approved")} disabled={busy}><Check /> تأیید و انتشار</Button><Button size="sm" variant="destructive" onClick={() => void review(version, "rejected")} disabled={busy}><X /> رد نسخه</Button></>}{["queued", "extracting", "extracted", "chunking", "embedding"].includes(version.status) && <span className="flex items-center gap-2 text-xs text-muted-foreground"><LoaderCircle className="size-4 animate-spin" /> پردازش در پس‌زمینه</span>}</div></div>)}{selected && versions.length === 0 && <p className="py-10 text-center text-sm text-muted-foreground">برای این سند هنوز فایلی بارگذاری نشده است.</p>}</CardContent></Card>
      </div>
    </div>
  );
}
