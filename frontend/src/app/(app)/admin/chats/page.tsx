"use client";

import { useEffect, useState } from "react";
import { Eye, LoaderCircle, Trash2, X } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AdminTable } from "@/components/admin-table";

type Row = { id: string; email: string; title: string; message_count: number; updated_at: string };
type Message = { id: string; role: "user" | "assistant"; content: string; created_at: string };

export default function ChatsPage() {
  const [rows, setRows] = useState<Row[]>([]);
  const [selected, setSelected] = useState<Row | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [busyId, setBusyId] = useState("");
  const [error, setError] = useState("");

  const load = () => api<Row[]>("api/v1/admin/chats").then(setRows);
  useEffect(() => { void load().catch((reason) => setError(reason instanceof Error ? reason.message : "دریافت گفتگوها انجام نشد.")); }, []);

  async function inspect(row: Row) {
    setError("");
    setBusyId(row.id);
    try {
      setMessages(await api<Message[]>(`api/v1/admin/chats/${row.id}`));
      setSelected(row);
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : "مشاهده گفتگو انجام نشد.");
    } finally {
      setBusyId("");
    }
  }

  async function remove(row: Row) {
    if (!window.confirm(`گفتگوی «${row.title}» حذف شود؟`)) return;
    setError("");
    setBusyId(row.id);
    try {
      await api(`api/v1/admin/chats/${row.id}`, { method: "DELETE" });
      if (selected?.id === row.id) setSelected(null);
      await load();
    } catch (reason) {
      setError(reason instanceof ApiError ? reason.message : "حذف گفتگو انجام نشد.");
    } finally {
      setBusyId("");
    }
  }

  return <div className="space-y-6">
    {error && <p role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{error}</p>}
    <AdminTable title="نظارت گفتگوها" subtitle="مشاهده گفتگوها و حذف محتوای نامناسب" headers={["کاربر", "عنوان گفتگو", "پیام", "آخرین فعالیت", "عملیات"]}>
      {rows.map((row) => <tr key={row.id} className="border-t"><td className="p-4" dir="ltr">{row.email}</td><td className="p-4 font-medium">{row.title}</td><td className="p-4">{row.message_count.toLocaleString("fa-IR")}</td><td className="p-4">{new Date(row.updated_at).toLocaleString("fa-IR")}</td><td className="p-4"><div className="flex gap-2"><Button size="sm" variant="outline" disabled={busyId === row.id} onClick={() => void inspect(row)}>{busyId === row.id ? <LoaderCircle className="animate-spin" /> : <Eye />} مشاهده</Button><Button size="icon-sm" variant="destructive" title="حذف گفتگو" disabled={busyId === row.id} onClick={() => void remove(row)}><Trash2 /></Button></div></td></tr>)}
    </AdminTable>
    {selected && <div className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-950/45 p-4 backdrop-blur-sm" onClick={() => setSelected(null)}><Card className="max-h-[85vh] w-full max-w-3xl overflow-hidden border-primary/20 bg-white shadow-2xl" onClick={(event) => event.stopPropagation()}><CardHeader><div className="flex items-center justify-between"><div><CardTitle>{selected.title}</CardTitle><p className="mt-1 text-xs text-muted-foreground" dir="ltr">{selected.email}</p></div><Button size="icon" variant="ghost" onClick={() => setSelected(null)}><X /></Button></div></CardHeader><CardContent className="max-h-[68vh] space-y-3 overflow-y-auto">{messages.length ? messages.map((message) => <div key={message.id} className={`max-w-[85%] rounded-2xl p-4 text-sm leading-7 ${message.role === "user" ? "mr-auto bg-slate-100" : "ml-auto bg-primary/10 text-slate-800"}`}><p>{message.content}</p><p className="mt-2 text-[10px] text-muted-foreground">{message.role === "user" ? "کاربر" : "دستیار"} · {new Date(message.created_at).toLocaleString("fa-IR")}</p></div>) : <p className="py-12 text-center text-muted-foreground">این گفتگو پیامی ندارد.</p>}</CardContent></Card></div>}
  </div>;
}
