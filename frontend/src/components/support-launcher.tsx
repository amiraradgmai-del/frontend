"use client";

import Link from "next/link";
import { useState } from "react";
import { ArrowLeft, Headphones, X } from "lucide-react";

export function SupportLauncher() {
  const [open, setOpen] = useState(false);
  const [answer, setAnswer] = useState("");
  const faq = [
    ["خرید اشتراک", "از بخش اشتراک و پرداخت، پلن مناسب را انتخاب کنید؛ اشتراک پس از پرداخت موفق خودکار فعال می‌شود."],
    ["پرداخت ناموفق", "اگر وجه کسر شده، شماره پیگیری و زمان پرداخت را بفرستید؛ برگشت بانکی معمولاً تا ۷۲ ساعت کاری است."],
    ["ارسال فایل", "از بخش اسناد من یا دکمه پیوست داخل گفتگوی پشتیبانی استفاده کنید."],
    ["رزرو مشاور", "در لیست مشاوران، مشاور و زمان آزاد را انتخاب و رزرو را نهایی کنید."],
  ];

  return (
    <div className="fixed bottom-5 right-5 z-[200] size-14 sm:bottom-6 sm:right-6">
      {open && (
        <section className="absolute bottom-0 right-[calc(100%+0.75rem)] w-72 max-w-[calc(100vw-6rem)] overflow-hidden rounded-2xl border border-sky-200 bg-white shadow-2xl shadow-slate-900/20">
          <div className="bg-gradient-to-l from-blue-600 to-cyan-500 p-4 text-white">
            <div className="flex items-center justify-between">
              <span className="flex size-9 items-center justify-center rounded-xl bg-white/15">
                <Headphones className="size-5" />
              </span>
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="rounded-lg bg-white/15 p-1.5"
                aria-label="بستن پنجره پشتیبانی"
              >
                <X className="size-4" />
              </button>
            </div>
            <h2 className="mt-3 text-base font-black">پشتیبانی آنلاین چکاه</h2>
            <p className="mt-1 text-[11px] leading-5 text-blue-50">
              پرسش‌های پرتکرار فوری پاسخ داده می‌شوند؛ درخواست‌های دیگر برای
              تیم پشتیبانی ثبت خواهند شد.
            </p>
          </div>
          <div className="p-3">
            <div className="flex items-center gap-2 rounded-lg bg-emerald-50 p-2.5 text-[11px] text-emerald-700">
              <span className="size-2 animate-pulse rounded-full bg-emerald-500" />
              آماده پاسخ‌گویی
            </div>
            <div className="mt-2 grid grid-cols-2 gap-1.5">
              {faq.map(([question, response]) => <button key={question} type="button" onClick={() => setAnswer(response)} className="rounded-lg border border-sky-100 bg-sky-50 px-2 py-2 text-[10px] font-bold text-blue-700">{question}</button>)}
            </div>
            {answer && <p className="mt-2 rounded-lg bg-slate-50 p-2.5 text-[11px] leading-5 text-slate-700">{answer}</p>}
            <Link
              href="/app/tickets"
              onClick={() => setOpen(false)}
              className="mt-2.5 flex items-center justify-center gap-2 rounded-xl bg-blue-600 px-3 py-2.5 text-xs font-bold text-white"
            >
              شروع گفتگوی پشتیبانی <ArrowLeft className="size-3.5" />
            </Link>
          </div>
        </section>
      )}
      <div className="group relative size-14">
        <span className="pointer-events-none absolute bottom-full right-0 mb-2 whitespace-nowrap rounded-lg bg-slate-900 px-3 py-2 text-xs font-bold text-white opacity-0 shadow-lg transition group-hover:opacity-100 group-focus-within:opacity-100">
          ارتباط با پشتیبانی
        </span>
        <button
          type="button"
          onClick={() => setOpen((value) => !value)}
          className="flex size-14 items-center justify-center rounded-full bg-gradient-to-br from-blue-600 to-cyan-500 text-white shadow-lg shadow-blue-600/25 transition hover:scale-105"
          aria-expanded={open}
          aria-label="ارتباط با پشتیبانی"
        >
          <Headphones className="size-6" />
        </button>
      </div>
    </div>
  );
}
