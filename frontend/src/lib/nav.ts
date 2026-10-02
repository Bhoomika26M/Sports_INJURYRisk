/** Only allow same-site relative redirects after login (blocks open-redirect via ?next=). */
export function safeNext(next: string | null | undefined, fallback = "/dashboard"): string {
  if (!next) return fallback;
  if (!next.startsWith("/") || next.startsWith("//") || next.startsWith("/\\")) return fallback;
  if (next.startsWith("/login") || next.startsWith("/register")) return fallback;
  return next;
}
