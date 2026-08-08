"use client";

import {
  FormEvent,
  useEffect,
  useRef,
  useState,
} from "react";
import Link from "next/link";
import {
  ArrowLeft,
  CheckCircle2,
  Eye,
  EyeOff,
  KeyRound,
  Mail,
  Phone,
  ShieldCheck,
  UserRound,
} from "lucide-react";

import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";

type Step = "details" | "verify" | "password";

const errorMessages: Record<string, string> = {
  "Phone is already registered":
    "این شماره موبایل قبلاً ثبت شده است.",
  "Email is already registered":
    "این ایمیل قبلاً ثبت شده است.",
  "Please wait before requesting another code":
    "برای ارسال دوباره کد کمی صبر کنید.",
  "Verification SMS could not be sent":
    "ارسال پیامک انجام نشد؛ دوباره تلاش کنید.",
  "Invalid or expired verification code":
    "کد واردشده اشتباه یا منقضی شده است.",
  "Invalid or expired password setup token":
    "زمان تعیین رمز عبور تمام شده است؛ ثبت‌نام را دوباره شروع کنید.",
};

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return (
      errorMessages[error.message] ??
      error.message ??
      "درخواست انجام نشد."
    );
  }

  return "ارتباط با سرور برقرار نشد؛ دوباره تلاش کنید.";
}

function toEnglishDigits(value: string): string {
  return value
    .replace(/[۰-۹]/g, (digit) =>
      String("۰۱۲۳۴۵۶۷۸۹".indexOf(digit)),
    )
    .replace(/[٠-٩]/g, (digit) =>
      String("٠١٢٣٤٥٦٧٨٩".indexOf(digit)),
    );
}

function normalizePhone(value: string): string {
  const compact = toEnglishDigits(value).replace(/[\s()+-]/g, "");
  if (/^(?:98|0098)9\d{9}$/.test(compact)) return `0${compact.slice(-10)}`;
  return compact;
}

export default function SignupPage() {
  const [step, setStep] = useState<Step>("details");

  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [referralCode, setReferralCode] =
    useState("");

  const [code, setCode] = useState("");
  const [setupToken, setSetupToken] =
    useState("");

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] =
    useState("");
  const [showPassword, setShowPassword] =
    useState(false);

  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [resendSeconds, setResendSeconds] =
    useState(0);

  const hidePasswordTimer =
    useRef<ReturnType<typeof setTimeout> | null>(
      null,
    );

  useEffect(() => {
    if (resendSeconds <= 0) return;

    const timer = window.setInterval(() => {
      setResendSeconds((seconds) =>
        Math.max(0, seconds - 1),
      );
    }, 1000);

    return () => window.clearInterval(timer);
  }, [resendSeconds]);

  useEffect(() => {
    return () => {
      if (hidePasswordTimer.current) {
        clearTimeout(hidePasswordTimer.current);
      }
    };
  }, []);

  function validateDetails(): boolean {
    const normalizedFirstName = firstName.trim();
    const normalizedLastName = lastName.trim();
    const normalizedEmail = email.trim();

    if (normalizedFirstName.length < 2) {
      setError("نام باید حداقل ۲ حرف باشد.");
      return false;
    }

    if (normalizedLastName.length < 2) {
      setError(
        "نام خانوادگی باید حداقل ۲ حرف باشد.",
      );
      return false;
    }

    if (!/^09\d{9}$/.test(normalizePhone(phone))) {
      setError(
        "شماره موبایل باید با 09 شروع شود و ۱۱ رقم باشد.",
      );
      return false;
    }

    if (
      normalizedEmail &&
      !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(
        normalizedEmail,
      )
    ) {
      setError("ایمیل واردشده معتبر نیست.");
      return false;
    }

    return true;
  }

  async function startSignup(
    event?: FormEvent,
  ): Promise<void> {
    event?.preventDefault();
    setError("");

    if (!validateDetails()) return;

    setLoading(true);

    try {
      const result = await api<{
        resend_after: number;
      }>("auth/signup/start", {
        method: "POST",
        body: JSON.stringify({
          first_name: firstName.trim(),
          last_name: lastName.trim(),
          phone: normalizePhone(phone),
          email: email.trim() || null,
          referral_code:
            referralCode.trim().toUpperCase(),
        }),
      });

      setResendSeconds(result.resend_after);
      setCode("");
      setStep("verify");
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }

  async function verifySignup(
    event: FormEvent,
  ): Promise<void> {
    event.preventDefault();
    setError("");

    if (!/^\d{6}$/.test(code)) {
      setError("کد ۶ رقمی پیامک‌شده را وارد کنید.");
      return;
    }

    setLoading(true);

    try {
      const result = await api<{
        setup_token: string;
      }>("auth/signup/verify", {
        method: "POST",
        body: JSON.stringify({
          phone: normalizePhone(phone),
          code,
        }),
      });

      setSetupToken(result.setup_token);
      setStep("password");
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }

  async function completeSignup(
    event: FormEvent,
  ): Promise<void> {
    event.preventDefault();
    setError("");

    if (!setupToken) {
      setError(
        "اطلاعات تأیید معتبر نیست؛ ثبت‌نام را دوباره شروع کنید.",
      );
      setStep("details");
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

    setLoading(true);

    try {
      await api("auth/signup/complete", {
        method: "POST",
        body: JSON.stringify({
          setup_token: setupToken,
          password,
        }),
      });

      const loginResponse = await fetch(
        "/api/auth/login",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            identifier: normalizePhone(phone),
            password,
            otp_code: "",
          }),
        },
      );

      if (!loginResponse.ok) {
        window.location.assign(
          "/login?registered=1",
        );
        return;
      }

      window.location.assign("/app/dashboard");
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }

  function revealPassword(): void {
    if (hidePasswordTimer.current) {
      clearTimeout(hidePasswordTimer.current);
    }

    setShowPassword(true);

    hidePasswordTimer.current = setTimeout(() => {
      setShowPassword(false);
    }, 5000);
  }

  const stepOrder: Step[] = [
    "details",
    "verify",
    "password",
  ];

  return (
    <main className="flex min-h-dvh items-start justify-center overflow-y-auto bg-slate-50 p-4 pt-6 sm:items-center sm:p-6">
      <Card className="w-full max-w-lg border-white/70 bg-white/90 shadow-2xl shadow-slate-900/10">
        <CardHeader className="space-y-3 text-center">
          <div className="mx-auto flex size-12 items-center justify-center rounded-2xl bg-primary/10 text-primary">
            {step === "details" ? (
              <UserRound />
            ) : step === "verify" ? (
              <Phone />
            ) : (
              <KeyRound />
            )}
          </div>

          <CardTitle className="text-2xl">
            ساخت حساب کاربری
          </CardTitle>

          <CardDescription>
            {step === "details" &&
              "اطلاعات اولیه خود را وارد کنید."}

            {step === "verify" &&
              `کد ۶ رقمی ارسال‌شده به ${phone} را وارد کنید.`}

            {step === "password" &&
              "شماره موبایل تأیید شد؛ حالا رمز عبور خود را بسازید."}
          </CardDescription>

          <div className="flex justify-center gap-2 pt-2">
            {stepOrder.map((item, index) => (
              <span
                key={item}
                className={`h-1.5 w-16 rounded-full ${
                  stepOrder.indexOf(step) >= index
                    ? "bg-primary"
                    : "bg-slate-200"
                }`}
              />
            ))}
          </div>
        </CardHeader>

        <CardContent>
          {step === "details" && (
            <form
              onSubmit={startSignup}
              className="space-y-4"
              noValidate
            >
              <div className="grid gap-4 sm:grid-cols-2">
                <label className="space-y-2 text-sm font-medium">
                  <span>نام</span>

                  <Input
                    value={firstName}
                    onChange={(event) =>
                      setFirstName(event.target.value)
                    }
                    placeholder="نام خود را وارد کنید:"
                    autoComplete="given-name"
                  />
                </label>

                <label className="space-y-2 text-sm font-medium">
                  <span>نام خانوادگی</span>

                  <Input
                    value={lastName}
                    onChange={(event) =>
                      setLastName(event.target.value)
                    }
                    placeholder="نام خانوادگی خود را وارد کنید:"
                    autoComplete="family-name"
                  />
                </label>
              </div>

              <label className="block space-y-2 text-sm font-medium">
                <span>شماره موبایل</span>

                <Input
                  dir="ltr"
                  type="tel"
                  inputMode="numeric"
                  autoComplete="tel"
                  maxLength={11}
                  value={phone}
                  onChange={(event) => {
                    const normalized = toEnglishDigits(
                      event.target.value,
                    )
                      .replace(/\D/g, "")
                      .slice(0, 11);

                    setPhone(normalized);
                  }}
                  className="text-left"
                  placeholder="شماره موبایل خود را وارد کنید:"
                />
              </label>

              <label className="block space-y-2 text-sm font-medium">
                <span className="flex items-center gap-1">
                  ایمیل
                  <small className="text-xs font-normal text-muted-foreground">
                    (اختیاری)
                  </small>
                </span>

                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" />

                  <Input
                    dir="ltr"
                    type="email"
                    value={email}
                    onChange={(event) =>
                      setEmail(event.target.value)
                    }
                    className="pl-10 text-left"
                    placeholder="ایمیل خود را وارد کنید:"
                    autoComplete="email"
                  />
                </div>
              </label>

              <label className="block space-y-2 text-sm font-medium">
                <span className="flex items-center gap-1">
                  کد معرف
                  <small className="text-xs font-normal text-muted-foreground">
                    (اختیاری)
                  </small>
                </span>

                <Input
                  dir="ltr"
                  value={referralCode}
                  onChange={(event) =>
                    setReferralCode(
                      event.target.value.toUpperCase(),
                    )
                  }
                  className="text-left"
                  placeholder="کد معرف خود را وارد کنید:"
                  maxLength={16}
                />
              </label>

              <Button
                type="submit"
                className="w-full"
                size="lg"
                disabled={loading}
              >
                {loading ? (
                  "در حال ارسال..."
                ) : (
                  <>
                    ارسال کد تأیید
                    <ArrowLeft />
                  </>
                )}
              </Button>
            </form>
          )}

          {step === "verify" && (
            <form
              onSubmit={verifySignup}
              className="space-y-4"
              noValidate
            >
              <Input
                dir="ltr"
                inputMode="numeric"
                autoComplete="one-time-code"
                value={code}
                onChange={(event) => {
                  const normalized = toEnglishDigits(
                    event.target.value,
                  )
                    .replace(/\D/g, "")
                    .slice(0, 6);

                  setCode(normalized);
                }}
                className="h-12 text-center tracking-[.4em]"
                placeholder="کد ۶ رقمی"
                maxLength={6}
              />

              <div className="flex flex-col gap-3 sm:flex-row">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => startSignup()}
                  disabled={
                    loading || resendSeconds > 0
                  }
                >
                  {resendSeconds > 0
                    ? `${resendSeconds.toLocaleString(
                        "fa-IR",
                      )} ثانیه`
                    : "ارسال دوباره"}
                </Button>

                <Button
                  type="submit"
                  className="flex-1"
                  size="lg"
                  disabled={
                    loading || code.length !== 6
                  }
                >
                  {loading
                    ? "در حال بررسی..."
                    : "تأیید شماره موبایل"}
                </Button>
              </div>

              <button
                type="button"
                className="w-full text-sm text-primary hover:underline"
                onClick={() => {
                  setError("");
                  setCode("");
                  setStep("details");
                }}
              >
                ویرایش شماره موبایل
              </button>

              <p className="flex gap-2 rounded-xl bg-amber-50 p-3 text-xs leading-6 text-amber-800">
                <ShieldCheck className="mt-1 size-4 shrink-0" />
                کد را در اختیار دیگران قرار ندهید؛
                پشتیبانی هرگز این کد را درخواست
                نمی‌کند.
              </p>
            </form>
          )}

          {step === "password" && (
            <form
              onSubmit={completeSignup}
              className="space-y-4"
              noValidate
            >
              <p className="flex items-center gap-2 rounded-xl bg-emerald-50 p-3 text-sm text-emerald-700">
                <CheckCircle2 className="size-5" />
                شماره موبایل شما با موفقیت تأیید شد.
              </p>

              <label className="block space-y-2 text-sm font-medium">
                <span>رمز عبور</span>

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
                    setPassword(event.target.value)
                  }
                  placeholder="حداقل ۸ کاراکتر"
                />
              </label>

              <label className="block space-y-2 text-sm font-medium">
                <span>تکرار رمز عبور</span>

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
                  placeholder="رمز عبور را دوباره وارد کنید"
                />
              </label>

              <div className="flex flex-col items-stretch justify-between gap-3 sm:flex-row sm:items-center">
                <p className="text-xs leading-6 text-muted-foreground">
                  شامل حرف بزرگ، حرف کوچک و عدد
                </p>

                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={
                    showPassword
                      ? () =>
                          setShowPassword(false)
                      : revealPassword
                  }
                >
                  {showPassword ? (
                    <>
                      <EyeOff />
                      مخفی‌کردن
                    </>
                  ) : (
                    <>
                      <Eye />
                      نمایش ۵ ثانیه
                    </>
                  )}
                </Button>
              </div>

              <Button
                type="submit"
                className="w-full"
                size="lg"
                disabled={loading}
              >
                {loading
                  ? "در حال ساخت حساب..."
                  : "تکمیل ثبت‌نام"}
              </Button>
            </form>
          )}

          {error && (
            <p className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">
              {error}
            </p>
          )}

          <p className="mt-6 text-center text-sm text-muted-foreground">
            حساب دارید؟{" "}
            <Link
              href="/login"
              className="font-semibold text-primary"
            >
              وارد شوید
            </Link>
          </p>
        </CardContent>
      </Card>
    </main>
  );
}
