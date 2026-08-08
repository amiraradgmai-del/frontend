import type { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  const baseUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";
  return { rules: { userAgent: "*", allow: ["/", "/about", "/contact", "/pricing", "/laws", "/advisors"], disallow: ["/app/", "/management/", "/support/", "/consultant/", "/api/"] }, sitemap: `${baseUrl}/sitemap.xml` };
}
