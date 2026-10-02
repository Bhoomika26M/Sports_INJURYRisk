// A NON-SECRET presence flag ("1") that lets Next.js middleware (which can only see cookies for the
// frontend origin) route-gate pages. It is not a token and grants nothing: every API call is still
// authorised by the access token, and the real session is the backend's httpOnly refresh cookie,
// which JavaScript never reads. See docs/DECISIONS.md (2026-10-02, middleware session hint).
export const SESSION_HINT_COOKIE = "session_active";
const MAX_AGE_SECONDS = 7 * 24 * 60 * 60;

export function setSessionHint(): void {
  if (typeof document === "undefined") return;
  const secure = window.location.protocol === "https:" ? "; Secure" : "";
  document.cookie = `${SESSION_HINT_COOKIE}=1; Path=/; Max-Age=${MAX_AGE_SECONDS}; SameSite=Lax${secure}`;
}

export function clearSessionHint(): void {
  if (typeof document === "undefined") return;
  document.cookie = `${SESSION_HINT_COOKIE}=; Path=/; Max-Age=0; SameSite=Lax`;
}
