"use client";

import {
  FormEvent,
  useEffect,
  useRef,
  useState,
} from "react";
import Link from "next/link";
import Image from "next/image";
import {
  ArrowLeft,
  Eye,
  EyeOff,
  KeyRound,
  LockKeyhole,
  Scale,
  ShieldCheck,
  UserRound,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";

function normalizeIdentifier(value: string): string {
  const normalized = value
    .trim()
    .replace(/[۰-۹]/g, (digit) => String("۰۱۲۳۴۵۶۷۸۹".indexOf(digit)))
    .replace(/[٠-٩]/g, (digit) => String("٠١٢٣٤٥٦٧٨٩".indexOf(digit)));
  const compact = normalized.replace(/[\s()-]/g, "");
  if (/^(?:\+98|0098)9\d{9}$/.test(compact)) return `0${compact.slice(-10)}`;
  return compact.startsWith("09") ? compact : normalized.toLowerCase();
}

export default function LoginPage() {
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const [showPassword, setShowPassword] =
    useState(false);

  const [needsTwoFactor, setNeedsTwoFactor] =
    useState(false);

  const [otpCode, setOtpCode] = useState("");

  const hidePasswordTimer =
    useRef<ReturnType<typeof setTimeout> | null>(
      null,
    );

  useEffect(() => {
    return () => {
      if (hidePasswordTimer.current) {
        clearTimeout(hidePasswordTimer.current);
      }
    };
  }, []);

  function revealPassword() {
    if (hidePasswordTimer.current) {
      clearTimeout(hidePasswordTimer.current);
    }

    setShowPassword(true);

    hidePasswordTimer.current = setTimeout(() => {
      setShowPassword(false);
    }, 5000);
  }

  function validateIdentifier() {
    const value = normalizeIdentifier(identifier);

    if (!value) {
      setError(
        "شماره موبایل یا ایمیل خود را وارد کنید.",
      );
      return false;
    }

    if (value.startsWith("09")) {
      if (!/^09\d{9}$/.test(value)) {
        setError(
          "شماره موبایل باید با 09 شروع شود و ۱۱ رقم باشد.",
        );
        return false;
      }

      return true;
    }

    if (
      !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)
    ) {
      setError(
        "شماره موبایل یا ایمیل معتبر وارد کنید.",
      );
      return false;
    }

    return true;
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");

    if (!validateIdentifier()) {
      return;
    }

    if (!password) {
      setError("رمز عبور را وارد کنید.");
      return;
    }

    if (
      needsTwoFactor &&
      !/^\d{6}$/.test(otpCode)
    ) {
      setError(
        "کد ۶ رقمی احراز هویت را وارد کنید.",
      );
      return;
    }

    setLoading(true);

    try {
      const response = await fetch(
        "/api/auth/login",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            identifier: normalizeIdentifier(identifier),
            password,
            otp_code: otpCode,
          }),
        },
      );

      if (!response.ok) {
        const payload = await response
          .json()
          .catch(() => null);

        if (
          payload?.detail ===
          "Two-factor code required"
        ) {
          setNeedsTwoFactor(true);

          setError(
            otpCode
              ? "کد احراز هویت صحیح نیست یا منقضی شده است."
              : "کد ۶ رقمی برنامه احراز هویت را وارد کنید.",
          );

          return;
        }

        if (
          payload?.detail ===
          "Account is temporarily locked"
        ) {
          setError(
            "حساب شما موقتاً قفل شده است. کمی بعد دوباره تلاش کنید.",
          );
          return;
        }

        if (
          payload?.detail ===
          "Invalid phone, email, or password"
        ) {
          setError(
            "شماره موبایل، ایمیل یا رمز عبور صحیح نیست.",
          );
          return;
        }

        setError(
          payload?.detail ||
            "ورود انجام نشد. دوباره تلاش کنید.",
        );

        return;
      }

      window.location.assign("/app/dashboard");
    } catch {
      setError(
        "ارتباط با سرور برقرار نشد. دوباره تلاش کنید.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="grid min-h-screen lg:grid-cols-2">
      <section className="relative hidden overflow-hidden bg-gradient-to-br from-sky-500 via-blue-600 to-cyan-500 p-14 text-white lg:flex lg:flex-col lg:justify-between">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(255,255,255,.28),transparent_34%),radial-gradient(circle_at_80%_80%,rgba(251,191,36,.32),transparent_32%)]" />

        <div className="relative flex items-center gap-3">
          <div className="size-14 overflow-hidden rounded-2xl bg-white shadow-lg">
            <Image
              src="/brand/chakah-logo.png"
              alt="لوگوی چکاه"
              width={56}
              height={56}
              className="size-full object-contain"
            />
          </div>

          <div>
            <p className="text-lg font-bold">
              چکاه
            </p>

            <p className="text-sm text-sky-100">
              دستیار هوشمند مالیاتی
            </p>
          </div>
        </div>

        <div className="relative max-w-xl">
          <p className="mb-5 text-sm font-bold text-amber-200">
            پاسخ مبتنی بر منبع، نه حدس مدل
          </p>

          <h1 className="text-4xl font-black leading-[1.6]">
            قانون را سریع‌تر پیدا کنید و پاسخ
            قابل استناد بگیرید.
          </h1>

          <div className="mt-10 flex gap-6 text-sm text-sky-50">
            <span className="flex items-center gap-2">
              <ShieldCheck className="size-4 text-amber-200" />
              اسناد تأییدشده
            </span>

            <span className="flex items-center gap-2">
              <ShieldCheck className="size-4 text-amber-200" />
              منابع قابل‌ردیابی
            </span>
          </div>
        </div>

        <p className="relative text-xs text-sky-100">
          این سامانه جایگزین بررسی پرونده توسط
          مشاور مالیاتی نیست.
        </p>
      </section>

      <section className="flex min-h-dvh items-start justify-center overflow-y-auto p-4 pt-8 sm:items-center sm:p-12">
        <Card className="w-full max-w-md border-white/70 bg-white/85 shadow-2xl shadow-slate-900/10 backdrop-blur-xl">
          <CardHeader className="space-y-3">
            <div className="mb-2 flex size-11 items-center justify-center rounded-xl bg-primary/10 text-primary lg:hidden">
              <Scale />
            </div>

            <CardTitle className="text-2xl">
              ورود به حساب کاربری
            </CardTitle>

            <CardDescription>
              برای ادامه، شماره موبایل یا ایمیل و
              رمز عبور خود را وارد کنید.
            </CardDescription>
          </CardHeader>

          <CardContent>
            <form
              onSubmit={submit}
              className="space-y-5"
              noValidate
            >
              <label className="block space-y-2 text-sm font-medium">
                <span>شماره موبایل یا ایمیل</span>

                <div className="relative">
                  <UserRound className="absolute right-3 top-3 size-4 text-muted-foreground" />

                  <Input
                    dir="ltr"
                    type="text"
                    autoComplete="username"
                    value={identifier}
                    inputMode={identifier.includes("@") ? "email" : "tel"}
                    onChange={(event) => setIdentifier(event.target.value)}
                    className="pr-10 text-left text-base sm:text-sm"
                    placeholder="شماره موبایل یا ایمیل"
                  />
                </div>
              </label>

              <label className="block space-y-2 text-sm font-medium">
                <span>رمز عبور</span>

                <div className="relative">
                  <LockKeyhole className="absolute right-3 top-3 size-4 text-muted-foreground" />

                  <Input
                    dir="ltr"
                    type={
                      showPassword
                        ? "text"
                        : "password"
                    }
                    autoComplete="current-password"
                    value={password}
                    onChange={(event) =>
                      setPassword(
                        event.target.value,
                      )
                    }
                    className="px-10 text-left text-base sm:text-sm"
                    placeholder="رمز عبور"
                  />

                  <button
                    type="button"
                    onClick={
                      showPassword
                        ? () =>
                            setShowPassword(false)
                        : revealPassword
                    }
                    className="absolute left-3 top-2.5 text-muted-foreground"
                    title={
                      showPassword
                        ? "مخفی‌کردن رمز"
                        : "نمایش رمز برای ۵ ثانیه"
                    }
                  >
                    {showPassword ? (
                      <EyeOff className="size-4" />
                    ) : (
                      <Eye className="size-4" />
                    )}
                  </button>
                </div>
              </label>

              <div className="text-left">
                <Link
                  href="/forgot-password"
                  className="text-xs font-semibold text-primary"
                >
                  رمز عبور را فراموش کرده‌اید؟
                </Link>
              </div>

              {needsTwoFactor && (
                <label className="block space-y-2 text-sm font-medium">
                  <span>
                    کد احراز هویت دومرحله‌ای
                  </span>

                  <div className="relative">
                    <KeyRound className="absolute right-3 top-3 size-4 text-muted-foreground" />

                    <Input
                      dir="ltr"
                      inputMode="numeric"
                      autoComplete="one-time-code"
                      value={otpCode}
                      onChange={(event) => setOtpCode(normalizeIdentifier(event.target.value).replace(/\D/g, "").slice(0, 6))}
                      className="pr-10 text-center font-mono text-base tracking-[.3em] sm:text-sm"
                      placeholder="000000"
                      maxLength={6}
                    />
                  </div>
                </label>
              )}

              {error && (
                <p className="rounded-lg bg-red-50 p-3 text-sm text-red-700">
                  {error}
                </p>
              )}

              <Button
                type="submit"
                className="w-full"
                size="lg"
                disabled={loading}
              >
                {loading ? (
                  "در حال ورود..."
                ) : (
                  <>
                    ورود
                    <ArrowLeft />
                  </>
                )}
              </Button>
            </form>

            <p className="mt-5 text-center text-sm text-muted-foreground">
              حساب ندارید؟{" "}
              <Link
                href="/signup"
                className="font-semibold text-primary"
              >
                ثبت‌نام کنید
              </Link>
            </p>
          </CardContent>
        </Card>
      </section>
    </main>
  );
}
