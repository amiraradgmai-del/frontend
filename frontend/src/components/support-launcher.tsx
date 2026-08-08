"use client";

import Link from "next/link";
import { useState } from "react";
import { ArrowLeft, Headphones, X } from "lucide-react";

export function SupportLauncher() {
  const [open, setOpen] = useState(false);

  return (
    <div className="fixed bottom-5 right-5 z-[200] size-14 sm:bottom-6 sm:right-6">
      {open && (
        <section className="absolute bottom-0 right-[calc(100%+0.75rem)] w-72 max-w-[calc(100vw-6rem)] overflow-hidden rounded-2xl border border-sky-200 bg-white shadow-2xl shadow-slate-900/20">
          <div className="bg-gradient-to-l from-blue-600 to-cyan-500 p-4 text-white">
            <div className="flex items-center justify-between">
              <span className="flex size-9 items-center justify-center rounded-xl bg-white/15">
                <Headphones className="size-5" />
              </span>
              <button type="button" onClick={() => setOpen(false)} className="rounded-lg bg-white/15 p-1.5" aria-label="بستن پنجره پشتیبانی">
                <X className="size-4" />
              </button>
            </div>
            <h2 className="mt-3 text-base font-black">پشتیبانی آنلاین چکاه</h2>
            <p className="mt-1 text-[11px] leading-5 text-blue-50">ارتباط با پشتیبانی رایگان است و درخواست شما به نزدیک‌ترین ادمین فعال ارجاع می‌شود.</p>
          </div>
          <div className="p-3">
            <div className="flex items-center gap-2 rounded-lg bg-emerald-50 p-2.5 text-[11px] text-emerald-700">
              <span className="size-2 animate-pulse rounded-full bg-emerald-500" />
              آماده پاسخ‌گویی
            </div>
            <Link href="/app/tickets" onClick={() => setOpen(false)} className="mt-2.5 flex items-center justify-center gap-2 rounded-xl bg-blue-600 px-3 py-2.5 text-xs font-bold text-white">
              شروع گفتگوی پشتیبانی <ArrowLeft className="size-3.5" />
            </Link>
          </div>
        </section>
      )}
      <div className="group relative size-14">
        <span className="pointer-events-none absolute bottom-full right-0 mb-2 whitespace-nowrap rounded-lg bg-slate-900 px-3 py-2 text-xs font-bold text-white opacity-0 shadow-lg transition group-hover:opacity-100 group-focus-within:opacity-100">
          ارتباط با پشتیبانی
        </span>
        <button type="button" onClick={() => setOpen((value) => !value)} className="flex size-14 items-center justify-center rounded-full bg-gradient-to-br from-blue-600 to-cyan-500 text-white shadow-lg shadow-blue-600/25 transition hover:scale-105" aria-expanded={open} aria-label="ارتباط با پشتیبانی">
          <Headphones className="size-6" />
        </button>
      </div>
    </div>
  );
}
