"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { AdminTable } from "@/components/admin-table";

type Audit = { id: number; actor_email: string; action: string; resource_type: string; resource_id: string | null; created_at: string };
export default function AuditPage() {
  const [rows, setRows] = useState<Audit[]>([]);
  useEffect(() => { void api<Audit[]>("api/v1/admin/audit-logs").then(setRows); }, []);
  return <AdminTable title="گزارش فعالیت مدیران" subtitle="آخرین ۲۵۰ عملیات حساس و مدیریتی سامانه" headers={["زمان", "مدیر", "عملیات", "منبع", "شناسه"]}>
    {rows.map((row) => <tr key={row.id} className="border-t"><td className="p-4 text-xs">{new Date(row.created_at).toLocaleString("fa-IR")}</td><td className="p-4" dir="ltr">{row.actor_email}</td><td className="p-4 font-medium">{row.action}</td><td className="p-4">{row.resource_type}</td><td className="p-4 text-xs">{row.resource_id || "—"}</td></tr>)}
  </AdminTable>;
}
