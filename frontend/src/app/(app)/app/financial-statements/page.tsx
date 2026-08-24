"use client";

import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, CheckCircle2, Download, FileSpreadsheet, Loader2, Plus, Search, Trash2, Upload } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

type Organization = { id: string; name: string; national_id: string; entity_type: "individual" | "company"; economic_code: string; registration_number: string; tax_file_number: string; province: string; city: string; postal_code: string; address: string };
type FiscalYear = { id: string; title: string; start_date?: string; end_date?: string; status: "open" | "closed" };
type ImportSummary = { id: string; organization_id: string; fiscal_year_id: string; original_filename: string; money_unit: string; status: string; total_accounts: number; mapped: number; needs_review: number; unmapped: number; ignored: number; mapping_coverage: number; created_at: string };
type Field = { id: string; statement: string; title: string; field_type: string };
type TrialRow = { id: string; general_code: string; general_name: string; subsidiary_code: string; subsidiary_name: string; detail_code: string; detail_name: string; closing_debit: number; closing_credit: number; net_closing_balance: number; target_field_id?: string; confidence: number; status: string };
type Run = { id: string; import_id: string; version: number; status: string; money_unit: string; finalized_at?: string };
type Value = { field_id: string; statement: string; title: string; calculated_value: number; adjustment_value: number; final_value: number; status: string; sources: { row_id: string; code: string; name: string; amount: number }[] };
type Validation = { code: string; status: string; difference: number; tolerance: number; message: string };

const statusLabel: Record<string, string> = { uploaded: "بارگذاری‌شده", parsing: "در حال پردازش", mapping_required: "نیازمند نگاشت", ready_to_calculate: "آماده محاسبه", calculated: "محاسبه‌شده", validation_failed: "کنترل ناموفق", failed: "پردازش ناموفق", mapped: "نگاشت‌شده", needs_review: "نیازمند بررسی", unmapped: "بدون نگاشت", ignored: "نادیده گرفته‌شده", finalized: "نهایی‌شده" };
const statementLabel: Record<string, string> = { BS: "صورت وضعیت مالی", PL: "صورت سود و زیان", CI: "سود و زیان جامع", EQ: "تغییرات حقوق مالکانه", CF: "جریان‌های نقدی" };
const moneyLabel: Record<string, string> = { rial: "ریال", toman: "تومان" };
const provinces = ["آذربایجان شرقی", "آذربایجان غربی", "اردبیل", "اصفهان", "البرز", "ایلام", "بوشهر", "تهران", "چهارمحال و بختیاری", "خراسان جنوبی", "خراسان رضوی", "خراسان شمالی", "خوزستان", "زنجان", "سمنان", "سیستان و بلوچستان", "فارس", "قزوین", "قم", "کردستان", "کرمان", "کرمانشاه", "کهگیلویه و بویراحمد", "گلستان", "گیلان", "لرستان", "مازندران", "مرکزی", "هرمزگان", "همدان", "یزد"];
const number = (value: number | string) => Number(value || 0).toLocaleString("fa-IR");

export default function FinancialStatementsPage() {
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [years, setYears] = useState<FiscalYear[]>([]);
  const [imports, setImports] = useState<ImportSummary[]>([]);
  const [fields, setFields] = useState<Field[]>([]);
  const [rows, setRows] = useState<TrialRow[]>([]);
  const [organizationId, setOrganizationId] = useState("");
  const [yearId, setYearId] = useState("");
  const [selectedImport, setSelectedImport] = useState<ImportSummary | null>(null);
  const [run, setRun] = useState<Run | null>(null);
  const [values, setValues] = useState<Value[]>([]);
  const [validations, setValidations] = useState<Validation[]>([]);
  const [activeStatement, setActiveStatement] = useState("BS");
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [moneyUnit, setMoneyUnit] = useState("rial");
  const [busy, setBusy] = useState("");
  const [message, setMessage] = useState("");
  const [showOrganizationForm, setShowOrganizationForm] = useState(false);
  const [showYearForm, setShowYearForm] = useState(false);
  const [organizationForm, setOrganizationForm] = useState({ name: "", entity_type: "company", national_id: "", economic_code: "", registration_number: "", tax_file_number: "", province: "", city: "", postal_code: "", address: "" });
  const [yearForm, setYearForm] = useState({ title: "", start_date: "", end_date: "", status: "open" });

  const loadBase = async () => {
    const [orgs, history, availableFields] = await Promise.all([
      api<Organization[]>("api/v1/financial-statements/organizations"),
      api<ImportSummary[]>("api/v1/financial-statements/imports"),
      api<Field[]>("api/v1/financial-statements/fields"),
    ]);
    setOrganizations(orgs); setImports(history); setFields(availableFields);
    if (!organizationId && orgs[0]) setOrganizationId(orgs[0].id);
  };

  useEffect(() => {
    void Promise.all([
      api<Organization[]>("api/v1/financial-statements/organizations"),
      api<ImportSummary[]>("api/v1/financial-statements/imports"),
      api<Field[]>("api/v1/financial-statements/fields"),
    ]).then(([orgs, history, availableFields]) => {
      setOrganizations(orgs); setImports(history); setFields(availableFields); setOrganizationId((current) => current || orgs[0]?.id || "");
    }).catch(showError);
  }, []);
  useEffect(() => {
    if (!organizationId) return;
    void api<FiscalYear[]>(`api/v1/financial-statements/fiscal-years?organization_id=${organizationId}`).then((data) => { setYears(data); setYearId(data[0]?.id ?? ""); }).catch(showError);
  }, [organizationId]);

  function showError(error: unknown) { setMessage(error instanceof ApiError ? error.message : "عملیات با خطا روبه‌رو شد."); }
  async function createOrganization() {
    if (organizationForm.name.trim().length < 2) return setMessage("نام شخص یا شرکت را کامل وارد کنید.");
    setBusy("organization");
    try { const item = await api<Organization>("api/v1/financial-statements/organizations", { method: "POST", body: JSON.stringify(organizationForm) }); await loadBase(); setOrganizationId(item.id); setShowOrganizationForm(false); setOrganizationForm({ name: "", entity_type: "company", national_id: "", economic_code: "", registration_number: "", tax_file_number: "", province: "", city: "", postal_code: "", address: "" }); setMessage("شخص یا شرکت با موفقیت ثبت شد."); } catch (error) { showError(error); } finally { setBusy(""); }
  }
  async function createYear() {
    if (!organizationId) return setMessage("ابتدا شرکت را انتخاب کنید.");
    if (yearForm.title.trim().length < 2) return setMessage("عنوان سال مالی را وارد کنید.");
    if (yearForm.start_date && yearForm.end_date && yearForm.end_date < yearForm.start_date) return setMessage("تاریخ پایان نمی‌تواند قبل از تاریخ شروع باشد.");
    setBusy("year");
    try { const item = await api<FiscalYear>("api/v1/financial-statements/fiscal-years", { method: "POST", body: JSON.stringify({ organization_id: organizationId, ...yearForm, start_date: yearForm.start_date || null, end_date: yearForm.end_date || null }) }); setYears((old) => [item, ...old]); setYearId(item.id); setShowYearForm(false); setYearForm({ title: "", start_date: "", end_date: "", status: "open" }); setMessage("سال مالی با موفقیت ثبت شد."); } catch (error) { showError(error); } finally { setBusy(""); }
  }
  async function upload() {
    if (!file || !organizationId || !yearId) return setMessage("شرکت، سال مالی و فایل تراز را مشخص کنید.");
    const form = new FormData(); form.append("organization_id", organizationId); form.append("fiscal_year_id", yearId); form.append("money_unit", moneyUnit); form.append("file", file); setBusy("upload");
    try { const item = await api<ImportSummary>("api/v1/financial-statements/imports", { method: "POST", body: form }); setSelectedImport(item); setImports((old) => [item, ...old]); setMessage("فایل امن بارگذاری شد؛ اکنون پردازش را شروع کنید."); } catch (error) { showError(error); } finally { setBusy(""); }
  }
  async function openImport(item: ImportSummary) {
    setSelectedImport(item); setRun(null); setValues([]); setValidations([]); setBusy("rows");
    try { setRows(await api<TrialRow[]>(`api/v1/financial-statements/imports/${item.id}/rows?limit=200`)); } catch (error) { showError(error); } finally { setBusy(""); }
  }
  async function parse() {
    if (!selectedImport) return; setBusy("parse");
    try { const item = await api<ImportSummary>(`api/v1/financial-statements/imports/${selectedImport.id}/parse`, { method: "POST" }); setSelectedImport(item); await openImport(item); await loadBase(); setMessage("تراز خوانده شد؛ حساب‌های نامشخص را بررسی کنید."); } catch (error) { showError(error); } finally { setBusy(""); }
  }
  async function deleteImport(item: ImportSummary) {
    if (!window.confirm(`سابقه «${item.original_filename}» و تمام نتایج آن حذف شود؟`)) return;
    setBusy(`delete-${item.id}`);
    try {
      await api<void>(`api/v1/financial-statements/imports/${item.id}`, { method: "DELETE" });
      if (selectedImport?.id === item.id) { setSelectedImport(null); setRows([]); setRun(null); setValues([]); setValidations([]); }
      setImports((current) => current.filter((entry) => entry.id !== item.id));
      setMessage("سابقه پردازش و فایل مربوط به آن حذف شد.");
    } catch (error) { showError(error); } finally { setBusy(""); }
  }
  async function mapRow(row: TrialRow, target: string) {
    if (!selectedImport) return;
    const ignored = target === "__ignore";
    try {
      const item = await api<ImportSummary>(`api/v1/financial-statements/imports/${selectedImport.id}/mapping`, { method: "POST", body: JSON.stringify({ decisions: [{ import_row_id: row.id, target_field_id: ignored ? null : target, amount_source: "net_closing", sign_multiplier: 1, status: ignored ? "ignored" : "mapped", ignore_reason: ignored ? "به تشخیص کاربر فاقد اثر در صورت‌های مالی" : null, save_rule: !ignored, global_rule: false }] }) });
      setSelectedImport(item); setRows((old) => old.map((x) => x.id === row.id ? { ...x, target_field_id: ignored ? undefined : target, status: ignored ? "ignored" : "mapped", confidence: 100 } : x));
    } catch (error) { showError(error); }
  }
  async function calculate() {
    if (!selectedImport) return; setBusy("calculate");
    try { const item = await api<Run>(`api/v1/financial-statements/imports/${selectedImport.id}/calculate`, { method: "POST", body: JSON.stringify({ tolerance: 0 }) }); setRun(item); const [calculated, checks] = await Promise.all([api<Value[]>(`api/v1/financial-statements/runs/${item.id}/values`), api<Validation[]>(`api/v1/financial-statements/runs/${item.id}/validations`)]); setValues(calculated); setValidations(checks); setMessage("صورت‌های مالی محاسبه شد."); } catch (error) { showError(error); } finally { setBusy(""); }
  }
  async function adjust(value: Value) {
    if (!run) return; const raw = window.prompt(`مبلغ تعدیل «${value.title}» را وارد کنید:`); if (!raw) return; const reason = window.prompt("دلیل تعدیل را بنویسید:"); if (!reason) return;
    try { const result = await api<{ run_id: string }>(`api/v1/financial-statements/runs/${run.id}/adjustments`, { method: "POST", body: JSON.stringify({ field_id: value.field_id, amount: raw.replaceAll(",", ""), reason }) }); if (result.run_id !== run.id) setRun({ ...run, id: result.run_id, version: run.version + 1, finalized_at: undefined }); setValues(await api<Value[]>(`api/v1/financial-statements/runs/${result.run_id}/values`)); setMessage("تعدیل با دلیل و سابقه ثبت شد."); } catch (error) { showError(error); }
  }
  const filteredRows = useMemo(() => rows.filter((row) => (!status || row.status === status) && (!search || `${row.general_code} ${row.general_name} ${row.subsidiary_code} ${row.subsidiary_name} ${row.detail_code} ${row.detail_name}`.includes(search))), [rows, search, status]);
  const visibleValues = values.filter((item) => item.statement === activeStatement);

  return <div className="space-y-6" dir="rtl">
    <header className="overflow-hidden rounded-[2rem] bg-gradient-to-l from-slate-950 via-blue-950 to-blue-700 p-7 text-white shadow-xl">
      <FileSpreadsheet className="size-11 text-cyan-200" /><p className="mt-4 text-sm font-bold text-cyan-200">از تراز آزمایشی تا گزارش قابل ردیابی</p>
      <h1 className="mt-1 text-3xl font-black">تهیه خودکار صورت‌های مالی</h1><p className="mt-3 max-w-3xl text-sm leading-8 text-blue-50">فایل Excel یا PDF تراز آزمایشی را بارگذاری کنید؛ سامانه حساب‌ها را بدون ساختن داده نگاشت می‌کند، موارد نامشخص را برای تصمیم شما نگه می‌دارد و خروجی Excel و PDF می‌سازد.</p>
    </header>
    {message && <div className="rounded-2xl border border-blue-200 bg-blue-50 px-5 py-3 text-sm text-blue-900">{message}<button className="mr-4 text-xs underline" onClick={() => setMessage("")}>بستن</button></div>}
    <div className="grid gap-6 xl:grid-cols-[1fr_320px]">
      <div className="space-y-6">
        <Card><CardHeader><CardTitle>۱. شرکت، سال مالی و فایل تراز</CardTitle></CardHeader><CardContent className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <div><label className="mb-1 block text-xs font-bold text-slate-600">شخص یا شرکت</label><div className="flex gap-2"><select aria-label="انتخاب شخص یا شرکت" className="h-10 min-w-0 flex-1 rounded-lg border bg-white px-3" value={organizationId} onChange={(e) => setOrganizationId(e.target.value)}><option value="" disabled>انتخاب شخص یا شرکت</option>{organizations.map((x) => <option key={x.id} value={x.id}>{x.name}{x.national_id ? ` — ${x.national_id}` : ""}</option>)}</select><Button title="افزودن شخص یا شرکت" variant="outline" size="icon" onClick={() => setShowOrganizationForm((value) => !value)}><Plus /></Button></div></div>
          <div><label className="mb-1 block text-xs font-bold text-slate-600">سال مالی</label><div className="flex gap-2"><select aria-label="انتخاب سال مالی" disabled={!organizationId} className="h-10 min-w-0 flex-1 rounded-lg border bg-white px-3 disabled:bg-slate-100" value={yearId} onChange={(e) => setYearId(e.target.value)}><option value="" disabled>{organizationId ? "انتخاب سال مالی" : "ابتدا شرکت را انتخاب کنید"}</option>{years.map((x) => <option key={x.id} value={x.id}>{x.title} — {x.status === "open" ? "باز" : "بسته"}</option>)}</select><Button title="افزودن سال مالی" disabled={!organizationId} variant="outline" size="icon" onClick={() => setShowYearForm((value) => !value)}><Plus /></Button></div></div>
          <div><label className="mb-1 block text-xs font-bold text-slate-600">واحد مبالغ داخل فایل</label><select aria-label="واحد مبالغ داخل فایل" className="h-10 w-full rounded-lg border bg-white px-3" value={moneyUnit} onChange={(e) => setMoneyUnit(e.target.value)}>{Object.entries(moneyLabel).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></div>
          <Input type="file" accept=".xlsx,.xls,.pdf" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
          <Button className="md:col-span-2 xl:col-span-4" onClick={upload} disabled={!!busy}><Upload /> {busy === "upload" ? "در حال بارگذاری..." : "بارگذاری امن فایل"}</Button>
          {showOrganizationForm && <div className="grid gap-3 rounded-2xl border border-blue-200 bg-blue-50 p-4 md:col-span-2 xl:col-span-4 md:grid-cols-2 xl:grid-cols-4"><h3 className="font-black text-blue-950 md:col-span-2 xl:col-span-4">افزودن شخص یا شرکت</h3><select className="h-10 rounded-lg border bg-white px-3" value={organizationForm.entity_type} onChange={(e) => setOrganizationForm({ ...organizationForm, entity_type: e.target.value })}><option value="company">شخص حقوقی / شرکت</option><option value="individual">شخص حقیقی</option></select><Input placeholder="نام کامل یا نام شرکت *" value={organizationForm.name} onChange={(e) => setOrganizationForm({ ...organizationForm, name: e.target.value })} /><Input inputMode="numeric" placeholder="شناسه ملی" value={organizationForm.national_id} onChange={(e) => setOrganizationForm({ ...organizationForm, national_id: e.target.value })} /><Input inputMode="numeric" placeholder="کد اقتصادی" value={organizationForm.economic_code} onChange={(e) => setOrganizationForm({ ...organizationForm, economic_code: e.target.value })} /><Input inputMode="numeric" placeholder="شماره ثبت" value={organizationForm.registration_number} onChange={(e) => setOrganizationForm({ ...organizationForm, registration_number: e.target.value })} /><Input inputMode="numeric" placeholder="شماره پرونده مالیاتی" value={organizationForm.tax_file_number} onChange={(e) => setOrganizationForm({ ...organizationForm, tax_file_number: e.target.value })} /><select className="h-10 rounded-lg border bg-white px-3" value={organizationForm.province} onChange={(e) => setOrganizationForm({ ...organizationForm, province: e.target.value })}><option value="">انتخاب استان</option>{provinces.map((province) => <option key={province}>{province}</option>)}</select><Input placeholder="شهر" value={organizationForm.city} onChange={(e) => setOrganizationForm({ ...organizationForm, city: e.target.value })} /><Input inputMode="numeric" placeholder="کد پستی ۱۰ رقمی" value={organizationForm.postal_code} onChange={(e) => setOrganizationForm({ ...organizationForm, postal_code: e.target.value })} /><Input className="xl:col-span-3" placeholder="نشانی" value={organizationForm.address} onChange={(e) => setOrganizationForm({ ...organizationForm, address: e.target.value })} /><div className="flex gap-2 md:col-span-2 xl:col-span-4"><Button onClick={createOrganization} disabled={busy === "organization"}>{busy === "organization" ? "در حال ثبت..." : "ثبت و انتخاب"}</Button><Button variant="outline" onClick={() => setShowOrganizationForm(false)}>انصراف</Button></div></div>}
          {showYearForm && <div className="grid gap-3 rounded-2xl border border-cyan-200 bg-cyan-50 p-4 md:col-span-2 xl:col-span-4 md:grid-cols-2 xl:grid-cols-4"><h3 className="font-black text-blue-950 md:col-span-2 xl:col-span-4">افزودن سال مالی</h3><Input placeholder="عنوان، مثلاً سال مالی ۱۴۰۵ *" value={yearForm.title} onChange={(e) => setYearForm({ ...yearForm, title: e.target.value })} /><label className="text-xs font-bold text-slate-600">تاریخ شروع<Input className="mt-1" type="date" value={yearForm.start_date} onChange={(e) => setYearForm({ ...yearForm, start_date: e.target.value })} /></label><label className="text-xs font-bold text-slate-600">تاریخ پایان<Input className="mt-1" type="date" value={yearForm.end_date} onChange={(e) => setYearForm({ ...yearForm, end_date: e.target.value })} /></label><select className="h-10 self-end rounded-lg border bg-white px-3" value={yearForm.status} onChange={(e) => setYearForm({ ...yearForm, status: e.target.value })}><option value="open">باز و قابل پردازش</option><option value="closed">بسته‌شده</option></select><div className="flex gap-2 md:col-span-2 xl:col-span-4"><Button onClick={createYear} disabled={busy === "year"}>{busy === "year" ? "در حال ثبت..." : "ثبت و انتخاب"}</Button><Button variant="outline" onClick={() => setShowYearForm(false)}>انصراف</Button></div></div>}
        </CardContent></Card>
        {selectedImport && <Card><CardHeader><CardTitle>۲. کنترل و نگاشت حساب‌ها</CardTitle></CardHeader><CardContent className="space-y-4">
          <div className="flex flex-wrap items-center gap-3 rounded-xl bg-slate-50 p-4 text-sm"><b>{selectedImport.original_filename}</b><span>{statusLabel[selectedImport.status] ?? selectedImport.status}</span><span>پوشش نگاشت: {number(selectedImport.mapping_coverage)}٪</span><span>کل حساب‌ها: {number(selectedImport.total_accounts)}</span><Button size="sm" onClick={parse} disabled={busy === "parse" || selectedImport.status === "parsing"}>{busy === "parse" && <Loader2 className="animate-spin" />} {selectedImport.status === "uploaded" || selectedImport.status === "failed" ? "پردازش فایل" : "پردازش مجدد"}</Button></div>
          <div className="grid gap-3 sm:grid-cols-[1fr_220px]"><label className="relative"><Search className="absolute right-3 top-2.5 size-5 text-slate-400" /><Input className="pr-10" placeholder="جست‌وجوی کد یا نام حساب" value={search} onChange={(e) => setSearch(e.target.value)} /></label><select className="h-10 rounded-lg border bg-white px-3" value={status} onChange={(e) => setStatus(e.target.value)}><option value="">همه وضعیت‌ها</option><option value="unmapped">بدون نگاشت</option><option value="needs_review">نیازمند بررسی</option><option value="mapped">نگاشت‌شده</option><option value="ignored">نادیده گرفته‌شده</option></select></div>
          <div className="overflow-x-auto rounded-xl border"><table className="w-full min-w-[900px] text-sm"><thead className="bg-slate-50 text-slate-600"><tr><th className="p-3 text-right">حساب</th><th className="p-3">بدهکار پایان</th><th className="p-3">بستانکار پایان</th><th className="p-3">وضعیت/اطمینان</th><th className="p-3 text-right">سرفصل صورت مالی</th></tr></thead><tbody>{filteredRows.map((row) => <tr key={row.id} className="border-t"><td className="p-3"><b dir="ltr">{row.detail_code || row.subsidiary_code || row.general_code}</b><div className="mt-1 text-slate-500">{row.detail_name || row.subsidiary_name || row.general_name}</div></td><td className="p-3 text-center">{number(row.closing_debit)}</td><td className="p-3 text-center">{number(row.closing_credit)}</td><td className="p-3 text-center"><span className={row.status === "mapped" ? "text-emerald-700" : "text-amber-700"}>{statusLabel[row.status] ?? row.status} ({number(row.confidence)}٪)</span></td><td className="p-3"><select className="h-10 w-full rounded-lg border bg-white px-2" value={row.status === "ignored" ? "__ignore" : row.target_field_id ?? ""} onChange={(e) => void mapRow(row, e.target.value)}><option value="">انتخاب سرفصل...</option>{fields.filter((x) => x.field_type === "mapped").map((x) => <option key={x.id} value={x.id}>{statementLabel[x.statement]} — {x.title}</option>)}<option value="__ignore">فاقد اثر / نادیده گرفته شود</option></select></td></tr>)}</tbody></table></div>
          <Button onClick={calculate} disabled={!!busy || selectedImport.unmapped + selectedImport.needs_review > 0}>{busy === "calculate" && <Loader2 className="animate-spin" />} محاسبه صورت‌های مالی</Button>{selectedImport.unmapped + selectedImport.needs_review > 0 && <p className="text-xs text-amber-700">برای محاسبه، ابتدا {number(selectedImport.unmapped + selectedImport.needs_review)} حساب نامشخص را نگاشت یا مستنداً نادیده بگیرید.</p>}
        </CardContent></Card>}
        {run && <Card><CardHeader><CardTitle>۳. پیش‌نمایش، کنترل و خروجی — نسخه {number(run.version)}</CardTitle></CardHeader><CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2">{Object.entries(statementLabel).map(([key, label]) => <Button key={key} size="sm" variant={activeStatement === key ? "default" : "outline"} onClick={() => setActiveStatement(key)}>{label}</Button>)}</div>
          <div className="overflow-hidden rounded-xl border">{visibleValues.map((value) => <details key={value.field_id} className="border-b last:border-0"><summary className="flex cursor-pointer items-center justify-between gap-4 p-4"><span>{value.title}{value.status === "manual_input_required" && <small className="mr-2 text-amber-700">نیازمند ورود دستی</small>}</span><b dir="ltr">{number(value.final_value)} {moneyLabel[run.money_unit]}</b></summary><div className="bg-slate-50 p-4 text-xs"><Button size="sm" variant="outline" onClick={() => void adjust(value)}>ثبت تعدیل با دلیل</Button><p className="my-3 text-slate-500">مبلغ محاسباتی: {number(value.calculated_value)} | تعدیلات: {number(value.adjustment_value)}</p>{value.sources.length ? value.sources.map((source) => <div key={source.row_id} className="flex justify-between border-t py-2"><span>{source.code} — {source.name}</span><b>{number(source.amount)}</b></div>) : <p>ردیف منبعی برای این سرفصل وجود ندارد.</p>}</div></details>)}</div>
          <div className="space-y-2">{validations.map((check) => <div key={check.code} className={`flex items-center gap-2 rounded-xl p-3 text-sm ${check.status === "passed" ? "bg-emerald-50 text-emerald-800" : "bg-rose-50 text-rose-800"}`}>{check.status === "passed" ? <CheckCircle2 /> : <AlertTriangle />}<span>{check.message} اختلاف: {number(check.difference)}</span></div>)}</div>
          <div className="flex flex-wrap gap-2"><a href={`/api/backend/api/v1/financial-statements/runs/${run.id}/export/excel`}><Button variant="outline"><Download /> خروجی Excel</Button></a><a href={`/api/backend/api/v1/financial-statements/runs/${run.id}/export/pdf`}><Button variant="outline"><Download /> خروجی PDF</Button></a></div>
        </CardContent></Card>}
      </div>
      <aside><Card className="xl:sticky xl:top-5"><CardHeader><CardTitle>سوابق پردازش</CardTitle></CardHeader><CardContent className="space-y-3">{imports.length === 0 && <p className="text-sm text-slate-500">هنوز فایلی بارگذاری نشده است.</p>}{imports.map((item) => <div key={item.id} className={`flex items-center gap-2 rounded-xl border p-2 transition hover:border-blue-300 ${selectedImport?.id === item.id ? "border-blue-500 bg-blue-50" : "bg-white"}`}><button onClick={() => void openImport(item)} className="min-w-0 flex-1 p-1 text-right"><b className="block truncate text-sm">{item.original_filename}</b><span className="mt-1 block text-xs text-slate-500">{statusLabel[item.status] ?? item.status} · {number(item.mapping_coverage)}٪ نگاشت</span></button><Button aria-label="حذف سابقه پردازش" title="حذف سابقه" size="icon" variant="outline" className="shrink-0 text-rose-600 hover:bg-rose-50 hover:text-rose-700" disabled={busy === `delete-${item.id}`} onClick={() => void deleteImport(item)}>{busy === `delete-${item.id}` ? <Loader2 className="animate-spin" /> : <Trash2 />}</Button></div>)}</CardContent></Card></aside>
    </div>
  </div>;
}
