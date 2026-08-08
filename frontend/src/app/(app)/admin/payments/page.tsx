"use client";

import { useEffect, useState } from "react";
import { RotateCcw } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { AdminTable } from "@/components/admin-table";

type Row = { id: string; email: string; plan: string; amount: number; discount_amount: number; status: string; reference: string; created_at: string };

export default function Page() {
  const [rows, setRows] = useState<Row[]>([]);
  const [message, setMessage] = useState("");
  const load = () => api<Row[]>("api/v1/admin/payments").then(setRows);
  useEffect(() => { void load(); }, []);

  async function refund(row: Row) {
    const reason = window.prompt("دلیل بازپرداخت را وارد کنید:");
    if (!reason || reason.trim().length < 5) return;
    if (!window.confirm(`${row.amount.toLocaleString("fa-IR")} تومان به کیف پول کاربر بازگردد؟`)) return;
    try {
      await api(`api/v1/admin/payments/${row.id}/refund`, { method: "POST", body: JSON.stringify({ reason }) });
      setMessage("بازپرداخت انجام و اشتراک مرتبط لغو شد.");
      await load();
    } catch (error) {
      setMessage(error instanceof ApiError ? error.message : "بازپرداخت انجام نشد.");
    }
  }

  return <div className="space-y-4">
    {message && <p className="rounded-xl bg-blue-50 p-3 text-sm text-blue-700">{message}</p>}
    <AdminTable title="مدیریت پرداخت‌ها" subtitle="تراکنش‌ها، تخفیف‌ها، پیگیری و بازپرداخت امن" headers={["کاربر", "پلن", "مبلغ", "تخفیف", "وضعیت", "پیگیری", "عملیات"]}>
      {rows.map((row) => <tr key={row.id} className="border-t">
        <td className="p-4" dir="ltr">{row.email}</td><td className="p-4">{row.plan}</td>
        <td className="p-4">{row.amount.toLocaleString("fa-IR")}</td><td className="p-4">{row.discount_amount.toLocaleString("fa-IR")}</td>
        <td className="p-4"><Badge variant={row.status === "paid" ? "default" : "secondary"}>{row.status}</Badge></td>
        <td className="p-4 text-xs">{row.reference}</td>
        <td className="p-4"><Button size="sm" variant="outline" disabled={row.status !== "paid"} onClick={() => void refund(row)}><RotateCcw /> بازپرداخت</Button></td>
      </tr>)}
    </AdminTable>
  </div>;
}
