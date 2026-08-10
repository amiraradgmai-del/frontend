"use client";
import Link from "next/link";
import { ChevronDown } from "lucide-react";
import { useEffect, useState } from "react";
type Article = { slug: string; title: string; category?: string };

export function ArticleDropdown({ compact = false }: { compact?: boolean }) {
  const [articles, setArticles] = useState<Article[]>([]);
  useEffect(() => {
    fetch("/api/backend/api/v1/site/content?page_type=post", {
      cache: "no-store",
    })
      .then((response) => (response.ok ? response.json() : []))
      .then((items: Article[]) => setArticles(items.slice(0, 6)))
      .catch(() => setArticles([]));
  }, []);
  return (
    <div className={`group relative ${compact ? "hidden lg:block" : ""}`}>
      <Link
        href="/blog"
        className={`flex items-center gap-1 whitespace-nowrap px-2 py-3 text-slate-700 transition hover:text-blue-700 ${compact ? "text-xs font-bold" : "text-sm font-normal"}`}
      >
        مقاله‌ها <ChevronDown className="size-3.5 text-slate-400" />
      </Link>
      <div className="invisible absolute right-1/2 top-full z-50 w-80 translate-x-1/2 translate-y-2 border border-slate-200 bg-white p-4 opacity-0 shadow-2xl transition group-hover:visible group-hover:translate-y-0 group-hover:opacity-100 group-focus-within:visible group-focus-within:translate-y-0 group-focus-within:opacity-100">
        <span className="absolute -top-2 right-1/2 size-4 translate-x-1/2 rotate-45 border-r border-t border-slate-200 bg-white" />
        <Link
          href="/blog"
          className="relative block border-b border-slate-100 pb-3 text-sm font-black text-blue-700"
        >
          همه مقاله‌ها
        </Link>
        <div className="relative divide-y divide-slate-100">
          {articles.map((article) => (
            <Link
              key={article.slug}
              href={`/blog/${article.slug}`}
              className="block py-3 text-sm leading-6 text-slate-700 transition hover:pr-1 hover:text-blue-700"
            >
              <span className="block font-bold">{article.title}</span>
              {article.category && (
                <span className="mt-0.5 block text-[10px] text-slate-400">
                  {article.category}
                </span>
              )}
            </Link>
          ))}
          {!articles.length && (
            <p className="py-4 text-xs text-slate-400">
              مقاله‌ای منتشر نشده است.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
