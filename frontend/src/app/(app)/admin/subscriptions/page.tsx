"use client";

import { useEffect, useState } from "react";
import { Ban, CircleDollarSign, RotateCcw, Save } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { AdminTable } from "@/components/admin-table";

type Row = { id: string; email: string; plan: string; package: string; status: string; starts_at: string; ends_at: string };
type Plan = { id: string; code: string; title: string; price: number; duration_days: number; is_active: boolean };

export default function SubscriptionsPage() {
  const [rows, setRows] = useState<Row[]>([]);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [message, setMessage] = useState("");
  const load = () => Promise.all([
    api<Row[]>("api/v1/admin/subscriptions"),
    api<Plan[]>("api/v1/admin/plans"),
  ]).then(([subscriptions, planItems]) => {
    setRows(subscriptions);
    setPlans(planItems);
  });
  useEffect(() => { void load(); }, []);

  async function updateSubscription(id: string, status: "active" | "cancelled") {
    await api(`api/v1/admin/subscriptions/${id}`, { method: "PATCH", body: JSON.stringify({ status }) });
    await load();
  }

  async function updatePlan(plan: Plan) {
    setMessage("");
    try {
      await api(`api/v1/admin/plans/${plan.id}`, {
        method: "PATCH",
        body: JSON.stringify({ price: plan.price, duration_days: plan.duration_days, is_active: plan.is_active }),
      });
      setMessage(`تنظیمات پلن ${plan.title} ذخیره شد.`);
      await load();
    } catch (error) {
      setMessage(error instanceof ApiError ? error.message : "ذخیره تنظیمات پلن انجام نشد.");
    }
  }

  function changePlan(id: string, patch: Partial<Plan>) {
    setPlans((current) => current.map((plan) => plan.id === id ? { ...plan, ...patch } : plan));
  }

  return <div className="space-y-7">
    <header>
      <p className="text-sm font-bold text-blue-600">قیمت‌گذاری و کنترل عضویت</p>
      <h1 className="mt-1 text-3xl font-black">مدیریت اشتراک‌ها</h1>
      <p className="mt-2 text-sm text-slate-500">قیمت پایه، مدت و وضعیت فروش پلن‌ها را مدیریت کنید.</p>
    </header>

    <section className="grid gap-4 lg:grid-cols-3">
      {plans.map((plan) => <Card key={plan.id} className="border-sky-100 bg-white">
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><CircleDollarSign className="text-blue-600" /> {plan.title}</CardTitle>
          <CardDescription>{plan.code === "normal" ? "پلن پایه سامانه" : "قیمت بسته Silver؛ Gold و Diamond خودکار محاسبه می‌شوند."}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <label className="grid gap-2 text-sm"><span>قیمت پایه (تومان)</span><Input type="number" min={0} step={1000} value={plan.price} onChange={(event) => changePlan(plan.id, { price: Number(event.target.value) })} disabled={plan.code === "normal"} /></label>
          <label className="grid gap-2 text-sm"><span>مدت اعتبار (روز)</span><Input type="number" min={1} max={3650} value={plan.duration_days} onChange={(event) => changePlan(plan.id, { duration_days: Number(event.target.value) })} /></label>
          <label className="flex items-center justify-between rounded-xl bg-sky-50 p-3 text-sm"><span>فروش فعال باشد</span><input type="checkbox" className="size-4 accent-blue-600" checked={plan.is_active} disabled={plan.code === "normal"} onChange={(event) => changePlan(plan.id, { is_active: event.target.checked })} /></label>
          <Button className="w-full" onClick={() => void updatePlan(plan)}><Save /> ذخیره پلن</Button>
        </CardContent>
      </Card>)}
    </section>
    {message && <p className="rounded-xl bg-blue-50 p-3 text-sm text-blue-700">{message}</p>}

    <AdminTable title="اشتراک کاربران" subtitle="فعال‌سازی، لغو و پایش تاریخ اعتبار اشتراک‌ها" headers={["کاربر", "پلن", "بسته", "وضعیت", "شروع", "پایان", "عملیات"]}>
      {rows.map((row) => <tr key={row.id} className="border-t transition hover:bg-slate-50/70">
        <td className="p-4" dir="ltr">{row.email}</td>
        <td className="p-4 font-semibold">{row.plan}</td>
        <td className="p-4"><Badge variant="outline" className="capitalize">{row.package}</Badge></td>
        <td className="p-4"><Badge variant={row.status === "active" ? "default" : "secondary"}>{row.status}</Badge></td>
        <td className="p-4">{new Date(row.starts_at).toLocaleDateString("fa-IR")}</td>
        <td className="p-4">{new Date(row.ends_at).toLocaleDateString("fa-IR")}</td>
        <td className="p-4">{row.status === "active" ? <Button size="sm" variant="destructive" onClick={() => void updateSubscription(row.id, "cancelled")}><Ban /> لغو</Button> : <Button size="sm" variant="outline" onClick={() => void updateSubscription(row.id, "active")}><RotateCcw /> فعال‌سازی</Button>}</td>
      </tr>)}
    </AdminTable>
  </div>;
}
