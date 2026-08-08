"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type Report = { paid_total: number; paid_last_30_days: number; wallet_charges: number; active_subscriptions: number };
type Usage = { chat_messages: number; recommended_monthly_alert: number; estimated_cost_toman: number; monthly_budget_toman: number; budget_percent: number; alert_reached: boolean; tool_usage: Record<string, number> };

export default function ReportsPage() {
  const [report, setReport] = useState<Report | null>(null);
  const [usage, setUsage] = useState<Usage | null>(null);
  useEffect(() => { Promise.all([api<Report>("api/v1/admin/financial-report"), api<Usage>("api/v1/admin/api-usage")]).then(([financial, apiUsage]) => { setReport(financial); setUsage(apiUsage); }); }, []);
  return <div className="space-y-7"><header><p className="text-sm font-bold text-blue-600">کنترل مالی و فنی</p><h1 className="mt-1 text-3xl font-black">گزارش‌های سامانه</h1></header><section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4"><Metric title="کل درآمد" value={`${(report?.paid_total ?? 0).toLocaleString("fa-IR")} تومان`} /><Metric title="درآمد ۳۰ روز" value={`${(report?.paid_last_30_days ?? 0).toLocaleString("fa-IR")} تومان`} /><Metric title="شارژ کیف پول" value={`${(report?.wallet_charges ?? 0).toLocaleString("fa-IR")} تومان`} /><Metric title="اشتراک فعال" value={(report?.active_subscriptions ?? 0).toLocaleString("fa-IR")} /></section><div className="grid gap-5 lg:grid-cols-2"><Card><CardHeader><CardTitle>مصرف API در ۳۰ روز</CardTitle></CardHeader><CardContent><p className="text-3xl font-black">{(usage?.estimated_cost_toman ?? 0).toLocaleString("fa-IR")} <span className="text-sm font-normal">تومان</span></p><p className="mt-2 text-sm text-slate-500">{(usage?.chat_messages ?? 0).toLocaleString("fa-IR")} پیام · سقف هزینه {(usage?.monthly_budget_toman ?? 0).toLocaleString("fa-IR")} تومان</p><div className="mt-4 h-3 overflow-hidden rounded-full bg-slate-100"><div className={`h-full rounded-full ${usage?.alert_reached ? "bg-red-500" : "bg-blue-600"}`} style={{ width: `${usage?.budget_percent ?? 0}%` }} /></div>{usage?.alert_reached && <p className="mt-3 rounded-xl bg-red-50 p-3 text-red-700">سقف هزینه API رد شده است؛ مدل یا سهمیه‌ها را بررسی کنید.</p>}</CardContent></Card><Card><CardHeader><CardTitle>خروجی مدیریتی</CardTitle></CardHeader><CardContent className="flex gap-3"><a className="rounded-xl bg-blue-600 px-4 py-3 text-sm font-bold text-white" href="/api/backend/api/v1/admin/export/users.xlsx">Excel کاربران</a><a className="rounded-xl bg-emerald-600 px-4 py-3 text-sm font-bold text-white" href="/api/backend/api/v1/admin/export/payments.xlsx">Excel پرداخت‌ها</a></CardContent></Card></div></div>;
}

function Metric({ title, value }: { title: string; value: string }) { return <Card><CardContent className="p-5"><p className="text-xs text-slate-500">{title}</p><p className="mt-2 text-xl font-black">{value}</p></CardContent></Card>; }
