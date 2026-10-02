/**
 * Session hint cookie.
 *
 * The real credential is the httpOnly refresh cookie, which the backend scopes to
 * `path=/api/v1/auth`. Browsers therefore never send it to page routes like
 * `/dashboard`, so Next's middleware can't see it. This is a NON-secret
 * "probably signed in" flag the middleware can read to avoid flashing protected
 * pages to signed-out visitors. It carries no token and grants no access: the API
 * still enforces auth on every call, and the client-side guard handles stale hints.
 */
const HINT_COOKIE = "session_hint";
const SEVEN_DAYS = 7 * 24 * 60 * 60;

export function setSessionHint(active: boolean): void {
  if (typeof document === "undefined") return;
  document.cookie = active
    ? `${HINT_COOKIE}=1; path=/; max-age=${SEVEN_DAYS}; samesite=lax`
    : `${HINT_COOKIE}=; path=/; max-age=0; samesite=lax`;
}

export function hasSessionHint(): boolean {
  if (typeof document === "undefined") return false;
  return document.cookie.split("; ").some((c) => c.startsWith(`${HINT_COOKIE}=1`));
}

export const SESSION_HINT_COOKIE = HINT_COOKIE;
