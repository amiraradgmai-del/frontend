"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowLeft, History, MessageSquareText } from "lucide-react";
import { api } from "@/lib/api";
import type { Conversation } from "@/lib/types";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export default function HistoryPage() {
  const [items, setItems] = useState<Conversation[] | null>(null);
  useEffect(() => { api<Conversation[]>("api/v1/conversations").then(setItems).catch(() => setItems([])); }, []);
  return <div className="space-y-7"><header><p className="text-sm font-medium text-primary">آرشیو شخصی</p><h1 className="mt-1 text-3xl font-black">تاریخچه گفت‌وگوها</h1><p className="mt-2 text-muted-foreground">تمام پرسش‌ها و پاسخ‌های قبلی شما</p></header><div className="space-y-3">{items === null ? [1,2,3].map((item) => <Skeleton key={item} className="h-24 rounded-2xl" />) : items.length ? items.map((item) => <Link href={`/chat?conversation=${item.id}`} key={item.id}><Card className="mb-3 border-white/70 bg-white/80 transition hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-lg"><CardContent className="flex items-center gap-4 p-5"><div className="flex size-11 items-center justify-center rounded-xl bg-primary/10 text-primary"><MessageSquareText /></div><div className="min-w-0 flex-1"><p className="truncate font-semibold">{item.title}</p><p className="mt-1 text-xs text-muted-foreground">آخرین بروزرسانی {new Date(item.updated_at).toLocaleString("fa-IR")}</p></div><ArrowLeft className="size-4 text-muted-foreground" /></CardContent></Card></Link>) : <div className="rounded-2xl border border-dashed bg-white/50 p-14 text-center"><History className="mx-auto mb-3 text-muted-foreground" /><p>هنوز گفت‌وگویی ثبت نشده است.</p></div>}</div></div>;
}
