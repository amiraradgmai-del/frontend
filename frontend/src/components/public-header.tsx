import Link from "next/link";
import { cookies } from "next/headers";
import { accessCookie } from "@/lib/backend";
import { SiteBrand } from "@/components/site-theme-provider";

export async function PublicHeader() {
  const cookieStore = await cookies();
  const isLoggedIn = Boolean(cookieStore.get(accessCookie)?.value);
  const advisorsHref = "/advisors";
  return <header className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-5 py-6"><Link href="/" className="flex items-center gap-3 font-black"><SiteBrand /></Link><nav className="hidden items-center gap-6 text-sm md:flex"><Link href={advisorsHref} className="font-bold text-blue-700">لیست مشاوران</Link><Link href="/blog">مقاله‌ها</Link><Link href="/laws">قوانین مالیاتی</Link><Link href="/pricing">تعرفه‌ها</Link><Link href="/about">درباره ما</Link><Link href="/contact">تماس</Link></nav><div className="flex items-center gap-2"><Link href={advisorsHref} className="whitespace-nowrap rounded-lg border border-blue-200 px-3 py-2 text-xs font-bold text-blue-700 md:hidden">لیست مشاوران</Link><Link href={isLoggedIn ? "/app/dashboard" : "/login"} className="whitespace-nowrap rounded-lg bg-primary px-3 py-2 text-xs font-semibold text-primary-foreground sm:px-4 sm:text-sm">{isLoggedIn ? "ورود به پنل" : "ورود به سامانه"}</Link></div></header>;
}
