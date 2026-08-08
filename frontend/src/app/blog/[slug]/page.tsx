import { notFound } from "next/navigation";
import { BlogComments } from "@/components/blog-comments";

type Page = { title: string; excerpt: string; content: string; cover_image_url: string };

export const dynamic = "force-dynamic";

export default async function BlogPost({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  let response: Response;
  try {
    response = await fetch(`${process.env.BACKEND_URL ?? "http://localhost:8000"}/api/v1/site/content/${slug}`, { cache: "no-store" });
  } catch {
    notFound();
  }
  if (!response.ok) notFound();
  const post: Page = await response.json();
  return <main dir="rtl" className="min-h-screen bg-sky-50/40 px-5 py-14"><article className="mx-auto max-w-4xl overflow-hidden rounded-[2rem] border bg-white shadow-sm">{post.cover_image_url && <div className="h-72 bg-cover bg-center" style={{ backgroundImage: `url(${post.cover_image_url})` }} />}<div className="p-7 sm:p-12"><h1 className="text-4xl font-black">{post.title}</h1><p className="mt-4 text-lg leading-8 text-slate-500">{post.excerpt}</p><div className="mt-10 whitespace-pre-wrap text-base leading-9 text-slate-700">{post.content}</div><BlogComments slug={slug} /></div></article></main>;
}
