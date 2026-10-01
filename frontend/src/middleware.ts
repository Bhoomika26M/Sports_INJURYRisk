import { NextRequest, NextResponse } from "next/server";

export function middleware(request: NextRequest) {
  // The backend's refresh_token cookie is httpOnly and scoped to /api/v1/auth, so the browser never sends
  // it to these page routes (previously every login bounced straight back to /login). The frontend sets a
  // non-secret presence flag instead; the API remains the real authorisation boundary.
  const hasSession = request.cookies.get("session_active");

  // Protect all authenticated routes
  if (
    request.nextUrl.pathname.startsWith("/dashboard") ||
    request.nextUrl.pathname.startsWith("/athletes") ||
    request.nextUrl.pathname.startsWith("/videos") ||
    request.nextUrl.pathname.startsWith("/notifications") ||
    request.nextUrl.pathname.startsWith("/reports")
  ) {
    if (!hasSession) {
      return NextResponse.redirect(new URL("/login", request.url));
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/dashboard/:path*", "/athletes/:path*", "/videos/:path*", "/notifications/:path*", "/reports/:path*"],
};
