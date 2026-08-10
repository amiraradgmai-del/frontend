"use client";

import type { FormEvent } from "react";
import { useEffect, useState } from "react";
import { BellRing, CalendarCheck2, Check, Plus, Trash2 } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { PersianDateInput } from "@/components/persian-date-input";

type Reminder = {
  id: string;
  title: string;
  description: string;
  due_date: string;
  category: string;
  is_done: boolean;
  notify_days_before: number;
};
type Template = { title: string; category: string; description: string };

export default function CalendarPage() {
  const [reminders, setReminders] = useState<Reminder[]>([]);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [message, setMessage] = useState("");
  const load = () =>
    api<{ reminders: Reminder[]; templates: Template[] }>(
      "api/v1/tools/calendar",
    ).then((data) => {
      setReminders(data.reminders);
      setTemplates(data.templates);
    });
  useEffect(() => {
    void load();
  }, []);
  async function create(event: FormEvent) {
    event.preventDefault();
    setMessage("");
    try {
      await api("api/v1/tools/reminders", {
        method: "POST",
        body: JSON.stringify({
          title,
          description,
          due_date: dueDate,
          category: "general",
          notify_days_before: 3,
        }),
      });
      setTitle("");
      setDescription("");
      setDueDate("");
      await load();
    } catch (error) {
      setMessage(
        error instanceof ApiError ? error.message : "ثبت یادآور انجام نشد.",
      );
    }
  }
  async function toggle(item: Reminder) {
    await api(`api/v1/tools/reminders/${item.id}`, {
      method: "PATCH",
      body: JSON.stringify({ is_done: !item.is_done }),
    });
    await load();
  }
  async function remove(id: string) {
    await api(`api/v1/tools/reminders/${id}`, { method: "DELETE" });
    await load();
  }
  return (
    <div className="space-y-7">
      <header className="relative overflow-hidden rounded-3xl bg-slate-950 p-8 text-white">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_15%_15%,rgba(20,184,166,.3),transparent_35%)]" />
        <div className="relative">
          <p className="text-sm text-teal-300">مدیریت سررسیدها</p>
          <h1 className="mt-2 text-3xl font-black">تقویم مالیاتی و اعلان‌ها</h1>
          <p className="mt-3 text-slate-400">
            مهلت‌های شخصی را ثبت کنید تا پیش از سررسید به شما یادآوری شود.
          </p>
        </div>
      </header>
      <div className="grid gap-6 lg:grid-cols-[.72fr_1.28fr]">
        <Card className="h-fit border-white/70 bg-white/85">
          <CardHeader>
            <CardTitle className="flex gap-2">
              <Plus className="text-primary" /> یادآور جدید
            </CardTitle>
            <CardDescription>
              تاریخ دقیق را مطابق آخرین ابلاغ و وضعیت پرونده وارد کنید.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={create} className="space-y-3">
              <Input
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                placeholder="عنوان تکلیف"
                required
              />
              <Textarea
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                placeholder="توضیحات اختیاری"
              />
                <PersianDateInput value={dueDate} onChange={setDueDate} required />
              <Button className="w-full">
                <BellRing /> ثبت و فعال‌سازی اعلان
              </Button>
            </form>
            {message && <p className="mt-3 text-sm text-red-600">{message}</p>}
            <div className="mt-6 space-y-2">
              <p className="text-xs font-semibold text-muted-foreground">
                قالب‌های پیشنهادی
              </p>
              {templates.map((item) => (
                <button
                  key={item.title}
                  onClick={() => {
                    setTitle(item.title);
                    setDescription(item.description);
                  }}
                  className="w-full rounded-xl border p-3 text-right text-xs transition hover:border-primary/30 hover:bg-primary/5"
                >
                  {item.title}
                </button>
              ))}
            </div>
          </CardContent>
        </Card>
        <section className="space-y-3">
          {reminders.map((item) => (
            <Card
              key={item.id}
              className={`border-white/70 bg-white/85 ${item.is_done ? "opacity-60" : ""}`}
            >
              <CardContent className="flex items-center gap-4 p-5">
                <button
                  onClick={() => toggle(item)}
                  className={`flex size-11 shrink-0 items-center justify-center rounded-2xl ${item.is_done ? "bg-emerald-100 text-emerald-600" : "bg-primary/10 text-primary"}`}
                >
                  {item.is_done ? <Check /> : <CalendarCheck2 />}
                </button>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="font-semibold">{item.title}</p>
                    <Badge variant="outline">
                      {new Date(item.due_date).toLocaleDateString("fa-IR")}
                    </Badge>
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {item.description}
                  </p>
                </div>
                <Button
                  size="icon"
                  variant="ghost"
                  onClick={() => remove(item.id)}
                >
                  <Trash2 />
                </Button>
              </CardContent>
            </Card>
          ))}
          {!reminders.length && (
            <div className="rounded-2xl border border-dashed p-14 text-center text-muted-foreground">
              هنوز یادآوری ثبت نشده است.
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
