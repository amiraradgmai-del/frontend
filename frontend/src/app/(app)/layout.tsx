import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { AppShell } from "@/components/app-shell";
import { accessCookie, refreshCookie } from "@/lib/backend";

export const metadata = { robots: { index: false, follow: false } };

export default async function DashboardLayout({ children }: { children: React.ReactNode }) {
  const store = await cookies();
  if (!store.has(accessCookie) && !store.has(refreshCookie)) redirect("/login");
  return <AppShell>{children}</AppShell>;
}
