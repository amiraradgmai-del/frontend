import Link from "next/link";
import { cookies } from "next/headers";
import { ChevronDown, Menu, ShieldCheck } from "lucide-react";
import { SiteBrand } from "@/components/site-theme-provider";
import { ArticleDropdown } from "@/components/article-dropdown";
import { accessCookie, refreshCookie } from "@/lib/backend";

const links = [
  { href: "/advisors", label: "مشاوران" },
  { href: "/app/laws", label: "مرکز قوانین" },
  { href: "/pricing", label: "تعرفه‌ها" },
  { href: "/about", label: "درباره ما" },
  { href: "/contact", label: "تماس با ما" },
];

export async function PublicHeader({
  showBrandDescription = false,
}: {
  showBrandDescription?: boolean;
}) {
  const store = await cookies();
  const isLoggedIn = store.has(accessCookie) || store.has(refreshCookie);
  return (
    <header className="sticky top-0 z-40 border-b border-blue-100/80 bg-white/90 shadow-[0_10px_35px_-28px_rgba(15,23,42,.55)] backdrop-blur-xl">
      <div className="mx-auto flex min-h-[76px] max-w-7xl items-center justify-between gap-4 px-4 sm:px-6">
        <SiteBrand showDescription={showBrandDescription} />
        <nav className="hidden items-center gap-1 rounded-2xl border border-blue-100 bg-blue-50/55 p-1.5 text-sm font-bold text-slate-700 lg:flex">
          {links.slice(0, 1).map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="rounded-xl px-3.5 py-2.5 transition hover:bg-white hover:text-blue-700"
            >
              {item.label}
            </Link>
          ))}
          <ArticleDropdown />
          {links.slice(1).map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="rounded-xl px-3.5 py-2.5 transition hover:bg-white hover:text-blue-700"
            >
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="flex items-center gap-2">
          <Link
            href={isLoggedIn ? "/app/dashboard" : "/login"}
            className="inline-flex min-h-11 items-center gap-2 whitespace-nowrap rounded-xl bg-gradient-to-l from-blue-700 to-blue-500 px-4 text-sm font-black text-white shadow-lg shadow-blue-600/20 transition hover:-translate-y-0.5"
          >
            <ShieldCheck className="size-4" />
            {isLoggedIn ? "ورود به پنل" : "ورود و ثبت‌نام"}
          </Link>
          <details className="group relative lg:hidden">
            <summary
              aria-label="بازکردن منو"
              className="flex size-11 cursor-pointer list-none items-center justify-center rounded-xl border border-blue-200 bg-white text-blue-700"
            >
              <Menu className="size-5" />
            </summary>
            <nav className="absolute left-0 top-14 z-50 w-64 rounded-2xl border border-blue-100 bg-white p-2 text-sm font-bold shadow-2xl">
              <Link
                href="/blog"
                className="flex items-center justify-between rounded-xl px-4 py-3 hover:bg-blue-50"
              >
                مقاله‌ها <ChevronDown className="size-4" />
              </Link>
              {links.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className="block rounded-xl px-4 py-3 hover:bg-blue-50 hover:text-blue-700"
                >
                  {item.label}
                </Link>
              ))}
            </nav>
          </details>
        </div>
      </div>
    </header>
  );
}
