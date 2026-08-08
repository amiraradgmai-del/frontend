import { NextResponse } from "next/server";
import { backendUrl, setAuthCookies } from "@/lib/backend";

export async function POST(request: Request) {
  try {
    const response = await fetch(`${backendUrl}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: await request.text(),
      cache: "no-store",
    });
    const payload = await response.json();
    if (!response.ok) return NextResponse.json(payload, { status: response.status });
    const result = NextResponse.json({ ok: true });
    setAuthCookies(result, payload);
    return result;
  } catch {
    return NextResponse.json({ detail: "Authentication service unavailable" }, { status: 503 });
  }
}
