"use client";

import {
  FormEvent,
  useState,
} from "react";
import Link from "next/link";
import {
  CheckCircle2,
  Eye,
  EyeOff,
  KeyRound,
  LockKeyhole,
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

type Step = "request" | "confirm" | "done";

function toEnglishDigits(value: string): string {
  return value
    .replace(/[۰-۹]/g, (digit) =>
      String("۰۱۲۳۴۵۶۷۸۹".indexOf(digit)),
    )
    .replace(/[٠-٩]/g, (digit) =>
      String("٠١٢٣٤٥٦٧٨٩".indexOf(digit)),
    );
}

async function readError(
  response: Response,
): Promise<string | null> {
  const payload = await response
    .json()
    .catch(() => null);

  return typeof payload?.detail === "string"
    ? payload.detail
    : null;
}

export default function ForgotPasswordPage() {
  const [step, setStep] =
    useState<Step>("request");

  const [identifier, setIdentifier] =
    useState("");
  const [code, setCode] = useState("");
  const [password, setPassword] =
    useState("");
  const [confirmPassword, setConfirmPassword] =
    useState("");

  const [showPassword, setShowPassword] =
    useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  function validateIdentifier(): boolean {
    const value = identifier.trim();

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
      !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(
        value,
      )
    ) {
      setError(
        "شماره موبایل یا ایمیل معتبر وارد کنید.",
      );
      return false;
    }

    return true;
  }

  async function requestCode(
    event: FormEvent,
  ): Promise<void> {
    event.preventDefault();
    setError("");
    setMessage("");

    if (!validateIdentifier()) {
      return;
    }

    setBusy(true);

    try {
      const response = await fetch(
        "/api/backend/auth/password-reset/start",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            identifier: identifier.trim(),
          }),
        },
      );

      if (!response.ok) {
        const detail = await readError(response);

        setError(
          detail ===
            "Password reset code could not be sent"
            ? "ارسال کد بازیابی انجام نشد؛ دوباره تلاش کنید."
            : "درخواست بازیابی انجام نشد؛ دوباره تلاش کنید.",
        );
        return;
      }

      setStep("confirm");
      setMessage(
        "اگر حساب فعالی با این شماره موبایل یا ایمیل وجود داشته باشد، کد بازیابی ارسال شده است.",
      );
    } catch {
      setError(
        "ارتباط با سرور برقرار نشد؛ دوباره تلاش کنید.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function resetPassword(
    event: FormEvent,
  ): Promise<void> {
    event.preventDefault();
    setError("");
    setMessage("");

    if (!/^\d{6}$/.test(code)) {
      setError("کد ۶ رقمی را وارد کنید.");
      return;
    }

    if (password !== confirmPassword) {
      setError(
        "رمز عبور و تکرار آن یکسان نیستند.",
      );
      return;
    }

    if (
      password.length < 8 ||
      !/[a-z]/.test(password) ||
      !/[A-Z]/.test(password) ||
      !/\d/.test(password)
    ) {
      setError(
        "رمز باید حداقل ۸ کاراکتر و شامل حرف بزرگ انگلیسی، حرف کوچک انگلیسی و عدد باشد.",
      );
      return;
    }

    setBusy(true);

    try {
      const response = await fetch(
        "/api/backend/auth/password-reset/complete",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            identifier: identifier.trim(),
            code,
            password,
          }),
        },
      );

      if (!response.ok) {
        setError(
          "کد بازیابی اشتباه یا منقضی شده است.",
        );
        return;
      }

      setStep("done");
    } catch {
      setError(
        "ارتباط با سرور برقرار نشد؛ دوباره تلاش کنید.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-gradient-to-br from-sky-50 to-white p-5">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-3">
          <div className="flex size-11 items-center justify-center rounded-xl bg-primary/10 text-primary">
            {step === "request" ? (
              <UserRound />
            ) : step === "confirm" ? (
              <KeyRound />
            ) : (
              <CheckCircle2 />
            )}
          </div>

          <CardTitle>
            بازیابی رمز عبور
          </CardTitle>

          <CardDescription>
            {step === "request" &&
              "کد تأیید به شماره موبایل یا ایمیل حساب ارسال می‌شود."}

            {step === "confirm" &&
              "کد دریافتی و رمز عبور جدید را وارد کنید."}

            {step === "done" &&
              "رمز عبور حساب با موفقیت تغییر کرد."}
          </CardDescription>
        </CardHeader>

        <CardContent>
          {step === "request" && (
            <form
              onSubmit={requestCode}
              className="space-y-4"
              noValidate
            >
              <label className="block space-y-2 text-sm font-medium">
                <span>
                  شماره موبایل یا ایمیل
                </span>

                <Input
                  dir="ltr"
                  type="text"
                  autoComplete="username"
                  value={identifier}
                  onChange={(event) => {
                    const rawValue =
                      event.target.value;

                    if (
                      /^[۰-۹٠-٩0-9]*$/.test(
                        rawValue,
                      )
                    ) {
                      setIdentifier(
                        toEnglishDigits(rawValue),
                      );
                      return;
                    }

                    setIdentifier(rawValue);
                  }}
                  className="text-left"
                  placeholder="شماره موبایل یا ایمیل خود را وارد کنید"
                />
              </label>

              <p className="text-xs text-muted-foreground">
                بازیابی رمز عبور با شماره موبایل
                یا ایمیل حساب
              </p>

              <Button
                type="submit"
                className="w-full"
                disabled={busy}
              >
                {busy
                  ? "در حال ارسال..."
                  : "ارسال کد بازیابی"}
              </Button>
            </form>
          )}

          {step === "confirm" && (
            <form
              onSubmit={resetPassword}
              className="space-y-4"
              noValidate
            >
              {message && (
                <p className="rounded-xl bg-sky-50 p-3 text-sm leading-6 text-sky-800">
                  {message}
                </p>
              )}

              <label className="block space-y-2 text-sm font-medium">
                <span>کد بازیابی</span>

                <Input
                  dir="ltr"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  value={code}
                  onChange={(event) =>
                    setCode(
                      toEnglishDigits(
                        event.target.value,
                      )
                        .replace(/\D/g, "")
                        .slice(0, 6),
                    )
                  }
                  className="text-center tracking-[.35em]"
                  placeholder="کد ۶ رقمی را وارد کنید"
                  maxLength={6}
                />
              </label>

              <label className="block space-y-2 text-sm font-medium">
                <span>رمز عبور جدید</span>

                <div className="relative">
                  <LockKeyhole className="absolute right-3 top-3 size-4 text-muted-foreground" />

                  <Input
                    dir="ltr"
                    type={
                      showPassword
                        ? "text"
                        : "password"
                    }
                    autoComplete="new-password"
                    value={password}
                    onChange={(event) =>
                      setPassword(
                        event.target.value,
                      )
                    }
                    className="px-10 text-left"
                    placeholder="رمز عبور جدید خود را وارد کنید"
                  />

                  <button
                    type="button"
                    onClick={() =>
                      setShowPassword(
                        (current) => !current,
                      )
                    }
                    className="absolute left-3 top-2.5 text-muted-foreground"
                    aria-label={
                      showPassword
                        ? "مخفی‌کردن رمز عبور"
                        : "نمایش رمز عبور"
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

              <label className="block space-y-2 text-sm font-medium">
                <span>
                  تکرار رمز عبور جدید
                </span>

                <Input
                  dir="ltr"
                  type={
                    showPassword
                      ? "text"
                      : "password"
                  }
                  autoComplete="new-password"
                  value={confirmPassword}
                  onChange={(event) =>
                    setConfirmPassword(
                      event.target.value,
                    )
                  }
                  className="text-left"
                  placeholder="رمز عبور جدید را دوباره وارد کنید"
                />
              </label>

              <p className="text-xs leading-6 text-muted-foreground">
                رمز باید حداقل ۸ کاراکتر و شامل
                حرف بزرگ انگلیسی، حرف کوچک
                انگلیسی و عدد باشد.
              </p>

              <Button
                type="submit"
                className="w-full"
                disabled={busy}
              >
                {busy
                  ? "در حال ثبت..."
                  : "ثبت رمز عبور جدید"}
              </Button>

              <button
                type="button"
                className="w-full text-sm text-primary hover:underline"
                onClick={() => {
                  setStep("request");
                  setCode("");
                  setPassword("");
                  setConfirmPassword("");
                  setMessage("");
                  setError("");
                }}
              >
                تغییر شماره موبایل یا ایمیل
              </button>
            </form>
          )}

          {step === "done" && (
            <div className="rounded-xl bg-emerald-50 p-5 text-center text-emerald-800">
              <CheckCircle2 className="mx-auto mb-3 size-10" />

              <p>
                رمز عبور با موفقیت تغییر کرد.
              </p>

              <Link
                href="/login"
                className="mt-4 inline-block font-bold text-primary"
              >
                ورود به حساب
              </Link>
            </div>
          )}

          {error && (
            <p className="mt-4 rounded-xl bg-red-50 p-3 text-sm leading-6 text-red-700">
              {error}
            </p>
          )}

          {step !== "done" && (
            <p className="mt-5 text-center text-sm text-muted-foreground">
              رمز خود را به یاد دارید؟{" "}
              <Link
                href="/login"
                className="font-semibold text-primary"
              >
                وارد شوید
              </Link>
            </p>
          )}
        </CardContent>
      </Card>
    </main>
  );
}