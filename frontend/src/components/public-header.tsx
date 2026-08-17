import Link from "next/link";
import { cookies } from "next/headers";
import { Menu } from "lucide-react";
import { SiteBrand } from "@/components/site-theme-provider";
import { ArticleDropdown } from "@/components/article-dropdown";
import { accessCookie, refreshCookie } from "@/lib/backend";

const links = [
  { href: "/advisors", label: "لیست مشاوران", primary: true },
  { href: "/app/laws", label: "قوانین مالیاتی" },
  { href: "/pricing", label: "تعرفه‌ها" },
  { href: "/about", label: "درباره ما" },
  { href: "/contact", label: "تماس" },
];

export async function PublicHeader({ showBrandDescription = false }: { showBrandDescription?: boolean }) {
  const store = await cookies();
  const isLoggedIn = store.has(accessCookie) || store.has(refreshCookie);
  return <header className="sticky top-0 z-40 border-b border-sky-100 bg-white/95 shadow-sm backdrop-blur">
    <div className="mx-auto flex min-h-20 max-w-6xl items-center justify-between gap-3 px-5">
      <SiteBrand showDescription={showBrandDescription} />
      <nav className="hidden items-center gap-5 text-sm font-bold text-slate-700 lg:flex">
        {links.slice(0, 1).map((item) => <Link key={item.href} href={item.href} className="text-blue-700 transition hover:text-blue-500">{item.label}</Link>)}
        <ArticleDropdown />
        {links.slice(1).map((item) => <Link key={item.href} href={item.href} className="transition hover:text-blue-600">{item.label}</Link>)}
      </nav>
      <div className="flex items-center gap-2">
        <Link href={isLoggedIn ? "/app/dashboard" : "/login"} className="whitespace-nowrap rounded-xl bg-primary px-3 py-2.5 text-xs font-bold text-primary-foreground sm:px-4 sm:text-sm">{isLoggedIn ? "بازگشت به پنل" : "ورود به سامانه"}</Link>
        <details className="relative lg:hidden"><summary aria-label="بازکردن منو" className="flex size-10 cursor-pointer list-none items-center justify-center rounded-xl border border-sky-200 text-blue-700"><Menu className="size-5" /></summary><nav className="absolute left-0 top-12 z-50 w-56 space-y-1 rounded-2xl border border-sky-100 bg-white p-3 text-sm font-bold shadow-xl">{links.map((item) => <Link key={item.href} href={item.href} className="block rounded-xl px-3 py-2.5 hover:bg-blue-50 hover:text-blue-700">{item.label}</Link>)}<Link href="/blog" className="block rounded-xl px-3 py-2.5 hover:bg-blue-50 hover:text-blue-700">مقاله‌ها</Link></nav></details>
      </div>
    </div>
  </header>;
}
