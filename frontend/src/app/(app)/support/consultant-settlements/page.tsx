"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";

type Summary = { consultant_id: string; full_name: string; gross_amount: number; unsettled_gross: number; payable: number; bank_iban: string };
type History = { id: string; consultant_id: string; payable_amount: number; status: string; reference: string; created_at: string };
type Response = { summaries: Summary[]; history: History[] };

export default function ConsultantSettlementsPage() {
  const [data, setData] = useState<Response>({ summaries: [], history: [] });
  const [message, setMessage] = useState("");
  const load = () => api<Response>("api/v1/admin/consultant-settlements").then(setData);
  useEffect(() => { void load().catch(() => setMessage("دریافت اطلاعات تسویه ممکن نیست.")); }, []);
  async function create(consultantId: string) {
    try { await api("api/v1/admin/consultant-settlements", { method: "POST", body: JSON.stringify({ consultant_id: consultantId, admin_note: "" }) }); setMessage("درخواست تسویه ثبت شد."); await load(); }
    catch (error) { setMessage(error instanceof Error ? error.message : "ثبت تسویه انجام نشد."); }
  }
  async function review(id: string, status: "paid" | "rejected") {
    const reference = status === "paid" ? window.prompt("شماره پیگیری بانکی را وارد کنید:") ?? "" : "";
    const admin_note = status === "rejected" ? window.prompt("دلیل رد را وارد کنید:") ?? "" : "";
    if (status === "paid" && !reference) return;
    try { await api(`api/v1/admin/consultant-settlements/${id}`, { method: "PATCH", body: JSON.stringify({ status, reference, admin_note }) }); await load(); }
    catch (error) { setMessage(error instanceof Error ? error.message : "به‌روزرسانی تسویه انجام نشد."); }
  }
  return <div className="space-y-7"><header><p className="text-sm font-bold text-blue-600">عملیات مالی مشاوران</p><h1 className="mt-1 text-3xl font-black">تسویه درآمد مشاوران</h1></header>{message && <p className="rounded-xl bg-sky-50 p-3 text-sm">{message}</p>}
    <section className="grid gap-4">{data.summaries.map((item) => <article key={item.consultant_id} className="rounded-2xl border bg-white p-5"><div className="flex flex-wrap items-center justify-between gap-4"><div><h2 className="font-black">{item.full_name}</h2><p className="mt-2 text-xs text-slate-500">شبا: {item.bank_iban || "ثبت نشده"}</p></div><div className="text-sm"><p>درآمد کل: {item.gross_amount.toLocaleString("fa-IR")} تومان</p><p className="mt-1 font-bold text-emerald-700">قابل پرداخت: {item.payable.toLocaleString("fa-IR")} تومان</p></div><Button disabled={!item.payable || !item.bank_iban} onClick={() => void create(item.consultant_id)}>ایجاد تسویه</Button></div></article>)}</section>
    <section className="rounded-2xl border bg-white p-5"><h2 className="font-black">تاریخچه تسویه</h2><div className="mt-4 space-y-3">{data.history.map((item) => <div key={item.id} className="flex flex-wrap items-center justify-between gap-3 rounded-xl bg-slate-50 p-4 text-sm"><span>{item.payable_amount.toLocaleString("fa-IR")} تومان</span><span>{item.status}</span>{item.status === "pending" && <div className="flex gap-2"><Button size="sm" onClick={() => void review(item.id, "paid")}>پرداخت شد</Button><Button size="sm" variant="destructive" onClick={() => void review(item.id, "rejected")}>رد</Button></div>}</div>)}</div></section>
  </div>;
}
