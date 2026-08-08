import { PublicFooter } from "@/components/public-footer";
import { PublicHeader } from "@/components/public-header";

export default function PrivacyPage() {
  return <main><PublicHeader /><article className="mx-auto max-w-4xl px-5 py-14"><h1 className="text-4xl font-black">حریم خصوصی</h1><div className="mt-8 space-y-5 leading-8 text-slate-600"><p>چکاه فقط اطلاعات لازم برای ارائه خدمات، امنیت حساب، پرداخت، پشتیبانی و بهبود کیفیت سامانه را پردازش می‌کند.</p><p>رمز عبور به‌صورت هش‌شده نگهداری می‌شود و اطلاعات کامل کارت بانکی ذخیره نمی‌شود. اسناد کاربران فقط طبق سطح دسترسی مجاز در دسترس هستند.</p><p>کاربر می‌تواند برای اصلاح اطلاعات یا پیگیری حذف حساب از مرکز پشتیبانی درخواست ثبت کند. رویدادهای امنیتی برای جلوگیری از سوءاستفاده ثبت می‌شوند.</p></div></article><PublicFooter /></main>;
}
