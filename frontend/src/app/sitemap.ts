import type { MetadataRoute } from "next";

type Post = { slug: string; updated_at: string };

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const baseUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "https://chekahtax.com";
  const staticPages: MetadataRoute.Sitemap = ["", "/about", "/contact", "/pricing", "/laws", "/advisors", "/blog"].map((path) => ({ url: `${baseUrl}${path}`, lastModified: new Date(), changeFrequency: path === "/blog" ? "weekly" : path ? "monthly" : "weekly", priority: path === "/blog" ? 0.9 : path ? 0.7 : 1 }));
  try {
    const response = await fetch(`${process.env.BACKEND_URL ?? "http://localhost:8000"}/api/v1/site/content?page_type=post`, { cache: "no-store" });
    const posts: Post[] = response.ok ? await response.json() : [];
    return [...staticPages, ...posts.map((post) => ({ url: `${baseUrl}/blog/${post.slug}`, lastModified: new Date(post.updated_at), changeFrequency: "monthly" as const, priority: 0.8 }))];
  } catch {
    return staticPages;
  }
}
