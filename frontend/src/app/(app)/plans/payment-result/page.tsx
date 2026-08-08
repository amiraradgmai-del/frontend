"use client";

import Link from "next/link";
import { CheckCircle2, CircleX, Clock3 } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

const states = {
  success: {
    title: "پرداخت با موفقیت تأیید شد",
    description: "اشتراک شما فعال شده و امکانات بسته اکنون در دسترس است.",
    icon: CheckCircle2,
    color: "text-emerald-600",
    background: "bg-emerald-50",
  },
  cancelled: {
    title: "پرداخت لغو شد",
    description: "مبلغی از حساب شما کسر نشده است و می‌توانید دوباره تلاش کنید.",
    icon: Clock3,
    color: "text-amber-600",
    background: "bg-amber-50",
  },
  failed: {
    title: "تأیید پرداخت انجام نشد",
    description: "در صورت کسر وجه، مبلغ طبق روال بانکی بازگردانده می‌شود. برای پیگیری با پشتیبانی در ارتباط باشید.",
    icon: CircleX,
    color: "text-rose-600",
    background: "bg-rose-50",
  },
  not_found: {
    title: "تراکنش پیدا نشد",
    description: "شناسه پرداخت معتبر نیست. لطفاً از بخش پرداخت‌ها وضعیت تراکنش را بررسی کنید.",
    icon: CircleX,
    color: "text-rose-600",
    background: "bg-rose-50",
  },
};

function PaymentResultContent() {
  const searchParams = useSearchParams();
  const status = searchParams.get("status") as keyof typeof states | null;
  const state = states[status ?? "failed"] ?? states.failed;
  const Icon = state.icon;

  return (
    <main className="mx-auto flex min-h-[65vh] max-w-2xl items-center justify-center p-6">
      <section className="w-full rounded-[2rem] border border-sky-100 bg-white p-9 text-center shadow-xl shadow-sky-900/5">
        <span className={`mx-auto flex size-20 items-center justify-center rounded-full ${state.background} ${state.color}`}>
          <Icon className="size-10" />
        </span>
        <h1 className="mt-6 text-2xl font-black">{state.title}</h1>
        <p className="mx-auto mt-3 max-w-lg leading-8 text-slate-600">{state.description}</p>
        <div className="mt-7 flex justify-center gap-3">
          <Link href="/plans" className="rounded-xl bg-blue-600 px-5 py-3 text-sm font-bold text-white">مشاهده اشتراک</Link>
          <Link href="/dashboard" className="rounded-xl border border-sky-200 bg-white px-5 py-3 text-sm font-bold text-slate-700">بازگشت به داشبورد</Link>
        </div>
      </section>
    </main>
  );
}

export default function PaymentResultPage() {
  return <Suspense><PaymentResultContent /></Suspense>;
}
