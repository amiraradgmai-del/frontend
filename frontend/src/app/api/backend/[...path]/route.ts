import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import {
  accessCookie,
  backendUrl,
  clearAuthCookies,
  refreshCookie,
  setAuthCookies,
} from "@/lib/backend";

type Context = { params: Promise<{ path: string[] }> };

const mutatingMethods = new Set(["POST", "PUT", "PATCH", "DELETE"]);

function isCrossSiteRequest(request: Request) {
  if (!mutatingMethods.has(request.method)) return false;
  if (request.headers.get("sec-fetch-site") === "cross-site") return true;
  const origin = request.headers.get("origin");
  if (!origin) return false;
  const requestUrl = new URL(request.url);
  const originUrl = new URL(origin);
  const allowedHosts = new Set(
    [
      requestUrl.host,
      request.headers.get("host"),
      ...(request.headers.get("x-forwarded-host") ?? "").split(","),
      new URL(
        process.env.NEXT_PUBLIC_SITE_URL ?? requestUrl.origin,
      ).host,
    ]
      .filter(Boolean)
      .map((host) => host!.trim().toLowerCase()),
  );
  return !allowedHosts.has(originUrl.host.toLowerCase());
}

async function proxy(request: Request, context: Context) {
  if (isCrossSiteRequest(request)) {
    return NextResponse.json(
      { detail: "Cross-site request rejected" },
      { status: 403 },
    );
  }
  const { path } = await context.params;
  const store = await cookies();
  const target = `${backendUrl}/${path.join("/")}${new URL(request.url).search}`;
  const body = ["GET", "HEAD"].includes(request.method)
    ? undefined
    : await request.arrayBuffer();

  const send = (token?: string) =>
    fetch(target, {
      method: request.method,
      headers: {
        ...(request.headers.get("content-type")
          ? { "Content-Type": request.headers.get("content-type")! }
          : {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(request.headers.get("accept")
          ? { Accept: request.headers.get("accept")! }
          : {}),
        ...(request.headers.get("x-request-id")
          ? { "X-Request-ID": request.headers.get("x-request-id")! }
          : {}),
      },
      body,
      cache: "no-store",
    });

  let upstream = await send(store.get(accessCookie)?.value);
  let refreshedTokens: {
    access_token: string;
    refresh_token: string;
    expires_in: number;
  } | null = null;

  if (upstream.status === 401 && store.get(refreshCookie)?.value) {
    const refresh = await fetch(`${backendUrl}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: store.get(refreshCookie)!.value }),
      cache: "no-store",
    });
    if (refresh.ok) {
      refreshedTokens = await refresh.json();
      upstream = await send(refreshedTokens!.access_token);
    }
  }

  const forwardedHeaders = new Headers();
  for (const name of [
    "content-type",
    "content-disposition",
    "content-length",
    "retry-after",
    "x-request-id",
    "location",
  ]) {
    const value = upstream.headers.get(name);
    if (value) forwardedHeaders.set(name, value);
  }
  if (!forwardedHeaders.has("content-type")) {
    forwardedHeaders.set("content-type", "application/json");
  }

  const response = new NextResponse(upstream.body, {
    status: upstream.status,
    headers: forwardedHeaders,
  });
  if (refreshedTokens) setAuthCookies(response, refreshedTokens);
  if (upstream.status === 401) clearAuthCookies(response);
  return response;
}

export const GET = proxy;
export const POST = proxy;
export const PATCH = proxy;
export const PUT = proxy;
export const DELETE = proxy;
