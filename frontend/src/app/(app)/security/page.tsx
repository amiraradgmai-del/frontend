"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { CheckCircle2, Copy, Download, KeyRound, ShieldCheck, Trash2 } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

type Setup={enabled:boolean;secret:string;otpauth_uri:string};
export default function SecurityPage(){
  const[setup,setSetup]=useState<Setup|null>(null),[code,setCode]=useState(""),[message,setMessage]=useState("");
  const load=()=>api<Setup>("api/v1/tools/security/2fa/setup").then(setSetup);
  useEffect(()=>{void load();},[]);
  async function enable(){setMessage("");try{await api("api/v1/tools/security/2fa/enable",{method:"POST",body:JSON.stringify({code})});setCode("");setMessage("ورود دومرحله‌ای فعال شد.");await load();}catch(error){setMessage(error instanceof ApiError?error.message:"فعال‌سازی انجام نشد.");}}
  async function disable(){setMessage("");try{await api("api/v1/tools/security/2fa",{method:"DELETE",body:JSON.stringify({code})});setCode("");setMessage("ورود دومرحله‌ای غیرفعال شد.");await load();}catch(error){setMessage(error instanceof ApiError?error.message:"غیرفعال‌سازی انجام نشد.");}}
  async function deleteRequest(){if(!window.confirm("درخواست حذف حساب برای بررسی پشتیبانی ثبت شود؟"))return;try{await api("api/v1/portal/account/delete-request",{method:"POST"});setMessage("درخواست حذف حساب ثبت شد و از بخش پشتیبانی قابل پیگیری است.");}catch(error){setMessage(error instanceof ApiError?error.message:"ثبت درخواست انجام نشد.");}}
  return <div className="mx-auto max-w-3xl space-y-7"><header><p className="text-sm font-medium text-primary">حفاظت و کنترل حساب</p><h1 className="mt-1 text-3xl font-black">امنیت و اطلاعات حساب</h1><p className="mt-2 text-muted-foreground">امنیت ورود، دریافت نسخه اطلاعات و درخواست حذف حساب را مدیریت کنید.</p></header>{message&&<p className="flex items-center gap-2 rounded-xl bg-blue-50 p-3 text-sm text-blue-700"><CheckCircle2 className="size-4"/>{message}</p>}
    <Card className="overflow-hidden"><div className="h-2 bg-gradient-to-l from-primary to-teal-300"/><CardHeader><div className="flex items-center justify-between"><span className="rounded-2xl bg-primary/10 p-4 text-primary"><ShieldCheck/></span><Badge variant={setup?.enabled?"default":"secondary"}>{setup?.enabled?"فعال":"غیرفعال"}</Badge></div><CardTitle>ورود دومرحله‌ای</CardTitle><CardDescription>از برنامه‌های استاندارد احراز هویت استفاده کنید.</CardDescription></CardHeader><CardContent className="space-y-5">{!setup?.enabled&&<div className="rounded-2xl bg-slate-950 p-5 text-white"><p className="text-xs text-slate-400">کلید راه‌اندازی</p><div className="mt-3 flex items-center gap-2"><code className="min-w-0 flex-1 break-all text-lg text-teal-300">{setup?.secret}</code><Button size="icon" variant="secondary" onClick={()=>navigator.clipboard.writeText(setup?.secret??"")}><Copy/></Button></div></div>}<div className="flex gap-2"><div className="relative flex-1"><KeyRound className="absolute right-3 top-3 size-4 text-muted-foreground"/><Input className="pr-10 text-center font-mono tracking-[.35em]" dir="ltr" inputMode="numeric" value={code} onChange={(event)=>setCode(event.target.value.replace(/\D/g,"").slice(0,6))} placeholder="000000"/></div><Button disabled={code.length!==6} variant={setup?.enabled?"destructive":"default"} onClick={setup?.enabled?disable:enable}>{setup?.enabled?"غیرفعال‌سازی":"تأیید و فعال‌سازی"}</Button></div></CardContent></Card>
    <Card><CardHeader><CardTitle>کنترل داده‌های حساب</CardTitle><CardDescription>نسخه قابل‌خواندن اطلاعات، پرداخت‌ها و تراکنش‌های خود را دریافت کنید.</CardDescription></CardHeader><CardContent className="grid gap-3 sm:grid-cols-2"><Link href="/api/backend/api/v1/portal/account/export" className="flex items-center justify-center gap-2 rounded-xl bg-emerald-600 px-4 py-3 text-sm font-bold text-white"><Download className="size-4"/>دانلود اطلاعات من</Link><Button type="button" variant="destructive" className="h-auto py-3" onClick={deleteRequest}><Trash2/>درخواست حذف حساب</Button><p className="text-xs leading-6 text-muted-foreground sm:col-span-2">حذف حساب فوری نیست؛ درخواست برای بررسی تعهدات مالی، سوابق پرداخت و الزامات قانونی به پشتیبانی ارسال می‌شود.</p></CardContent></Card>
  </div>;
}
