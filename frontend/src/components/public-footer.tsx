import Link from "next/link";
import { ArrowUpLeft, Scale, ShieldCheck } from "lucide-react";

const groups = [
  { title:"خدمات", links:[["دستیار هوشمند","/app/chat"],["مرکز قوانین","/app/laws"],["ابزارهای مالیاتی","/app/tools"],["مشاوران","/advisors"]] },
  { title:"چکاه", links:[["درباره ما","/about"],["مقاله‌ها","/blog"],["تعرفه‌ها","/pricing"],["تماس با ما","/contact"]] },
  { title:"راهنما", links:[["پشتیبانی","/app/tickets"],["حریم خصوصی","/privacy"],["شرایط استفاده","/terms"],["امنیت حساب","/app/security"]] },
];

export function PublicFooter(){return <footer className="luxe-footer"><div className="luxe-container luxe-footer-top"><div className="luxe-footer-brand"><span><Scale/></span><h2>چکاه</h2><p>دستیار هوشمند، مرکز قوانین، ابزارهای مالیاتی و شبکه مشاوران؛ برای تصمیم‌های شفاف‌تر و قابل پیگیری.</p><div><ShieldCheck/> حفاظت از اطلاعات کاربران</div></div><div className="luxe-footer-links">{groups.map(group=><section key={group.title}><h3>{group.title}</h3>{group.links.map(([label,href])=><Link href={href} key={href}>{label}<ArrowUpLeft/></Link>)}</section>)}</div></div><div className="luxe-footer-bottom"><div className="luxe-container"><span>© {new Date().getFullYear()} چکاه؛ همه حقوق محفوظ است.</span><span>پاسخ هوشمند جایگزین بررسی تخصصی پرونده نیست.</span></div></div></footer>}
