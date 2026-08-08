"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ArrowRight, Check, Crown, Gem, ShieldCheck, Sparkles, WalletCards } from "lucide-react";
import { useParams } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

type Plan = { code: string; title: string; description: string; price: number; benefits: string[] };
type Preview = { amount: number; discount_amount: number; payable: number };
type Wallet = { balance: number };
type GatewayResult = { payment_id: string; status: string; payment_url: string };
type Receipt = { payment_id: string; amount: number; discount_amount: number; reference: string; package: string };
type PackageCode = "silver" | "gold" | "diamond";

const packages = [
  { code: "silver" as const, title: "Silver", multiplier: 1, quota: 1, icon: ShieldCheck, color: "from-slate-400 to-slate-600", support: "پشتیبانی استاندارد" },
  { code: "gold" as const, title: "Gold", multiplier: 1.75, quota: 2, icon: Sparkles, color: "from-amber-300 to-orange-500", support: "پشتیبانی با اولویت" },
  { code: "diamond" as const, title: "Diamond", multiplier: 3.2, quota: 4, icon: Gem, color: "from-cyan-400 to-blue-600", support: "پشتیبانی ویژه و سریع" },
];

const packagePrice = (basePrice: number, multiplier: number) => Math.round(basePrice * multiplier / 1000) * 1000;
const baseLimits = {
  plus: { questions: 100, lawSearch: 100, calculations: 100, letters: 10, documents: 5, tickets: 5, consultations: 2 },
  pro: { questions: 1000, lawSearch: 1000, calculations: 1000, letters: 100, documents: 20, tickets: 20, consultations: 10 },
};

function packageBenefits(planCode: string, multiplier: number, support: string) {
  const limits = baseLimits[planCode as keyof typeof baseLimits] ?? baseLimits.plus;
  const value = (key: keyof typeof limits) => (limits[key] * multiplier).toLocaleString("fa-IR");
  return [
    `${value("questions")} پرسش هوشمند در ماه`,
    `${value("lawSearch")} جست‌وجوی قانون و ${value("calculations")} محاسبه`,
    `${value("documents")} سند و ${value("tickets")} تیکت پشتیبانی`,
    `${value("letters")} نامه مالیاتی`,
    `${value("consultations")} درخواست مشاوره شرکتی`,
    support,
  ];
}

export default function PlanDetailsPage() {
  const params = useParams<{ plan: string }>();
  const [plan, setPlan] = useState<Plan | null>(null);
  const [wallet, setWallet] = useState<Wallet | null>(null);
  const [packageCode, setPackageCode] = useState<PackageCode>("silver");
  const [discount, setDiscount] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [paid, setPaid] = useState(false);
  const [preview, setPreview] = useState<Preview | null>(null);

  const load = useCallback(
    () =>
      Promise.all([
        api<Plan[]>("api/v1/portal/plans"),
        api<Wallet>("api/v1/portal/wallet"),
      ]).then(([plans, walletInfo]) => {
        setPlan(plans.find((item) => item.code === params.plan && item.price > 0) ?? null);
        setWallet(walletInfo);
      }),
    [params.plan],
  );

  useEffect(() => {
    void load();
  }, [load]);

  const selectedPackage = useMemo(
    () => packages.find((item) => item.code === packageCode)!,
    [packageCode],
  );
  const price = plan ? packagePrice(plan.price, selectedPackage.multiplier) : 0;

  async function previewPayment() {
    if (!plan) return;
    setBusy(true);
    setMessage("");
    try {
      setPreview(
        await api<Preview>("api/v1/portal/checkout/preview", {
          method: "POST",
          body: JSON.stringify({ plan_code: plan.code, package: packageCode, discount_code: discount }),
        }),
      );
    } catch (error) {
      setMessage(error instanceof ApiError ? error.message : "بررسی مبلغ انجام نشد.");
    } finally {
      setBusy(false);
    }
  }

  async function payWithGateway() {
    if (!plan) return;
    setBusy(true);
    setMessage("");
    try {
      const result = await api<GatewayResult>("api/v1/portal/checkout/zarinpal", {
        method: "POST",
        body: JSON.stringify({ plan_code: plan.code, package: packageCode, discount_code: discount }),
      });
      window.location.assign(result.payment_url);
    } catch (error) {
      setMessage(error instanceof ApiError ? error.message : "اتصال به درگاه پرداخت انجام نشد.");
      setBusy(false);
    }
  }

  async function payWithWallet() {
    if (!plan) return;
    setBusy(true);
    setMessage("");
    try {
      await api<Receipt>("api/v1/portal/checkout/wallet", {
        method: "POST",
        body: JSON.stringify({ plan_code: plan.code, package: packageCode, discount_code: discount }),
      });
      setPaid(true);
      setDiscount("");
      setPreview(null);
      await load();
      window.setTimeout(() => setPaid(false), 4000);
    } catch (error) {
      setMessage(error instanceof ApiError ? error.message : "پرداخت از کیف پول انجام نشد.");
    } finally {
      setBusy(false);
    }
  }

  if (!plan) {
    return (
      <div className="rounded-3xl border border-dashed p-16 text-center">
        <p>پلن موردنظر پیدا نشد.</p>
        <Link href="/app/plans" className="mt-4 inline-block text-primary">بازگشت به پلن‌ها</Link>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <header className="rounded-[2rem] bg-gradient-to-l from-sky-500 via-blue-600 to-cyan-500 p-8 text-white shadow-xl shadow-blue-900/10">
        <Link href="/app/plans" className="mb-5 flex w-fit items-center gap-2 text-sm text-blue-50">
          <ArrowRight className="size-4" /> بازگشت
        </Link>
        <div className="flex items-center gap-4">
          <span className="flex size-14 items-center justify-center rounded-2xl bg-white/15"><Crown /></span>
          <div><p className="text-sm text-blue-50">پلن اشتراک</p><h1 className="text-3xl font-black">{plan.title}</h1></div>
        </div>
        <p className="mt-4 max-w-2xl leading-8 text-blue-50">{plan.description}</p>
      </header>

      <section className="grid items-stretch gap-5 lg:grid-cols-3">
        {packages.map((item) => (
          <button
            type="button"
            key={item.code}
            onClick={() => { setPackageCode(item.code); setPreview(null); }}
            className={`h-full overflow-hidden rounded-3xl border bg-white text-right shadow-sm transition hover:-translate-y-1 hover:shadow-xl ${packageCode === item.code ? "border-blue-500 ring-2 ring-blue-100" : "border-sky-100"}`}
          >
            <div className={`h-2 bg-gradient-to-l ${item.color}`} />
            <div className="p-6">
              <div className="flex items-center justify-between">
                <span className={`flex size-12 items-center justify-center rounded-2xl bg-gradient-to-l text-white ${item.color}`}><item.icon /></span>
                {item.code === "gold" && <Badge className="bg-amber-100 text-amber-800">محبوب‌ترین</Badge>}
              </div>
              <h2 className="mt-5 text-2xl font-black" dir="ltr">{item.title}</h2>
              <p className="mt-2 text-3xl font-black text-blue-700">
                {packagePrice(plan.price, item.multiplier).toLocaleString("fa-IR")} <span className="text-sm font-normal">تومان</span>
              </p>
              <p className="mt-1 text-xs text-muted-foreground">اشتراک یک‌ماهه · ظرفیت ×{item.quota.toLocaleString("fa-IR")}</p>
              <div className="mt-5 space-y-3">
                {packageBenefits(plan.code, item.quota, item.support).map((benefit) => (
                  <p key={benefit} className="flex gap-2 text-sm"><Check className="size-4 shrink-0 text-emerald-600" />{benefit}</p>
                ))}
              </div>
            </div>
          </button>
        ))}
      </section>

      {message && <p className="rounded-xl bg-amber-50 p-4 text-sm text-amber-800">{message}</p>}

      <Card className="mx-auto max-w-3xl border-sky-100 bg-white">
        <CardHeader>
          <CardTitle className="flex gap-2"><WalletCards className="text-blue-600" /> پرداخت امن اشتراک</CardTitle>
          <CardDescription>بسته {selectedPackage.title} با مبلغ {price.toLocaleString("fa-IR")} تومان</CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="flex gap-2">
            <Input
              dir="ltr"
              value={discount}
              onChange={(event) => { setDiscount(event.target.value.toUpperCase()); setPreview(null); }}
              placeholder="کد تخفیف (اختیاری)"
            />
            <Button type="button" variant="outline" onClick={() => void previewPayment()} disabled={busy}>بررسی</Button>
          </div>
          {preview && (
            <div className="space-y-2 rounded-2xl bg-sky-50 p-4 text-sm">
              <p className="flex justify-between"><span>مبلغ بسته</span><strong>{preview.amount.toLocaleString("fa-IR")} تومان</strong></p>
              <p className="flex justify-between text-emerald-700"><span>تخفیف</span><strong>{preview.discount_amount.toLocaleString("fa-IR")} تومان</strong></p>
              <p className="flex justify-between border-t border-sky-200 pt-2 text-blue-800"><span>مبلغ پرداخت</span><strong>{preview.payable.toLocaleString("fa-IR")} تومان</strong></p>
            </div>
          )}
          <div className="grid gap-3 sm:grid-cols-2">
            <Button type="button" className="h-12 bg-blue-600 hover:bg-blue-700" onClick={() => void payWithGateway()} disabled={busy}>
              پرداخت آنلاین با زرین‌پال
            </Button>
            <Button
              type="button"
              variant="outline"
              className="h-12 border-emerald-200 text-emerald-700"
              onClick={() => void payWithWallet()}
              disabled={busy || (wallet?.balance ?? 0) < (preview?.payable ?? price)}
            >
              پرداخت با کیف پول
            </Button>
          </div>
          <div className="flex items-center justify-between rounded-2xl border border-emerald-100 bg-emerald-50 p-4 text-sm">
            <span className="font-bold text-emerald-900">موجودی کیف پول</span>
            <strong className="text-emerald-700">{(wallet?.balance ?? 0).toLocaleString("fa-IR")} تومان</strong>
          </div>
          <p className="text-center text-xs leading-6 text-slate-500">اطلاعات کارت بانکی فقط در صفحه امن درگاه وارد می‌شود و چکاه آن را دریافت یا ذخیره نمی‌کند.</p>
        </CardContent>
      </Card>

      {paid && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-blue-950/25 p-6 backdrop-blur-sm">
          <div className="rounded-3xl bg-white p-9 text-center shadow-2xl">
            <span className="mx-auto flex size-16 items-center justify-center rounded-full bg-emerald-100 text-emerald-700"><Check /></span>
            <h2 className="mt-5 text-2xl font-black">پرداخت موفق بود</h2>
            <p className="mt-2 text-muted-foreground">از اعتماد شما به چکاه متشکریم.</p>
          </div>
        </div>
      )}
    </div>
  );
}
