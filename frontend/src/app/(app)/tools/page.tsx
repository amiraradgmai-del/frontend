"use client";

import type { FormEvent } from "react";
import { useState } from "react";
import { Calculator, Copy, FileSignature, Sparkles } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { formatToman, normalizeDigits, numberToPersianWords } from "@/lib/persian-number";

export default function ToolsPage() {
  const [amount, setAmount] = useState(""); const [rate, setRate] = useState(""); const [months, setMonths] = useState("");
  const [calculationType, setCalculationType] = useState("vat"); const [calculation, setCalculation] = useState<number | null>(null);
  const [recipient, setRecipient] = useState(""); const [subject, setSubject] = useState(""); const [taxpayer, setTaxpayer] = useState("");
  const [caseNumber, setCaseNumber] = useState(""); const [facts, setFacts] = useState(""); const [requestText, setRequestText] = useState("");
  const [letterType, setLetterType] = useState("objection"); const [letter, setLetter] = useState(""); const [message, setMessage] = useState("");

  async function calculate(event: FormEvent) {
    event.preventDefault(); setMessage(""); setCalculation(null);
    if (!amount || !rate || (calculationType === "penalty" && !months)) { setMessage("مبلغ و نرخ را کامل وارد کنید."); return; }
    try {
      const result = await api<{ result: number }>("api/v1/tools/calculator", { method: "POST", body: JSON.stringify({ calculation_type: calculationType, amount: Number(amount), rate: Number(rate), months: calculationType === "penalty" ? Number(months) : 1 }) });
      setCalculation(result.result);
    } catch (caught) { setMessage(caught instanceof ApiError ? caught.message : "محاسبه انجام نشد."); }
  }
  async function generate(event: FormEvent) {
    event.preventDefault(); setMessage("");
    try {
      const result = await api<{ content: string }>("api/v1/tools/letters", { method: "POST", body: JSON.stringify({ letter_type: letterType, recipient, subject, taxpayer_name: taxpayer, case_number: caseNumber, facts, request_text: requestText }) });
      setLetter(result.content);
    } catch (caught) { setMessage(caught instanceof ApiError ? caught.message : "ساخت پیش‌نویس انجام نشد."); }
  }

  return <div className="space-y-8">
    <header className="relative overflow-hidden rounded-[2rem] bg-gradient-to-l from-cyan-600 via-blue-600 to-indigo-600 p-8 text-white shadow-xl shadow-blue-200/60">
      <Sparkles className="size-9 text-cyan-100" /><p className="mt-4 text-sm text-cyan-100">جعبه‌ابزار کاربردی</p>
      <h1 className="mt-1 text-3xl font-black">ابزارهای مالیاتی</h1><p className="mt-3 text-blue-50">محاسبه سریع و ساخت پیش‌نویس مکاتبات در یک فضای ساده.</p>
    </header>
    {message && <p className="rounded-xl bg-red-50 p-4 text-sm text-red-700">{message}</p>}
    <div className="grid gap-6 xl:grid-cols-2">
      <Card className="border-sky-100 bg-gradient-to-br from-white to-cyan-50/60 shadow-lg shadow-sky-100/40">
        <CardHeader><div className="flex size-12 items-center justify-center rounded-2xl bg-cyan-100 text-cyan-700"><Calculator /></div><CardTitle>ماشین‌حساب مالیاتی</CardTitle><CardDescription>مبلغ به تومان، جداسازی‌شده و به حروف نمایش داده می‌شود.</CardDescription></CardHeader>
        <CardContent><form onSubmit={calculate} className="space-y-3">
          <select value={calculationType} onChange={(event) => setCalculationType(event.target.value)} className="h-10 w-full rounded-lg border bg-white px-3 text-sm"><option value="vat">ارزش افزوده</option><option value="percentage">محاسبه درصد</option><option value="penalty">جریمه ماهانه</option></select>
          <Input inputMode="numeric" value={formatToman(amount)} onChange={(event) => setAmount(normalizeDigits(event.target.value))} placeholder="مبلغ پایه (تومان)" className="text-left font-bold" dir="ltr" required />
          {amount && <p className="rounded-lg bg-cyan-50 px-3 py-2 text-xs leading-6 text-cyan-900">{numberToPersianWords(Number(amount))} تومان</p>}
          <Input type="number" min="0" max="100" step="0.01" value={rate} onChange={(event) => setRate(event.target.value)} placeholder="نرخ درصد" required />
          {calculationType === "penalty" && <Input type="number" min="1" value={months} onChange={(event) => setMonths(event.target.value)} placeholder="تعداد ماه" required />}
          <Button className="w-full">محاسبه</Button>
        </form>
        {calculation !== null && <div className="mt-5 rounded-2xl bg-blue-50 p-5 text-center"><p className="text-sm text-slate-500">نتیجه برآوردی</p><p className="mt-2 text-3xl font-black text-blue-700">{calculation.toLocaleString("fa-IR")} تومان</p><p className="mt-2 text-xs leading-6 text-blue-800">{numberToPersianWords(calculation)} تومان</p></div>}
        <p className="mt-4 text-xs leading-6 text-slate-500">نتیجه برآورد اولیه است و مبنای قانونی پرونده باید جداگانه بررسی شود.</p></CardContent>
      </Card>
      <Card className="border-amber-100 bg-gradient-to-br from-white to-amber-50/60 shadow-lg shadow-amber-100/40">
        <CardHeader><div className="flex size-12 items-center justify-center rounded-2xl bg-amber-100 text-amber-700"><FileSignature /></div><CardTitle>نامه و لایحه‌ساز</CardTitle><CardDescription>پیش‌نویس قابل ویرایش برای اعتراض، تمدید یا رفع ابهام.</CardDescription></CardHeader>
        <CardContent><form onSubmit={generate} className="space-y-3">
          <select value={letterType} onChange={(event) => setLetterType(event.target.value)} className="h-10 w-full rounded-lg border bg-white px-3 text-sm"><option value="objection">لایحه اعتراض</option><option value="extension">درخواست تمدید</option><option value="clarification">درخواست رفع ابهام</option></select>
          <Input value={recipient} onChange={(event) => setRecipient(event.target.value)} placeholder="مخاطب" required /><Input value={subject} onChange={(event) => setSubject(event.target.value)} placeholder="موضوع نامه" required />
          <Input value={taxpayer} onChange={(event) => setTaxpayer(event.target.value)} placeholder="نام مؤدی یا شرکت" required /><Input value={caseNumber} onChange={(event) => setCaseNumber(event.target.value)} placeholder="شماره پرونده (اختیاری)" />
          <Textarea value={facts} onChange={(event) => setFacts(event.target.value)} placeholder="شرح ماجرا و مستندات" className="min-h-24" required /><Textarea value={requestText} onChange={(event) => setRequestText(event.target.value)} placeholder="درخواست نهایی شما" required />
          <Button className="w-full">ساخت پیش‌نویس</Button>
        </form></CardContent>
      </Card>
    </div>
    {letter && <Card className="border-blue-100 bg-white/95"><CardHeader><div className="flex items-center justify-between"><CardTitle>پیش‌نویس آماده</CardTitle><Button variant="outline" onClick={() => navigator.clipboard.writeText(letter)}><Copy /> کپی متن</Button></div></CardHeader><CardContent><pre className="whitespace-pre-wrap rounded-2xl bg-slate-50 p-5 font-sans text-sm leading-8">{letter}</pre><p className="mt-3 text-xs text-amber-700">پیش از ارسال رسمی، متن توسط متخصص بررسی شود.</p></CardContent></Card>}
  </div>;
}
