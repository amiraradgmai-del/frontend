"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

type Post = { category?: string; tags?: string[] };

export function ArticleHeaderLinks({ compact = false }: { compact?: boolean }) {
  const [items, setItems] = useState<Array<{ label: string; href: string }>>([]);

  useEffect(() => {
    fetch("/api/backend/api/v1/site/content?page_type=post", { cache: "no-store" })
      .then((response) => response.ok ? response.json() : [])
      .then((posts: Post[]) => { const categories=[...new Set(posts.map(post=>post.category?.trim()).filter(Boolean) as string[])]; const tags=[...new Set(posts.flatMap(post=>post.tags||[]).map(tag=>tag.trim()).filter(Boolean))].filter(tag=>!categories.includes(tag)); setItems([...categories.map(label=>({label,href:`/blog?category=${encodeURIComponent(label)}`})),...tags.map(label=>({label,href:`/blog?q=${encodeURIComponent(label)}`}))].slice(0,8)); })
      .catch(() => setItems([]));
  }, []);

  if (!items.length) return null;
  return <nav aria-label="دسته‌ها و برچسب‌های مقاله" className={`flex items-center gap-2 overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden ${compact ? "max-w-xl" : "w-full border-t border-sky-100 px-5 py-2"}`}>
    <span className="shrink-0 text-[11px] font-bold text-slate-400">موضوعات:</span>
    {items.map((item) => <Link key={item.href} href={item.href} className="shrink-0 rounded-full bg-sky-50 px-3 py-1 text-[11px] font-bold text-blue-700 transition hover:bg-blue-100">{item.label}</Link>)}
  </nav>;
}
