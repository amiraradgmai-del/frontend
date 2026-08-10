"use client";

import Link from "next/link";
import { createContext, useContext, useEffect, useState } from "react";

type SiteConfiguration = {
    theme: {
      primary_color: string;
      accent_color: string;
      background_color: string;
      font_family: string;
      border_radius: number;
    };
    branding: { site_name: string; short_description: string; logo_url: string; support_email: string; support_phone: string; support_mobile: string; office_address: string; working_hours: string; legal_name: string; map_url: string; instagram_url: string; whatsapp_url: string; telegram_url: string };
    features: { maintenance_mode: boolean; registration_enabled: boolean; chatbot_enabled: boolean; consultations_enabled: boolean };
};

type PublicConfig = { configuration: SiteConfiguration };

const defaultConfiguration: SiteConfiguration = {
  theme: { primary_color: "#2563eb", accent_color: "#f97316", background_color: "#fffaf5", font_family: "Vazirmatn", border_radius: 14 },
  branding: { site_name: "چکاه", short_description: "دستیار هوشمند مالیاتی", logo_url: "/brand/chakah-logo.png", support_email: "", support_phone: "", support_mobile: "", office_address: "", working_hours: "", legal_name: "", map_url: "", instagram_url: "", whatsapp_url: "", telegram_url: "" },
  features: { maintenance_mode: false, registration_enabled: true, chatbot_enabled: true, consultations_enabled: true },
};

const SiteConfigurationContext = createContext(defaultConfiguration);

export function applyTheme(theme: PublicConfig["configuration"]["theme"]) {
  const root = document.documentElement;
  root.style.setProperty("--primary", theme.primary_color);
  root.style.setProperty("--accent", theme.accent_color);
  root.style.setProperty("--background", theme.background_color);
  root.style.setProperty("--radius", `${theme.border_radius / 16}rem`);
  document.body.style.fontFamily = `"${theme.font_family}", Vazirmatn, Tahoma, Arial, sans-serif`;
}

export function SiteThemeProvider({ children }: { children: React.ReactNode }) {
  const [configuration, setConfiguration] = useState(defaultConfiguration);
  useEffect(() => {
    fetch("/api/backend/api/v1/site/config", { cache: "no-store" })
      .then((response) => response.ok ? response.json() as Promise<PublicConfig> : null)
      .then((payload) => { if (payload) { applyTheme(payload.configuration.theme); setConfiguration({ ...defaultConfiguration, ...payload.configuration, branding: { ...defaultConfiguration.branding, ...payload.configuration.branding }, features: { ...defaultConfiguration.features, ...payload.configuration.features } }); } })
      .catch(() => undefined);
  }, []);

  return <SiteConfigurationContext.Provider value={configuration}>{configuration.features.maintenance_mode && <div className="sticky top-0 z-[100] bg-amber-400 px-4 py-2 text-center text-sm font-bold text-amber-950">سامانه در حالت نگهداری است؛ برخی قابلیت‌ها ممکن است موقتاً در دسترس نباشند.</div>}{children}</SiteConfigurationContext.Provider>;
}

export function useSiteConfiguration() {
  return useContext(SiteConfigurationContext);
}

export function SiteBrand({ management = false, showDescription = false }: { management?: boolean; showDescription?: boolean }) {
  const { branding } = useSiteConfiguration();
  return <Link href="/" className="flex items-center gap-3 font-black" aria-label="رفتن به صفحه اصلی"><span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-primary text-primary-foreground" style={branding.logo_url ? { backgroundImage: `url(${branding.logo_url})`, backgroundPosition: "center", backgroundRepeat: "no-repeat", backgroundSize: "contain" } : undefined}>{branding.logo_url ? null : "ت"}</span><span className="flex flex-col"><span>{management ? "مرکز مدیریت" : branding.site_name}</span>{showDescription && !management && <span className="mt-0.5 text-[11px] font-medium text-muted-foreground">{branding.short_description || "دستیار هوشمند مالیاتی"}</span>}</span></Link>;
}

export function ContactDetails() {
  const { branding } = useSiteConfiguration();
  return <div className="mt-3 space-y-1 text-sm text-muted-foreground">{branding.office_address && <p>{branding.office_address}</p>}{branding.working_hours && <p>{branding.working_hours}</p>}{branding.support_email && <p dir="ltr" className="text-left">{branding.support_email}</p>}{branding.support_phone && <p dir="ltr" className="text-left">{branding.support_phone}</p>}{branding.support_mobile && <p dir="ltr" className="text-left">{branding.support_mobile}</p>}{!branding.support_email && !branding.support_phone && !branding.support_mobile && <p>اطلاعات تماس هنوز توسط مدیر سامانه ثبت نشده است.</p>}</div>;
}
