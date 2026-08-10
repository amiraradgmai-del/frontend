import type { Metadata } from "next";
import Link from "next/link";
import { Search } from "lucide-react";

import { PublicFooter } from "@/components/public-footer";
import { PublicHeader } from "@/components/public-header";

type Post = {
  slug: string;
  title: string;
  excerpt: string;
  cover_image_url: string;
  published_at: string | null;
  category: string;
};

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "مقاله‌ها و راهنماهای مالیاتی | چکاه",
  description: "مقاله‌ها، بخشنامه‌ها و راهنماهای کاربردی مالیاتی چکاه",
  alternates: { canonical: "/blog" },
};

export default async function BlogPage({ searchParams }: { searchParams: Promise<{ q?: string; category?: string }> }) {
  const { q = "", category = "" } = await searchParams;
  let posts: Post[] = [];
  try {
    const response = await fetch(`${process.env.BACKEND_URL ?? "http://localhost:8000"}/api/v1/site/content?page_type=post`, { cache: "no-store" });
    posts = response.ok ? await response.json() : [];
  } catch {
    posts = [];
  }

  const categories = [...new Set(posts.map((post) => post.category.trim()).filter(Boolean))].sort((a, b) => a.localeCompare(b, "fa"));
  const normalizedQuery = q.trim().toLocaleLowerCase("fa");
  const visiblePosts = posts.filter((post) => {
    const matchesCategory = !category || post.category === category;
    const matchesQuery = !normalizedQuery || `${post.title} ${post.excerpt} ${post.category}`.toLocaleLowerCase("fa").includes(normalizedQuery);
    return matchesCategory && matchesQuery;
  });

  return (
    <main dir="rtl" className="min-h-screen bg-slate-50 text-slate-900">
      <PublicHeader />
      <section className="border-b bg-gradient-to-l from-blue-950 via-blue-900 to-cyan-800 px-5 py-12 text-white">
        <div className="mx-auto max-w-7xl"><p className="text-sm font-bold text-cyan-200">دانشنامه چکاه</p><h1 className="mt-2 text-3xl font-black sm:text-4xl">مقاله‌ها و راهنماهای مالیاتی</h1><p className="mt-3 max-w-2xl text-sm leading-7 text-blue-100">مطالب تخصصی را جست‌وجو کنید یا از دسته‌بندی‌های موضوعی به مطلب موردنیازتان برسید.</p></div>
      </section>
      <section className="px-5 py-10">
        <div className="mx-auto grid max-w-7xl gap-8 lg:grid-cols-[minmax(0,1fr)_280px] lg:items-start">
          <div className="space-y-6">
            <div className="flex items-center justify-between border-b pb-4"><h2 className="text-xl font-black">{category || q ? "نتایج جست‌وجو" : "تازه‌ترین مقاله‌ها"}</h2><span className="text-sm text-slate-500">{visiblePosts.length.toLocaleString("fa-IR")} مطلب</span></div>
            {visiblePosts.map((post) => <article key={post.slug} className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm"><div className="grid md:grid-cols-[220px_1fr]">{post.cover_image_url ? <div className="min-h-48 bg-cover bg-center" style={{ backgroundImage: `url(${post.cover_image_url})` }} /> : <div className="min-h-48 bg-gradient-to-br from-blue-100 to-cyan-50" />}<div className="p-6"><p className="text-xs font-bold text-blue-600">{post.category || "مقاله"}</p><h2 className="mt-2 text-2xl font-black leading-10"><Link href={`/blog/${post.slug}`} className="hover:text-blue-700">{post.title}</Link></h2>{post.published_at && <time className="mt-2 block text-xs text-slate-400">انتشار در {new Date(post.published_at).toLocaleDateString("fa-IR")}</time>}<p className="mt-4 line-clamp-3 text-sm leading-7 text-slate-600">{post.excerpt}</p><Link href={`/blog/${post.slug}`} className="mt-5 inline-flex rounded-lg border border-orange-500 px-4 py-2 text-sm font-bold text-orange-600 transition hover:bg-orange-50">ادامه ←</Link></div></div></article>)}
            {!visiblePosts.length && <div className="rounded-2xl border border-dashed bg-white p-12 text-center text-slate-500">مقاله‌ای مطابق این جست‌وجو پیدا نشد.</div>}
          </div>
          <aside className="space-y-7 lg:sticky lg:top-24">
            <form action="/blog" className="flex overflow-hidden rounded-xl border bg-white shadow-sm"><input name="q" defaultValue={q} aria-label="جست‌وجوی مقاله" className="min-w-0 flex-1 px-4 outline-none" placeholder="جست‌وجو..." /><button className="grid size-12 shrink-0 place-items-center bg-orange-600 text-white" aria-label="جست‌وجو"><Search className="size-5" /></button></form>
            <nav className="rounded-2xl border bg-white p-5 shadow-sm" aria-label="دسته‌بندی مقاله‌ها"><h2 className="border-b pb-4 text-lg font-black">دسته‌ها</h2><div className="divide-y"><Link href="/blog" className={`block py-3 text-sm transition hover:text-blue-700 ${!category ? "font-black text-blue-700" : "text-slate-600"}`}>همه مقاله‌ها</Link>{categories.map((item) => <Link key={item} href={`/blog?category=${encodeURIComponent(item)}`} className={`block py-3 text-sm transition hover:text-blue-700 ${category === item ? "font-black text-blue-700" : "text-slate-600"}`}>{item}</Link>)}</div></nav>
          </aside>
        </div>
      </section>
      <PublicFooter />
    </main>
  );
}
