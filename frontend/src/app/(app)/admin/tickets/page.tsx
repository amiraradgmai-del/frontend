"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { Headphones, Send } from "lucide-react";
import { api } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

type Message = { id: string; message: string; is_staff: boolean; created_at: string };
type Ticket = { id: string; user_id: string; subject: string; status: string; assigned_staff_id?: string; assigned_staff_name: string; messages: Message[]; updated_at: string };

export default function AdminSupportChatPage() {
  const [items, setItems] = useState<Ticket[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [text, setText] = useState("");
  const [error, setError] = useState("");
  const selected = items.find((item) => item.id === selectedId) ?? items[0];
  const load = useCallback(() => api<Ticket[]>("api/v1/admin/tickets").then((result) => { setItems(result); if (!selectedId && result[0]) setSelectedId(result[0].id); }), [selectedId]);

  useEffect(() => {
    void load().catch(() => setError("دریافت چت‌های پشتیبانی انجام نشد."));
    const timer = window.setInterval(() => void load(), 10000);
    return () => window.clearInterval(timer);
  }, [load]);

  async function send(event: FormEvent) {
    event.preventDefault();
    if (!selected || !text.trim()) return;
    try {
      await api(`api/v1/admin/tickets/${selected.id}/reply`, { method: "POST", body: JSON.stringify({ message: text }) });
      setText(""); await load();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "ارسال پاسخ انجام نشد."); }
  }

  return <div className="space-y-6"><header><p className="text-sm font-bold text-primary">مرکز پاسخ‌گویی ادمین</p><h1 className="mt-1 text-3xl font-black">چت‌های پشتیبانی</h1><p className="mt-2 text-muted-foreground">گفتگوهای شما در ابتدای فهرست قرار می‌گیرند؛ گفتگوهای بدون مسئول با اولین پاسخ به شما تخصیص داده می‌شوند.</p></header>{error && <p className="rounded-xl bg-rose-50 p-4 text-sm text-rose-700">{error}</p>}<div className="grid min-h-[40rem] gap-5 lg:grid-cols-[340px_1fr]"><aside className="space-y-2 overflow-y-auto">{items.map((item) => <button key={item.id} type="button" onClick={() => setSelectedId(item.id)} className={`w-full rounded-2xl border p-4 text-right ${selected?.id === item.id ? "border-blue-400 bg-blue-50" : "bg-white"}`}><div className="flex items-center justify-between gap-2"><p className="truncate font-bold">{item.subject}</p><Badge>{item.status === "answered" ? "پاسخ داده‌شده" : "در انتظار"}</Badge></div><p className="mt-2 text-xs text-slate-500">{item.assigned_staff_id ? `مسئول: ${item.assigned_staff_name}` : "بدون مسئول · قابل دریافت"}</p><p className="mt-1 text-[10px] text-slate-400">{new Date(item.updated_at).toLocaleString("fa-IR")}</p></button>)}</aside><Card className="flex min-h-[40rem] flex-col overflow-hidden"><CardHeader className="border-b"><CardTitle>{selected?.subject ?? "گفتگویی انتخاب نشده است"}</CardTitle></CardHeader><CardContent className="flex flex-1 flex-col p-0">{selected ? <><div className="flex-1 space-y-3 overflow-y-auto p-5">{selected.messages.map((message) => <div key={message.id} className={`w-fit max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-7 ${message.is_staff ? "ml-auto bg-blue-600 text-white" : "mr-auto bg-slate-100"}`}><p className="mb-1 text-[10px] opacity-60">{message.is_staff ? "پشتیبانی" : "کاربر"}</p>{message.message}<p className="mt-2 text-[10px] opacity-60">{new Date(message.created_at).toLocaleString("fa-IR")}</p></div>)}</div><form onSubmit={send} className="flex gap-2 border-t p-4"><Input value={text} onChange={(event) => setText(event.target.value)} placeholder="پاسخ پشتیبانی…" required /><Button type="submit"><Send /> ارسال</Button></form></> : <div className="flex flex-1 items-center justify-center text-slate-400"><Headphones className="size-12" /></div>}</CardContent></Card></div></div>;
}
