import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { backendUrl, clearAuthCookies, refreshCookie } from "@/lib/backend";

export async function POST() {
  const store = await cookies();
  const refreshToken = store.get(refreshCookie)?.value;
  if (refreshToken) {
    await fetch(`${backendUrl}/auth/logout`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    }).catch(() => null);
  }
  const response = NextResponse.json({ ok: true });
  clearAuthCookies(response);
  return response;
}
