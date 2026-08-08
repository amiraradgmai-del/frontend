import type { NextConfig } from "next";

const contentSecurityPolicy = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-inline'",
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob:",
  "font-src 'self' data:",
  "connect-src 'self'",
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
].join("; ");

const securityHeaders = [
  { key: "Content-Security-Policy", value: contentSecurityPolicy },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  {
    key: "Permissions-Policy",
    value: "camera=(), microphone=(), geolocation=(), payment=()",
  },
];

const nextConfig: NextConfig = {
  output: "standalone",
  turbopack: {
    root: process.cwd(),
  },
  poweredByHeader: false,
  async headers() {
    return [
      { source: "/(.*)", headers: securityHeaders },
      {
        source: "/fonts/:path*",
        headers: [{ key: "Cache-Control", value: "public, max-age=31536000, immutable" }],
      },
      {
        source: "/brand/:path*",
        headers: [{ key: "Cache-Control", value: "public, max-age=2592000, stale-while-revalidate=86400" }],
      },
    ];
  },
  async redirects() {
    return [
      { source: "/dashboard", destination: "/app/dashboard", permanent: true },
      { source: "/chat", destination: "/app/chat", permanent: true },
      { source: "/history", destination: "/app/history", permanent: true },
      { source: "/calendar", destination: "/app/calendar", permanent: true },
      { source: "/tools", destination: "/app/tools", permanent: true },
      { source: "/usage", destination: "/app/usage", permanent: true },
      { source: "/plans", destination: "/app/plans", permanent: true },
      { source: "/my-documents", destination: "/app/documents", permanent: true },
      { source: "/tickets", destination: "/app/tickets", permanent: true },
      { source: "/consultations", destination: "/app/consultations", permanent: true },
      { source: "/profile", destination: "/app/profile", permanent: true },
      { source: "/security", destination: "/app/security", permanent: true },
      { source: "/documents", destination: "/laws", permanent: true },
      { source: "/admin/documents", destination: "/management/datasets", permanent: true },
      { source: "/admin/:path*", destination: "/management/:path*", permanent: true },
      { source: "/admin", destination: "/management", permanent: true },
    ];
  },
};

export default nextConfig;
