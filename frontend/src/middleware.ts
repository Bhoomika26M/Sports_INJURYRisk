import { NextRequest, NextResponse } from "next/server";
import { SESSION_HINT_COOKIE } from "@/lib/session";

/**
 * Keeps signed-out visitors away from app pages without a flash of protected UI.
 *
 * NOTE: this reads a non-secret `session_hint` cookie, not the refresh token. The
 * backend scopes the httpOnly refresh cookie to /api/v1/auth, so the browser never
 * sends it to page routes — checking it here would redirect *everyone* to /login.
 * Real authentication is enforced by the API on every request; a stale hint is
 * caught by the client-side guard in AppShell.
 */
export function middleware(request: NextRequest) {
  if (!request.cookies.get(SESSION_HINT_COOKIE)) {
    const url = new URL("/login", request.url);
    const target = request.nextUrl.pathname + request.nextUrl.search;
    if (target !== "/dashboard") url.searchParams.set("next", target);
    return NextResponse.redirect(url);
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/dashboard/:path*", "/athletes/:path*", "/videos/:path*", "/notifications/:path*", "/reports/:path*"],
};
