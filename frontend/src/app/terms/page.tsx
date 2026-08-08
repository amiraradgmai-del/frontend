import { PublicFooter } from "@/components/public-footer";
import { PublicHeader } from "@/components/public-header";

export default function TermsPage() {
  return <main><PublicHeader /><article className="mx-auto max-w-4xl px-5 py-14"><h1 className="text-4xl font-black">شرایط استفاده</h1><div className="mt-8 space-y-5 leading-8 text-slate-600"><p>استفاده از چکاه به معنی پذیرش قوانین سامانه، رعایت حقوق دیگران و ارائه اطلاعات صحیح است.</p><p>پاسخ هوشمند برای راهنمایی عمومی است و در پرونده‌های حساس جایگزین بررسی اسناد توسط متخصص یا مرجع قانونی نیست.</p><p>خرید اشتراک، ظرفیت‌ها و مدت درج‌شده در زمان پرداخت را فعال می‌کند. شرایط لغو رزرو و بازپرداخت پیش از تأیید نهایی به کاربر نمایش داده می‌شود.</p><p>هرگونه استفاده غیرمجاز، تلاش برای نفوذ، انتشار محتوای مجرمانه یا سوءاستفاده از منابع سامانه می‌تواند باعث محدودشدن حساب شود.</p></div></article><PublicFooter /></main>;
}
