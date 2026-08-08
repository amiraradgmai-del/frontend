import { NextResponse } from "next/server";

export const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";
export const accessCookie = "tax_ai_access";
export const refreshCookie = "tax_ai_refresh";

export function setAuthCookies(
  response: NextResponse,
  tokens: { access_token: string; refresh_token: string; expires_in: number },
) {
  const secure = process.env.AUTH_COOKIE_SECURE
    ? process.env.AUTH_COOKIE_SECURE === "true"
    : process.env.NODE_ENV === "production";
  response.cookies.set(accessCookie, tokens.access_token, {
    httpOnly: true,
    sameSite: "lax",
    secure,
    path: "/",
    maxAge: tokens.expires_in,
  });
  response.cookies.set(refreshCookie, tokens.refresh_token, {
    httpOnly: true,
    sameSite: "strict",
    secure,
    path: "/",
    maxAge: 60 * 60 * 24 * 30,
  });
}

export function clearAuthCookies(response: NextResponse) {
  response.cookies.delete(accessCookie);
  response.cookies.delete(refreshCookie);
}
