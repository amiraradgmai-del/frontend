import Link from "next/link";
import {
  ArrowLeft,
  BookOpen,
  BookOpenCheck,
  Bot,
  Calculator,
  CheckCircle2,
  MapPin,
  Search,
  ShieldCheck,
  Star,
  UserRoundCheck,
} from "lucide-react";
import { PublicFooter } from "@/components/public-footer";
import { PublicHeader } from "@/components/public-header";

type Advisor = {
  slug: string;
  full_name: string;
  professional_title: string;
  city: string;
  rating: number;
  review_count: number;
  years_experience: number;
  specialties: string[];
};

async function bestAdvisors(): Promise<Advisor[]> {
  try {
    const response = await fetch(
      `${process.env.BACKEND_URL ?? "http://localhost:8000"}/api/v1/consultations/public/advisors?limit=24`,
      { next: { revalidate: 300 } },
    );
    return response.ok ? response.json() : [];
  } catch {
    return [];
  }
}

export default async function Home() {
  const advisors = await bestAdvisors();
  const cities = [
    ...new Set(advisors.map((item) => item.city).filter(Boolean)),
  ].slice(0, 10);
  return (
    <main>
      <PublicHeader showBrandDescription />
      <section className="mx-auto grid max-w-6xl items-center gap-12 px-5 py-16 lg:grid-cols-2">
        <div>
          <p className="text-sm font-bold text-primary">
            قانون را سریع‌تر و مطمئن‌تر پیدا کنید
          </p>
          <h1 className="mt-4 text-4xl font-black leading-[1.5] sm:text-5xl">
            دستیار هوشمند برای پاسخ‌های مالیاتی و ارتباط با مشاور متخصص
          </h1>
          <p className="mt-5 max-w-xl leading-8 text-muted-foreground">
            جست‌وجوی قوانین، گفت‌وگوی هوشمند، ابزارهای محاسباتی و مشاوره تخصصی
            در یک سامانه امن.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link
              href="/signup"
              className="flex items-center gap-2 rounded-xl bg-primary px-6 py-3 font-bold text-primary-foreground"
            >
              شروع رایگان <ArrowLeft className="size-4" />
            </Link>
            <Link
              href="/pricing"
              className="rounded-xl border bg-white px-6 py-3 font-bold"
            >
              مشاهده پلن‌ها
            </Link>
          </div>
        </div>
        <div className="relative rounded-[2rem] bg-gradient-to-br from-sky-500 via-blue-600 to-cyan-500 p-7 text-white shadow-2xl shadow-blue-500/25">
          <div className="relative grid gap-4 sm:grid-cols-2">
            <Feature
              icon={BookOpenCheck}
              title="بانک دانش"
              text="قوانین دسته‌بندی‌شده و قابل جست‌وجو"
            />
            <Feature
              icon={Bot}
              title="پاسخ هوشمند"
              text="پاسخ کوتاه و متناسب با پرسش شما"
            />
            <Feature
              icon={UserRoundCheck}
              title="مرکز مشاوران"
              text="رزرو آنلاین یا حضوری با متخصص"
            />
            <Feature
              icon={ShieldCheck}
              title="فضای امن"
              text="کنترل دسترسی و حفظ اطلاعات کاربران"
            />
          </div>
        </div>
      </section>
      <section className="border-y border-sky-100 bg-white/70 py-8">
        <div className="mx-auto grid max-w-6xl gap-4 px-5 sm:grid-cols-2 lg:grid-cols-4">
          <Trust title="محرمانگی اطلاعات" text="کنترل دسترسی و حفاظت از اسناد" />
          <Trust title="پاسخ مستند" text="نمایش قانون، ماده و منبع پاسخ" />
          <Trust title="دسترسی به متخصص" text="ارجاع پرونده‌های حساس به مشاور" />
          <Trust title="ابزارهای کاربردی" text="محاسبات و تحلیل‌های مالیاتی" />
        </div>
      </section>
      <section className="mx-auto max-w-6xl px-5 py-16">
        <div className="text-center">
          <p className="text-sm font-bold text-blue-600">خدمات تخصصی چکاه</p>
          <h2 className="mt-2 text-3xl font-black">از پرسش مالیاتی تا تصمیم قابل اجرا</h2>
          <p className="mx-auto mt-3 max-w-2xl text-sm leading-7 text-slate-600">هر خدمت مسیر مشخص، خروجی قابل بررسی و امکان ادامه با کارشناس انسانی دارد.</p>
        </div>
        <div className="mt-8 grid gap-5 md:grid-cols-2 lg:grid-cols-4">
          <Service icon={Bot} title="دستیارهای تخصصی" text="پاسخ‌گویی مالیاتی، حسابداری، حقوقی و راهنمای سامانه" href="/app/chat" />
          <Service icon={BookOpenCheck} title="مرکز قوانین" text="جست‌وجوی قانون، ماده، تبصره و بخشنامه‌های مالیاتی" href="/app/laws" />
          <Service icon={Calculator} title="ابزارهای مالیاتی" text="محاسبات کاربردی و تهیه خودکار صورت‌های مالی" href="/app/tools" />
          <Service icon={UserRoundCheck} title="مشاوره تخصصی" text="انتخاب، رزرو و پیگیری مشاوره با متخصص تأییدشده" href="/advisors" />
        </div>
      </section>
      <section className="bg-gradient-to-b from-blue-950 to-slate-950 py-16 text-white">
        <div className="mx-auto max-w-6xl px-5">
          <p className="text-sm font-bold text-cyan-300">فرایند استفاده</p>
          <h2 className="mt-2 text-3xl font-black">از مسئله تا نتیجه، مرحله‌به‌مرحله</h2>
          <div className="mt-9 grid gap-5 md:grid-cols-2 lg:grid-cols-4">
            <Step number="۱" title="ثبت مسئله" text="سؤال، فایل یا نیاز مالیاتی خود را وارد کنید." />
            <Step number="۲" title="بررسی تخصصی" text="موضوع و ریسک درخواست به‌صورت خودکار تشخیص داده می‌شود." />
            <Step number="۳" title="پاسخ و مستندات" text="نتیجه همراه منبع، سطح اطمینان و اقدام پیشنهادی نمایش داده می‌شود." />
            <Step number="۴" title="بررسی انسانی" text="در موارد حساس، درخواست را برای مشاور متخصص ارسال کنید." />
          </div>
        </div>
      </section>
      <section className="mx-auto max-w-6xl px-5 py-16">
        <div className="mb-6">
          <p className="text-sm font-bold text-blue-600">دسترسی سریع</p>
          <h2 className="mt-2 text-2xl font-black">
            مسیر موردنظر خود را انتخاب کنید
          </h2>
        </div>
        <div className="grid gap-5 lg:grid-cols-[1.1fr_.9fr]">
          <Link
            href="/app/laws"
            className="group rounded-[2rem] bg-gradient-to-l from-blue-700 via-blue-600 to-cyan-500 p-7 text-white shadow-xl transition hover:-translate-y-1"
          >
            <BookOpen className="size-12" />
            <h3 className="mt-5 text-2xl font-black">مرکز قوانین و مقررات</h3>
            <p className="mt-3 text-sm leading-7 text-blue-50">
              جست‌وجوی سریع قوانین، مواد و تبصره‌های مالیاتی.
            </p>
            <span className="mt-8 flex w-fit items-center gap-2 rounded-xl bg-white px-4 py-2.5 text-sm font-bold text-blue-700">
              ورود به مرکز قوانین <Search className="size-4" />
            </span>
          </Link>
          <div className="rounded-[2rem] border border-emerald-200 bg-gradient-to-br from-emerald-50 via-teal-50/70 to-white p-7 shadow-lg shadow-emerald-900/5">
            <div className="flex items-center justify-between">
              <span className="flex size-12 items-center justify-center rounded-2xl bg-emerald-100 text-emerald-700">
                <UserRoundCheck />
              </span>
              <Star className="fill-teal-500 text-teal-500" />
            </div>
            <h3 className="mt-5 text-2xl font-black">
              بهترین مشاوران مالیاتی ایران
            </h3>
            <p className="mt-2 text-sm leading-7 text-slate-600">
              مشاور برتر شهر خود را براساس امتیاز و تخصص پیدا کنید.
            </p>
            <div className="mt-5 flex flex-wrap gap-2">
              {cities.length ? (
                cities.map((city) => (
                  <Link
                    key={city}
                    href={`/app/consultations/independent?city=${encodeURIComponent(city)}`}
                    className="rounded-full border border-emerald-200 bg-white px-3 py-1.5 text-xs font-bold text-emerald-700"
                  >
                    بهترین مشاوران {city}
                  </Link>
                ))
              ) : (
                <span className="text-xs text-slate-400">
                  شهرها پس از تکمیل پروفایل مشاوران نمایش داده می‌شوند.
                </span>
              )}
            </div>
            <Link
              href="/app/consultations/independent"
              className="mt-6 flex w-fit items-center gap-2 rounded-xl bg-gradient-to-l from-emerald-600 to-teal-600 px-4 py-2.5 text-sm font-bold text-white shadow-md shadow-emerald-600/20"
            >
              فهرست همه مشاوران <ArrowLeft className="size-4" />
            </Link>
          </div>
        </div>
      </section>
      <section
        id="top-advisors"
        className="scroll-mt-24 border-y border-sky-100 bg-gradient-to-b from-sky-50/70 to-white py-16"
      >
        <div className="mx-auto max-w-6xl px-5">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="text-sm font-bold text-orange-600">
                منتخب سراسر کشور
              </p>
              <h2 className="mt-2 text-3xl font-black">
                مشاوران مالیاتی برتر ایران
              </h2>
              <p className="mt-3 text-sm text-slate-600">
                رتبه‌بندی براساس امتیاز و نظر کاربران سامانه.
              </p>
            </div>
            <Link
              href="/login?next=/app/consultations/independent"
              className="text-sm font-bold text-blue-600"
            >
              ورود و مشاهده همه مشاوران
            </Link>
          </div>
          <div className="mt-8 space-y-3">
            {advisors.slice(0, 6).map((advisor) => (
              <Link
                key={advisor.slug}
                href="/login?next=/app/consultations/independent"
                className="group flex flex-col gap-4 rounded-2xl border border-sky-100 bg-white p-4 shadow-sm transition hover:border-blue-200 hover:shadow-lg sm:flex-row sm:items-center"
              >
                <span className="flex size-12 shrink-0 items-center justify-center rounded-2xl bg-blue-50 text-blue-600">
                  <UserRoundCheck />
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-3">
                    <h3 className="font-black">{advisor.full_name}</h3>
                    <span className="flex items-center gap-1 rounded-full bg-amber-50 px-2.5 py-1 text-xs font-bold text-amber-700">
                      <Star className="size-3.5 fill-amber-400" />
                      {advisor.rating.toLocaleString("fa-IR")}
                    </span>
                  </div>
                  <p className="mt-1 text-sm text-slate-500">
                    {advisor.professional_title}
                  </p>
                </div>
                <p className="flex shrink-0 items-center gap-2 text-sm text-slate-600">
                  <MapPin className="size-4 text-blue-500" />
                  {advisor.city || "آنلاین"} ·{" "}
                  {advisor.years_experience.toLocaleString("fa-IR")} سال سابقه
                </p>
                <div className="flex flex-wrap gap-1.5 sm:max-w-72">
                  {advisor.specialties.slice(0, 3).map((item) => (
                    <span
                      key={item}
                      className="rounded-full bg-sky-50 px-2.5 py-1 text-xs text-sky-700"
                    >
                      {item}
                    </span>
                  ))}
                </div>
                <ArrowLeft className="hidden size-5 shrink-0 text-blue-600 transition group-hover:-translate-x-1 sm:block" />
              </Link>
            ))}
            {!advisors.length && (
              <div className="rounded-2xl border border-dashed bg-white p-10 text-center text-sm text-slate-500">
                پس از تأیید مشاوران، فهرست برترین‌ها در این بخش نمایش داده
                می‌شود.
              </div>
            )}
          </div>
        </div>
      </section>
      <section className="mx-auto max-w-6xl px-5 py-16">
        <div className="rounded-[2rem] bg-gradient-to-l from-slate-900 to-blue-900 p-8 text-white sm:flex sm:items-center sm:justify-between sm:gap-8">
          <div>
            <p className="text-sm font-bold text-cyan-200">
              چکاه را بهتر بشناسید
            </p>
            <h2 className="mt-2 text-2xl font-black">
              شفافیت، منبع معتبر و دسترسی به متخصص
            </h2>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-blue-100">
              با مأموریت، خدمات و مرز مسئولیت دستیار هوشمند مالیاتی چکاه آشنا
              شوید.
            </p>
          </div>
          <Link
            href="/about"
            className="mt-6 inline-flex shrink-0 items-center gap-2 rounded-xl bg-white px-5 py-3 font-bold text-blue-800 sm:mt-0"
          >
            درباره ما <ArrowLeft className="size-4" />
          </Link>
        </div>
      </section>
      <PublicFooter />
    </main>
  );
}

function Feature({
  icon: Icon,
  title,
  text,
}: {
  icon: typeof Bot;
  title: string;
  text: string;
}) {
  return (
    <div className="rounded-2xl bg-white/15 p-5 backdrop-blur">
      <Icon className="mb-4 text-amber-200" />
      <h2 className="font-bold">{title}</h2>
      <p className="mt-2 text-xs leading-6 text-sky-50">{text}</p>
    </div>
  );
}

function Trust({ title, text }: { title: string; text: string }) {
  return <div className="flex gap-3 rounded-2xl p-3"><span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-blue-600"><CheckCircle2 className="size-5" /></span><div><h2 className="text-sm font-black">{title}</h2><p className="mt-1 text-xs leading-5 text-slate-500">{text}</p></div></div>;
}

function Service({ icon: Icon, title, text, href }: { icon: typeof Bot; title: string; text: string; href: string }) {
  return <Link href={href} className="group rounded-3xl border border-sky-100 bg-white p-6 shadow-sm transition hover:-translate-y-1 hover:border-blue-200 hover:shadow-xl"><span className="flex size-12 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-600 to-cyan-500 text-white"><Icon /></span><h3 className="mt-5 font-black">{title}</h3><p className="mt-2 min-h-14 text-xs leading-7 text-slate-600">{text}</p><span className="mt-5 flex items-center gap-2 text-xs font-bold text-blue-700">مشاهده و شروع <ArrowLeft className="size-3.5 transition group-hover:-translate-x-1" /></span></Link>;
}

function Step({ number, title, text }: { number: string; title: string; text: string }) {
  return <div className="rounded-3xl border border-white/10 bg-white/5 p-6"><span className="text-3xl font-black text-cyan-300">{number}</span><h3 className="mt-4 font-black">{title}</h3><p className="mt-2 text-xs leading-7 text-blue-100">{text}</p></div>;
}
