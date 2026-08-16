"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import {
  ArrowDownLeft,
  ArrowUpRight,
  Copy,
  Minus,
  Plus,
  ReceiptText,
  WalletCards,
} from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";

type Transaction = {
  id: string;
  type: string;
  amount: number;
  status: string;
  reference: string;
  created_at: string;
};
type Wallet = {
  balance: number;
  points: number;
  referral_code: string;
  daily_withdrawal_limit: number;
  withdrawn_today: number;
  withdrawal_remaining: number;
  transactions: Transaction[];
};
type Action = "charge" | "withdraw";
type Otp = { transaction_id: string; expires_in: number };

export default function WalletPage() {
  const [wallet, setWallet] = useState<Wallet | null>(null);
  const [action, setAction] = useState<Action | null>(null);
  const [amount, setAmount] = useState("");
  const [otp, setOtp] = useState<Otp | null>(null);
  const [code, setCode] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const load = useCallback(
    () => api<Wallet>("api/v1/portal/wallet").then(setWallet),
    [],
  );
  useEffect(() => {
    void load();
  }, [load]);

  function choose(nextAction: Action) {
    setAction(nextAction);
    setAmount("");
    setCode("");
    setOtp(null);
    setMessage("");
  }
  async function requestCode(event: FormEvent) {
    event.preventDefault();
    if (!action) return;
    setBusy(true);
    setMessage("");
    try {
      if (action === "charge") {
        await api("api/v1/portal/wallet/deposits", {
          method: "POST",
          body: JSON.stringify({ amount: Number(amount) }),
        });
        setMessage("کیف پول با موفقیت شارژ شد.");
        setAction(null);
        await load();
      } else {
        setOtp(
          await api<Otp>("api/v1/portal/wallet/withdrawals/otp", {
            method: "POST",
            body: JSON.stringify({ amount: Number(amount) }),
          }),
        );
        setMessage("کد تأیید به شماره موبایل تأییدشده شما پیامک شد.");
      }
    } catch (error) {
      setMessage(
        error instanceof ApiError ? error.message : "عملیات انجام نشد.",
      );
    } finally {
      setBusy(false);
    }
  }
  async function confirm(event: FormEvent) {
    event.preventDefault();
    if (!otp || !action) return;
    setBusy(true);
    setMessage("");
    try {
      const path = action === "charge" ? "deposits" : "withdrawals";
      await api(`api/v1/portal/wallet/${path}/confirm`, {
        method: "POST",
        body: JSON.stringify({ transaction_id: otp.transaction_id, code }),
      });
      setMessage(
        action === "charge"
          ? "کیف پول با موفقیت شارژ شد."
          : "درخواست برداشت برای بررسی ثبت شد.",
      );
      setAction(null);
      setOtp(null);
      await load();
    } catch (error) {
      setMessage(
        error instanceof ApiError ? error.message : "تأیید انجام نشد.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-7">
      <header className="rounded-[2rem] bg-gradient-to-l from-sky-500 via-blue-600 to-cyan-500 p-8 text-white shadow-2xl shadow-blue-900/15">
        <p className="text-sm text-blue-50">مدیریت اعتبار حساب</p>
        <h1 className="mt-2 text-3xl font-black">کیف پول من</h1>
        <p className="mt-3 text-blue-50">
          شارژ، برداشت و پیگیری تراکنش‌ها با تأیید دومرحله‌ای.
        </p>
      </header>

      <section className="grid gap-6 lg:grid-cols-[1.15fr_.85fr]">
        <div className="relative min-h-64 overflow-hidden rounded-[2rem] bg-gradient-to-br from-cyan-500 via-blue-600 to-sky-700 p-7 text-white shadow-2xl shadow-blue-900/20">
          <div className="absolute -left-16 -top-20 size-56 rounded-full bg-white/15" />
          <div className="absolute -bottom-24 -right-10 size-64 rounded-full bg-cyan-200/15" />
          <div className="relative flex h-full flex-col justify-between">
            <div className="flex items-center justify-between">
              <span className="flex size-12 items-center justify-center rounded-2xl bg-white/15">
                <WalletCards />
              </span>
              <p className="text-sm text-blue-50">CHAKA WALLET</p>
            </div>
            <div className="my-8">
              <p className="text-sm text-blue-100">موجودی قابل استفاده</p>
              <p className="mt-2 text-4xl font-black">
                {(wallet?.balance ?? 0).toLocaleString("fa-IR")}{" "}
                <span className="text-base font-normal">تومان</span>
              </p>
              <p className="mt-3 text-sm text-cyan-100">
                {(wallet?.points ?? 0).toLocaleString("fa-IR")} امتیاز پاداش
              </p>
            </div>
            <div className="flex items-end justify-between">
              <div>
                <p className="text-xs text-blue-100">کد معرف</p>
                <button
                  type="button"
                  className="mt-1 flex items-center gap-2 font-mono"
                  onClick={() =>
                    navigator.clipboard.writeText(wallet?.referral_code || "")
                  }
                >
                  {wallet?.referral_code || "—"}
                  <Copy className="size-3.5" />
                </button>
              </div>
              <div className="flex gap-3">
                <WalletAction
                  icon={Plus}
                  label="شارژ کیف پول"
                  onClick={() => choose("charge")}
                />
                <WalletAction
                  icon={Minus}
                  label="برداشت وجه"
                  onClick={() => choose("withdraw")}
                />
              </div>
            </div>
          </div>
        </div>

        <Card className="border-white/70 bg-white/95">
          <CardHeader>
            <CardTitle>
              {action === "charge"
                ? "شارژ کیف پول"
                : action === "withdraw"
                  ? "برداشت وجه"
                  : "عملیات کیف پول"}
            </CardTitle>
            <CardDescription>
              {action
                ? action === "charge"
                  ? "مبلغ شارژ را وارد کنید؛ این عملیات نیاز به کد تأیید ندارد."
                  : "مبلغ را وارد و با کد پیامک‌شده به شماره موبایل تأیید کنید."
                : "برای شروع روی دکمه مثبت یا منفی کیف پول بزنید."}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {action && !otp && (
              <form onSubmit={requestCode} className="space-y-4">
                <Input
                  inputMode="numeric"
                  dir="ltr"
                  value={amount ? Number(amount).toLocaleString("en-US") : ""}
                  onChange={(event) =>
                    setAmount(event.target.value.replace(/\D/g, "").slice(0, 9))
                  }
                  placeholder="مبلغ به تومان"
                  required
                />
                <p className="text-xs text-slate-500">
                  {amount
                    ? `${Number(amount).toLocaleString("fa-IR")} تومان`
                    : "حداقل مبلغ ۱۰٬۰۰۰ تومان"}
                </p>
                <Button
                  className="w-full bg-blue-600 hover:bg-blue-700"
                  disabled={busy || Number(amount) < 10000}
                >
                {action === "charge" ? "شارژ کیف پول" : "دریافت کد تأیید پیامکی"}
                </Button>
                {action === "withdraw" && (
                  <div className="rounded-xl bg-amber-50 p-3 text-xs leading-6 text-amber-900">
                    <p>
                      سقف برداشت روزانه:{" "}
                      {(
                        wallet?.daily_withdrawal_limit ?? 15_000_000
                      ).toLocaleString("fa-IR")}{" "}
                      تومان
                    </p>
                    <p>
                      ظرفیت باقی‌مانده امروز:{" "}
                      {(
                        wallet?.withdrawal_remaining ?? 15_000_000
                      ).toLocaleString("fa-IR")}{" "}
                      تومان
                    </p>
                  </div>
                )}
              </form>
            )}
            {action && otp && (
              <form onSubmit={confirm} className="space-y-4">
                <Input
                  inputMode="numeric"
                  value={code}
                  onChange={(event) =>
                    setCode(event.target.value.replace(/\D/g, "").slice(0, 6))
                  }
                placeholder="کد ۶ رقمی ارسال‌شده به موبایل"
                  required
                />
                <Button
                  className="w-full bg-blue-600 hover:bg-blue-700"
                  disabled={busy || code.length !== 6}
                >
                  تأیید نهایی
                </Button>
              </form>
            )}
            {!action && (
              <div className="flex min-h-32 items-center justify-center rounded-2xl border border-dashed text-sm text-muted-foreground">
                یک عملیات را انتخاب کنید
              </div>
            )}
            {message && (
              <p className="mt-4 rounded-xl bg-sky-50 p-3 text-sm text-sky-800">
                {message}
              </p>
            )}
          </CardContent>
        </Card>
      </section>

      <Card className="border-white/70 bg-white/95">
        <CardHeader>
          <CardTitle className="flex gap-2">
            <ReceiptText className="text-blue-600" /> تاریخچه کیف پول
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {wallet?.transactions.map((item) => (
            <div
              key={item.id}
              className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border bg-white p-4"
            >
              <div className="flex items-center gap-3">
                <span
                  className={`flex size-10 items-center justify-center rounded-xl ${item.type === "charge" ? "bg-emerald-50 text-emerald-600" : "bg-rose-50 text-rose-600"}`}
                >
                  {item.type === "charge" ? (
                    <ArrowDownLeft />
                  ) : (
                    <ArrowUpRight />
                  )}
                </span>
                <div>
                  <p className="font-semibold">
                    {item.type === "charge"
                      ? "شارژ کیف پول"
                      : item.type === "withdraw"
                        ? "برداشت وجه"
                        : item.type === "consultation"
                          ? "پرداخت مشاوره"
                          : "پرداخت کیف پول"}
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground" dir="ltr">
                    {item.reference}
                  </p>
                </div>
              </div>
              <div className="text-left">
                <p className="font-black">
                  {item.amount.toLocaleString("fa-IR")} تومان
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {item.status === "completed"
                    ? "تکمیل‌شده"
                    : item.status === "pending"
                      ? "در انتظار بررسی"
                      : item.status === "failed"
                        ? "ناموفق"
                        : "در انتظار تأیید"}
                </p>
              </div>
            </div>
          ))}
          {!wallet?.transactions.length && (
            <p className="py-10 text-center text-sm text-muted-foreground">
              هنوز تراکنشی ثبت نشده است.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function WalletAction({
  icon: Icon,
  label,
  onClick,
}: {
  icon: typeof Plus;
  label: string;
  onClick: () => void;
}) {
  return (
    <div className="group relative">
      <button
        type="button"
        onClick={onClick}
        className="flex size-11 items-center justify-center rounded-full border border-white/30 bg-white/15 transition hover:-translate-y-1 hover:bg-white hover:text-blue-700"
      >
        <Icon />
      </button>
      <span className="pointer-events-none absolute left-1/2 top-[calc(100%+8px)] z-10 -translate-x-1/2 whitespace-nowrap rounded-lg bg-white px-2.5 py-1.5 text-[11px] font-medium text-blue-800 opacity-0 shadow-lg transition group-hover:opacity-100">
        {label}
      </span>
    </div>
  );
}
