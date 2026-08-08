"use client";

import { AlertCircle, CheckCircle2, Info, X } from "lucide-react";

import { Button } from "@/components/ui/button";

type FeedbackKind = "error" | "success" | "info";

export function FormFeedbackDialog({
  open,
  title,
  message,
  kind = "error",
  onClose,
}: {
  open: boolean;
  title: string;
  message: string;
  kind?: FeedbackKind;
  onClose: () => void;
}) {
  if (!open) return null;

  const Icon = kind === "success" ? CheckCircle2 : kind === "info" ? Info : AlertCircle;
  const tone = kind === "success"
    ? "bg-emerald-100 text-emerald-700"
    : kind === "info"
      ? "bg-blue-100 text-blue-700"
      : "bg-rose-100 text-rose-700";

  return (
    <div className="fixed inset-0 z-[300] flex items-center justify-center bg-slate-950/40 p-4 backdrop-blur-sm" role="dialog" aria-modal="true" aria-labelledby="feedback-title">
      <button type="button" className="absolute inset-0" aria-label="بستن پیام" onClick={onClose} />
      <section className="relative w-full max-w-md rounded-3xl border border-white/70 bg-white p-6 shadow-2xl">
        <button type="button" onClick={onClose} className="absolute left-4 top-4 rounded-xl p-2 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700" aria-label="بستن">
          <X className="size-5" />
        </button>
        <span className={`flex size-12 items-center justify-center rounded-2xl ${tone}`}>
          <Icon className="size-6" />
        </span>
        <h2 id="feedback-title" className="mt-4 text-lg font-black text-slate-900">{title}</h2>
        <p className="mt-2 text-sm leading-7 text-slate-600">{message}</p>
        <Button type="button" className="mt-5 w-full" onClick={onClose}>متوجه شدم</Button>
      </section>
    </div>
  );
}
