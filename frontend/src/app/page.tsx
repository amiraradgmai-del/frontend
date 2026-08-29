import Link from "next/link";
import { ArrowLeft, Bot, BookOpenCheck, Calculator, Check, FileSearch, Scale, ShieldCheck, Sparkles, UserRoundCheck } from "lucide-react";
import { PublicFooter } from "@/components/public-footer";
import { PublicHeader } from "@/components/public-header";

const services = [
  { icon: Bot, title: "دستیار هوشمند مالیاتی", text: "پرسش خود را مطرح کنید و پاسخ مستند، مرحله‌بندی‌شده و قابل پیگیری دریافت کنید.", href: "/app/chat", number: "01" },
  { icon: BookOpenCheck, title: "مرکز قوانین و مقررات", text: "قانون، ماده، تبصره و بخشنامه موردنیازتان را سریع و دقیق پیدا کنید.", href: "/app/laws", number: "02" },
  { icon: Calculator, title: "ابزارهای مالی و مالیاتی", text: "محاسبات کاربردی و تهیه صورت‌های مالی را در یک فضای کنترل‌شده انجام دهید.", href: "/app/tools", number: "03" },
  { icon: UserRoundCheck, title: "مشاوره با متخصص", text: "مشاور مناسب را براساس تخصص، شهر، امتیاز و زمان آزاد انتخاب و رزرو کنید.", href: "/advisors", number: "04" },
];

const steps = [
  ["نیازتان را مشخص کنید", "پرسش، سند، محاسبه یا موضوع پرونده را انتخاب کنید."],
  ["اطلاعات را ثبت کنید", "جزئیات لازم را در مسیر کوتاه و مرحله‌ای وارد کنید."],
  ["پاسخ قابل بررسی بگیرید", "نتیجه، منبع و اقدام بعدی را شفاف مشاهده کنید."],
  ["در صورت نیاز ارجاع دهید", "موضوعات حساس را مستقیم برای مشاور متخصص بفرستید."],
];

export default function Home() {
  return <main className="luxe-site">
    <PublicHeader showBrandDescription />
    <section className="luxe-hero"><div className="luxe-container luxe-hero-grid">
      <div className="luxe-hero-copy"><span className="luxe-eyebrow"><Sparkles className="size-4" /> دستیار هوشمند امور مالیاتی</span><h1>مسائل مالیاتی را<br/><span>ساده، مستند و مطمئن</span><br/>مدیریت کنید.</h1><p>از پیدا کردن قانون و پاسخ پرسش تا محاسبه، بررسی سند و ارتباط با مشاور؛ چکاه مسیر انجام کار را کوتاه، روشن و قابل پیگیری می‌کند.</p><div className="luxe-actions"><Link href="/signup" className="luxe-primary">شروع رایگان <ArrowLeft /></Link><Link href="/app/chat" className="luxe-secondary">مشاهده دستیار هوشمند</Link></div><div className="luxe-proof"><span><Check /> پاسخ مبتنی بر منبع</span><span><Check /> اطلاعات محرمانه</span><span><Check /> ارجاع به متخصص</span></div></div>
      <div className="luxe-hero-panel"><div className="luxe-panel-top"><span><Bot /></span><div><b>چکاه آماده پاسخ‌گویی است</b><small>موضوع مالیاتی خود را انتخاب کنید</small></div></div><div className="luxe-panel-search"><FileSearch /><span>مثلاً: مهلت اعتراض به برگ تشخیص چقدر است؟</span></div><div className="luxe-panel-options"><Link href="/app/chat">پرسش مالیاتی <ArrowLeft /></Link><Link href="/app/laws">جست‌وجوی قانون <ArrowLeft /></Link><Link href="/advisors">رزرو مشاور <ArrowLeft /></Link></div><div className="luxe-panel-note"><ShieldCheck /> پاسخ هوشمند در موارد حساس جایگزین بررسی مشاور نیست.</div></div>
    </div></section>
    <section className="luxe-trust"><div className="luxe-container"><p>یک مسیر یکپارچه برای امور مالیاتی</p><div><span>قوانین و بخشنامه‌ها</span><span>پاسخ هوشمند</span><span>محاسبات مالی</span><span>مشاوران تأییدشده</span><span>پیگیری درخواست</span></div></div></section>
    <section className="luxe-section luxe-services"><div className="luxe-container"><div className="luxe-heading"><div><span>خدمات چکاه</span><h2>هر ابزار لازم، در جای درست</h2></div><p>به‌جای جابه‌جایی میان سامانه‌ها و منابع پراکنده، مسیر کامل کار را در یک محیط منظم انجام دهید.</p></div><div className="luxe-service-grid">{services.map(({icon:Icon,...item}) => <Link href={item.href} key={item.href} className="luxe-service-card"><div className="luxe-service-meta"><span><Icon /></span><b>{item.number}</b></div><h3>{item.title}</h3><p>{item.text}</p><i>مشاهده خدمت <ArrowLeft /></i></Link>)}</div></div></section>
    <section className="luxe-section luxe-process"><div className="luxe-container luxe-process-grid"><div className="luxe-process-intro"><span>فرایند روشن</span><h2>از مسئله تا پاسخ، فقط چهار گام</h2><p>هر مرحله مشخص است؛ می‌دانید چه اطلاعاتی لازم است، نتیجه از کجا آمده و قدم بعدی چیست.</p><Link href="/signup">ساخت حساب کاربری <ArrowLeft /></Link></div><div className="luxe-steps">{steps.map((step,index)=><article key={step[0]}><b>۰{index+1}</b><div><h3>{step[0]}</h3><p>{step[1]}</p></div></article>)}</div></div></section>
    <section className="luxe-section"><div className="luxe-container luxe-split"><div className="luxe-dark-card"><span>برای پرونده‌های مهم</span><h2>هوش مصنوعی، همراه با امکان بررسی انسانی</h2><p>اگر پاسخ نیازمند قضاوت تخصصی، بررسی سند یا تصمیم پرریسک باشد، همان موضوع را بدون شروع دوباره برای مشاور ارسال کنید.</p><ul><li><Check/> انتخاب مشاور براساس تخصص</li><li><Check/> رزرو آنلاین و پیگیری جلسه</li><li><Check/> نگهداری سابقه درخواست‌ها</li></ul><Link href="/advisors">مشاهده مشاوران <ArrowLeft/></Link></div><div className="luxe-quote"><Scale/><blockquote>هدف چکاه فقط ارائه یک جواب نیست؛ کاربر باید منبع، میزان اطمینان و اقدام بعدی را هم بداند.</blockquote><p>پاسخ شفاف، تصمیم مطمئن‌تر</p></div></div></section>
    <section className="luxe-cta"><div className="luxe-container"><div><span>آماده‌اید؟</span><h2>اولین مسئله مالیاتی خود را با چکاه حل کنید.</h2></div><div><Link href="/signup" className="luxe-primary">شروع رایگان <ArrowLeft/></Link><Link href="/pricing" className="luxe-secondary luxe-secondary-light">مشاهده تعرفه‌ها</Link></div></div></section>
    <PublicFooter />
  </main>;
}
