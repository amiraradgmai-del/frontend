"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { ShieldX } from "lucide-react";
import { api } from "@/lib/api";
import type { User } from "@/lib/types";

const routePermissions: Record<string, string> = {
  "/admin/users": "users:manage",
  "/admin/profiles": "users:manage",
  "/admin/payments": "payments:manage",
  "/admin/discounts": "payments:manage",
  "/admin/subscriptions": "subscriptions:manage",
  "/admin/customer-documents": "user_documents:manage",
  "/admin/documents": "documents:manage",
  "/admin/tickets": "tickets:manage",
  "/admin/consultations": "consultations:manage",
  "/admin/chats": "chats:manage",
  "/admin": "users:manage",
};

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [allowed, setAllowed] = useState<boolean | null>(null);

  useEffect(() => {
    api<User>("users/me").then((user) => {
      const permission = Object.entries(routePermissions).find(([path]) => path === "/admin" ? pathname === path : pathname.startsWith(path))?.[1];
      const hasAccess = Boolean(permission && user.permissions.includes(permission));
      setAllowed(hasAccess);
      if (!hasAccess) setTimeout(() => router.replace("/dashboard"), 1800);
    }).catch(() => router.replace("/login"));
  }, [pathname, router]);

  if (allowed === null) return <div className="p-12 text-center text-muted-foreground">در حال بررسی دسترسی...</div>;
  if (!allowed) return <div className="mx-auto max-w-lg rounded-2xl border bg-white p-10 text-center shadow-sm"><ShieldX className="mx-auto mb-4 size-10 text-red-500" /><h1 className="text-xl font-bold">دسترسی غیرمجاز</h1><p className="mt-2 text-sm text-muted-foreground">این بخش فقط برای نقش‌های مدیریتی مجاز است. در حال بازگشت به داشبورد...</p></div>;
  return children;
}
