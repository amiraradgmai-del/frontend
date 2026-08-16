"use client";

import Script from "next/script";
import { useCallback, useEffect, useId, useRef, useState } from "react";

type TurnstileApi = {
  render: (element: HTMLElement, options: Record<string, unknown>) => string;
  remove: (widgetId: string) => void;
};

declare global {
  interface Window { turnstile?: TurnstileApi; }
}

type Config = { enabled: boolean; site_key: string | null };

export function TurnstileCaptcha({ onToken, onConfigured, resetKey = 0 }: {
  onToken: (token: string) => void;
  onConfigured?: (required: boolean) => void;
  resetKey?: number;
}) {
  const elementId = `turnstile-${useId().replace(/:/g, "")}`;
  const container = useRef<HTMLDivElement>(null);
  const widgetId = useRef<string | null>(null);
  const [config, setConfig] = useState<Config | null>(null);
  const [scriptReady, setScriptReady] = useState(false);

  useEffect(() => {
    fetch("/api/backend/auth/captcha/config", { cache: "no-store" })
      .then((response) => response.ok ? response.json() : { enabled: false, site_key: null })
      .then((value: Config) => { setConfig(value); onConfigured?.(value.enabled); })
      .catch(() => { setConfig({ enabled: false, site_key: null }); onConfigured?.(false); });
  }, [onConfigured]);

  const renderWidget = useCallback(() => {
    if (!config?.enabled || !config.site_key || !container.current || !window.turnstile || widgetId.current) return;
    widgetId.current = window.turnstile.render(container.current, {
      sitekey: config.site_key,
      language: "fa",
      theme: "light",
      callback: (token: string) => onToken(token),
      "expired-callback": () => onToken(""),
      "error-callback": () => onToken(""),
    });
  }, [config, onToken]);

  useEffect(() => {
    if (scriptReady) renderWidget();
    return () => {
      if (widgetId.current && window.turnstile) window.turnstile.remove(widgetId.current);
      widgetId.current = null;
    };
  }, [scriptReady, renderWidget, resetKey]);

  if (!config?.enabled) return null;
  return <>
    <Script src="https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit" strategy="afterInteractive" onLoad={() => setScriptReady(true)} />
    <div id={elementId} ref={container} className="flex min-h-16 items-center justify-center" aria-label="تأیید امنیتی" />
  </>;
}
