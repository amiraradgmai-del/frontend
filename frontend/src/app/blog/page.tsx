import Link from "next/link";
import { PublicFooter } from "@/components/public-footer";
import { PublicHeader } from "@/components/public-header";

type Post = { slug: string; title: string; excerpt: string; cover_image_url: string; published_at: string };

export const dynamic = "force-dynamic";

export default async function BlogPage() {
  let posts: Post[] = [];
  try {
    const response = await fetch(`${process.env.BACKEND_URL ?? "http://localhost:8000"}/api/v1/site/content?page_type=post`, { cache: "no-store" });
    posts = response.ok ? await response.json() : [];
  } catch {
    posts = [];
  }
  return <main dir="rtl" className="min-h-screen bg-sky-50/40"><PublicHeader /><section className="px-5 py-14"><div className="mx-auto max-w-6xl"><p className="text-sm font-bold text-blue-600">دانشنامه چکاه</p><h1 className="mt-2 text-4xl font-black">مطالب و راهنماهای مالیاتی</h1><div className="mt-10 grid gap-5 md:grid-cols-2 lg:grid-cols-3">{posts.map((post) => <Link href={`/blog/${post.slug}`} key={post.slug} className="overflow-hidden rounded-3xl border bg-white shadow-sm transition hover:-translate-y-1 hover:shadow-xl">{post.cover_image_url && <div className="h-44 bg-cover bg-center" style={{ backgroundImage: `url(${post.cover_image_url})` }} />}<div className="p-6"><h2 className="text-xl font-black">{post.title}</h2><p className="mt-3 line-clamp-3 text-sm leading-7 text-slate-500">{post.excerpt}</p></div></Link>)}</div>{!posts.length && <p className="mt-10 rounded-2xl border border-dashed bg-white p-12 text-center text-slate-500">هنوز مطلبی منتشر نشده است.</p>}</div></section><PublicFooter /></main>;
}
