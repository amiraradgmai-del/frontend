import type { Metadata } from "next";
import { backendUrl } from "@/lib/backend";
import { SiteThemeProvider } from "@/components/site-theme-provider";
import "./vazirmatn.css";
import "./font-collection.css";
import "./globals.css";

export async function generateMetadata(): Promise<Metadata> {
  const metadataBase = new URL(process.env.NEXT_PUBLIC_SITE_URL ?? "https://chekahtax.com");
  const fallback: Metadata = {
    metadataBase,
    title: "چکاه | دستیار هوشمند مالیاتی",
    description: "پاسخ مستند به پرسش‌های مالیاتی ایران",
    robots: { index: true, follow: true },
  };
  try {
    const response = await fetch(`${backendUrl}/api/v1/site/config`, { next: { revalidate: 300 } });
    if (!response.ok) return fallback;
    const payload = await response.json();
    return {
      metadataBase,
      title: { default: payload.configuration.seo.default_title, template: `%s | ${payload.configuration.branding.site_name}` },
      description: payload.configuration.seo.default_description,
      keywords: payload.configuration.seo.keywords.split("،").map((item: string) => item.trim()),
      applicationName: payload.configuration.branding.site_name,
      robots: { index: true, follow: true },
      openGraph: {
        type: "website",
        locale: "fa_IR",
        siteName: payload.configuration.branding.site_name,
        title: payload.configuration.seo.default_title,
        description: payload.configuration.seo.default_description,
      },
    };
  } catch {
    return fallback;
  }
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="fa" dir="rtl" className="h-full antialiased">
      <body className="min-h-full"><SiteThemeProvider>{children}</SiteThemeProvider></body>
    </html>
  );
}
