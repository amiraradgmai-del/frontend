import Link from "next/link";
import { cookies } from "next/headers";
import { ArrowLeft, Menu, ShieldCheck } from "lucide-react";
import { SiteBrand } from "@/components/site-theme-provider";
import { ArticleDropdown } from "@/components/article-dropdown";
import { accessCookie, refreshCookie } from "@/lib/backend";

const links = [
  ["خدمات", "/#services"], ["مشاوران", "/advisors"], ["قوانین مالیاتی", "/app/laws"],
  ["تعرفه‌ها", "/pricing"], ["درباره ما", "/about"], ["تماس با ما", "/contact"],
];

export async function PublicHeader({ showBrandDescription = false }: { showBrandDescription?: boolean }) {
  const store = await cookies();
  const loggedIn = store.has(accessCookie) || store.has(refreshCookie);
  return <header className="luxe-header">
    <div className="luxe-header-bar"><div className="luxe-container"><span>دستیار هوشمند و همراه مالیاتی شما</span><Link href="/app/chat">پرسش خود را مطرح کنید <ArrowLeft/></Link></div></div>
    <div className="luxe-container luxe-header-main">
      <SiteBrand showDescription={showBrandDescription} />
      <nav className="luxe-nav">
        {links.slice(0,2).map(([label,href])=><Link href={href} key={href}>{label}</Link>)}
        <ArticleDropdown />
        {links.slice(2).map(([label,href])=><Link href={href} key={href}>{label}</Link>)}
      </nav>
      <div className="luxe-header-actions"><Link href={loggedIn?"/app/dashboard":"/login"}><ShieldCheck/>{loggedIn?"ورود به پنل":"ورود و ثبت‌نام"}</Link><details><summary aria-label="بازکردن منو"><Menu/></summary><nav>{links.map(([label,href])=><Link href={href} key={href}>{label}</Link>)}<Link href="/blog">مقاله‌ها</Link></nav></details></div>
    </div>
  </header>;
}
