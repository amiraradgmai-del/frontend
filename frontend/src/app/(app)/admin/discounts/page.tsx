"use client";

import { FormEvent, useEffect, useState } from "react";
import { Plus, Power } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

type Discount = { id: string; code: string; percent: number; max_uses: number; used_count: number; is_active: boolean };

export default function DiscountsPage() {
  const [items, setItems] = useState<Discount[]>([]);
  const [message, setMessage] = useState("");
  const [code, setCode] = useState("");
  const [percent, setPercent] = useState("");
  const [maxUses, setMaxUses] = useState("");
  const load = () => api<Discount[]>("api/v1/admin/discounts").then(setItems);
  useEffect(() => { void load(); }, []);

  async function create(event: FormEvent) {
    event.preventDefault(); setMessage("");
    try {
      await api("api/v1/admin/discounts", { method: "POST", body: JSON.stringify({ code, percent: Number(percent), max_uses: Number(maxUses), is_active: true }) });
      setCode(""); setPercent(""); setMaxUses(""); setMessage("کد تخفیف ساخته شد."); await load();
    } catch (error) { setMessage(error instanceof ApiError ? error.message : "ساخت کد انجام نشد."); }
  }

  async function toggle(item: Discount) {
    await api(`api/v1/admin/discounts/${item.id}`, { method: "PATCH", body: JSON.stringify({ is_active: !item.is_active }) });
    await load();
  }

  return <div className="space-y-6">
    <header><p className="text-sm font-medium text-primary">فروش و بازاریابی</p><h1 className="mt-1 text-3xl font-black">کدهای تخفیف</h1><p className="mt-2 text-muted-foreground">ساخت، توقف و بررسی میزان استفاده از تخفیف‌ها</p></header>
    <Card className="border-white/70 bg-white/85"><CardHeader><CardTitle className="text-lg">کد جدید</CardTitle></CardHeader><CardContent>
      <form onSubmit={create} className="grid gap-3 md:grid-cols-[1.4fr_.7fr_.7fr_auto]">
        <Input value={code} onChange={(event) => setCode(event.target.value.toUpperCase())} placeholder="مثلاً SUMMER25" dir="ltr" required />
        <Input value={percent} onChange={(event) => setPercent(event.target.value)} type="number" min="1" max="100" placeholder="درصد" required />
        <Input value={maxUses} onChange={(event) => setMaxUses(event.target.value)} type="number" min="1" placeholder="تعداد استفاده" required />
        <Button><Plus /> ساخت کد</Button>
      </form>{message && <p className="mt-3 text-sm text-primary">{message}</p>}
    </CardContent></Card>
    <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{items.map((item) => <Card key={item.id} className="overflow-hidden border-white/70 bg-white/90"><CardContent className="p-5">
      <div className="flex items-center justify-between"><code className="rounded-lg bg-slate-950 px-3 py-1.5 font-bold text-teal-300">{item.code}</code><Badge variant={item.is_active ? "default" : "secondary"}>{item.is_active ? "فعال" : "متوقف"}</Badge></div>
      <p className="mt-5 text-3xl font-black text-slate-900">{item.percent.toLocaleString("fa-IR")}٪</p><p className="text-sm text-muted-foreground">تخفیف روی خرید اشتراک</p>
      <div className="mt-5 h-2 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-primary" style={{ width: `${Math.min(100, item.used_count / item.max_uses * 100)}%` }} /></div>
      <div className="mt-2 flex justify-between text-xs text-muted-foreground"><span>{item.used_count.toLocaleString("fa-IR")} استفاده</span><span>سقف {item.max_uses.toLocaleString("fa-IR")}</span></div>
      <Button className="mt-5 w-full" variant="outline" onClick={() => toggle(item)}><Power /> {item.is_active ? "توقف کد" : "فعال‌سازی"}</Button>
    </CardContent></Card>)}</section>
  </div>;
}
