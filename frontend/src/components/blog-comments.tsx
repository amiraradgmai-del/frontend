"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

type Comment = { id: string; full_name: string; message: string; created_at: string };
export function BlogComments({ slug }: { slug: string }) {
  const [items, setItems] = useState<Comment[]>([]);
  const [message, setMessage] = useState("");
  const [notice, setNotice] = useState("");
  const load = useCallback(() => api<Comment[]>(`api/v1/site/content/${slug}/comments`).then(setItems), [slug]);
  useEffect(() => { void load(); }, [load]);
  async function submit(event: FormEvent) {
    event.preventDefault();
    try { await api(`api/v1/site/content/${slug}/comments`, { method: "POST", body: JSON.stringify({ message }) }); setMessage(""); setNotice("نظر شما ثبت شد و پس از تأیید نمایش داده می‌شود."); }
    catch (error) { setNotice(error instanceof Error ? error.message : "ثبت نظر انجام نشد."); }
  }
  return <section className="mt-10 border-t pt-8"><h2 className="text-2xl font-black">نظرات کاربران</h2><form onSubmit={submit} className="mt-5 space-y-3"><Textarea value={message} onChange={(e) => setMessage(e.target.value)} minLength={3} required placeholder="نظر خود را بنویسید..." /><Button>ارسال نظر</Button></form>{notice && <p className="mt-3 rounded-xl bg-sky-50 p-3 text-sm">{notice}</p>}<div className="mt-6 space-y-3">{items.map((item) => <article key={item.id} className="rounded-2xl bg-slate-50 p-4"><p className="font-bold">{item.full_name}</p><p className="mt-2 text-sm leading-7 text-slate-600">{item.message}</p></article>)}</div></section>;
}
