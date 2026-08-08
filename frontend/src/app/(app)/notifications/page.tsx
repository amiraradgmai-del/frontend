"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Bell, CheckCheck } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

type Notification = { id: string; title: string; message: string; type: string; action_url: string; is_read: boolean; created_at: string };

export default function NotificationsPage() {
  const [items, setItems] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    setError("");
    try {
      const data = await api<{ items: Notification[] }>("api/v1/notifications");
      setItems(data.items);
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : "دریافت اعلان‌ها انجام نشد.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    let active = true;
    api<{ items: Notification[] }>("api/v1/notifications")
      .then((data) => { if (active) setItems(data.items); })
      .catch((reason) => { if (active) setError(reason instanceof ApiError ? reason.message : "دریافت اعلان‌ها انجام نشد."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);
  async function readAll() { await api("api/v1/notifications/read-all", { method: "POST" }); await load(); }
  async function read(item: Notification) { if (!item.is_read) await api(`api/v1/notifications/${item.id}/read`, { method: "PATCH" }); }

  return <div className="space-y-6">
    <header className="flex flex-wrap items-end justify-between gap-3"><div><p className="text-sm font-bold text-blue-600">مرکز اطلاع‌رسانی</p><h1 className="mt-1 text-3xl font-black">اعلان‌های من</h1></div><Button variant="outline" onClick={() => void readAll()} disabled={loading || !items.length}><CheckCheck /> خواندن همه</Button></header>
    {error && <p className="rounded-xl bg-rose-50 p-4 text-sm text-rose-700">{error}</p>}
    <section className="space-y-3">{items.map((item) => <Card key={item.id} className={item.is_read ? "opacity-70" : "border-blue-200 bg-blue-50/30"}><CardContent className="flex gap-4 p-5"><Bell className="mt-1 size-5 shrink-0 text-blue-600" /><div className="flex-1"><p className="font-bold">{item.title}</p><p className="mt-1 text-sm leading-7 text-slate-600">{item.message}</p><p className="mt-2 text-xs text-slate-400">{new Date(item.created_at).toLocaleString("fa-IR")}</p>{item.action_url && <Link href={item.action_url} onClick={() => void read(item)} className="mt-3 inline-block text-sm font-bold text-blue-600">مشاهده</Link>}</div></CardContent></Card>)}
      {!loading && !items.length && !error && <div className="rounded-2xl border border-dashed p-12 text-center text-slate-500">اعلانی ندارید.</div>}
      {loading && <div className="p-12 text-center text-sm text-slate-500">در حال دریافت اعلان‌ها…</div>}
    </section>
  </div>;
}
