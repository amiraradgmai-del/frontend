"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowLeft, Check, Crown, Gem, ShieldCheck, Sparkles, WalletCards } from "lucide-react";
import { api } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

type Plan = { code: string; title: string; description: string; price: number; benefits: string[] };
type Wallet = { balance: number; points: number };
type Payment = { id: string; amount: number; status: string; reference: string; created_at: string; plan: string };

export default function PlansPage() {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [wallet, setWallet] = useState<Wallet | null>(null);
  const [payments, setPayments] = useState<Payment[]>([]);

  useEffect(() => {
    void Promise.all([
      api<Plan[]>("api/v1/portal/plans"),
      api<Wallet>("api/v1/portal/wallet"),
      api<Payment[]>("api/v1/portal/payments"),
    ]).then(([planItems, walletData, paymentItems]) => {
      setPlans(planItems);
      setWallet(walletData);
      setPayments(paymentItems);
    });
  }, []);

  return <div className="space-y-8">
    <header className="relative overflow-hidden rounded-[2rem] bg-gradient-to-l from-sky-500 via-blue-600 to-cyan-500 p-8 text-white shadow-2xl shadow-blue-900/15">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_15%_20%,rgba(255,255,255,.22),transparent_28%)]" />
      <div className="relative"><Badge className="mb-4 bg-white/15 text-white"><Gem /> عضویت منعطف چکاه</Badge><h1 className="text-3xl font-black sm:text-4xl">پلن اشتراک مناسب شما</h1><p className="mt-3 max-w-2xl leading-8 text-blue-50">پلن را انتخاب کنید و سپس بسته Silver، Gold یا Diamond را بر اساس میزان استفاده خود بردارید.</p></div>
    </header>

    <Link href="/app/wallet" className="group block rounded-3xl border border-sky-200 bg-gradient-to-l from-white to-sky-50 px-6 py-5 shadow-lg shadow-sky-900/5 transition hover:-translate-y-0.5 hover:shadow-xl">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-4"><span className="flex size-12 items-center justify-center rounded-2xl bg-sky-100 text-blue-600"><WalletCards /></span><div><p className="font-bold text-slate-900">کیف پول و امتیاز من</p><p className="mt-1 text-xs text-slate-500">شارژ، برداشت، تراکنش‌ها و امتیازها</p></div></div>
        <div className="flex items-center gap-5"><div className="text-left"><p className="text-2xl font-black text-blue-700">{(wallet?.balance ?? 0).toLocaleString("fa-IR")}</p><p className="text-[11px] text-slate-500">تومان · {(wallet?.points ?? 0).toLocaleString("fa-IR")} امتیاز</p></div><ArrowLeft className="text-blue-600 transition group-hover:-translate-x-1" /></div>
      </div>
    </Link>

    <section className="grid gap-5 lg:grid-cols-3">{plans.map((plan) => {
      const paid = plan.price > 0;
      const Icon = plan.code === "pro" ? Crown : plan.code === "plus" ? Sparkles : ShieldCheck;
      const palette = plan.code === "pro" ? "from-rose-50 to-orange-50 border-rose-200" : plan.code === "plus" ? "from-cyan-50 to-blue-50 border-cyan-200" : "from-sky-50 to-white border-sky-200";
      const strip = plan.code === "pro" ? "from-rose-400 to-orange-400" : plan.code === "plus" ? "from-cyan-400 to-blue-500" : "from-sky-400 to-blue-500";
      const content = <Card className={`flex h-full flex-col overflow-hidden border bg-gradient-to-br ${palette} transition ${paid ? "hover:-translate-y-1 hover:shadow-2xl" : "opacity-95"}`}>
        {plan.code === "pro" && <div className="bg-rose-100 py-1.5 text-center text-xs font-bold text-rose-700">پیشنهاد ویژه حرفه‌ای‌ها</div>}
        <div className={`h-2 bg-gradient-to-l ${strip}`} /><CardHeader><div className="mb-3 flex size-12 items-center justify-center rounded-2xl bg-white/80 text-blue-600 shadow-sm"><Icon /></div><CardTitle className="text-2xl">{plan.title}</CardTitle><CardDescription className="min-h-14 leading-7">{plan.description}</CardDescription><p className="pt-3 text-3xl font-black">{paid ? `از ${plan.price.toLocaleString("fa-IR")} تومان` : "رایگان"}</p></CardHeader>
        <CardContent className="flex flex-1 flex-col"><div className="space-y-3">{plan.benefits.map((item) => <p key={item} className="flex gap-2 text-sm"><Check className="size-4 shrink-0 text-emerald-600" />{item}</p>)}</div><div className={`mt-auto flex items-center justify-center gap-2 rounded-xl py-3 text-sm font-bold ${paid ? "bg-blue-600 text-white" : "bg-slate-100 text-slate-500"}`}>{paid ? <>مشاهده بسته‌ها <ArrowLeft className="size-4" /></> : "پلن پایه فعال"}</div></CardContent>
      </Card>;
      return paid ? <Link className="h-full" key={plan.code} href={`/app/plans/${plan.code}`}>{content}</Link> : <div className="h-full" key={plan.code}>{content}</div>;
    })}</section>
    {payments.length > 0 && <section className="rounded-3xl border border-sky-100 bg-white p-6"><h2 className="text-xl font-black">فاکتورهای من</h2><div className="mt-4 divide-y">{payments.filter((item) => item.status === "paid").slice(0, 10).map((item) => <div key={item.id} className="flex flex-wrap items-center justify-between gap-3 py-3 text-sm"><div><p className="font-bold">{item.plan}</p><p className="mt-1 text-xs text-slate-500">{item.amount.toLocaleString("fa-IR")} تومان · {new Date(item.created_at).toLocaleDateString("fa-IR")}</p></div><a href={`/api/backend/api/v1/portal/payments/${item.id}/invoice.pdf`} className="rounded-xl bg-sky-50 px-4 py-2 font-bold text-blue-700">دریافت PDF</a></div>)}</div></section>}
  </div>;
}
