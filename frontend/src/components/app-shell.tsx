"use client";

import Link from "next/link";
import { ArticleDropdown } from "@/components/article-dropdown";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  BadgeCheck,
  BarChart3,
  Bell,
  BookOpen,
  CalendarDays,
  Camera,
  ClipboardCheck,
  ContactRound,
  CreditCard,
  Database,
  FileText,
  FileSpreadsheet,
  Headphones,
  History,
  LayoutDashboard,
  LockKeyhole,
  LogOut,
  Menu,
  MessageCircle,
  MessageCircleQuestion,
  Newspaper,
  Phone,
  Scale,
  Send,
  Settings,
  ShieldCheck,
  Tags,
  TicketCheck,
  UploadCloud,
  UserCog,
  Users,
  WalletCards,
  Wrench,
  X,
} from "lucide-react";

import { api } from "@/lib/api";
import type { User } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useSiteConfiguration } from "@/components/site-theme-provider";
import { SupportLauncher } from "@/components/support-launcher";

const navigation = [
  {
    href: "/app/dashboard",
    label: "صفحه اصلی",
    icon: LayoutDashboard,
  },
  {
    href: "/app/chat",
    label: "گفت‌وگوی مالیاتی",
    icon: MessageCircleQuestion,
  },
  {
    href: "/app/history",
    label: "تاریخچه گفتگو",
    icon: History,
  },
  {
    href: "/app/calendar",
    label: "تقویم و اعلان‌ها",
    icon: CalendarDays,
  },
  {
    href: "/app/notifications",
    label: "اعلان‌های سامانه",
    icon: Bell,
  },
  {
    href: "/app/tools",
    label: "ابزارهای مالیاتی",
    icon: Wrench,
  },
  {
    href: "/app/laws",
    label: "مرکز قوانین",
    icon: BookOpen,
  },
  {
    href: "/app/usage",
    label: "مصرف و امتیاز",
    icon: BarChart3,
  },
  {
    href: "/app/plans",
    label: "اشتراک و پرداخت",
    icon: CreditCard,
  },
  {
    href: "/app/wallet",
    label: "کیف پول",
    icon: WalletCards,
  },
  {
    href: "/app/documents",
    label: "اسناد من",
    icon: UploadCloud,
  },
  {
    href: "/app/financial-statements",
    label: "تهیه صورت‌های مالی",
    icon: FileSpreadsheet,
  },
  {
    href: "/app/tickets",
    label: "چت پشتیبانی",
    icon: TicketCheck,
  },
  {
    href: "/app/consultations",
    label: "مرکز مشاوران",
    icon: Headphones,
  },
  {
    href: "/app/consultant-verification",
    label: "همکاری به‌عنوان مشاور",
    icon: BadgeCheck,
  },
  {
    href: "/app/profile",
    label: "پروفایل و امتیاز",
    icon: UserCog,
  },
  {
    href: "/app/security",
    label: "امنیت حساب",
    icon: ShieldCheck,
  },
];

const publicNavigation = [
  { href: "/advisors", label: "لیست مشاوران", icon: Users },
  { href: "/blog", label: "مقاله‌ها", icon: Newspaper },
  { href: "/laws", label: "قوانین مالیاتی", icon: Scale },
  { href: "/pricing", label: "تعرفه‌ها", icon: Tags },
  { href: "/about", label: "درباره ما", icon: ContactRound },
  { href: "/contact", label: "تماس", icon: Phone },
];

const managedNavigation = [
  {
    href: "/management",
    label: "مرکز کنترل سایت",
    icon: LayoutDashboard,
    permission: "users:manage",
  },
  {
    href: "/management/users",
    label: "مدیریت کاربران",
    icon: Users,
    permission: "users:manage",
  },
  {
    href: "/management/consultants",
    label: "مدیریت مشاوران",
    icon: BadgeCheck,
    permission: "users:manage",
  },
  {
    href: "/management/payments",
    label: "پرداخت‌ها",
    icon: WalletCards,
    permission: "payments:manage",
  },
  {
    href: "/management/consultant-settlements",
    label: "تسویه مشاوران",
    icon: WalletCards,
    permission: "payments:manage",
  },
  {
    href: "/management/reports",
    label: "گزارش مالی و مصرف",
    icon: BarChart3,
    permission: "users:manage",
  },
  {
    href: "/management/announcements",
    label: "اعلان عمومی",
    icon: Bell,
    permission: "notifications:manage",
  },
  {
    href: "/management/audit",
    label: "فعالیت مدیران",
    icon: History,
    permission: "audit:read",
  },
  {
    href: "/management/discounts",
    label: "کدهای تخفیف",
    icon: Tags,
    permission: "payments:manage",
  },
  {
    href: "/management/subscriptions",
    label: "اشتراک‌ها",
    icon: CreditCard,
    permission: "subscriptions:manage",
  },
  {
    href: "/management/customer-documents",
    label: "اسناد کاربران",
    icon: FileText,
    permission: "user_documents:manage",
  },
  {
    href: "/management/datasets",
    label: "دیتاست و بانک دانش",
    icon: Database,
    permission: "documents:manage",
  },
  {
    href: "/management/laws",
    label: "مدیریت قوانین",
    icon: BookOpen,
    permission: "documents:manage",
  },
  {
    href: "/management/content",
    label: "صفحات و مقاله‌ها",
    icon: Newspaper,
    permission: "site:manage",
  },
  {
    href: "/management/tickets",
    label: "تیکت‌ها",
    icon: TicketCheck,
    permission: "tickets:manage",
  },
  {
    href: "/management/consultations",
    label: "مدیریت مشاوره‌ها",
    icon: ClipboardCheck,
    permission: "consultations:manage",
  },
  {
    href: "/management/chats",
    label: "نظارت گفتگوها",
    icon: MessageCircleQuestion,
    permission: "chats:manage",
  },
  {
    href: "/management/settings",
    label: "تنظیمات کل سامانه",
    icon: Settings,
    permission: "site:manage",
  },
];

const supportNavigation = [
  {
    href: "/support",
    label: "داشبورد پاسخ‌گویی",
    icon: LayoutDashboard,
    permission: "tickets:manage",
  },
  {
    href: "/support/tickets",
    label: "تیکت‌های کاربران",
    icon: TicketCheck,
    permission: "tickets:manage",
  },
  {
    href: "/support/consultations",
    label: "ارجاع به کارشناس",
    icon: ClipboardCheck,
    permission: "consultations:manage",
  },
  {
    href: "/support/consultant-approvals",
    label: "مدیریت مشاوران",
    icon: BadgeCheck,
    permission: "consultations:manage",
  },
  {
    href: "/support/consultant-settlements",
    label: "تسویه مشاوران",
    icon: WalletCards,
    permission: "payments:manage",
  },
  {
    href: "/management/content",
    label: "صفحات و مقاله‌ها",
    icon: Newspaper,
    permission: "site:manage",
  },
  {
    href: "/support/documents",
    label: "مدارک کاربران",
    icon: FileText,
    permission: "user_documents:manage",
  },
  {
    href: "/support/payments",
    label: "پرداخت و بازپرداخت",
    icon: WalletCards,
    permission: "payments:manage",
  },
  {
    href: "/support/announcements",
    label: "ارسال اعلان",
    icon: Bell,
    permission: "notifications:manage",
  },
];

const expertNavigation = [
  {
    href: "/consultant",
    label: "میزکار مشاور",
    icon: LayoutDashboard,
    permission: "consultations:handle",
  },
  {
    href: "/consultant/profile",
    label: "پروفایل حرفه‌ای",
    icon: UserCog,
    permission: "consultations:handle",
  },
  {
    href: "/consultant/tickets",
    label: "تیکت‌ها",
    icon: TicketCheck,
    permission: "tickets:manage",
  },
];

const roleLabels: Record<string, string> = {
  system_admin: "مدیر سامانه",
  admin: "ادمین",
  tax_expert: "کارشناس مالی",
  company_expert: "کارشناس شرکت",
  user: "کاربر",
};

const tierLabels = {
  normal: "عادی",
  plus: "پلاس",
  pro: "حرفه‌ای",
};

type ProfileStatus = {
  profile_score: number;
  profile_complete: boolean;
  missing_required_fields: string[];
};

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();

  const [user, setUser] = useState<User | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const [profileCompleted, setProfileCompleted] = useState<boolean | null>(
    null,
  );

  const { branding } = useSiteConfiguration();

  useEffect(() => {
    let active = true;

    const loadUser = async () => {
      try {
        const currentUser = await api<User>("users/me");

        if (!active) return;

        const isSystemAdmin = currentUser.roles.includes("system_admin");

        const isAdmin = currentUser.roles.includes("admin");

        const isExpert =
          currentUser.roles.includes("company_expert") ||
          currentUser.roles.includes("tax_expert");

        if (isSystemAdmin) {
          setProfileCompleted(true);
          setUser(currentUser);

          if (!pathname.startsWith("/management")) {
            router.replace("/management");
          }

          return;
        }

        if (isAdmin) {
          setProfileCompleted(true);
          setUser(currentUser);

          if (
            !pathname.startsWith("/support") &&
            !pathname.startsWith("/management/content")
          ) {
            router.replace("/support");
          }

          return;
        }

        if (isExpert) {
          setProfileCompleted(true);
          setUser(currentUser);

          if (!pathname.startsWith("/consultant")) {
            router.replace("/consultant");
          }

          return;
        }

        const profile = await api<ProfileStatus>("api/v1/portal/profile");

        if (!active) return;

        const profileCompleted = profile.profile_complete;

        const isProfilePage =
          pathname === "/app/profile" || pathname.startsWith("/app/profile/");
        const isSupportPage =
          pathname === "/app/tickets" || pathname.startsWith("/app/tickets/");

        setProfileCompleted(profileCompleted);
        setUser(currentUser);

        if (!profileCompleted && !isProfilePage && !isSupportPage) {
          router.replace("/app/profile");
          return;
        }

        if (!pathname.startsWith("/app")) {
          router.replace(profileCompleted ? "/app/dashboard" : "/app/profile");
        }
      } catch {
        if (active) {
          router.replace("/login");
        }
      }
    };

    void loadUser();

    window.addEventListener("focus", loadUser);

    return () => {
      active = false;
      window.removeEventListener("focus", loadUser);
    };
  }, [pathname, router]);

  async function logout() {
    await fetch("/api/auth/logout", {
      method: "POST",
    });

    window.location.assign("/login");
  }

  if (!user) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-sky-50 text-sm text-slate-500">
        در حال آماده‌سازی چکاه...
      </div>
    );
  }

  const role = user.roles.includes("system_admin")
    ? "system_admin"
    : user.roles.includes("admin")
      ? "admin"
      : user.roles.includes("company_expert")
        ? "company_expert"
        : user.roles.includes("tax_expert")
          ? "tax_expert"
          : "user";

  if (role === "user") {
    return (
      <>
        <UserShell
          user={user}
          branding={branding}
          pathname={pathname}
          menuOpen={menuOpen}
          setMenuOpen={setMenuOpen}
          logout={logout}
          profileCompleted={profileCompleted === true}
        >
          {children}
        </UserShell>
        <SupportLauncher />
      </>
    );
  }

  const visibleNavigation =
    role === "admin"
      ? supportNavigation.filter((item) =>
          user.permissions.includes(item.permission),
        )
      : ["company_expert", "tax_expert"].includes(role)
        ? expertNavigation.filter((item) =>
            user.permissions.includes(item.permission),
          )
        : managedNavigation;

  return (
    <div className="site-surface min-h-screen lg:grid lg:grid-cols-[280px_1fr]">
      <aside className="border-l border-white/25 bg-gradient-to-b from-cyan-500 via-blue-600 to-indigo-700 p-5 text-white shadow-2xl shadow-blue-950/20 lg:sticky lg:top-0 lg:flex lg:h-screen lg:flex-col">
        <Brand branding={branding} subtitle="مرکز مدیریت و پاسخ‌گویی" />

        <nav className="grid grid-cols-2 gap-2 lg:min-h-0 lg:flex-1 lg:grid-cols-1 lg:overflow-y-auto lg:[scrollbar-width:none] lg:[&::-webkit-scrollbar]:hidden">
          {visibleNavigation.map((item) => (
            <NavigationLink
              key={item.href}
              item={item}
              active={isNavigationActive(pathname, item.href)}
            />
          ))}
        </nav>

        <Account user={user} role={role} logout={logout} />
      </aside>

      <main className="min-w-0 p-4 sm:p-7 lg:p-10">
        <div className="mx-auto max-w-6xl">{children}</div>
      </main>
    </div>
  );
}

type Branding = {
  site_name: string;
  short_description: string;
  logo_url: string;
  support_email: string;
  support_phone: string;
  support_mobile: string;
  office_address: string;
  working_hours: string;
  legal_name: string;
  map_url: string;
  instagram_url: string;
  whatsapp_url: string;
  telegram_url: string;
};

function UserShell({
  user,
  branding,
  pathname,
  menuOpen,
  setMenuOpen,
  logout,
  profileCompleted,
  children,
}: {
  user: User;
  branding: Branding;
  pathname: string;
  menuOpen: boolean;
  setMenuOpen: (value: boolean) => void;
  logout: () => void;
  profileCompleted: boolean;
  children: React.ReactNode;
}) {
  const router = useRouter();
  const [profileNoticeOpen, setProfileNoticeOpen] = useState(false);

  function openProtectedPage(href: string) {
    const isProfileRoute =
      href === "/app/profile" || href.startsWith("/app/profile/");
    const isSupportRoute =
      href === "/app/tickets" || href.startsWith("/app/tickets/");

    if (!profileCompleted && !isProfileRoute && !isSupportRoute) {
      setMenuOpen(false);
      setProfileNoticeOpen(true);
      return;
    }

    setMenuOpen(false);
    router.push(href);
  }

  return (
    <div className="site-surface min-h-screen">
      <header className="sticky top-0 z-40 border-b border-sky-100/80 bg-white/95 shadow-sm backdrop-blur">
        <div className="mx-auto flex h-20 max-w-7xl items-center justify-between px-4 sm:px-6">
          <div className="flex items-center gap-3">
            <Button
              type="button"
              variant="outline"
              size="icon"
              className="size-11 rounded-2xl border-sky-200 bg-gradient-to-br from-white to-sky-50 text-blue-700 shadow-sm transition hover:-translate-y-0.5 hover:border-blue-300 hover:bg-sky-50"
              onClick={() => setMenuOpen(true)}
              aria-label="بازکردن منو"
            >
              <Menu className="size-5" />
            </Button>

            <Link href="/" className="flex items-center gap-3 text-right">
              <Logo branding={branding} />
              <div>
                <p className="font-black text-slate-900">
                  {branding.site_name}
                </p>
                <p className="hidden text-[11px] text-slate-500 sm:block">
                  {branding.short_description}
                </p>
              </div>
            </Link>
          </div>

          <div className="flex items-center gap-2">
            <Link
              href="/advisors"
              className="hidden whitespace-nowrap px-2 text-xs font-bold text-blue-700 transition hover:text-blue-600 lg:block"
            >
              لیست مشاوران
            </Link>
            <ArticleDropdown compact />
            <Link
              href="/app/laws"
              className="hidden whitespace-nowrap px-2 text-xs font-bold text-slate-600 transition hover:text-blue-600 xl:block"
            >
              قوانین مالیاتی
            </Link>
            <Link
              href="/pricing"
              className="hidden whitespace-nowrap px-2 text-xs font-bold text-slate-600 transition hover:text-blue-600 xl:block"
            >
              تعرفه‌ها
            </Link>
            <Link
              href="/about"
              className="hidden whitespace-nowrap px-2 text-xs font-bold text-slate-600 transition hover:text-blue-600 xl:block"
            >
              درباره ما
            </Link>
            <Link
              href="/contact"
              className="hidden whitespace-nowrap px-2 text-xs font-bold text-slate-600 transition hover:text-blue-600 xl:block"
            >
              تماس
            </Link>

            <button
              type="button"
              onClick={() => openProtectedPage("/app/profile")}
              className="flex items-center gap-2 rounded-2xl border border-sky-100 bg-white p-1.5 pl-3 shadow-sm transition hover:border-sky-200 hover:shadow-md"
            >
              <Avatar className="size-9">
                <AvatarFallback className="bg-gradient-to-br from-amber-300 to-orange-400 text-slate-900">
                  {user.full_name.slice(0, 1)}
                </AvatarFallback>
              </Avatar>

              <div className="hidden text-right md:block">
                <p className="max-w-32 truncate text-xs font-bold">
                  {user.full_name}
                </p>
                <p className="text-[10px] text-blue-600">
                  پلن {tierLabels[user.account_tier]}
                </p>
              </div>
            </button>
          </div>
        </div>
      </header>

      <div
        className={cn(
          "fixed inset-0 z-50 transition-[visibility] duration-300",
          menuOpen ? "visible" : "invisible",
        )}
      >
        <button
          type="button"
          aria-label="بستن منو"
          onClick={() => setMenuOpen(false)}
          className={cn(
            "absolute inset-0 bg-slate-950/35 backdrop-blur-[2px] transition-opacity duration-300",
            menuOpen ? "opacity-100" : "opacity-0",
          )}
        />

        <aside
          className={cn(
            "absolute right-0 top-0 flex h-full w-[min(90vw,380px)] flex-col overflow-hidden rounded-l-[2rem] border-l border-sky-100 bg-white shadow-2xl shadow-slate-950/20 transition-transform duration-300 ease-out",
            menuOpen ? "translate-x-0" : "translate-x-full",
          )}
        >
          <div className="border-b border-sky-100 bg-gradient-to-l from-sky-50 via-white to-white p-5">
            <div className="flex items-center justify-between">
              <Brand
                branding={branding}
                subtitle="دسترسی سریع به خدمات"
                compact
              />

              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="rounded-xl text-slate-500 hover:bg-white hover:text-slate-900"
                onClick={() => setMenuOpen(false)}
                aria-label="بستن منو"
              >
                <X />
              </Button>
            </div>

            {!profileCompleted && (
              <button
                type="button"
                onClick={() => openProtectedPage("/app/profile")}
                className="mt-5 flex w-full items-center gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-3 text-right transition hover:bg-amber-100"
              >
                <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-white text-amber-600 shadow-sm">
                  <LockKeyhole className="size-5" />
                </span>
                <span>
                  <span className="block text-sm font-black text-amber-900">
                    تکمیل پروفایل
                  </span>
                  <span className="mt-0.5 block text-xs leading-5 text-amber-700">
                    برای فعال‌شدن همه امکانات، اطلاعات ضروری را تکمیل کنید.
                  </span>
                </span>
              </button>
            )}
          </div>

          <nav className="min-h-0 flex-1 overflow-y-auto p-4 [scrollbar-width:thin]">
            <p className="mb-3 px-2 text-[11px] font-bold text-slate-400">
              منوی کاربری
            </p>

            <div className="grid gap-1.5">
              {navigation.map((item) => {
                const active =
                  pathname === item.href ||
                  pathname.startsWith(`${item.href}/`);

                const locked =
                  !profileCompleted && item.href !== "/app/profile";

                return (
                  <button
                    type="button"
                    onClick={() => openProtectedPage(item.href)}
                    key={item.href}
                    className={cn(
                      "group flex min-h-13 w-full items-center gap-3 rounded-2xl px-3.5 py-3 text-right text-sm transition",
                      active
                        ? "bg-gradient-to-l from-blue-600 to-cyan-500 font-bold text-white shadow-lg shadow-blue-600/20"
                        : "text-slate-600 hover:bg-sky-50 hover:text-blue-700",
                    )}
                  >
                    <span
                      className={cn(
                        "flex size-9 shrink-0 items-center justify-center rounded-xl transition",
                        active
                          ? "bg-white/15 text-white"
                          : "bg-slate-50 text-slate-500 group-hover:bg-white group-hover:text-blue-600",
                      )}
                    >
                      <item.icon className="size-4.5" />
                    </span>

                    <span className="min-w-0 flex-1">{item.label}</span>

                    {locked && (
                      <LockKeyhole
                        className={cn(
                          "size-3.5 shrink-0",
                          active ? "text-white/80" : "text-slate-300",
                        )}
                      />
                    )}
                  </button>
                );
              })}
            </div>

            <p className="mb-3 mt-6 px-2 text-[11px] font-bold text-slate-400">
              لینک‌های سایت
            </p>
            <div className="grid grid-cols-2 gap-2">
              {publicNavigation.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setMenuOpen(false)}
                  className="flex min-h-11 items-center gap-2 rounded-xl border border-sky-100 bg-sky-50/60 px-3 py-2 text-xs font-bold text-slate-600 transition hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700"
                >
                  <item.icon className="size-4 shrink-0" />
                  <span>{item.label}</span>
                </Link>
              ))}
            </div>
          </nav>

          <div className="border-t border-sky-100 bg-slate-50/70 p-4">
            <div className="flex items-center gap-3 rounded-2xl bg-white p-3 shadow-sm">
              <Avatar>
                <AvatarFallback className="bg-amber-300 text-blue-950">
                  {user.full_name.slice(0, 1)}
                </AvatarFallback>
              </Avatar>

              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-bold text-slate-900">
                  {user.full_name}
                </p>
                <p className="mt-0.5 text-xs text-slate-500">
                  پلن اشتراک {tierLabels[user.account_tier]}
                </p>
              </div>

              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="rounded-xl text-slate-500 hover:bg-red-50 hover:text-red-600"
                onClick={logout}
                title="خروج"
              >
                <LogOut />
              </Button>
            </div>
          </div>
        </aside>
      </div>

      {profileNoticeOpen && (
        <div className="fixed inset-0 z-[70] flex items-center justify-center p-4">
          <button
            type="button"
            aria-label="بستن پیام"
            onClick={() => setProfileNoticeOpen(false)}
            className="absolute inset-0 bg-slate-950/45 backdrop-blur-sm"
          />

          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="profile-required-title"
            className="relative w-full max-w-md overflow-hidden rounded-[2rem] border border-white/70 bg-white shadow-2xl"
          >
            <div className="bg-gradient-to-l from-amber-50 via-white to-white p-6">
              <span className="flex size-14 items-center justify-center rounded-2xl bg-amber-100 text-amber-600">
                <LockKeyhole className="size-7" />
              </span>

              <h2
                id="profile-required-title"
                className="mt-5 text-xl font-black text-slate-900"
              >
                ابتدا پروفایل خود را تکمیل کنید
              </h2>

              <p className="mt-3 text-sm leading-7 text-slate-600">
                برای استفاده از این بخش، لازم است اطلاعات ضروری پروفایل خود را
                تکمیل و ذخیره کنید. پس از تکمیل پروفایل، همه امکانات حساب شما
                فعال می‌شود.
              </p>
            </div>

            <div className="flex flex-col-reverse gap-2 border-t border-slate-100 p-4 sm:flex-row">
              <Button
                type="button"
                variant="outline"
                className="flex-1 rounded-xl"
                onClick={() => setProfileNoticeOpen(false)}
              >
                فعلاً نه
              </Button>

              <Button
                type="button"
                className="flex-1 rounded-xl bg-blue-600 hover:bg-blue-700"
                onClick={() => {
                  setProfileNoticeOpen(false);
                  router.push("/app/profile");
                }}
              >
                تکمیل پروفایل
              </Button>
            </div>
          </div>
        </div>
      )}

      <main className="mx-auto min-h-[70vh] max-w-7xl px-4 py-7 sm:px-6 sm:py-10">
        {children}
      </main>

      <UserFooter branding={branding} />
      <ContactStrip branding={branding} />
    </div>
  );
}

function UserFooter({ branding }: { branding: Branding }) {
  return (
    <footer
      id="contact"
      className="mt-12 scroll-mt-24 border-t border-sky-100 bg-white"
    >
      <div className="mx-auto grid max-w-7xl gap-10 px-5 py-12 md:grid-cols-[1.3fr_.7fr_1fr]">
        <div>
          <Brand
            branding={branding}
            subtitle={branding.short_description}
            compact
          />

          {(branding.office_address ||
            branding.working_hours ||
            branding.support_email) && (
            <div className="mt-4 space-y-1 text-xs leading-6 text-slate-500">
              {branding.legal_name && (
                <p className="font-bold text-slate-700">
                  {branding.legal_name}
                </p>
              )}
              {branding.office_address && <p>{branding.office_address}</p>}
              {branding.working_hours && (
                <p>ساعات پاسخ‌گویی: {branding.working_hours}</p>
              )}
              {branding.support_email && (
                <a
                  className="block text-blue-600"
                  href={`mailto:${branding.support_email}`}
                  dir="ltr"
                >
                  {branding.support_email}
                </a>
              )}
            </div>
          )}

          <div className="group relative mt-5 w-fit">
            <button
              type="button"
              className="flex items-center gap-2 rounded-xl bg-sky-50 px-3 py-2 text-sm font-bold text-blue-700"
            >
              <ContactRound className="size-4" />
              درباره ما
            </button>

            <div className="invisible absolute bottom-[calc(100%+10px)] right-0 z-20 w-72 translate-y-2 rounded-2xl border border-sky-100 bg-white p-4 opacity-0 shadow-2xl transition group-hover:visible group-hover:translate-y-0 group-hover:opacity-100 group-focus-within:visible group-focus-within:translate-y-0 group-focus-within:opacity-100">
              <p className="text-xs leading-6 text-slate-500">
                چکاه برای ساده‌کردن امور مالیاتی، دسترسی به ابزارها و ارتباط
                سریع با کارشناسان ساخته شده است.
              </p>

              <div className="mt-4 flex gap-2">
                <ContactLinks branding={branding} />
              </div>
            </div>
          </div>

          <p className="mt-4 max-w-md text-sm leading-7 text-slate-500">
            دسترسی ساده به ابزارهای مالیاتی، بانک دانش، پیگیری پرونده و ارتباط
            با کارشناسان در یک محیط امن و یکپارچه.
          </p>
        </div>

        <div>
          <p className="font-bold">دسترسی سریع</p>

          <div className="mt-4 grid gap-3 text-sm text-slate-500">
            <Link href="/app/plans">پلن‌های اشتراک</Link>

            <Link href="/app/tickets">مرکز پشتیبانی</Link>

            <Link href="/app/security">امنیت حساب</Link>
          </div>
        </div>

        <div>
          <p className="font-bold">اعتماد و شفافیت</p>

          <div className="mt-4 grid grid-cols-3 gap-2">
            <Trust icon={ShieldCheck} label="حفاظت داده" />

            <Trust icon={Scale} label="پاسخ مستند" />

            <Trust icon={ContactRound} label="پشتیبانی" />
          </div>

          <p className="mt-3 text-[11px] leading-5 text-slate-400">
            جایگاه نمایش مجوزها و نمادهای رسمی پس از دریافت و تأیید نهایی.
          </p>
        </div>
      </div>

      <div className="border-t border-sky-50 px-5 py-5 text-center text-xs text-slate-400">
        © {new Date().getFullYear()} {branding.site_name}؛ همه حقوق محفوظ است.
      </div>
    </footer>
  );
}

function SocialLink({
  icon: Icon,
  label,
  href,
  color,
}: {
  icon: typeof Camera;
  label: string;
  href: string;
  color: string;
}) {
  return href ? (
    <a
      href={href}
      target={href.startsWith("http") ? "_blank" : undefined}
      rel={href.startsWith("http") ? "noreferrer" : undefined}
      aria-label={label}
      title={label}
      className={`flex size-10 items-center justify-center rounded-xl border border-slate-100 text-slate-500 transition ${color}`}
    >
      <Icon className="size-5" />
    </a>
  ) : (
    <span
      aria-label={`${label} ثبت نشده`}
      title={`${label} هنوز ثبت نشده است`}
      className="flex size-10 cursor-not-allowed items-center justify-center rounded-xl border border-slate-100 text-slate-300"
    >
      <Icon className="size-5" />
    </span>
  );
}

function ContactLinks({ branding }: { branding: Branding }) {
  return (
    <>
      <SocialLink
        icon={Camera}
        label="اینستاگرام"
        href={branding.instagram_url}
        color="hover:bg-rose-50 hover:text-rose-600"
      />

      <SocialLink
        icon={MessageCircle}
        label="واتساپ"
        href={branding.whatsapp_url}
        color="hover:bg-emerald-50 hover:text-emerald-600"
      />

      <SocialLink
        icon={Send}
        label="تلگرام"
        href={branding.telegram_url}
        color="hover:bg-sky-50 hover:text-sky-600"
      />

      <SocialLink
        icon={Phone}
        label="تماس تلفنی"
        href={
          branding.support_phone || branding.support_mobile
            ? `tel:${branding.support_phone || branding.support_mobile}`
            : ""
        }
        color="hover:bg-amber-50 hover:text-amber-600"
      />
    </>
  );
}

function ContactStrip({ branding }: { branding: Branding }) {
  return (
    <section
      id="contact-links"
      className="border-t border-sky-100 bg-sky-50/70"
    >
      <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-5 px-5 py-7 sm:flex-row">
        <div>
          <p className="text-sm font-black text-slate-900">ارتباط با ما</p>

          <p className="mt-1 text-xs text-slate-500">
            برای پرسش، پیگیری یا دریافت راهنمایی با چکاه در ارتباط باشید.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <ContactLinks branding={branding} />
        </div>
      </div>
    </section>
  );
}

function Trust({
  icon: Icon,
  label,
}: {
  icon: typeof ShieldCheck;
  label: string;
}) {
  return (
    <div className="flex min-h-24 flex-col items-center justify-center rounded-2xl border border-sky-100 bg-sky-50/70 p-2 text-center">
      <Icon className="mb-2 size-6 text-blue-600" />
      <span className="text-[10px] text-slate-600">{label}</span>
    </div>
  );
}

function NavigationLink({
  item,
  active,
}: {
  item: {
    href: string;
    label: string;
    icon: typeof LayoutDashboard;
  };
  active: boolean;
}) {
  return (
    <Link
      href={item.href}
      className={cn(
        "flex items-center gap-3 rounded-xl px-3 py-3 text-sm transition",
        active
          ? "bg-white text-blue-700 shadow-lg shadow-blue-950/20"
          : "text-blue-50 hover:bg-white/15 hover:text-white",
      )}
    >
      <item.icon className="size-4.5" />
      <span>{item.label}</span>
    </Link>
  );
}

function isNavigationActive(pathname: string, href: string) {
  const isPanelRoot = ["/management", "/support", "/consultant"].includes(href);

  return pathname === href || (!isPanelRoot && pathname.startsWith(`${href}/`));
}

function Logo({
  branding,
}: {
  branding: {
    logo_url: string;
  };
}) {
  return (
    <div
      className="flex size-11 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-600 to-cyan-500 text-white shadow-lg shadow-blue-600/20"
      style={
        branding.logo_url
          ? {
              backgroundImage: `url(${branding.logo_url})`,
              backgroundPosition: "center",
              backgroundRepeat: "no-repeat",
              backgroundSize: "contain",
            }
          : undefined
      }
    >
      {branding.logo_url ? null : <Scale />}
    </div>
  );
}

function Brand({
  branding,
  subtitle,
  compact = false,
}: {
  branding: {
    site_name: string;
    logo_url: string;
  };
  subtitle: string;
  compact?: boolean;
}) {
  return (
    <Link
      href="/"
      aria-label="رفتن به صفحه اصلی"
      className={cn("flex items-center gap-3", compact ? "" : "mb-8 px-2")}
    >
      <Logo branding={branding} />

      <div>
        <p className="font-bold">{branding.site_name}</p>

        <p className="text-xs opacity-70">{subtitle}</p>
      </div>
    </Link>
  );
}

function Account({
  user,
  role,
  logout,
}: {
  user: User;
  role: string;
  logout: () => void;
}) {
  return (
    <div className="mt-5 rounded-2xl border border-white/25 bg-white/15 p-4">
      <div className="flex items-center gap-3">
        <Avatar>
          <AvatarFallback className="bg-amber-300 text-blue-950">
            {user.full_name.slice(0, 1)}
          </AvatarFallback>
        </Avatar>

        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold text-white">
            {user.full_name}
          </p>

          <Badge variant="secondary" className="mt-1 text-[10px]">
            {roleLabels[role]}
          </Badge>
        </div>

        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="text-white hover:bg-white/15"
          onClick={logout}
        >
          <LogOut />
        </Button>
      </div>
    </div>
  );
}
