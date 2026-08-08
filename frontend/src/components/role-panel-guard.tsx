"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ShieldX } from "lucide-react";
import { api } from "@/lib/api";
import type { User } from "@/lib/types";

export function RolePanelGuard({ children, roles, fallback }: { children: React.ReactNode; roles: readonly string[]; fallback: string }) {
  const router = useRouter();
  const [allowed, setAllowed] = useState<boolean | null>(null);

  useEffect(() => {
    api<User>("users/me").then((user) => {
      const hasAccess = user.roles.some((role) => roles.includes(role));
      setAllowed(hasAccess);
      if (!hasAccess) router.replace(fallback);
    }).catch(() => router.replace("/login"));
  }, [fallback, roles, router]);

  if (allowed === null) return <div className="p-12 text-center text-muted-foreground">در حال بررسی دسترسی...</div>;
  if (!allowed) return <div className="mx-auto max-w-lg rounded-2xl border bg-white p-10 text-center shadow-sm"><ShieldX className="mx-auto mb-4 size-10 text-red-500" /><h1 className="text-xl font-bold">دسترسی غیرمجاز</h1><p className="mt-2 text-sm text-muted-foreground">این پنل برای نقش حساب شما فعال نیست.</p></div>;
  return children;
}
