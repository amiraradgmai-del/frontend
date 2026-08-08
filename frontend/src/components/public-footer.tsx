import Link from "next/link";

export function PublicFooter() {
  return <footer className="mt-20 border-t bg-white/60"><div className="mx-auto flex max-w-6xl flex-col gap-4 px-5 py-8 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between"><p>© دستیار هوشمند مالیاتی ایران</p><div className="flex flex-wrap gap-4"><Link href="/about">درباره ما</Link><Link href="/contact">تماس با ما</Link><Link href="/pricing">پلن‌ها</Link><Link href="/privacy">حریم خصوصی</Link><Link href="/terms">شرایط استفاده</Link></div></div></footer>;
}
