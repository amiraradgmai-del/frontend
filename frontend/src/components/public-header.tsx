import Link from "next/link";
import { cookies } from "next/headers";
import { SiteBrand } from "@/components/site-theme-provider";
import { ArticleDropdown } from "@/components/article-dropdown";
import { accessCookie } from "@/lib/backend";

export async function PublicHeader({
  showBrandDescription = false,
}: {
  showBrandDescription?: boolean;
}) {
  const isLoggedIn = Boolean((await cookies()).get(accessCookie)?.value);
  return (
    <header className="border-b border-sky-100 bg-white">
      <div className="mx-auto flex h-20 max-w-6xl items-center justify-between gap-3 px-5">
        <SiteBrand showDescription={showBrandDescription} />
        <nav className="hidden items-center gap-6 text-sm md:flex">
          <Link href="/advisors" className="font-bold text-blue-700">
            لیست مشاوران
          </Link>
          <ArticleDropdown />
          <Link href="/laws">قوانین مالیاتی</Link>
          <Link href="/pricing">تعرفه‌ها</Link>
          <Link href="/about">درباره ما</Link>
          <Link href="/contact">تماس</Link>
        </nav>
        <div className="flex items-center gap-2">
          <Link
            href="/advisors"
            className="whitespace-nowrap rounded-lg border border-blue-200 px-3 py-2 text-xs font-bold text-blue-700 md:hidden"
          >
            مشاوران
          </Link>
          <Link
            href={isLoggedIn ? "/app/dashboard" : "/login"}
            className="whitespace-nowrap rounded-lg bg-primary px-3 py-2 text-xs font-semibold text-primary-foreground sm:px-4 sm:text-sm"
          >
            {isLoggedIn ? "ورود به پنل" : "ورود به سامانه"}
          </Link>
        </div>
      </div>
    </header>
  );
}
