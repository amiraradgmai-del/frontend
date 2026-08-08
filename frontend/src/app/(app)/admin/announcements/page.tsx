"use client";

import { FormEvent, useState } from "react";
import { Megaphone, Send } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

export default function AnnouncementsPage() {
  const [title, setTitle] = useState("");
  const [message, setMessage] = useState("");
  const [actionUrl, setActionUrl] = useState("");
  const [audience, setAudience] = useState("all");
  const [result, setResult] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setResult("");
    try {
      const response = await api<{ recipients: number }>("api/v1/admin/notifications/broadcast", { method: "POST", body: JSON.stringify({ title, message, action_url: actionUrl, audience }) });
      setResult(`اعلان برای ${response.recipients.toLocaleString("fa-IR")} کاربر ارسال شد.`);
      setTitle(""); setMessage(""); setActionUrl("");
    } catch (error) { setResult(error instanceof ApiError ? error.message : "ارسال اعلان انجام نشد."); }
    finally { setBusy(false); }
  }
  return <div className="mx-auto max-w-3xl"><Card className="border-sky-100">
    <CardHeader><CardTitle className="flex gap-2"><Megaphone className="text-blue-600" /> اعلان عمومی</CardTitle><CardDescription>پیام سامانه را برای همه کاربران یا یک سطح اشتراک ارسال کنید.</CardDescription></CardHeader>
    <CardContent><form onSubmit={submit} className="space-y-4">
      <Input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="عنوان اعلان" minLength={3} required />
      <Textarea value={message} onChange={(event) => setMessage(event.target.value)} placeholder="متن اعلان" className="min-h-32" minLength={5} required />
      <div className="grid gap-4 sm:grid-cols-2"><select className="h-10 rounded-lg border bg-white px-3 text-sm" value={audience} onChange={(event) => setAudience(event.target.value)}><option value="all">همه کاربران</option><option value="normal">کاربران عادی</option><option value="plus">کاربران پلاس</option><option value="pro">کاربران حرفه‌ای</option></select><Input dir="ltr" value={actionUrl} onChange={(event) => setActionUrl(event.target.value)} placeholder="/app/plans (اختیاری)" /></div>
      <Button className="w-full" disabled={busy}><Send /> ارسال اعلان</Button>
    </form>{result && <p className="mt-4 rounded-xl bg-blue-50 p-3 text-sm text-blue-700">{result}</p>}</CardContent>
  </Card></div>;
}
