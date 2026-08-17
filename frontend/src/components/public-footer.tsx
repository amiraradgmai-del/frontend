import Link from "next/link";

export function PublicFooter() {
  return <footer className="mt-20 border-t bg-white/70"><div className="mx-auto flex max-w-6xl flex-col gap-4 px-5 py-8 text-sm text-slate-500 sm:flex-row sm:items-center sm:justify-between"><p>© چکاه؛ دستیار هوشمند مالیاتی ایران</p><div className="flex flex-wrap gap-4"><Link href="/about" className="hover:text-blue-600">درباره ما</Link><Link href="/contact" className="hover:text-blue-600">تماس با ما</Link><Link href="/pricing" className="hover:text-blue-600">پلن‌ها</Link><Link href="/privacy" className="hover:text-blue-600">حریم خصوصی</Link><Link href="/terms" className="hover:text-blue-600">شرایط استفاده</Link></div></div></footer>;
}
