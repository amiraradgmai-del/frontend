import Link from "next/link";
import { BookOpen, Headphones, Scale, ShieldCheck } from "lucide-react";

const groups = [
  {
    title: "خدمات چکاه",
    links: [
      ["دستیار هوشمند", "/app/chat"],
      ["مرکز قوانین", "/app/laws"],
      ["ابزارهای مالیاتی", "/app/tools"],
      ["مشاوران", "/advisors"],
    ],
  },
  {
    title: "راهنما",
    links: [
      ["تعرفه‌ها", "/pricing"],
      ["مقاله‌ها", "/blog"],
      ["درباره ما", "/about"],
      ["تماس با ما", "/contact"],
    ],
  },
  {
    title: "قوانین",
    links: [
      ["حریم خصوصی", "/privacy"],
      ["شرایط استفاده", "/terms"],
      ["پشتیبانی", "/app/tickets"],
      ["امنیت حساب", "/app/security"],
    ],
  },
];

export function PublicFooter() {
  return (
    <footer className="mt-20 overflow-hidden border-t border-blue-100 bg-slate-950 text-slate-300">
      <div className="mx-auto grid max-w-7xl gap-10 px-5 py-14 lg:grid-cols-[1.3fr_2fr]">
        <div>
          <div className="flex items-center gap-3">
            <div className="flex size-12 items-center justify-center rounded-2xl bg-blue-600">
              <Scale />
            </div>
            <div>
              <p className="text-xl font-black text-white">چکاه</p>
              <p className="text-xs text-blue-200">
                دستیار هوشمند و همراه مالیاتی شما
              </p>
            </div>
          </div>
          <p className="mt-5 max-w-md text-sm leading-8 text-slate-400">
            قوانین، ابزارهای کاربردی، تحلیل اسناد و ارتباط با مشاور مالیاتی در
            یک فضای امن، شفاف و یکپارچه.
          </p>
          <div className="mt-6 flex flex-wrap gap-2 text-xs">
            <span className="flex items-center gap-2 rounded-xl bg-white/5 px-3 py-2">
              <ShieldCheck className="size-4 text-cyan-400" />
              حفاظت از داده
            </span>
            <span className="flex items-center gap-2 rounded-xl bg-white/5 px-3 py-2">
              <BookOpen className="size-4 text-cyan-400" />
              پاسخ مستند
            </span>
            <span className="flex items-center gap-2 rounded-xl bg-white/5 px-3 py-2">
              <Headphones className="size-4 text-cyan-400" />
              پشتیبانی تخصصی
            </span>
          </div>
        </div>
        <div className="grid gap-8 sm:grid-cols-3">
          {groups.map((group) => (
            <div key={group.title}>
              <p className="font-black text-white">{group.title}</p>
              <div className="mt-5 grid gap-3 text-sm text-slate-400">
                {group.links.map(([label, href]) => (
                  <Link
                    key={href}
                    href={href}
                    className="transition hover:text-cyan-300"
                  >
                    {label}
                  </Link>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
      <div className="border-t border-white/10 px-5 py-5 text-center text-xs text-slate-500">
        © {new Date().getFullYear()} چکاه؛ همه حقوق محفوظ است.
      </div>
    </footer>
  );
}
