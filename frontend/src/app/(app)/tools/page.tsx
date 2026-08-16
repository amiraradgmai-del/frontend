"use client";

import type { FormEvent } from "react";
import { useState } from "react";
import { Calculator, CheckCircle2, Copy, FileSignature, Info, RotateCcw, Sparkles } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { formatToman, normalizeDigits, numberToPersianWords } from "@/lib/persian-number";

type Calculation = { result: number; base_amount: number; rate: number; months: number; disclaimer: string };
const calculationHelp: Record<string, string> = {
  vat: "مالیات و عوارض را بر اساس مبلغ پایه و نرخ انتخابی محاسبه می‌کند؛ نرخ را مطابق دوره و نوع فعالیت خود کنترل کنید.",
  percentage: "درصد دلخواه از یک مبلغ را محاسبه می‌کند؛ مناسب برآورد کسورات، ذخیره یا سهم مالیاتی.",
  penalty: "جریمه ساده ماهانه را از حاصل مبلغ × نرخ × تعداد ماه برآورد می‌کند؛ بخشودگی و سقف قانونی در آن لحاظ نمی‌شود.",
};

export default function ToolsPage() {
  const [amount, setAmount] = useState(""); const [rate, setRate] = useState("10"); const [months, setMonths] = useState("1");
  const [calculationType, setCalculationType] = useState("vat"); const [calculation, setCalculation] = useState<Calculation | null>(null);
  const [recipient, setRecipient] = useState(""); const [subject, setSubject] = useState(""); const [taxpayer, setTaxpayer] = useState("");
  const [caseNumber, setCaseNumber] = useState(""); const [facts, setFacts] = useState(""); const [requestText, setRequestText] = useState("");
  const [letterType, setLetterType] = useState("objection"); const [letter, setLetter] = useState(""); const [message, setMessage] = useState(""); const [copied, setCopied] = useState(false);

  async function calculate(event: FormEvent) {
    event.preventDefault(); setMessage(""); setCalculation(null);
    if (!amount || !rate || (calculationType === "penalty" && !months)) { setMessage("مبلغ، نرخ و اطلاعات لازم را کامل وارد کنید."); return; }
    try { setCalculation(await api<Calculation>("api/v1/tools/calculator", { method: "POST", body: JSON.stringify({ calculation_type: calculationType, amount: Number(amount), rate: Number(rate), months: calculationType === "penalty" ? Number(months) : 1 }) })); }
    catch (caught) { setMessage(caught instanceof ApiError ? caught.message : "محاسبه انجام نشد."); }
  }
  async function generate(event: FormEvent) {
    event.preventDefault(); setMessage(""); setLetter("");
    try { const result = await api<{ content: string }>("api/v1/tools/letters", { method: "POST", body: JSON.stringify({ letter_type: letterType, recipient, subject, taxpayer_name: taxpayer, case_number: caseNumber, facts, request_text: requestText }) }); setLetter(result.content); }
    catch (caught) { setMessage(caught instanceof ApiError ? caught.message : "ساخت پیش‌نویس انجام نشد."); }
  }
  function resetCalculator() { setAmount(""); setRate("10"); setMonths("1"); setCalculation(null); setMessage(""); }
  function resetLetter() { setRecipient(""); setSubject(""); setTaxpayer(""); setCaseNumber(""); setFacts(""); setRequestText(""); setLetter(""); setMessage(""); }
  async function copyLetter() { await navigator.clipboard.writeText(letter); setCopied(true); window.setTimeout(() => setCopied(false), 1800); }

  return <div className="space-y-8">
    <header className="relative overflow-hidden rounded-[2rem] bg-gradient-to-l from-cyan-600 via-blue-600 to-indigo-700 p-8 text-white shadow-xl shadow-blue-900/15"><Sparkles className="size-10 text-cyan-100" /><p className="mt-4 text-sm font-bold text-cyan-100">محاسبه و آماده‌سازی مکاتبات</p><h1 className="mt-1 text-3xl font-black">ابزارهای مالیاتی چکاه</h1><p className="mt-3 max-w-3xl text-sm leading-8 text-blue-50">مبلغ‌های مالیاتی را سریع برآورد کنید یا یک پیش‌نویس ساخت‌یافته برای مکاتبه بسازید. هر خروجی همراه با توضیح و هشدار استفاده نمایش داده می‌شود.</p></header>
    {message && <p role="alert" className="rounded-xl border border-red-100 bg-red-50 p-4 text-sm text-red-700">{message}</p>}
    <div className="grid gap-6 xl:grid-cols-2">
      <Card className="border-sky-100 bg-gradient-to-br from-white to-cyan-50/60 shadow-lg shadow-sky-100/40"><CardHeader><div className="flex items-start justify-between gap-3"><div><div className="flex size-12 items-center justify-center rounded-2xl bg-cyan-100 text-cyan-700"><Calculator /></div><CardTitle className="mt-4">ماشین‌حساب مالیاتی</CardTitle></div><Button type="button" variant="ghost" size="sm" onClick={resetCalculator}><RotateCcw /> پاک‌کردن</Button></div><CardDescription>نوع محاسبه را انتخاب کنید؛ نتیجه هم به عدد و هم به حروف نمایش داده می‌شود.</CardDescription></CardHeader>
        <CardContent><form onSubmit={calculate} className="space-y-4">
          <label className="block text-sm font-bold">نوع محاسبه<select value={calculationType} onChange={(event) => { setCalculationType(event.target.value); setCalculation(null); }} className="mt-2 h-11 w-full rounded-lg border bg-white px-3 text-sm"><option value="vat">مالیات و عوارض ارزش افزوده</option><option value="percentage">محاسبه درصد از مبلغ</option><option value="penalty">برآورد جریمه ماهانه</option></select></label>
          <p className="rounded-xl border border-cyan-100 bg-cyan-50 p-3 text-xs leading-6 text-cyan-900"><Info className="ml-1 inline size-4" />{calculationHelp[calculationType]}</p>
          <label className="block text-sm font-bold">مبلغ پایه (تومان)<Input inputMode="numeric" value={formatToman(amount)} onChange={(event) => setAmount(normalizeDigits(event.target.value))} placeholder="مثلاً ۱۰۰,۰۰۰,۰۰۰" className="mt-2 text-left font-bold" dir="ltr" required /></label>
          {amount && <p className="rounded-lg bg-white px-3 py-2 text-xs leading-6 text-slate-600">{numberToPersianWords(Number(amount))} تومان</p>}
          <label className="block text-sm font-bold">نرخ درصد<Input type="number" min="0" max="100" step="0.01" value={rate} onChange={(event) => setRate(event.target.value)} className="mt-2" required /></label>
          <div className="flex flex-wrap gap-2">{[1, 2, 3, 9, 10].map((value) => <button type="button" key={value} onClick={() => setRate(String(value))} className="rounded-full border bg-white px-3 py-1 text-xs font-bold hover:border-blue-400">{value.toLocaleString("fa-IR")}٪</button>)}</div>
          {calculationType === "penalty" && <label className="block text-sm font-bold">تعداد ماه<Input type="number" min="1" max="120" value={months} onChange={(event) => setMonths(event.target.value)} className="mt-2" required /></label>}
          <Button className="w-full">محاسبه نتیجه</Button>
        </form>
        {calculation && <div className="mt-5 rounded-2xl border border-blue-100 bg-white p-5"><p className="text-xs font-bold text-slate-500">نتیجه برآوردی</p><p className="mt-2 text-3xl font-black text-blue-700">{calculation.result.toLocaleString("fa-IR")} تومان</p><p className="mt-2 text-xs leading-6 text-blue-800">{numberToPersianWords(calculation.result)} تومان</p><div className="mt-4 grid grid-cols-2 gap-2 text-xs"><p className="rounded-lg bg-slate-50 p-3">مبلغ پایه<br/><b>{calculation.base_amount.toLocaleString("fa-IR")}</b></p><p className="rounded-lg bg-slate-50 p-3">مبلغ نهایی با نتیجه<br/><b>{(calculation.base_amount + calculation.result).toLocaleString("fa-IR")}</b></p></div></div>}
        <p className="mt-4 text-xs leading-6 text-amber-700">این ابزار برآورد ساده انجام می‌دهد؛ معافیت، بخشودگی، سقف و شرایط اختصاصی پرونده را جداگانه بررسی کنید.</p></CardContent></Card>
      <Card className="border-amber-100 bg-gradient-to-br from-white to-amber-50/60 shadow-lg shadow-amber-100/40"><CardHeader><div className="flex items-start justify-between gap-3"><div><div className="flex size-12 items-center justify-center rounded-2xl bg-amber-100 text-amber-700"><FileSignature /></div><CardTitle className="mt-4">نامه و لایحه‌ساز</CardTitle></div><Button type="button" variant="ghost" size="sm" onClick={resetLetter}><RotateCcw /> پاک‌کردن</Button></div><CardDescription>اطلاعات واقعی پرونده را وارد کنید تا پیش‌نویس منظم و قابل ویرایش ساخته شود.</CardDescription></CardHeader>
        <CardContent><form onSubmit={generate} className="space-y-3"><select aria-label="نوع نامه" value={letterType} onChange={(event) => setLetterType(event.target.value)} className="h-11 w-full rounded-lg border bg-white px-3 text-sm"><option value="objection">لایحه اعتراض مالیاتی</option><option value="extension">درخواست تمدید مهلت</option><option value="clarification">درخواست رفع ابهام و ارائه توضیحات</option></select><div className="grid gap-3 sm:grid-cols-2"><Input value={recipient} onChange={(event) => setRecipient(event.target.value)} placeholder="مخاطب؛ مثال: اداره امور مالیاتی" required /><Input value={subject} onChange={(event) => setSubject(event.target.value)} placeholder="موضوع دقیق نامه" required /><Input value={taxpayer} onChange={(event) => setTaxpayer(event.target.value)} placeholder="نام مؤدی یا شرکت" required /><Input value={caseNumber} onChange={(event) => setCaseNumber(event.target.value)} placeholder="شماره پرونده (اختیاری)" /></div><Textarea value={facts} onChange={(event) => setFacts(event.target.value)} placeholder="شرح ماجرا را به‌ترتیب زمانی بنویسید و نام مستندات را ذکر کنید (حداقل ۱۰ حرف)" className="min-h-28" required /><Textarea value={requestText} onChange={(event) => setRequestText(event.target.value)} placeholder="درخواست نهایی و روشن شما چیست؟" className="min-h-20" required /><Button className="w-full">ساخت پیش‌نویس</Button></form><p className="mt-4 text-xs leading-6 text-amber-700">پیش از ارسال، شماره پرونده، تاریخ ابلاغ، مهلت اعتراض، مواد استنادی و پیوست‌ها را با متخصص کنترل کنید.</p></CardContent></Card>
    </div>
    {letter && <Card className="border-blue-100 bg-white/95"><CardHeader><div className="flex items-center justify-between gap-3"><CardTitle>پیش‌نویس آماده و قابل ویرایش</CardTitle><Button variant="outline" onClick={() => void copyLetter()}>{copied ? <CheckCircle2 /> : <Copy />} {copied ? "کپی شد" : "کپی متن"}</Button></div></CardHeader><CardContent><pre className="whitespace-pre-wrap rounded-2xl bg-slate-50 p-5 font-sans text-sm leading-8">{letter}</pre></CardContent></Card>}
  </div>;
}
