"use client";

import { useEffect, useState } from "react";
import { Download, ShieldCheck, UserCheck, UserRoundCog, UserX } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import type { User } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

const roleLabels: Record<string, string> = {
  user: "کاربر",
  admin: "ادمین",
  tax_expert: "کارشناس مالی",
  company_expert: "کارشناس شرکت",
  system_admin: "مدیر سامانه",
};

const tierLabels = { normal: "عادی", plus: "پلاس", pro: "حرفه‌ای" };

export default function AdminUsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [savingUserId, setSavingUserId] = useState<string | null>(null);

  useEffect(() => {
    api<User[]>("users?limit=100")
      .then((result) => { setUsers(result); setError(""); })
      .catch(() => setError("دسترسی به فهرست کاربران ممکن نیست."))
      .finally(() => setLoading(false));
  }, []);

  async function update(user: User, changes: Record<string, unknown>) {
    setSavingUserId(user.id);
    try {
      const updated = await api<User>(`users/${user.id}`, {
        method: "PATCH",
        body: JSON.stringify(changes),
      });
      setUsers((items) => items.map((item) => item.id === updated.id ? updated : item));
      setError("");
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "تغییر کاربر ذخیره نشد.");
    } finally { setSavingUserId(null); }
  }

  return (
    <div className="space-y-7">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
        <p className="text-sm font-medium text-primary">پنل مدیریت</p>
        <h1 className="mt-1 text-3xl font-black">مدیریت کاربران</h1>
        <p className="mt-2 text-muted-foreground">نقش، سطح اشتراک و وضعیت دسترسی کاربران را کنترل کنید.</p>
        </div>
        <a href="/api/backend/api/v1/admin/export/users.xlsx" className="flex items-center gap-2 rounded-xl bg-emerald-600 px-5 py-3 text-sm font-bold text-white shadow-sm"><Download className="size-4" /> Excel همه کاربران</a>
      </header>
      <div className="grid gap-4 sm:grid-cols-3">
        <Summary icon={UserRoundCog} label="کل کاربران" value={users.length} />
        <Summary icon={UserCheck} label="کاربران فعال" value={users.filter((user) => user.is_active).length} />
        <Summary icon={ShieldCheck} label="مدیران سیستم" value={users.filter((user) => user.roles.some((role) => ["system_admin", "admin"].includes(role))).length} />
      </div>
      {error && <p className="rounded-xl bg-red-50 p-4 text-sm text-red-700">{error}</p>}
      <Card className="border-white/70 bg-white/85">
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[850px] text-right text-sm">
              <thead className="border-b bg-slate-50 text-slate-500"><tr><th className="p-4">کاربر</th><th className="p-4">نقش اصلی</th><th className="p-4">پلن</th><th className="p-4">وضعیت</th><th className="p-4">تاریخ عضویت</th></tr></thead>
              <tbody className="divide-y">
                {users.map((user) => (
                  <tr key={user.id} className="hover:bg-slate-50/70">
                    <td className="p-4"><p className="font-semibold">{user.full_name}</p><p dir="ltr" className="mt-1 text-left text-xs text-muted-foreground">{user.email}</p></td>
                    <td className="p-4"><select value={primaryRole(user)} disabled={savingUserId === user.id} onChange={(event) => void update(user, { roles: [event.target.value] })} className="h-10 rounded-lg border bg-white px-3"><option value="user">کاربر</option><option value="admin">ادمین</option><option value="tax_expert">کارشناس مالی</option><option value="company_expert">کارشناس شرکت</option><option value="system_admin">مدیر سامانه</option></select></td>
                    <td className="p-4"><select value={user.account_tier} disabled={savingUserId === user.id} onChange={(event) => void update(user, { account_tier: event.target.value })} className="h-10 rounded-lg border bg-white px-3"><option value="normal">عادی</option><option value="plus">پلاس</option><option value="pro">حرفه‌ای</option></select></td>
                    <td className="p-4"><Button variant={user.is_active ? "outline" : "destructive"} size="sm" onClick={() => void update(user, { is_active: !user.is_active })}>{user.is_active ? <><UserCheck /> فعال</> : <><UserX /> غیرفعال</>}</Button></td>
                    <td className="p-4 text-muted-foreground">{new Date(user.created_at).toLocaleDateString("fa-IR")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {!loading && users.length === 0 && <p className="p-10 text-center text-muted-foreground">کاربری یافت نشد.</p>}
          {loading && <p className="p-10 text-center text-muted-foreground">در حال دریافت کاربران...</p>}
        </CardContent>
      </Card>
      <p className="text-xs text-muted-foreground">نقش‌ها: {Object.entries(roleLabels).map(([key, value]) => `${value} (${key})`).join("، ")} · پلن‌ها: {Object.values(tierLabels).join("، ")}</p>
    </div>
  );
}

function Summary({ icon: Icon, label, value }: { icon: typeof UserRoundCog; label: string; value: number }) {
  return <Card className="border-white/70 bg-white/80"><CardContent className="flex items-center gap-4 p-5"><span className="flex size-11 items-center justify-center rounded-xl bg-primary/10 text-primary"><Icon /></span><div><p className="text-2xl font-black">{value}</p><p className="text-sm text-muted-foreground">{label}</p></div></CardContent></Card>;
}

function primaryRole(user: User) {
  return ["system_admin", "admin", "company_expert", "tax_expert", "user"].find((role) => user.roles.includes(role)) ?? "user";
}
